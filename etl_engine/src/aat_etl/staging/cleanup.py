"""Delete only canonical run directories after native/metadata/retention proof."""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from pathlib import Path
import shutil
from sqlalchemy import text
from ..recovery.coordinator import require_old_session_finished
from .manager import hashed
from .quota import QuotaManager


@dataclass(frozen=True)
class CleanupResult:
    collected:bool
    reason:str


def collect_dataset(engine,*,root,dataset_id,target_session,old_session_id,retention_days=7,now=None):
    if type(retention_days) is not int or not 1<=retention_days<=365:raise ValueError('Invalid staging retention.')
    root=Path(root).absolute()
    if root.is_symlink() or not root.is_dir():raise ValueError('An existing staging root is required.')
    now=now or datetime.now(timezone.utc)
    require_old_session_finished(target_session,old_session_id)
    reservations=[]
    with engine.begin() as c:
        row=c.execute(text('''SELECT d.id,d.path_key,d.state AS dataset_state,b.id AS binding_id,b.dag_id,b.state,
            b.commit_uncertain,b.last_reconciled_at,b.updated_at,i.run_uuid,l.target_identity,l.recovery_state
            FROM dataset_manifests d JOIN execution_bindings b ON b.id=d.execution_binding_id
            JOIN run_intents i ON i.id=b.run_intent_id LEFT JOIN runtime_leases l ON l.binding_id=b.id
            WHERE d.id=:id AND b.dataset_id=d.id FOR UPDATE OF b,d'''),{'id':dataset_id}).mappings().first()
        if row is None:return CleanupResult(False,'DATASET_NOT_FOUND')
        if row['target_identity']!=target_session.physical_identity:return CleanupResult(False,'TARGET_IDENTITY_UNVERIFIED')
        if row['commit_uncertain'] or row['last_reconciled_at'] is None or row['recovery_state'] not in ('COMMIT_VERIFIED','ROLLBACK_VERIFIED','CLOSED'):
            return CleanupResult(False,'RECOVERY_PROTECTED')
        if row['state'] not in ('SUCCEEDED','FAILED','CANCELED','COMMIT_VERIFIED','ROLLBACK_VERIFIED'):
            return CleanupResult(False,'RUN_NOT_TERMINAL')
        if max(row['last_reconciled_at'],row['updated_at'])>now-timedelta(days=retention_days):return CleanupResult(False,'RETENTION_ACTIVE')
        active=c.scalar(text("SELECT count(*) FROM replacement_admissions WHERE binding_id=:id AND state IN ('ADMITTED','NEEDS_RECONCILIATION')"),{'id':row['binding_id']})
        protected=c.scalar(text('SELECT count(*) FROM staging_artifacts WHERE dataset_id=:id AND recovery_protected'),{'id':dataset_id})
        if active or protected:return CleanupResult(False,'RECOVERY_PROTECTED')
        prefix=Path(hashed(row['dag_id']))/hashed(str(row['run_uuid']))
        if row['path_key']!=(prefix/str(dataset_id)).as_posix():return CleanupResult(False,'NONCANONICAL_DATASET_PATH')
        run_path=root/prefix
        for path in (root/prefix.parts[0],run_path):
            if path.is_symlink():return CleanupResult(False,'UNSAFE_STAGING_PATH')
        if not run_path.resolve().is_relative_to(root.resolve()) or run_path.resolve()==root.resolve():raise ValueError('Staging cleanup path escaped its root.')
        if run_path.exists():shutil.rmtree(run_path)
        # Metadata is retained as expiry evidence. A failed filesystem deletion
        # raises before state/quota changes, preserving the recovery accounting.
        c.execute(text("UPDATE staging_artifacts SET state='EXPIRED',updated_at=now() WHERE dataset_id IN (SELECT id FROM dataset_manifests WHERE execution_binding_id=:binding)"),{'binding':row['binding_id']})
        c.execute(text("UPDATE dataset_manifests SET state='EXPIRED',updated_at=now() WHERE execution_binding_id=:binding"),{'binding':row['binding_id']})
        reservations=list(c.execute(text("SELECT id FROM staging_reservations WHERE run_uuid=:run AND state<>'RELEASED'"),{'run':row['run_uuid']}).scalars())
    quota=QuotaManager(engine,root)
    for identity in reservations:
        quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)
    return CleanupResult(True,'EXPIRED_AFTER_VERIFIED_CLEANUP')
