"""Persist explicit scope-bound replacement grants with idempotent consent."""
from datetime import datetime,timezone
from uuid import UUID
from sqlalchemy import select
from aat_metadata.models.authorizations import DataReplacementAuthorization as Authorization
from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
from aat_metadata.models.definitions import DefinitionUpload
from aat_metadata.models.operations import Operation,AuditEvent
from aat_metadata.models.replacement_runs import RunIntent,ReplacementAdmission
from aat_metadata.repositories.bindings import schedule_hash
from aat_api.errors import APIError
from aat_api.schemas.authorizations import AuthorizationRequest
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import digest,enqueue,page
from aat_api.services.etl_dependencies import lock_current
from aat_api.services.etl_preview import preview,confirmation_scope
from aat_api.services.table_preview import signer


def require(session,identity,*,lock=False):
    statement=select(Authorization).where(Authorization.id==identity)
    if lock:statement=statement.with_for_update()
    authority=session.scalar(statement)
    if authority is None:raise APIError('AUTHORIZATION_NOT_FOUND','Replacement authorization not found.',404)
    return authority


def public(session,authority):
    reserved=session.get(RunIntent,authority.reserved_intent_id) if authority.reserved_intent_id else None
    unresolved=session.scalar(select(ReplacementAdmission.id).where(ReplacementAdmission.authorization_id==authority.id,
        ReplacementAdmission.state.in_(['ADMITTED','NEEDS_RECONCILIATION'])).limit(1))
    return dict(id=authority.id,revision_id=authority.etl_revision_id,dag_id=authority.dag_id,
        physical_target_id=authority.physical_target_id,scope=authority.scope,scope_sha256=authority.scope_sha256,
        schedule_sha256=authority.schedule_sha256,allow_empty=authority.allow_empty,
        acknowledged_at=authority.acknowledged_at,allow_empty_acknowledged_at=authority.allow_empty_acknowledged_at,
        state=authority.state,revision=authority.revision,reserved_intent_id=authority.reserved_intent_id,
        reserved_run_id=reserved.airflow_run_id if reserved else None,consumed_at=authority.consumed_at,
        closed_at=authority.closed_at,revoked_at=authority.revoked_at,invalidated_at=authority.invalidated_at,
        replacement_in_progress=None if unresolved else False)


def _existing(session,kind,key,fingerprint):
    operation=session.scalar(select(Operation).where(Operation.kind==kind,Operation.idempotency_key==str(key)))
    if operation is not None and operation.request_sha256!=fingerprint:
        raise APIError('IDEMPOTENCY_CONFLICT','Idempotency key was used for another request.',409)
    return operation


def _scope(session,upload_id):
    upload=session.get(DefinitionUpload,upload_id)
    if upload is None or upload.kind!='ETL' or upload.status!='VALIDATED':
        raise APIError('PREVIEW_UNAVAILABLE','Validate the workbook first.',409)
    revisions=session.scalars(select(ETLDefinitionRevision).where(ETLDefinitionRevision.upload_id==upload_id)
        .order_by(ETLDefinitionRevision.created_at,ETLDefinitionRevision.id)).all()
    parents={}
    for identity in sorted({row.definition_id for row in revisions},key=str):
        parent=session.scalar(select(ETLDefinition).where(ETLDefinition.id==identity).with_for_update())
        parents[identity]=parent.current_revision_id
    identities=[dict(id=str(row.id),config_sha256=row.config_sha256,dependency_fingerprint=row.dependency_fingerprint,
        previous_revision_id=str(parents[row.definition_id]) if parents[row.definition_id] else None) for row in revisions]
    return confirmation_scope(upload_id,upload.workbook_sha256,identities)


def grant(definition_id,value,key):
    value=AuthorizationRequest.model_validate(value.model_dump())
    fingerprint=digest({'definition_id':str(definition_id),**value.model_dump(mode='json')})
    with transaction() as session:
        existing=_existing(session,'AUTHORIZATION_CREATE',key,fingerprint)
        if existing:return public(session,require(session,UUID(existing.result_ref.rsplit('/',1)[1])))
        revision=session.get(ETLDefinitionRevision,value.revision_id)
        if revision is None or revision.definition_id!=definition_id:
            raise APIError('ETL_REVISION_NOT_FOUND','ETL revision not found.',404)
        upload_id=revision.upload_id
    # Whole-workbook live compilation precedes any grant; confirmation binds its full revision set.
    preview(upload_id)
    with transaction() as session:
        existing=_existing(session,'AUTHORIZATION_CREATE',key,fingerprint)
        if existing:return public(session,require(session,UUID(existing.result_ref.rsplit('/',1)[1])))
        scope=_scope(session,upload_id)
        try:signer().verify(value.confirmation_token,scope)
        except ValueError:raise APIError('CONFIRMATION_STALE_OR_INVALID','Confirmation expired or dependencies changed. Preview again.',409) from None
        revision=session.get(ETLDefinitionRevision,value.revision_id)
        config=revision.config_json
        if revision.status not in ('VALIDATED','DEPLOYED') or config['load_strategy']!='FULL_REFRESH' or config['target']['physical_target_id']!=value.physical_target_id:
            raise APIError('AUTHORIZATION_SCOPE_MISMATCH','Replacement scope does not match this revision.',409)
        if value.scope=='SCHEDULED' and config['schedule']=='Manual':
            raise APIError('AUTHORIZATION_SCOPE_MISMATCH','Scheduled authority requires a validated cron schedule.',409)
        lock_current(session,config)
        operation,created=enqueue(session,'AUTHORIZATION_CREATE',key,{},request_fingerprint=fingerprint)
        if not created:return public(session,require(session,UUID(operation.result_ref.rsplit('/',1)[1])))
        now=datetime.now(timezone.utc)
        scope_hash=digest(dict(dag_id=config['dag_id'],revision_id=str(revision.id),config_sha256=revision.config_sha256,
            physical_target_id=value.physical_target_id,scope=value.scope,allow_empty=value.allow_empty))
        authority=Authorization(dag_id=config['dag_id'],etl_revision_id=revision.id,physical_target_id=value.physical_target_id,
            scope=value.scope,scope_sha256=scope_hash,schedule_sha256=schedule_hash(config) if value.scope=='SCHEDULED' else None,
            allow_empty=value.allow_empty,allow_empty_acknowledged_at=now if value.allow_empty else None,acknowledged_at=now)
        session.add(authority);session.flush()
        operation.result_ref='/api/v1/replacement-authorizations/'+str(authority.id)
        operation.state='RUNNING';session.flush();operation.state='SUCCEEDED'
        session.add(AuditEvent(operation_id=operation.id,subject_type='ReplacementAuthorization',subject_id=authority.id,
            action='GRANT',acknowledgment_scope={'scope_sha256':scope_hash,'allow_empty':value.allow_empty},safe_summary='authorization.granted'))
        return public(session,authority)


def detail(identity):
    with transaction() as session:return public(session,require(session,identity))


def listing(definition_id,limit,offset):
    with transaction() as session:
        definition=session.get(ETLDefinition,definition_id)
        if definition is None:raise APIError('ETL_DEFINITION_NOT_FOUND','ETL definition not found.',404)
        statement=select(Authorization).where(Authorization.dag_id==definition.dag_id).order_by(Authorization.created_at,Authorization.id)
        return page(session,statement,limit,offset,lambda authority:public(session,authority))


def revoke(identity,expected_revision,key):
    fingerprint=digest({'id':str(identity),'expected_revision':expected_revision})
    with transaction() as session:
        existing=_existing(session,'AUTHORIZATION_REVOKE',key,fingerprint)
        if existing:return public(session,require(session,identity))
        authority=require(session,identity,lock=True)
        if authority.revision!=expected_revision:
            raise APIError('REVISION_MISMATCH','Authorization changed. Refresh before revoking.',412)
        operation,created=enqueue(session,'AUTHORIZATION_REVOKE',key,{},request_fingerprint=fingerprint)
        if not created:return public(session,authority)
        if authority.state in ('GRANTED','RESERVED'):authority.state='REVOKED'
        if authority.revoked_at is None:authority.revoked_at=datetime.now(timezone.utc)
        session.flush();session.refresh(authority)
        operation.result_ref='/api/v1/replacement-authorizations/'+str(identity)
        operation.state='RUNNING';session.flush();operation.state='SUCCEEDED'
        session.add(AuditEvent(operation_id=operation.id,subject_type='ReplacementAuthorization',subject_id=authority.id,
            action='REVOKE',acknowledgment_scope={'scope_sha256':authority.scope_sha256},safe_summary='authorization.revoked'))
        return public(session,authority)
