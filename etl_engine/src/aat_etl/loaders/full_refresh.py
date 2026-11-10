"""Authorized replacement is one target transaction, with a final commit marker."""
from uuid import UUID
from sqlalchemy import Table,MetaData,select,func,text
from sqlalchemy.exc import DBAPIError,IntegrityError
from .ledger import RunMarker
from .batches import CommitUncertain
from .replacement_admission import AdmissionDataset
from ..readers.schema import inspect_table,digest
from ..contracts.values import driver_row
from ..contracts.cancellation import check_cancelled


class ProjectionPending(ValueError):pass


def check_dependencies(session):
    c=session.connection
    if c.dialect.name=='postgresql':
        inbound=c.scalar(text('SELECT count(*) FROM pg_constraint WHERE contype=\'f\' AND confrelid=:oid'),{'oid':session.oid})
        triggers=c.scalar(text('SELECT count(*) FROM pg_trigger WHERE tgrelid=:oid AND NOT tgisinternal'),{'oid':session.oid})
    else:
        # information_schema.TRIGGERS silently omits inaccessible triggers.
        # Require inspection privilege explicitly instead of treating no rows
        # as proof when the account cannot inspect the target's triggers.
        from .privileges import mysql_permissions
        allowed='TRIGGER' in mysql_permissions(c.exec_driver_sql('SHOW GRANTS').scalars(),session.schema,session.table)
        if not allowed:raise ValueError('Target trigger inspection privilege is required before replacement.')
        inbound=c.scalar(text('SELECT count(*) FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_SCHEMA=:schema AND REFERENCED_TABLE_NAME=:table'),{'schema':session.schema,'table':session.table})
        triggers=c.scalar(text('SELECT count(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=:schema AND EVENT_OBJECT_TABLE=:table'),{'schema':session.schema,'table':session.table})
    if inbound or triggers:raise ValueError('Replacement is blocked by inbound foreign keys or target triggers.')
    c.rollback()


def execute(dataset,session,ledger,admission,*,owner_process_id,batch_rows=1000,cancelled=None):
    c=session.connection
    session.require_owned();c.rollback()
    if session.physical_identity!=dataset.target_identity:raise ValueError('Replacement physical target does not match its binding.')
    authorization_sha=digest([str(admission.request['authorization_id']),admission.request['scope_sha256']])
    final=RunMarker(dataset.target_identity,dataset.run_uuid,dataset.manifest_sha256,dataset.binding_sha256,dataset.validated_rows,authorization_sha)
    if ledger.verify_run(c,final):
        c.rollback()
        try:admission.reconcile_committed(dataset.manifest_sha256)
        except Exception:raise ProjectionPending('Target replacement commit is verified; metadata reconciliation remains pending.') from None
        return dataset.validated_rows
    c.rollback()
    reader=dataset.reader()
    if reader.manifest['validated_rows']!=dataset.validated_rows or dataset.validated_rows!=dataset.extracted_rows:
        raise ValueError('Full replacement dataset must be validated before admission.')
    if type(batch_rows) is not int or not 1<=batch_rows<=10000:raise ValueError('Invalid replacement batch size.')
    reader.verify()
    current=inspect_table(session.engine,schema=session.schema,table=session.table,used_columns=[p['name'] for p in reader.manifest['columns']])
    current.require_fingerprint(dataset.target_schema_hash)
    check_dependencies(session)
    check_cancelled(cancelled)
    prepared=AdmissionDataset(UUID(reader.manifest['dataset_id']),dataset.manifest_sha256,dataset.binding_sha256,dataset.run_uuid,dataset.validated_rows)
    admitted=admission.admit(session,prepared,owner_process_id=owner_process_id)
    target=Table(session.table,MetaData(),schema=session.schema,autoload_with=c);c.rollback()
    try:
        with c.begin():
            session.require_owned()
            check_cancelled(cancelled)
            c.execute(target.delete())
            for batch in dataset.batches(batch_rows):
                check_cancelled(cancelled)
                c.execute(target.insert(),[driver_row(value,reader.manifest['columns'],c.dialect.name) for value in batch.rows])
            check_cancelled(cancelled)
            if c.scalar(select(func.count()).select_from(target))!=dataset.validated_rows:raise ValueError('Replacement row count verification failed.')
            ledger.record_run(c,final)
    except IntegrityError:
        admission.reconcile(admitted['id'],outcome='ROLLBACK_VERIFIED',writer_finished=True)
        raise ValueError('Replacement rolled back after a target constraint failure; old data is preserved.') from None
    except DBAPIError:
        c.invalidate()
        try:admission.reconcile(admitted['id'],outcome='NEEDS_RECONCILIATION')
        except Exception:pass
        raise CommitUncertain('Replacement commit outcome is unknown; keep artifacts and reconcile the final marker before retry.') from None
    except BaseException:
        if not c.invalidated:
            admission.reconcile(admitted['id'],outcome='ROLLBACK_VERIFIED',writer_finished=True)
        raise
    try:admission.reconcile(admitted['id'],outcome='COMMIT_VERIFIED',writer_finished=True)
    except Exception:raise ProjectionPending('Target replacement commit is verified; metadata reconciliation remains pending.') from None
    return dataset.validated_rows
