"""Serialize desired pause state; ONCE never authorizes recurring execution."""
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from aat_metadata.models.operations import Operation,AuditEvent
from aat_metadata.models.etl import ETLDefinitionRevision
from aat_metadata.models.authorizations import DataReplacementAuthorization
from aat_metadata.repositories.bindings import schedule_hash
from aat_api.errors import APIError
from aat_api.schemas.dag_control import DagStateRequest
from aat_api.services.connections.service import transaction
from aat_api.services.dag_control import managed
from aat_api.services.definition_uploads import digest,enqueue
from aat_api.services.etl_dependencies import lock_current
from aat_api.services.etl_preview import preview
from aat_api.services.replacement_authorizations import _scope,_existing
from aat_api.services.table_preview import signer


def check_authority(session,revision,authorization_id,is_paused):
    config=revision.config_json
    if is_paused or config['load_strategy']!='FULL_REFRESH' or config['schedule']=='Manual':return
    authority=session.scalar(select(DataReplacementAuthorization).where(
        DataReplacementAuthorization.id==authorization_id).with_for_update()) if authorization_id else None
    if (authority is None or authority.scope!='SCHEDULED' or authority.state!='GRANTED'
            or authority.revoked_at or authority.invalidated_at or authority.etl_revision_id!=revision.id
            or authority.dag_id!=config['dag_id'] or authority.physical_target_id!=config['target']['physical_target_id']
            or authority.schedule_sha256!=schedule_hash(config)):
        raise APIError('SCHEDULED_AUTHORIZATION_REQUIRED','Activating this schedule requires matching SCHEDULED authority.',409)


def request(dag_id,value,expected_generation,key):
    value=DagStateRequest.model_validate(value.model_dump())
    fingerprint=digest({'dag_id':dag_id,'expected_generation':expected_generation,**value.model_dump(mode='json')})
    with transaction() as session:
        existing=_existing(session,'DAG_STATE',key,fingerprint)
        if existing:return existing.id
        revision=session.get(ETLDefinitionRevision,value.expected_revision)
        if revision is None:raise APIError('ETL_REVISION_NOT_FOUND','ETL revision not found.',404)
        upload_id=revision.upload_id
    # Pause does not need source connectivity; it changes future scheduling only.
    if not value.is_paused:preview(upload_id)
    with transaction() as session:
        existing=_existing(session,'DAG_STATE',key,fingerprint)
        if existing:return existing.id
        scope=_scope(session,upload_id)
        try:signer().verify(value.confirmation_token,scope)
        except ValueError:raise APIError('CONFIRMATION_STALE_OR_INVALID','Confirmation expired or dependencies changed. Preview again.',409) from None
        revision,gate,_=managed(session,dag_id,value.expected_revision)
        if gate.generation!=expected_generation:
            raise APIError('REVISION_MISMATCH','DAG controls changed. Refresh before continuing.',412)
        busy=session.scalar(select(Operation.id).where(Operation.kind=='DAG_STATE',
            Operation.progress_json['dag_id'].astext==dag_id,
            Operation.state.in_(['QUEUED','RUNNING','NEEDS_RECONCILIATION'])).limit(1))
        if busy:raise APIError('DAG_CONTROL_BUSY','A state command is pending or requires reconciliation.',409)
        if not value.is_paused:lock_current(session,revision.config_json)
        check_authority(session,revision,value.authorization_id,value.is_paused)
        generation=gate.generation+1
        payload={'dag_id':dag_id,'revision_id':str(revision.id),'generation':generation,
                 'is_paused':value.is_paused,'authorization_id':str(value.authorization_id) if value.authorization_id else None,'phase':'STATE'}
        operation,created=enqueue(session,'DAG_STATE',key,payload,request_fingerprint=fingerprint)
        if not created:return operation.id
        gate.generation=generation;gate.desired_paused=value.is_paused
        operation.deadline_at=datetime.now(timezone.utc)+timedelta(seconds=120)
        session.add(AuditEvent(operation_id=operation.id,subject_type='ETLDefinition',subject_id=revision.definition_id,
            action='PAUSE' if value.is_paused else 'ACTIVATE',acknowledgment_scope={'revision_id':str(revision.id),'generation':generation},
            safe_summary='dag.state_requested'))
        return operation.id
