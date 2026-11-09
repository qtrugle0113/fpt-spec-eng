"""Durable per-table DDL dispatch; uncertain outcomes are never replayed."""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from aat_metadata.models.operations import TableCreationJob, TableCreationResult
from aat_metadata.models.definitions import TableDefinition
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import fence
from aat_api.services.table_preview import snapshot, spec, target_engine
from aat_api.ddl import postgres, mysql
from aat_api.ddl.common import DDLOutcomeUnknown


def execute(operation, owner):
    with transaction() as session:
        fence(session,operation,owner)
        job=session.scalar(select(TableCreationJob).where(TableCreationJob.operation_id==operation['id']))
        if job is None: raise APIError('JOB_NOT_FOUND','Table creation job not found.',404)
        definitions,revision,_=snapshot(session,job.upload_id)
        if revision.id!=job.target_revision_id: raise APIError('TARGET_CHANGED','Target changed after confirmation.',409)
        job.started_at=datetime.now(timezone.utc)
        identities=[d.id for d in definitions];revision_id=revision.id
        job_id=job.id;adapter=postgres if revision.database_type=='POSTGRESQL' else mysql
    outcomes=[]
    for identity in identities:
        with transaction() as session:
            fence(session,operation,owner)
            job=session.get(TableCreationJob,job_id)
            # Recheck current revision before each independently committed table.
            snapshot(session,job.upload_id)
            result=session.scalar(select(TableCreationResult).where(TableCreationResult.job_id==job_id,TableCreationResult.table_definition_id==identity).with_for_update())
            if result.state!='PENDING':
                # A CREATING row after a crash is evidence of uncertainty, not permission to replay.
                return 'NEEDS_RECONCILIATION','DDL_OUTCOME_UNKNOWN'
            definition_spec=spec(session,session.get(TableDefinition,identity))
            result.state='CREATING';result.started_at=datetime.now(timezone.utc)
        error_code=None
        try:
            with target_engine(revision_id) as engine: state=adapter.create(engine,definition_spec)
        except DDLOutcomeUnknown:
            state='UNKNOWN';error_code='DDL_OUTCOME_UNKNOWN'
        except (SQLAlchemyError,APIError,OSError,ValueError):
            state='FAILED';error_code='TABLE_CREATE_FAILED'
        with transaction() as session:
            fence(session,operation,owner)
            result=session.scalar(select(TableCreationResult).where(TableCreationResult.job_id==job_id,TableCreationResult.table_definition_id==identity).with_for_update())
            result.state=state;result.finished_at=datetime.now(timezone.utc);result.error_code=error_code
            result.safe_error='Target DDL completion is uncertain. Reconciliation is required.' if state=='UNKNOWN' else 'Table could not be created. Check target permissions and definition.' if state=='FAILED' else None
        outcomes.append(state)
        if state=='UNKNOWN': break
    with transaction() as session:
        fence(session,operation,owner)
        session.get(TableCreationJob,job_id).finished_at=datetime.now(timezone.utc)
    if 'UNKNOWN' in outcomes:return 'NEEDS_RECONCILIATION','DDL_OUTCOME_UNKNOWN'
    if 'FAILED' in outcomes:
        return ('PARTIALLY_SUCCEEDED' if any(value in ('CREATED','ALREADY_EXISTS') for value in outcomes) else 'FAILED'),'TABLE_CREATE_FAILED'
    return 'SUCCEEDED',None
