"""Fenced publication and registration; uncertain files are read, never replayed."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import time
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from aat_metadata.models.etl import ETLDefinition, ETLDefinitionRevision
from aat_metadata.models.operations import DAGDeployment, Operation
from aat_metadata.models.authorizations import DataReplacementAuthorization
from aat_api.airflow_client.client import AirflowError
from aat_api.airflow_client.deployment import DeploymentClient
from aat_api.deployments import admission, factory, registration, storage
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import fence
from aat_api.services.etl_dependencies import lock_current as _lock_dependencies
from aat_api.services.etl_preview import preview
from aat_api.services.runtime_binding import airflow
from aat_api.services.table_preview import target_engine
from aat_etl.loaders.ledger import ensure_support


def _revalidate(identity):
    with transaction() as session:
        deployment = session.get(DAGDeployment, identity)
        revision = session.get(ETLDefinitionRevision, deployment.etl_revision_id)
        upload_id = revision.upload_id
    preview(upload_id)


def _uncertain(identity, operation, owner):
    with transaction() as session:
        fence(session, operation, owner)
        deployment = session.get(DAGDeployment, identity)
        if deployment.state=='DEPLOYED' and not deployment.reconcile_required:return 'SUCCEEDED'
        deployment.reconcile_required = True
    return 'NEEDS_RECONCILIATION'


def _failed(identity, operation, owner, *, parse_error=False):
    with transaction() as session:
        fence(session, operation, owner)
        deployment = session.get(DAGDeployment, identity)
        deployment.state = 'PARSE_ERROR' if parse_error else 'DEPLOYMENT_FAILED'
        deployment.reconcile_required = False
    return 'FAILED'


def _expected(session, deployment):
    original = session.get(Operation, deployment.operation_id)
    publication = original.progress_json.get('publications', {}).get(str(deployment.id))
    if not publication or not deployment.generated_file_key or not deployment.file_sha256:
        raise ValueError('PUBLICATION_EVIDENCE_MISSING')
    root = os.environ.get('AAT_AIRFLOW_DAGS_ROOT', '/opt/airflow/dags')
    return dict(dag_id=deployment.dag_id, owner_tag=deployment.expected_owner_tag,
                revision_id=str(deployment.etl_revision_id),
                revision_sha256=deployment.revision_sha256,
                fileloc=str(Path(root)/deployment.generated_file_key),
                published_at=publication['published_at'])


def _finalize(identity, operation, owner, evidence, preparation, client):
    _revalidate(identity)
    admission.assert_ready(preparation, client)
    with transaction() as session:
        fence(session, operation, owner)
        deployment, gate = admission._check_gate(session, preparation)
        if deployment.id != identity:
            raise ValueError('DEPLOYMENT_IDENTITY_CHANGED')
        revision = session.get(ETLDefinitionRevision, deployment.etl_revision_id)
        _lock_dependencies(session, revision.config_json)
        definition = session.get(ETLDefinition, revision.definition_id)
        deployment.state = 'DEPLOYED'
        deployment.parsed_at = registration.timestamp(evidence['parsed_at'])
        deployment.airflow_version_id = UUID(evidence['version_id'])
        deployment.airflow_version_number = evidence['version_number']
        deployment.last_verified_at = datetime.now(timezone.utc)
        deployment.reconcile_required = False
        revision.status = 'DEPLOYED'
        for authority in session.scalars(select(DataReplacementAuthorization).where(
                DataReplacementAuthorization.dag_id==deployment.dag_id,
                DataReplacementAuthorization.etl_revision_id!=revision.id,
                DataReplacementAuthorization.state.in_(['GRANTED','RESERVED']))
                .order_by(DataReplacementAuthorization.id).with_for_update()):
            authority.state = 'INVALIDATED'
            authority.invalidated_at = datetime.now(timezone.utc)
        definition.current_revision_id = revision.id
        definition.lifecycle = 'DEPLOYED'
        gate.gate_state = 'OPEN'
        gate.reason = None
    return 'SUCCEEDED'


def _one(identity, operation, owner, client, deadline):
    with transaction() as session:
        current = fence(session, operation, owner)
        deployment = session.get(DAGDeployment, identity)
        if deployment.state == 'DEPLOYED' and not deployment.reconcile_required:
            return 'SUCCEEDED'
        if deployment.state == 'DEPLOYMENT_PENDING' or deployment.reconcile_required:
            return 'NEEDS_RECONCILIATION'
        if deployment.state != 'READY_TO_DEPLOY':
            return 'FAILED'
        revision = session.get(ETLDefinitionRevision, deployment.etl_revision_id)
        config, revision_id, sha = revision.config_json, revision.id, revision.config_sha256
        consent = current.progress_json.get('support_objects_acknowledged') is True
    dispatched = False
    try:
        _revalidate(identity)
        if time.monotonic()>=deadline:raise APIError('DEADLINE_EXPIRED','Deployment deadline expired before publication.',409)
        prepared = admission.prepare(identity, client,
            airflow_dags_root=os.environ.get('AAT_AIRFLOW_DAGS_ROOT', '/opt/airflow/dags'))
        with transaction() as session:
            fence(session, operation, owner)
        # Only explicit persisted acknowledgment permits support object DDL.
        with target_engine(UUID(config['target']['connection_revision_id'])) as engine, engine.begin() as connection:
            ensure_support(connection, schema=config['target']['schema'], consent=consent)
        source = factory.render(config, revision_id=revision_id, revision_sha256=sha)
        admission.assert_ready(prepared, client)
        with transaction() as session:
            current = fence(session, operation, owner)
            deployment, _ = admission._check_gate(session, prepared)
            _lock_dependencies(session, config)
            previous = session.get(DAGDeployment, deployment.previous_deployment_id) if deployment.previous_deployment_id else None
            key = previous.generated_file_key if previous else str(uuid4())+'.py'
            UUID(key[:-3])
            deployment.generated_file_key = key
            deployment.file_sha256 = hashlib.sha256(source).hexdigest()
            deployment.previous_file_sha256 = previous.file_sha256 if previous else None
            deployment.state = 'DEPLOYMENT_PENDING'
            payload = dict(current.progress_json)
            publications = dict(payload.get('publications', {}))
            publications[str(identity)] = {'published_at': datetime.now(timezone.utc).isoformat()}
            payload['publications'] = publications
            current.progress_json = payload
        dispatched = True
        # No network I/O while these short locks fence revision/gate/lease against publication.
        with transaction() as session:
            fence(session, operation, owner)
            deployment, _ = admission._check_gate(session, prepared)
            artifact = storage.write(source, file_id=UUID(deployment.generated_file_key[:-3]))
            if artifact.key != deployment.generated_file_key or artifact.sha256 != deployment.file_sha256:
                raise ValueError('PUBLICATION_HASH_MISMATCH')
            expected = _expected(session, deployment)
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise registration.RegistrationTimeout('Deployment deadline exceeded.')
        evidence = registration.wait(expected, client, timeout=min(120, remaining))
        return _finalize(identity, operation, owner, evidence, prepared, client)
    except (registration.RegistrationTimeout, AirflowError, OSError, SQLAlchemyError):
        return _uncertain(identity, operation, owner) if dispatched else _failed(identity, operation, owner)
    except (APIError, ValueError) as error:
        if dispatched:
            if str(error) == 'REGISTRATION_PARSE_ERROR':
                return _failed(identity, operation, owner, parse_error=True)
            return _uncertain(identity, operation, owner)
        return _failed(identity, operation, owner)


def execute(operation, owner):
    with transaction() as session:
        current=fence(session, operation, owner)
        remaining=(current.deadline_at-datetime.now(timezone.utc)).total_seconds() if current.deadline_at else 120
        identities = list(session.scalars(select(DAGDeployment.id).where(
            DAGDeployment.operation_id == operation['id']).order_by(DAGDeployment.dag_id)))
    if not identities:
        return 'FAILED', 'DEPLOYMENT_NOT_FOUND'
    if remaining<=0:return 'FAILED','DEADLINE_EXPIRED'
    deadline = time.monotonic()+min(120,remaining)
    client = airflow()
    client = DeploymentClient(registration._DeadlineTransport(client.client, deadline))
    outcomes=[]
    for identity in identities:
        outcomes.append(_one(identity, operation, owner, client, deadline))
        with transaction() as session:
            current=fence(session,operation,owner)
            current.progress_json={**current.progress_json,'completed':len(outcomes),'total':len(identities)}
    if 'NEEDS_RECONCILIATION' in outcomes:
        return 'NEEDS_RECONCILIATION', 'DEPLOYMENT_UNCONFIRMED'
    if all(state == 'SUCCEEDED' for state in outcomes):
        return 'SUCCEEDED', None
    return ('PARTIALLY_SUCCEEDED' if 'SUCCEEDED' in outcomes else 'FAILED'), 'DEPLOYMENT_FAILED'


def reconcile(operation, owner):
    """Verify the same published bytes/version; never generate a new file or run."""
    identity = UUID(operation['progress_json']['deployment_id'])
    with transaction() as session:
        fence(session, operation, owner)
        deployment = session.get(DAGDeployment, identity)
        if deployment is None:
            return 'FAILED', 'DEPLOYMENT_NOT_FOUND'
        if deployment.state == 'DEPLOYED' and not deployment.reconcile_required:
            return 'SUCCEEDED', None
        original = session.scalar(select(Operation).where(Operation.id==deployment.operation_id).with_for_update())
        if original.state != 'NEEDS_RECONCILIATION' or deployment.state not in ('READY_TO_DEPLOY','DEPLOYMENT_PENDING'):
            return 'FAILED', 'DEPLOYMENT_NOT_RECONCILABLE'
        if deployment.state=='READY_TO_DEPLOY':
            if deployment.generated_file_key or deployment.file_sha256:
                return 'NEEDS_RECONCILIATION','PUBLICATION_EVIDENCE_INCONSISTENT'
            deployment.state='DEPLOYMENT_FAILED';deployment.reconcile_required=False
            session.flush()
            results=session.scalars(select(DAGDeployment).where(DAGDeployment.operation_id==original.id)).all()
            if not any(item.reconcile_required or item.state in ('READY_TO_DEPLOY','DEPLOYMENT_PENDING') for item in results):
                passed=sum(item.state=='DEPLOYED' for item in results)
                original.state='SUCCEEDED' if passed==len(results) else 'PARTIALLY_SUCCEEDED' if passed else 'FAILED'
                original.error_code=None if passed==len(results) else 'DEPLOYMENT_FAILED'
            return 'SUCCEEDED',None
        expected = _expected(session, deployment)
        key, sha = deployment.generated_file_key, deployment.file_sha256
        from aat_metadata.models.operations import AdmissionState
        gate = session.scalar(select(AdmissionState).where(AdmissionState.dag_id==deployment.dag_id))
        if gate is None or gate.deployment_id != identity or gate.gate_state != 'BLOCKED':
            return 'NEEDS_RECONCILIATION', 'DEPLOYMENT_GATE_CHANGED'
        prepared = admission.Preparation(identity, deployment.dag_id, deployment.etl_revision_id,
                                         gate.generation, deployment.previous_deployment_id is None,
                                         deployment.previous_paused)
        original_id = original.id
    try:
        # Filesystem roots and IDs are internal configuration, never public paths.
        root = Path(os.environ.get('AAT_DAGS_ROOT', '/data/generated_dags')).absolute()
        if root.resolve() != root or key != str(UUID(key[:-3]))+'.py':
            raise ValueError('PUBLICATION_PATH_INVALID')
        directory_fd = os.open(root, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            fd = os.open(key, os.O_RDONLY|os.O_NOFOLLOW, dir_fd=directory_fd)
            with os.fdopen(fd, 'rb') as source:
                actual = hashlib.file_digest(source, 'sha256').hexdigest()
        finally:
            os.close(directory_fd)
        if actual != sha:
            raise ValueError('PUBLICATION_HASH_MISMATCH')
        client = airflow()
        evidence = registration.wait(expected, client)
        _finalize(identity, operation, owner, evidence, prepared, client)
        with transaction() as session:
            fence(session, operation, owner)
            original = session.scalar(select(Operation).where(Operation.id==original_id).with_for_update())
            results = session.scalars(select(DAGDeployment).where(DAGDeployment.operation_id==original_id)).all()
            if not any(item.reconcile_required or item.state in ('READY_TO_DEPLOY','DEPLOYMENT_PENDING') for item in results):
                passed = sum(item.state=='DEPLOYED' for item in results)
                original.state = 'SUCCEEDED' if passed==len(results) else 'PARTIALLY_SUCCEEDED' if passed else 'FAILED'
                original.error_code = None if passed==len(results) else 'DEPLOYMENT_FAILED'
        return 'SUCCEEDED', None
    except (registration.RegistrationTimeout, AirflowError, OSError, SQLAlchemyError, APIError, ValueError):
        state=_uncertain(identity, operation, owner)
        return state,None if state=='SUCCEEDED' else 'DEPLOYMENT_UNCONFIRMED'
