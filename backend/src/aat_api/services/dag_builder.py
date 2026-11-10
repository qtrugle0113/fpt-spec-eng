"""Confirm a workbook atomically, retaining independent durable DAG results."""
from datetime import datetime,timedelta,timezone
from uuid import UUID
import os
from urllib.parse import quote,urlsplit
from sqlalchemy import select
from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
from aat_metadata.models.operations import DAGDeployment,Operation,AdmissionState,AuditEvent
from aat_api.errors import APIError
from aat_api.schemas.deployments import DeployRequest
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import digest,enqueue
from aat_api.services.etl_dependencies import lock_current
from aat_api.services.etl_preview import preview
from aat_api.services.replacement_authorizations import _scope,_existing
from aat_api.services.table_preview import signer


def create(value,key):
    value=DeployRequest.model_validate(value.model_dump())
    fingerprint=digest(value.model_dump(mode='json'))
    with transaction() as session:
        existing=_existing(session,'DAG_DEPLOY',key,fingerprint)
        if existing:return existing.id
    current=preview(value.upload_id)
    selected={item['config']['dag_id']:item for item in current['items'] if item['config']['dag_id'] in value.dag_ids}
    if set(selected)!=set(value.dag_ids):
        raise APIError('DAG_SELECTION_INVALID','Every selected DAG must belong to this validated workbook.',409)
    if not value.support_objects_acknowledged and any(item['support_ddl'] for item in selected.values()):
        raise APIError('SUPPORT_OBJECTS_ACKNOWLEDGMENT_REQUIRED','Review and acknowledge the support object DDL before deployment.',409)
    with transaction() as session:
        existing=_existing(session,'DAG_DEPLOY',key,fingerprint)
        if existing:return existing.id
        scope=_scope(session,value.upload_id)
        try:signer().verify(value.confirmation_token,scope)
        except ValueError:raise APIError('CONFIRMATION_STALE_OR_INVALID','Confirmation expired or dependencies changed. Preview again.',409) from None
        revisions=[]
        for dag_id in value.dag_ids:
            revision=session.get(ETLDefinitionRevision,UUID(selected[dag_id]['id']))
            if revision.upload_id!=value.upload_id or revision.status not in ('VALIDATED','DEPLOYED'):
                raise APIError('DEPENDENCY_CHANGED','A selected definition changed. Preview again.',409)
            lock_current(session,revision.config_json)
            busy=session.scalar(select(DAGDeployment.id).where(DAGDeployment.dag_id==dag_id,
                DAGDeployment.state.in_(['READY_TO_DEPLOY','DEPLOYMENT_PENDING'])).limit(1))
            if busy:raise APIError('DEPLOYMENT_BUSY','A selected DAG has a pending deployment or requires reconciliation.',409)
            revisions.append(revision)
        payload={'upload_id':str(value.upload_id),'dag_ids':value.dag_ids,
                 'support_objects_acknowledged':value.support_objects_acknowledged,'phase':'DEPLOYMENT',
                 'completed':0,'total':len(revisions)}
        operation,created=enqueue(session,'DAG_DEPLOY',key,payload,request_fingerprint=fingerprint)
        if not created:return operation.id
        results=[]
        for revision in revisions:
            definition=session.get(ETLDefinition,revision.definition_id)
            previous=session.scalar(select(DAGDeployment).where(DAGDeployment.dag_id==definition.dag_id,
                DAGDeployment.etl_revision_id==definition.current_revision_id,DAGDeployment.state=='DEPLOYED',
                DAGDeployment.reconcile_required.is_(False)).order_by(DAGDeployment.last_verified_at.desc().nullslast(),DAGDeployment.created_at.desc()).limit(1))
            result=DAGDeployment(operation_id=operation.id,etl_revision_id=revision.id,state='READY_TO_DEPLOY',
                revision_sha256=revision.config_sha256,previous_deployment_id=previous.id if previous else None)
            session.add(result);session.flush();results.append(result)
            session.add(AuditEvent(operation_id=operation.id,subject_type='ETLDefinition',subject_id=definition.id,
                action='DEPLOY',acknowledgment_scope={'revision_id':str(revision.id),'support_objects_acknowledged':value.support_objects_acknowledged},
                safe_summary='dag.deployment_requested'))
        payload['result_links']=['/api/v1/dag-deployments/'+str(row.id) for row in results]
        operation.progress_json=payload
        operation.result_ref=payload['result_links'][0]
        operation.deadline_at=datetime.now(timezone.utc)+timedelta(seconds=120)
        return operation.id


def detail(identity):
    with transaction() as session:
        deployment=session.get(DAGDeployment,identity)
        if deployment is None:raise APIError('DEPLOYMENT_NOT_FOUND','DAG deployment not found.',404)
        operation=session.get(Operation,deployment.operation_id)
        uncertain=deployment.reconcile_required or (deployment.state=='READY_TO_DEPLOY' and operation.state=='NEEDS_RECONCILIATION')
        gate=session.scalar(select(AdmissionState).where(AdmissionState.dag_id==deployment.dag_id))
        generation=gate.generation if gate and gate.deployment_id==deployment.id else None
        origin=os.environ.get('AAT_AIRFLOW_PUBLIC_URL','http://localhost:8080').rstrip('/')
        parsed=urlsplit(origin)
        if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise APIError('AIRFLOW_PUBLIC_URL_INVALID','The public Airflow address is not configured correctly.',503)
        result=dict(id=deployment.id,dag_id=deployment.dag_id,revision=str(deployment.etl_revision_id),
            airflow_url=origin+'/dags/'+quote(deployment.dag_id,safe=''),
            state=deployment.state,reconcile_required=uncertain,
            airflow_version_id=str(deployment.airflow_version_id) if deployment.airflow_version_id else None,
            error_summary='Deployment requires reconciliation.' if uncertain else 'DAG registration has a parse error.' if deployment.state=='PARSE_ERROR' else 'DAG deployment failed.' if deployment.state=='DEPLOYMENT_FAILED' else None,
            last_verified_at=deployment.last_verified_at)
        return result,generation


def reconcile(identity,key):
    fingerprint=digest({'deployment_id':str(identity)})
    with transaction() as session:
        existing=_existing(session,'DAG_RECONCILE',key,fingerprint)
        if existing:return existing.id
        deployment=session.get(DAGDeployment,identity)
        if deployment is None:raise APIError('DEPLOYMENT_NOT_FOUND','DAG deployment not found.',404)
        original=session.scalar(select(Operation).where(Operation.id==deployment.operation_id).with_for_update())
        deployment=session.scalar(select(DAGDeployment).where(DAGDeployment.id==identity).with_for_update().execution_options(populate_existing=True))
        if deployment.state!='DEPLOYED' and (original.state!='NEEDS_RECONCILIATION' or deployment.state not in ('READY_TO_DEPLOY','DEPLOYMENT_PENDING')):
            raise APIError('DEPLOYMENT_NOT_RECONCILABLE','Wait for the active deployment or submit a confirmed new revision.',409)
        busy=session.scalar(select(Operation.id).where(Operation.kind=='DAG_RECONCILE',
            Operation.progress_json['deployment_id'].astext==str(identity),Operation.state.in_(['QUEUED','RUNNING'])).limit(1))
        if busy:raise APIError('DEPLOYMENT_BUSY','Reconciliation is already pending for this deployment.',409)
        operation,_=enqueue(session,'DAG_RECONCILE',key,{'deployment_id':str(identity),'phase':'RECONCILIATION'},request_fingerprint=fingerprint)
        operation.result_ref='/api/v1/dag-deployments/'+str(identity)
        operation.deadline_at=datetime.now(timezone.utc)+timedelta(seconds=120)
        return operation.id
