"""Post-reap reconciliation. Never infer writer death from a heartbeat."""
import json
import os
from pathlib import Path
import shutil
from uuid import UUID,uuid5
from sqlalchemy import text
from aat_metadata.repositories.base import create_app_engine
from aat_metadata.repositories.metrics import project
from .contracts.config import ETLConfig
from .metrics import MetricSnapshot
from .resources import SupervisionResult
from .runtime_state import RuntimeState
from .runtime_connections import revision_engine
from .staging.manager import hashed
from .staging.quota import QuotaManager
from .recovery.coordinator import NeedsReconciliation,reconcile_batches


def _lease(state,c):
    state.fence(c)
    return c.execute(text('SELECT * FROM runtime_leases WHERE binding_id=:id'),{'id':state.binding_id}).mappings().one()


def _project(state,*,terminal,loaded,complete=False):
    row=state.dataset or {};extracted=row.get('extracted_rows',0)
    validated=extracted if complete else max(row.get('validated_rows',0),loaded)
    capacity=QuotaManager(state.metadata,state.root).usage(state.binding['run_uuid'])['run_reserved_bytes']
    status='COMMIT_VERIFIED' if complete else ('FAILED' if terminal else 'BOUND')
    with state.metadata.begin() as c:
        _lease(state,c)
        project(c,state.binding_id,MetricSnapshot(extracted,validated,loaded,0 if complete else None,capacity,phase=status))
        c.execute(text('UPDATE execution_bindings SET state=:status,commit_uncertain=false,last_reconciled_at=now(),updated_at=now() WHERE id=:id'),{'id':state.binding_id,'status':status})
        c.execute(text('UPDATE runtime_leases SET recovery_state=:status,updated_at=now() WHERE binding_id=:id'),{'id':state.binding_id,'status':'COMMIT_VERIFIED' if complete else 'CLOSED'})


def _retire_incomplete(state,journal):
    """Only this reaped child, with no target registration, owns these paths."""
    row=state.dataset
    with state.metadata.begin() as c:
        lease=_lease(state,c)
        uncertain=c.scalar(text('SELECT commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':state.binding_id})
        if uncertain or lease['target_lock_identity']!='PREPARING' or lease['recovery_state'] not in ('EXTRACTING','NEEDS_RECONCILIATION'):
            raise NeedsReconciliation('Target writer evidence prevents extraction cleanup.')
        if row is None:return
        stored=c.execute(text('SELECT state FROM dataset_manifests WHERE id=:id FOR UPDATE'),{'id':row['id']}).scalar_one()
        if stored!='INCOMPLETE':raise NeedsReconciliation('Published datasets cannot be retired for extraction retry.')
        prefix=Path(hashed(state.binding['dag_id']))/hashed(str(state.binding['run_uuid']))
        if row['path_key']!=(prefix/str(row['id'])).as_posix():raise NeedsReconciliation('Noncanonical staging generation.')
        attempts={UUID(item['attempt']) for item in journal['attempts'] if UUID(item['run'])==state.binding['run_uuid']}
        if len(attempts)!=len(journal['attempts']):raise NeedsReconciliation('Allocation journal differs from the bound run.')
        paths=[state.root/prefix/str(identity) for identity in (row['id'],uuid5(row['id'],'source'))]
        for path in paths:
            relative=path.relative_to(state.root)
            current=state.root
            for component in relative.parts:
                current=current/component
                if current.is_symlink():raise NeedsReconciliation('Symlink staging cleanup is blocked.')
            if not path.resolve().is_relative_to(state.root.resolve()):raise NeedsReconciliation('Staging cleanup escaped root.')
            # A complete disk manifest without metadata publication needs recovery,
            # never a new source snapshot. Partial manifests remain disposable.
            if (path/'manifest.json').exists():raise NeedsReconciliation('A completed disk generation must be reconciled before retry.')
            if path.exists():
                entries=path/'attempts'
                if entries.exists() and any(not item.is_dir() or item.is_symlink() or UUID(item.name) not in attempts for item in entries.iterdir()):
                    raise NeedsReconciliation('Unjournaled staging writer prevents cleanup.')
        # Parent holds the binding advisory lock and owner fence while removing
        # only these two server-derived, unpublished generation directories.
        for path in paths:
            if path.exists():shutil.rmtree(path)
        c.execute(text('UPDATE execution_bindings SET dataset_id=NULL,updated_at=now() WHERE id=:id'),{'id':state.binding_id})
        c.execute(text("UPDATE dataset_manifests SET state='EXPIRED',updated_at=now() WHERE id=:id"),{'id':row['id']})
    quota=QuotaManager(state.metadata,state.root)
    for attempt in attempts:
        with state.metadata.connect() as c:
            identity=c.scalar(text('SELECT id FROM staging_reservations WHERE run_uuid=:run AND attempt_id=:attempt'),{'run':state.binding['run_uuid'],'attempt':attempt})
        if identity:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)
    state.dataset=None


def _authority(state,decision,target_session=None):
    if state.binding['authorization_id'] is None:return
    from .runtime import _connect
    from .loaders.replacement_admission import AdmissionAdapter
    adapter=AdmissionAdapter(lambda:_connect(state.metadata),authorization_id=state.binding['authorization_id'],run_intent_id=state.binding['run_intent_id'],
        binding_id=state.binding_id,scope_sha256=state.binding['scope_sha256'])
    if decision=='COMMIT_VERIFIED':adapter.reconcile_committed(state.dataset['manifest_sha256'])
    elif decision=='ROLLBACK_VERIFIED':
        with state.metadata.connect() as c:
            admission=c.scalar(text('SELECT id FROM replacement_admissions WHERE binding_id=:id AND target_session_identity=:native ORDER BY admission_epoch DESC LIMIT 1'),{'id':state.binding_id,'native':str(state.old_session_id)})
        if admission:adapter.reconcile_rollback(state.dataset['manifest_sha256'],target_session,state.old_session_id)
    elif decision=='TERMINAL':adapter.close_terminal(terminal_verified=True,retry_possible=False,writer_finished=True)


def finish_attempt(binding_id,*,proof,journal_path,root=None,metadata_engine=None,terminal=False):
    """Called only after run_supervised has waited/reaped its specific child."""
    metadata=metadata_engine
    try:
        if metadata is None:metadata=create_app_engine(runtime=True)
        if not isinstance(proof,SupervisionResult) or type(proof.exit_code) is not int:return 'NEEDS_RECONCILIATION'
        path=Path(journal_path)
        if path.is_symlink() or path.stat().st_size>8192:return 'NEEDS_RECONCILIATION'
        journal=json.loads(path.read_text())
        if journal['binding_id']!=str(binding_id) or journal['pid']!=proof.pid or not journal['owner'].startswith(str(proof.pid)+':'):
            return 'NEEDS_RECONCILIATION'
        with metadata.connect().execution_options(isolation_level='AUTOCOMMIT') as ownership:
            if not ownership.scalar(text('SELECT pg_try_advisory_lock(718423104,hashtext(:binding))'),{'binding':str(binding_id)}):return 'NEEDS_RECONCILIATION'
            try:
                state=RuntimeState(metadata,binding_id,root or os.environ.get('AAT_STAGING_ROOT','/data/staging'))
                state.load();state.owner=journal['owner']
                with metadata.begin() as c:_lease(state,c)
                if state.dataset is None or state.dataset['state']=='INCOMPLETE':
                    _retire_incomplete(state,journal)
                    _project(state,terminal=terminal,loaded=0)
                    if terminal:_authority(state,'TERMINAL')
                    return 'TERMINAL_VERIFIED' if terminal else 'RETRY_READY'
                config=ETLConfig.model_validate(state.binding['config_json'])
                with revision_engine(metadata,config.target.connection_revision_id) as target:
                    prepared=state.restore(config,target)
                    from .loaders.session import TargetSession
                    from .loaders.ledger import ensure_support
                    from .readers.schema import digest
                    with TargetSession(target,schema=config.target.schema_,table=config.target.table,timeout=0) as session:
                        ledger=ensure_support(session.connection,schema=config.target.schema_,consent=False);session.connection.commit()
                        authority_sha=digest([str(state.binding['authorization_id']),state.binding['scope_sha256']]) if config.load_strategy=='FULL_REFRESH' else None
                        decision=reconcile_batches(prepared,session,ledger,old_session_id=state.old_session_id,strategy=config.load_strategy,batch_rows=config.batch_size,replacement_authorization_sha=authority_sha)
                        _authority(state,decision.state,session)
                        _project(state,terminal=terminal,loaded=decision.verified_rows,complete=decision.state=='COMMIT_VERIFIED')
                if terminal and decision.state!='COMMIT_VERIFIED':_authority(state,'TERMINAL')
                return decision.state
            finally:
                try:ownership.execute(text('SELECT pg_advisory_unlock(718423104,hashtext(:binding))'),{'binding':str(binding_id)})
                except Exception:ownership.invalidate()
    except Exception:
        # Missing journal, unavailable metadata/native ownership or corrupt staging
        # preserves evidence. No raw exception reaches task logs.
        return 'NEEDS_RECONCILIATION'
    finally:
        if metadata_engine is None and metadata is not None:metadata.dispose()
