"""Bounded startup reconciliation; stale heartbeats never authorize reclamation."""
from pathlib import Path
import os
import re
import stat
import time
import threading
from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeout
from sqlalchemy import text
from psycopg.rows import dict_row
from aat_api.logging import logger

_recovery_pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='aat-target-recovery')
_recovery_slots=threading.BoundedSemaphore(2)


def admitted_inspection(row,resolve_target,root):
    try:return inspect_candidate(row,resolve_target,root)
    finally:_recovery_slots.release()


def inspect_candidate(row,resolve_target,root):
    """Read-only target inspection; may outlive a reporting deadline, never write."""
    from contextlib import ExitStack
    from aat_etl.contracts.config import ETLConfig
    from aat_etl.contracts.writer import PreparedDataset
    from aat_etl.loaders.session import TargetSession
    from aat_etl.loaders.ledger import ensure_support
    from aat_etl.readers.schema import digest,inspect_table
    from aat_etl.recovery.coordinator import reconcile_batches
    with ExitStack() as owned:
        try:
            config=ETLConfig.model_validate(row['config_json'])
            relative=Path(row['path_key'])
            base=Path(root).resolve();manifest=base/relative/'manifest.json'
            if relative.is_absolute() or not manifest.resolve().is_relative_to(base):raise ValueError('Invalid persisted staging path.')
            dataset=PreparedDataset(manifest,row['manifest_sha256'],row['binding_hash'],row['run_uuid'],row['target_identity'],
                row['schema_fingerprint_source'],row['schema_fingerprint_target'],row['mapping_hash'],row['extracted_rows'],row['validated_rows'])
            resolved=resolve_target(row['target_revision_id'])
            if hasattr(resolved,'connect'):
                target=resolved;owned.callback(target.dispose)
            else:target=owned.enter_context(resolved)
            with TargetSession(target,schema=config.target.schema_,table=config.target.table,timeout=0) as session:
                if session.connection.dialect.name=='postgresql':session.connection.execute(text("SET statement_timeout='10s'"))
                ledger=ensure_support(session.connection,schema=session.schema,consent=False);session.connection.commit()
                if config.source.type in ('CSV','TXT') and config.load_strategy!='FULL_REFRESH':
                    run_key=row['run_uuid'] if session.connection.dialect.name=='postgresql' else str(row['run_uuid'])
                    from sqlalchemy import select,inspect
                    final=session.connection.execute(select(ledger.run).where(ledger.run.c.target_identity==session.physical_identity,ledger.run.c.run_uuid==run_key)).first()
                    if final is None:
                        from aat_etl.readers.file_source import FileDataset
                        from aat_etl.staging.manager import StagingReader
                        raw=StagingReader(manifest,manifest_sha256=row['manifest_sha256'],binding_sha256=row['binding_hash'])
                        enabled=[m for m in config.mappings if m.enabled]
                        names=[m.target_column for m in enabled] if enabled else [p['name'] for p in inspect(target).get_columns(config.target.table,schema=config.target.schema_) if p['name'] in {v['name'] for v in raw.manifest['columns']}]
                        profile=inspect_table(target,schema=config.target.schema_,table=config.target.table,used_columns=names)
                        profile.require_fingerprint(row['schema_fingerprint_target'])
                        dataset=FileDataset.from_manifest(manifest,manifest_sha256=row['manifest_sha256'],binding_sha256=row['binding_hash'],
                            config=config,source_schema_hash=row['schema_fingerprint_source'],target=profile,run_uuid=row['run_uuid'])
                authorization_sha=digest([str(row['authorization_id']),row['scope_sha256']]) if config.load_strategy=='FULL_REFRESH' else None
                decision=reconcile_batches(dataset,session,ledger,old_session_id=int(row['target_lock_identity']),strategy=config.load_strategy,
                    batch_rows=config.batch_size,replacement_authorization_sha=authorization_sha)
                return decision.state,decision.verified_rows,'TARGET_MARKERS_VERIFIED'
        except Exception:return 'NEEDS_RECONCILIATION',0,'TARGET_OWNER_OR_EVIDENCE_UNVERIFIED'


def recover_pending(connect,*,resolve_target=None,root=None,budget_seconds=120):
    if not 0<budget_seconds<=120:raise ValueError('Startup recovery budget must be within 120 seconds.')
    started=time.monotonic();results=[]
    root=root or os.environ.get('AAT_STAGING_ROOT','/data/staging')
    if resolve_target is None:
        # Reuse the existing immutable-revision resolver and its allowlist,
        # encrypted credentials, numeric DNS pinning and endpoint fingerprint.
        from aat_api.services.table_preview import target_engine
        resolve_target=target_engine
    with connect() as c,c.cursor(row_factory=dict_row) as cursor:
        pending=cursor.execute("""SELECT b.id,b.run_intent_id,b.target_revision_id,b.binding_hash,b.authorization_id,d.path_key,d.manifest_sha256,
            d.extracted_rows,d.validated_rows,d.mapping_hash,i.run_uuid,r.config_json,r.schema_fingerprint_source,r.schema_fingerprint_target,
            l.owner_process_id,l.target_lock_identity,l.target_identity,l.recovery_state,a.scope_sha256
            FROM execution_bindings b JOIN run_intents i ON i.id=b.run_intent_id
            JOIN etl_definition_revisions r ON r.id=b.etl_revision_id
            LEFT JOIN dataset_manifests d ON d.id=b.dataset_id LEFT JOIN runtime_leases l ON l.binding_id=b.id
            LEFT JOIN replacement_authorizations a ON a.id=b.authorization_id
            WHERE b.commit_uncertain OR l.recovery_state IN ('NEEDS_RECONCILIATION','EXTRACTING','WRITING')
            ORDER BY b.updated_at LIMIT 100""").fetchall()
    for row in pending:
        reason='TARGET_RESOLUTION_UNAVAILABLE';state='NEEDS_RECONCILIATION';verified=0
        if time.monotonic()-started>=budget_seconds:
            reason='STARTUP_RECOVERY_BUDGET_EXHAUSTED'
        elif row['target_lock_identity']=='PREPARING':
            reason='SOURCE_WRITER_TERMINATION_UNVERIFIED'
        elif resolve_target is not None and not _recovery_slots.acquire(blocking=False):
            reason='TARGET_INSPECTION_IN_PROGRESS'
        elif resolve_target is not None:
            try:future=_recovery_pool.submit(admitted_inspection,row,resolve_target,root)
            except Exception:
                _recovery_slots.release();raise
            try:
                state,verified,reason=future.result(timeout=max(.001,budget_seconds-(time.monotonic()-started)))
            except FutureTimeout:
                if future.cancel():_recovery_slots.release()
                reason='STARTUP_RECOVERY_BUDGET_EXHAUSTED'
            except Exception:reason='TARGET_OWNER_OR_EVIDENCE_UNVERIFIED'
        if time.monotonic()-started<budget_seconds:
            with connect() as c:
                # Match the inspected owner under the same lock order as admission.
                # Target I/O is already finished; these metadata locks are short.
                if row['authorization_id'] is not None:
                    c.execute('SELECT id FROM replacement_authorizations WHERE id=%s FOR UPDATE',(row['authorization_id'],)).fetchone()
                    c.execute('SELECT id FROM run_intents WHERE id=%s FOR UPDATE',(row['run_intent_id'],)).fetchone()
                binding=c.execute('SELECT commit_uncertain,state FROM execution_bindings WHERE id=%s FOR UPDATE',(row['id'],)).fetchone()
                lease=c.execute('SELECT owner_process_id,target_lock_identity,recovery_state FROM runtime_leases WHERE binding_id=%s FOR UPDATE',(row['id'],)).fetchone()
                if lease is not None and (lease[0]!=row['owner_process_id'] or lease[1]!=row['target_lock_identity']):
                    state='NEEDS_RECONCILIATION';reason='OWNER_FENCE_CHANGED';verified=0
                elif binding and not binding[0] and lease and lease[2] in ('COMMIT_VERIFIED','ROLLBACK_VERIFIED','CLOSED'):
                    state=lease[2];reason='ALREADY_RECONCILED'
                else:
                    proven=state in ('COMMIT_VERIFIED','ROLLBACK_VERIFIED','RESUME_VERIFIED_DATASET')
                    if proven and (not isinstance(row['manifest_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',row['manifest_sha256'])
                                   or any(type(row[key]) is not int or row[key]<0 for key in ('extracted_rows','validated_rows'))
                                   or type(verified) is not int or not 0<=verified<=row['extracted_rows']):
                        proven=False;state='NEEDS_RECONCILIATION';reason='DATASET_EVIDENCE_UNVERIFIED';verified=0
                    if proven and row['config_json'].get('load_strategy')=='FULL_REFRESH':
                        from aat_metadata.repositories.authorizations import AuthorizationRepository
                        admission=c.execute('SELECT id FROM replacement_admissions WHERE binding_id=%s AND dataset_sha256=%s ORDER BY admission_epoch DESC LIMIT 1',(row['id'],row['manifest_sha256'])).fetchone()
                        if admission is None:
                            proven=False;state='NEEDS_RECONCILIATION';reason='ADMISSION_EVIDENCE_UNVERIFIED';verified=0
                        else:
                            AuthorizationRepository(c).reconcile(admission[0],outcome=state,writer_finished=True)
                    if proven:
                        terminal='COMMIT_VERIFIED' if state=='COMMIT_VERIFIED' else 'BOUND'
                        c.execute("UPDATE execution_bindings SET state=%s,commit_uncertain=false,last_reconciled_at=now(),updated_at=now() WHERE id=%s",(terminal,row['id']))
                        from uuid import uuid4
                        capacity=int(c.execute("SELECT COALESCE(sum(reserved_bytes),0) FROM staging_reservations WHERE run_uuid=%s AND state<>'RELEASED'",(row['run_uuid'],)).fetchone()[0])
                        validated=row['extracted_rows'] if state=='COMMIT_VERIFIED' else max(row['validated_rows'],verified)
                        failed=0 if state=='COMMIT_VERIFIED' else None
                        c.execute("""INSERT INTO execution_metrics(id,binding_id,extracted_rows,validated_rows,loaded_rows,failed_rows_nullable,staging_bytes_current,staging_bytes_peak,phase,metric_updated_at)
                          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,now()) ON CONFLICT(binding_id) DO UPDATE SET
                          extracted_rows=EXCLUDED.extracted_rows,validated_rows=EXCLUDED.validated_rows,loaded_rows=EXCLUDED.loaded_rows,
                          failed_rows_nullable=EXCLUDED.failed_rows_nullable,staging_bytes_current=EXCLUDED.staging_bytes_current,
                          staging_bytes_peak=GREATEST(execution_metrics.staging_bytes_peak,EXCLUDED.staging_bytes_peak),
                          phase=EXCLUDED.phase,metric_updated_at=now()""",(uuid4(),row['id'],row['extracted_rows'],validated,verified,failed,capacity,capacity,state))
                    c.execute('UPDATE runtime_leases SET recovery_state=%s,updated_at=now() WHERE binding_id=%s',(state,row['id']))
            # Metrics remain unknown/pending when the ledger cannot be read.
            # No writer callback, artifact deletion or reservation release runs.
        result=dict(binding_id=str(row['id']),state=state,reason=reason,verified_rows=verified)
        results.append(result)
        (logger.warning if state=='NEEDS_RECONCILIATION' else logger.info)('runtime_recovery binding_id=%s state=%s reason=%s',row['id'],state,reason)
    return results


def collect_expired_sources(connect,*,root=None,limit=50):
    """Retain metadata/parser history; remove only expired unreferenced blobs."""
    if type(limit) is not int or not 1<=limit<=100:raise ValueError('Invalid source cleanup page size.')
    root=Path(root or os.environ.get('AAT_UPLOADS_ROOT','/data/uploads')).absolute()
    if root.is_symlink() or not root.is_dir():return []
    collected=[]
    with connect() as c,c.cursor(row_factory=dict_row) as cursor:
        candidates=cursor.execute("""SELECT f.id,f.safe_storage_key FROM uploaded_files f
          WHERE f.extension IN ('.csv','.txt') AND f.expires_at<=now()
            AND f.created_at<now()-interval '30 days' AND f.updated_at<now()-interval '1 day'
            AND NOT EXISTS (SELECT 1 FROM etl_definition_revisions r WHERE r.config_json->'source'->>'file_id'=f.id::text)
            AND NOT EXISTS (SELECT 1 FROM execution_bindings b JOIN file_parser_revisions p ON p.id=b.file_parser_revision WHERE p.file_id=f.id)
            AND NOT EXISTS (SELECT 1 FROM operations o WHERE o.progress_json->>'file_id'=f.id::text AND o.state IN ('QUEUED','RUNNING','NEEDS_RECONCILIATION'))
          ORDER BY f.updated_at LIMIT %s FOR UPDATE OF f SKIP LOCKED""",(limit,)).fetchall()
        for candidate in candidates:
            key=candidate['safe_storage_key']
            if not re.fullmatch(r'[a-f0-9]{32}',key):continue
            path=root/key
            try:
                info=path.lstat()
                if not stat.S_ISREG(info.st_mode):continue
                path.unlink()
            except FileNotFoundError:pass
            except OSError:
                logger.warning('source_gc_blocked reference_id=%s reason=STORAGE_UNAVAILABLE',candidate['id'])
                continue
            # Updated timestamp moves already-collected metadata behind other
            # candidates, while retaining its checksum, byte count and history.
            c.execute("UPDATE uploaded_files SET validation_status='INVALID',updated_at=now() WHERE id=%s",(candidate['id'],))
            collected.append(str(candidate['id']))
            logger.info('source_gc_collected reference_id=%s',candidate['id'])
    return collected


def collect_terminal_staging(connect,*,root=None,limit=10,resolve_target=None):
    """Resolve immutable credentials, prove old owner ended, then apply GC gates."""
    from aat_api.services.table_preview import target_engine
    from aat_metadata.repositories.base import create_app_engine
    from aat_etl.contracts.config import ETLConfig
    from aat_etl.loaders.session import TargetSession
    from aat_etl.staging.cleanup import collect_dataset
    resolve_target=resolve_target or target_engine
    root=root or os.environ.get('AAT_STAGING_ROOT','/data/staging')
    if not Path(root).is_dir():return []
    with connect() as c,c.cursor(row_factory=dict_row) as cursor:
        candidates=cursor.execute("""SELECT b.id,b.dataset_id,b.target_revision_id,r.config_json,l.target_lock_identity
          FROM execution_bindings b JOIN etl_definition_revisions r ON r.id=b.etl_revision_id
          JOIN runtime_leases l ON l.binding_id=b.id JOIN dataset_manifests d ON d.id=b.dataset_id
          WHERE NOT b.commit_uncertain AND b.last_reconciled_at IS NOT NULL
            AND b.state IN ('SUCCEEDED','FAILED','CANCELED','COMMIT_VERIFIED','ROLLBACK_VERIFIED') AND d.state<>'EXPIRED'
            AND GREATEST(b.updated_at,b.last_reconciled_at)<now()-interval '1 day'
          ORDER BY b.updated_at LIMIT %s""",(limit,)).fetchall()
    results=[];metadata=create_app_engine()
    try:
        with connect() as c:
            value=c.execute("SELECT value_json FROM application_settings WHERE key='staging_retention_days'").fetchone()
        retention=value[0] if value else 7
        for candidate in candidates:
            try:
                config=ETLConfig.model_validate(candidate['config_json'])
                with resolve_target(candidate['target_revision_id']) as target:
                    with TargetSession(target,schema=config.target.schema_,table=config.target.table,timeout=0) as session:
                        result=collect_dataset(metadata,root=root,dataset_id=candidate['dataset_id'],target_session=session,
                            old_session_id=int(candidate['target_lock_identity']),retention_days=retention)
                results.append(dict(binding_id=str(candidate['id']),collected=result.collected,reason=result.reason))
            except Exception:
                logger.info('staging_gc_blocked binding_id=%s reason=OWNER_OR_EVIDENCE_UNVERIFIED',candidate['id'])
    finally:metadata.dispose()
    return results
