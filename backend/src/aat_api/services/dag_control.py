"""One durable manual command and ONCE intent before any Airflow side effect."""
from datetime import datetime,timedelta,timezone
from uuid import UUID,uuid4
from urllib.parse import quote
from pathlib import PurePosixPath
import os
from sqlalchemy import select
from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
from aat_metadata.models.operations import Operation,DAGDeployment,AdmissionState,AuditEvent
from aat_metadata.models.authorizations import DataReplacementAuthorization
from aat_metadata.models.replacement_runs import RunIntent
from aat_metadata.repositories.authorizations import AuthorizationRepository
from aat_api.errors import APIError
from aat_api.schemas.dag_control import TriggerRequest
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import enqueue,digest
from aat_api.services.etl_dependencies import lock_current
from aat_api.services.etl_preview import preview
from aat_api.services.table_preview import signer
from aat_api.services.replacement_authorizations import _existing,_scope


def managed(session,dag_id,expected_revision):
    definition=session.scalar(select(ETLDefinition).where(ETLDefinition.dag_id==dag_id).with_for_update())
    if definition is None or definition.owner!='aat':
        raise APIError('MANAGED_DAG_NOT_FOUND','Managed DAG not found.',404)
    if definition.current_revision_id!=expected_revision:
        raise APIError('REVISION_MISMATCH','DAG revision changed. Refresh before continuing.',409)
    revision=session.get(ETLDefinitionRevision,expected_revision)
    gate=session.scalar(select(AdmissionState).where(AdmissionState.dag_id==dag_id).with_for_update())
    deployed=session.get(DAGDeployment,gate.deployment_id) if gate and gate.deployment_id else None
    if (not gate or gate.gate_state!='OPEN' or gate.etl_revision_id!=revision.id or not deployed
            or deployed.state!='DEPLOYED' or deployed.reconcile_required or deployed.etl_revision_id!=revision.id):
        raise APIError('DAG_NOT_READY','DAG deployment must be verified before this command.',409)
    return revision,gate,deployed


def verify_live(client,dag_id,expected_revision):
    with transaction() as session:
        revision,_,deployed=managed(session,dag_id,expected_revision)
        expected_hash=revision.config_sha256
        fileloc=str(PurePosixPath(os.environ.get('AAT_AIRFLOW_DAGS_ROOT','/opt/airflow/dags'))/deployed.generated_file_key)
        version=str(deployed.airflow_version_id)
    dag=client.dag(dag_id);details=client.details(dag_id)
    tags={tag.get('name') for tag in dag.get('tags',[]) if isinstance(tag,dict)}
    if (dag.get('dag_id')!=dag_id or dag.get('fileloc')!=fileloc
            or not {'aat','aat_revision:'+expected_hash}<=tags
            or str((details.get('latest_dag_version') or {}).get('id'))!=version):
        raise APIError('EXTERNAL_DAG_CONFLICT','Airflow ownership or revision changed. Reconcile before controlling this DAG.',409)
    return dag


def trigger(dag_id,value,key):
    value=TriggerRequest.model_validate(value.model_dump())
    fingerprint=digest({'dag_id':dag_id,**value.model_dump(mode='json')})
    with transaction() as session:
        existing=_existing(session,'DAG_TRIGGER',key,fingerprint)
        if existing:return existing.id
        revision=session.get(ETLDefinitionRevision,value.expected_revision)
        if revision is None:raise APIError('ETL_REVISION_NOT_FOUND','ETL revision not found.',404)
        upload_id=revision.upload_id
    preview(upload_id)
    with transaction() as session:
        existing=_existing(session,'DAG_TRIGGER',key,fingerprint)
        if existing:return existing.id
        scope=_scope(session,upload_id)
        try:signer().verify(value.confirmation_token,scope)
        except ValueError:raise APIError('CONFIRMATION_STALE_OR_INVALID','Confirmation expired or dependencies changed. Preview again.',409) from None
        revision,_,_=managed(session,dag_id,value.expected_revision)
        config=revision.config_json
        lock_current(session,config)
        if config['load_strategy']=='FULL_REFRESH':
            authority=session.scalar(select(DataReplacementAuthorization).where(
                DataReplacementAuthorization.id==value.authorization_id).with_for_update()) if value.authorization_id else None
            if (authority is None or authority.scope!='ONCE' or authority.etl_revision_id!=revision.id
                    or authority.dag_id!=dag_id or authority.physical_target_id!=config['target']['physical_target_id']):
                raise APIError('ONCE_AUTHORIZATION_REQUIRED','Manual replacement requires a separate ONCE authorization.',409)
            operation_id=uuid4()
            try:
                intent=AuthorizationRepository(session.connection().connection.driver_connection).reserve_once(
                    authorization_id=authority.id,dag_id=dag_id,etl_revision_id=revision.id,
                    physical_target_id=authority.physical_target_id,scope_sha256=authority.scope_sha256,
                    idempotency_key=key,request_sha256=fingerprint,run_uuid=uuid4(),
                    operation_id=operation_id,airflow_run_id='manual__aat_'+str(operation_id))
            except ValueError:raise APIError('AUTHORIZATION_UNAVAILABLE','ONCE authorization is reserved, revoked or no longer valid.',409) from None
            operation=session.get(Operation,intent['operation_id'])
        else:
            if value.authorization_id is not None:
                raise APIError('AUTHORIZATION_SCOPE_MISMATCH','Replacement authority does not apply to this load policy.',409)
            operation,created=enqueue(session,'DAG_TRIGGER',key,{},request_fingerprint=fingerprint)
            if not created:return operation.id
            session.add(RunIntent(operation_id=operation.id,run_uuid=uuid4(),dag_id=dag_id,
                airflow_run_id='manual__aat_'+str(operation.id),run_type='manual',etl_revision_id=revision.id,
                authorization_id=None,request_sha256=fingerprint,state='RESERVED'))
        operation.progress_json={'dag_id':dag_id,'revision_id':str(revision.id),'phase':'TRIGGER'}
        operation.deadline_at=datetime.now(timezone.utc)+timedelta(seconds=120)
        operation.result_ref='/api/v1/dags/'+quote(dag_id,safe='')+'/runs/'+quote('manual__aat_'+str(operation.id),safe='')
        session.add(AuditEvent(operation_id=operation.id,subject_type='ETLDefinition',subject_id=revision.definition_id,
            action='TRIGGER',acknowledgment_scope={'revision_id':str(revision.id)},safe_summary='dag.trigger_requested'))
        return operation.id
