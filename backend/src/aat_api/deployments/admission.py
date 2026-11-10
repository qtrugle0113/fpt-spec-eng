"""Close application admission before verified pause and drain; never cancel runs."""
from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID

from sqlalchemy import select
from aat_metadata.models.etl import ETLDefinition, ETLDefinitionRevision
from aat_metadata.models.operations import AdmissionState, DAGDeployment,Operation
from aat_metadata.models.runtime import ExecutionBinding
from aat_api.airflow_client.client import AirflowError
from aat_api.services.connections.service import transaction


@dataclass(frozen=True)
class Preparation:
    deployment_id: UUID
    dag_id: str
    revision_id: UUID
    generation: int
    is_new: bool
    previous_paused: bool | None


def _candidate(session, identity):
    deployment = session.get(DAGDeployment, identity)
    if deployment is None or deployment.state not in ('READY_TO_DEPLOY', 'DEPLOYMENT_PENDING'):
        raise ValueError('DEPLOYMENT_NOT_PENDING')
    revision = session.get(ETLDefinitionRevision, deployment.etl_revision_id)
    definition = session.scalar(select(ETLDefinition).where(
        ETLDefinition.id == revision.definition_id).with_for_update())
    if session.scalar(select(Operation.id).where(Operation.kind=='DAG_STATE',
            Operation.progress_json['dag_id'].astext==deployment.dag_id,
            Operation.state.in_(['QUEUED','RUNNING','NEEDS_RECONCILIATION'])).limit(1)):
        raise ValueError('DAG_STATE_COMMAND_UNRESOLVED')
    previous = (session.get(DAGDeployment, deployment.previous_deployment_id)
                if deployment.previous_deployment_id else None)
    expected_current = (previous.etl_revision_id if previous and previous.dag_id == deployment.dag_id
                        and previous.state == 'DEPLOYED' and not previous.reconcile_required else revision.id)
    if (definition.owner != 'aat' or definition.current_revision_id != expected_current
            or revision.status not in ('VALIDATED', 'DEPLOYED')
            or deployment.revision_sha256 != revision.config_sha256):
        raise ValueError('DEPLOYMENT_REVISION_CHANGED')
    return deployment, revision


def _check_gate(session, preparation):
    deployment, revision = _candidate(session, preparation.deployment_id)
    gate = session.scalar(select(AdmissionState).where(
        AdmissionState.dag_id == preparation.dag_id).with_for_update())
    if (gate is None or gate.gate_state != 'BLOCKED' or gate.generation != preparation.generation
            or gate.deployment_id != deployment.id or gate.etl_revision_id != revision.id):
        raise ValueError('DEPLOYMENT_GATE_CHANGED')
    if session.scalar(select(ExecutionBinding.id).where(
            ExecutionBinding.dag_id == preparation.dag_id,
            ExecutionBinding.commit_uncertain.is_(True)).limit(1)):
        raise ValueError('RUNTIME_RECONCILIATION_REQUIRED')
    return deployment, gate


def assert_ready(preparation: Preparation, airflow) -> None:
    """Recheck after I/O, including a second inventory immediately before publication."""
    if not preparation.is_new:
        runs = airflow.runs(preparation.dag_id)
        if any(run.get('state') not in ('success', 'failed') for run in runs):
            raise ValueError('DAG_RUNS_NOT_DRAINED')
        if airflow.dag(preparation.dag_id).get('is_paused') is not True:
            raise ValueError('DAG_PAUSE_NOT_CONFIRMED')
    with transaction() as session:
        _check_gate(session, preparation)


def prepare(deployment_id: UUID | str, airflow, *, airflow_dags_root: str = '/opt/airflow/dags') -> Preparation:
    identity = UUID(str(deployment_id))
    with transaction() as session:
        deployment, revision = _candidate(session, identity)
        gate = session.scalar(select(AdmissionState).where(
            AdmissionState.dag_id == deployment.dag_id).with_for_update())
        if gate is None:
            gate = AdmissionState(dag_id=deployment.dag_id)
            session.add(gate)
            session.flush()
        if gate.deployment_id != identity:
            gate.generation += 1
        gate.gate_state = 'BLOCKED'
        gate.reason = 'DEPLOYMENT_IN_PROGRESS'
        gate.deployment_id = identity
        gate.etl_revision_id = revision.id
        previous = (session.get(DAGDeployment, deployment.previous_deployment_id)
                    if deployment.previous_deployment_id else None)
        # Copy immutable expected ownership facts before leaving the short DB transaction.
        prior = (dict(state=previous.state, reconcile=previous.reconcile_required,
                      key=previous.generated_file_key, sha=previous.revision_sha256,
                      version=str(previous.airflow_version_id), number=previous.airflow_version_number,
                      owner=previous.expected_owner_tag, dag_id=previous.dag_id)
                 if previous else None)
        preparation = Preparation(identity, deployment.dag_id, revision.id, gate.generation, True, None)
    try:
        dag = airflow.dag(preparation.dag_id)
    except AirflowError as error:
        if error.status != 404:
            raise
        if prior is not None:
            raise ValueError('PREVIOUS_DAG_NOT_VERIFIABLE') from None
        assert_ready(preparation, airflow)
        return preparation
    # Tags alone do not authorize taking over an existing DAG: registry, exact
    # file location and the last verified Airflow version must all agree.
    if (prior is None or prior['state'] != 'DEPLOYED' or prior['reconcile'] or prior['owner'] != 'aat'
            or prior['dag_id'] != preparation.dag_id or not prior['key']):
        raise ValueError('EXTERNAL_DAG_CONFLICT')
    try:
        if PurePosixPath(prior['key']).name != prior['key'] or not prior['key'].endswith('.py'):
            raise ValueError()
        UUID(prior['key'][:-3])
    except (ValueError, TypeError, AttributeError):
        raise ValueError('DAG_ARTIFACT_IDENTITY_INVALID') from None
    tags = {tag.get('name') for tag in dag.get('tags', []) if isinstance(tag, dict)}
    expected_file = str(PurePosixPath(airflow_dags_root) / prior['key'])
    if (dag.get('dag_id') != preparation.dag_id or dag.get('fileloc') != expected_file
            or not {'aat', 'aat_revision:' + prior['sha']} <= tags
            or type(dag.get('is_paused')) is not bool):
        raise ValueError('DAG_OWNERSHIP_CHANGED')
    details = airflow.details(preparation.dag_id)
    version = details.get('latest_dag_version') or {}
    if str(version.get('id')) != prior['version'] or version.get('version_number') != prior['number']:
        raise ValueError('DAG_VERSION_CHANGED')
    paused = dag['is_paused']
    with transaction() as session:
        deployment, _ = _check_gate(session, preparation)
        if deployment.previous_paused is None:
            deployment.previous_paused = paused
        paused = deployment.previous_paused
    airflow.pause(preparation.dag_id, True)
    preparation = Preparation(identity, preparation.dag_id, preparation.revision_id,
                              preparation.generation, False, paused)
    assert_ready(preparation, airflow)
    return preparation
