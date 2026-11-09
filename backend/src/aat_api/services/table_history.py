"""Persistent job history and independent live target schema verification."""
from datetime import datetime, timezone
import hashlib
from uuid import UUID
from sqlalchemy import select,func
from aat_metadata.models.operations import Operation, TableCreationJob, TableCreationResult
from aat_metadata.models.definitions import TableDefinition
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction, active
from aat_api.services.definition_uploads import enqueue, digest, page
from aat_api.services.table_preview import preview, signer, snapshot, spec, columns_public, target_engine
from aat_api.ddl import postgres, mysql


def result_public(session,result):
    definition=session.get(TableDefinition,result.table_definition_id)
    return dict(table_id=result.table_definition_id,table_name=definition.table_name,state=result.state,
        **({'ddl':result.ddl_text} if result.ddl_text else {}),started_at=result.started_at,finished_at=result.finished_at,
        error=dict(scope='resource',code=result.error_code,message=result.safe_error or 'Table creation failed.') if result.error_code else None)


def job_public(session,job):
    operation=session.get(Operation,job.operation_id)
    results=session.scalars(select(TableCreationResult).where(TableCreationResult.job_id==job.id).order_by(TableCreationResult.created_at,TableCreationResult.id)).all()
    return dict(id=job.id,operation_id=job.operation_id,upload_id=job.upload_id,target_connection_revision_id=job.target_revision_id,
        state=operation.state,created_at=job.created_at,started_at=job.started_at,finished_at=job.finished_at,
        results=[result_public(session,result) for result in results])


def create(value,key):
    payload=dict(upload_id=str(value.upload_id),confirmation_hash=digest(value.confirmation_token))
    # Idempotent replay must return the original operation even after the target table exists.
    with transaction() as session:
        previous=session.scalar(select(Operation).where(Operation.kind=='TABLE_CREATE',Operation.idempotency_key==str(key)))
        if previous:
            if previous.request_sha256!=digest(payload): raise APIError('IDEMPOTENCY_CONFLICT','Idempotency key was used for another request.',409)
            return previous.id
    current=preview(value.upload_id)
    with transaction() as session:
        definitions,revision,scope=snapshot(session,value.upload_id)
        active(session,revision.connection_id,lock=True)
        # Serialize admission across connection aliases for the same physical
        # table, not merely requests using the same Connection row or key.
        for physical in sorted(d.physical_table_identity for d in definitions):
            lock=int.from_bytes(hashlib.sha256(('aat.table.create\0'+physical).encode()).digest()[:8],'big',signed=True)
            session.execute(select(func.pg_advisory_xact_lock(lock)))
        unresolved=session.scalar(select(TableCreationResult.id).join(TableDefinition,
            TableDefinition.id==TableCreationResult.table_definition_id)
            .where(TableDefinition.physical_table_identity.in_([d.physical_table_identity for d in definitions]),
                   TableCreationResult.state.in_(['PENDING','CREATING','UNKNOWN'])).limit(1))
        if unresolved:
            raise APIError('TABLE_RECONCILIATION_REQUIRED','A target table has an active or uncertain creation attempt. Review the existing job before another attempt.',409)
        scope['existence']={item['id']:item['existing_table'] for item in current['items']}
        try: signer().verify(value.confirmation_token,scope)
        except ValueError: raise APIError('CONFIRMATION_STALE_OR_INVALID','Confirmation expired or dependencies changed. Preview again.',409) from None
        operation,created=enqueue(session,'TABLE_CREATE',key,payload)
        if not created:return operation.id
        job=TableCreationJob(operation_id=operation.id,upload_id=value.upload_id,target_revision_id=revision.id,confirmation_hash=payload['confirmation_hash'])
        session.add(job);session.flush()
        adapter=postgres if revision.database_type=='POSTGRESQL' else mysql
        for definition in definitions:
            ddl=adapter.compile_table(spec(session,definition))
            session.add(TableCreationResult(job_id=job.id,table_definition_id=definition.id,state='PENDING',ddl_text=ddl,ddl_sha256=hashlib.sha256(ddl.encode()).hexdigest()))
        operation.result_ref='/api/v1/table-creation-jobs/'+str(job.id)
        return operation.id


def detail_job(identity):
    with transaction() as session:
        job=session.get(TableCreationJob,identity)
        if job is None:raise APIError('JOB_NOT_FOUND','Table creation job not found.',404)
        return job_public(session,job)


def jobs(upload_id,target_connection_id,state,from_,to,limit,offset):
    from aat_metadata.models.connections import ConnectionRevision
    if from_ and to and from_>to:raise APIError('INVALID_DATE_RANGE','From must not be after to.',422)
    with transaction() as session:
        statement=select(TableCreationJob).join(Operation,Operation.id==TableCreationJob.operation_id)
        if upload_id:statement=statement.where(TableCreationJob.upload_id==upload_id)
        if target_connection_id:
            statement=statement.join(ConnectionRevision,ConnectionRevision.id==TableCreationJob.target_revision_id).where(ConnectionRevision.connection_id==target_connection_id)
        if state:statement=statement.where(Operation.state==state)
        if from_:statement=statement.where(TableCreationJob.created_at>=from_)
        if to:statement=statement.where(TableCreationJob.created_at<=to)
        return page(session,statement.order_by(TableCreationJob.created_at,TableCreationJob.id),limit,offset,lambda job:job_public(session,job))


def table_detail(identity):
    from aat_api.services.table_introspection import actual_definition, equivalent
    from sqlalchemy.exc import SQLAlchemyError
    with transaction() as session:
        definition=session.get(TableDefinition,identity)
        if definition is None:raise APIError('TABLE_DEFINITION_NOT_FOUND','Table definition not found.',404)
        stored=spec(session,definition)
        results=session.scalars(select(TableCreationResult).where(TableCreationResult.table_definition_id==identity).order_by(TableCreationResult.created_at,TableCreationResult.id)).all()
        body=dict(id=definition.id,upload_id=definition.upload_id,table_name=definition.table_name,
            target_connection_revision_id=definition.target_connection_revision_id,target_schema=definition.target_schema,
            columns=columns_public(stored),primary_key=stored.primary_key,creation_results=[result_public(session,result) for result in results],
            verification_status='NOT_CREATED',verified_at=None,actual_columns=None,unavailable_reason=None)
        revision_id=definition.target_connection_revision_id
    try:
        with target_engine(revision_id) as engine: actual=actual_definition(engine,stored)
        body['verified_at']=datetime.now(timezone.utc)
        if actual is None:
            body['verification_status']='DRIFTED' if any(result.state=='CREATED' for result in results) else 'NOT_CREATED'
        else:
            body['actual_columns']=columns_public(actual)
            body['verification_status']='VERIFIED' if equivalent(stored,actual) else 'DRIFTED'
    except (APIError,SQLAlchemyError,OSError,ValueError):
        body['verification_status']='UNAVAILABLE';body['unavailable_reason']='Live target schema could not be verified.'
    return body
