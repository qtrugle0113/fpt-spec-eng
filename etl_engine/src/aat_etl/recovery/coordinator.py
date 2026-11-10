"""Reacquire native ownership, prove the old DB session ended, then inspect evidence."""
from dataclasses import dataclass
from sqlalchemy import select,text
from sqlalchemy.exc import SQLAlchemyError
from ..loaders.ledger import BatchMarker,RunMarker
from ..loaders.batches import CommitUncertain


class NeedsReconciliation(ValueError):pass


@dataclass(frozen=True)
class RecoveryDecision:
    state:str
    verified_rows:int


def require_old_session_finished(session,old_session_id):
    if type(old_session_id) is not int or old_session_id<1:raise NeedsReconciliation('The prior writer session identity is unknown.')
    session.require_owned();c=session.connection
    if c.dialect.name=='postgresql':
        alive=c.scalar(text('SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE pid=:pid)'),{'pid':old_session_id})
    else:
        alive=c.scalar(text('SELECT count(*) FROM information_schema.PROCESSLIST WHERE ID=:pid'),{'pid':old_session_id})
    if alive:raise NeedsReconciliation('Prior database session is still present; do not reclaim or replay.')
    c.rollback()


def reconcile_batches(dataset,session,ledger,*,old_session_id,strategy,batch_rows=1000,replacement_authorization_sha=None):
    if dataset.target_identity!=session.physical_identity:raise NeedsReconciliation('Recovery target changed.')
    try:
        require_old_session_finished(session,old_session_id)
        c=session.connection
        final=RunMarker(dataset.target_identity,dataset.run_uuid,dataset.manifest_sha256,dataset.binding_sha256,dataset.extracted_rows,replacement_authorization_sha)
        if ledger.verify_run(c,final):
            c.rollback();return RecoveryDecision('COMMIT_VERIFIED',dataset.extracted_rows)
        c.rollback()
        if strategy=='FULL_REFRESH':return RecoveryDecision('ROLLBACK_VERIFIED',0)
        records=c.execute(select(ledger.batch).where(ledger.batch.c.target_identity==dataset.target_identity,
            ledger.batch.c.run_uuid==ledger.values(final)['run_uuid']).order_by(ledger.batch.c.batch_index)).mappings().all()
        if any(record['batch_index']!=index or record['dataset_sha']!=dataset.manifest_sha256 or record['binding_sha']!=dataset.binding_sha256 or record['strategy']!=strategy for index,record in enumerate(records)):
            raise NeedsReconciliation('Committed batches differ from the pinned contiguous dataset prefix.')
        dataset.reader().verify()
        verified=0;seen=0
        from itertools import islice
        # A raw-file non-key conversion error in the uncommitted tail does not
        # invalidate proof of earlier commits. Only map the recorded prefix.
        for batch in islice(dataset.batches(batch_rows),len(records)):
            marker=BatchMarker(dataset.target_identity,dataset.run_uuid,dataset.manifest_sha256,batch.index,dataset.binding_sha256,len(batch.rows),batch.payload_sha256,strategy)
            if not ledger.verify_batch(c,marker):raise NeedsReconciliation('Recorded batch is absent from the pinned dataset.')
            verified+=len(batch.rows);seen+=1
        if seen!=len(records):raise NeedsReconciliation('Protected staging is shorter than the committed prefix.')
        c.rollback()
        return RecoveryDecision('RESUME_VERIFIED_DATASET',verified)
    except (SQLAlchemyError,ValueError,OSError) as error:
        if isinstance(error,NeedsReconciliation):raise
        raise NeedsReconciliation('Commit evidence or protected staging could not be verified; replay is blocked.') from None


def execute_with_recovery(dataset,*,session_factory,ledger_factory,writer,strategy,retry_count=0,retry_delay=60,
                          batch_rows=1000,sleep=None,replacement_authorization_sha=None,after_reconcile=None):
    """Retry only connection/commit uncertainty, with the same prepared dataset.

    Business/validation/constraint failures propagate immediately. Metadata
    projection failures never call the writer again through this coordinator.
    """
    import time
    if type(retry_count) is not int or not 0<=retry_count<=10 or type(retry_delay) is not int or not 0<=retry_delay<=3600:
        raise ValueError('Invalid finite retry policy.')
    wait=sleep or time.sleep;previous=None
    for attempt in range(retry_count+1):
        try:
            with session_factory() as session:
                ledger=ledger_factory(session.connection);session.connection.commit()
                if previous is not None:
                    decision=reconcile_batches(dataset,session,ledger,old_session_id=previous,strategy=strategy,batch_rows=batch_rows,
                        replacement_authorization_sha=replacement_authorization_sha)
                    if after_reconcile:after_reconcile(decision,previous,session)
                    if decision.state=='COMMIT_VERIFIED':return decision.verified_rows
                previous=session.session_id
                return writer(dataset,session,ledger)
        except CommitUncertain:
            if attempt==retry_count:raise NeedsReconciliation('Retry budget ended with an uncertain target commit; preserve artifacts.') from None
        wait(retry_delay)
