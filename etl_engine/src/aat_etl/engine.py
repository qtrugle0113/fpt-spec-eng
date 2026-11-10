"""Preparation is separate from target policy dispatch and performs no target DML."""
from dataclasses import dataclass
from datetime import datetime,timezone
from uuid import UUID,uuid5
from sqlalchemy import inspect
from .contracts.config import ETLConfig
from .contracts.writer import PreparedDataset
from .mapping.mapper import map_row
from .mapping.validation import validate_rows
from .readers.schema import inspect_table,preflight,digest
from .readers import postgres,mysql
from .staging.manager import StagingWriter,StagingReader
from .staging.quota import RUN_LIMIT


@dataclass(frozen=True)
class PreparationPins:
    source_identity:str
    source_schema_hash:str
    target_identity:str
    target_schema_hash:str


def inspect_inputs(config:ETLConfig,source_engine,target_engine):
    if config.source.type!='DB':raise ValueError('Database preparation requires a DB source.')
    source_columns=inspect(source_engine).get_columns(config.source.table,schema=config.source.schema_)
    target_columns=inspect(target_engine).get_columns(config.target.table,schema=config.target.schema_)
    source_names={c['name'] for c in source_columns};target_names={c['name'] for c in target_columns}
    enabled=[m for m in config.mappings if m.enabled]
    if enabled:
        projected=list(dict.fromkeys(m.source_column for m in enabled if m.transformation!='CONSTANT'))
        mapped=list(dict.fromkeys(m.target_column for m in enabled))
    else:
        projected=[c['name'] for c in source_columns if c['name'] in target_names];mapped=list(projected)
    # Constant-only DB mapping still needs a source projection to preserve its
    # cardinality and snapshot; choose one real source column, not COUNT(*).
    if not projected and source_columns:projected=[source_columns[0]['name']]
    if config.filter:
        projected=list(dict.fromkeys([*projected,*(p.column for p in config.filter.and_)]))
    if not mapped or not set(projected)<=source_names or not set(mapped)<=target_names:raise ValueError('Mapped source/target columns must exist.')
    for column in target_columns:
        if column['name'] not in mapped and not column['nullable'] and column.get('default') is None and not column.get('identity') and not column.get('computed'):
            raise ValueError('A required target column has no mapping or default.')
    return (inspect_table(source_engine,schema=config.source.schema_,table=config.source.table,used_columns=projected),
            inspect_table(target_engine,schema=config.target.schema_,table=config.target.table,used_columns=mapped))


def prepare_database(config,source_engine,target_engine,*,root,quota,run_uuid,dataset_id,binding_sha256,pins):
    if not isinstance(config,ETLConfig):config=ETLConfig.model_validate(config)
    run_uuid=UUID(str(run_uuid));dataset_id=UUID(str(dataset_id))
    source,target=inspect_inputs(config,source_engine,target_engine)
    preflight(source,target,expected_source_hash=pins.source_schema_hash,expected_target_hash=pins.target_schema_hash,
        expected_source_identity=pins.source_identity,expected_target_identity=pins.target_identity)
    if config.target.physical_target_id!=target.physical_identity:raise ValueError('Configured physical target does not match the pinned identity.')
    mapping_hash=digest([m.model_dump(mode='json') for m in config.mappings])
    common=dict(root=root,dag_id=config.dag_id,run_id=str(run_uuid),binding_sha256=binding_sha256,
        source_schema_hash=source.fingerprint,target_schema_hash=target.fingerprint,mapping_hash=mapping_hash,
        source_snapshot_time=datetime.now(timezone.utc),quota=quota,run_uuid=run_uuid)
    def capacity():return RUN_LIMIT-quota.usage(run_uuid)['run_reserved_bytes']
    adapter=postgres if source_engine.dialect.name=='postgresql' else mysql
    with adapter.SnapshotReader(source_engine,schema=source.schema,table=source.table,columns=[c['name'] for c in source.columns],
            filter=config.filter.model_dump(mode='json',by_alias=True) if config.filter else None) as reader:
        with StagingWriter(**common,dataset_id=uuid5(dataset_id,'source'),columns=list(source.columns),reservation_bytes=capacity()) as raw:
            for value in reader.rows():raw.append([value[c['name']] for c in source.columns])
            raw_manifest=raw.complete()
    # Source transaction and cursor are closed before mapping/target validation.
    raw_reader=StagingReader(raw_manifest,manifest_sha256=raw.manifest_sha256,binding_sha256=binding_sha256)
    with StagingWriter(**common,dataset_id=dataset_id,columns=list(target.columns),reservation_bytes=capacity()) as mapped:
        def values():
            for index,value in enumerate(raw_reader.rows(),1):
                source_row=dict(zip((c['name'] for c in source.columns),value))
                output=map_row(source_row,source_schema=source.columns,target_schema=target.columns,mappings=config.mappings,row_number=index)
                mapped.append([output[c['name']] for c in target.columns]);yield output
        with target_engine.connect() as connection:
            result=validate_rows(connection,schema=target.schema,table=target.table,columns=[c['name'] for c in target.columns],
                rows=values(),conflict_keys=config.conflict_keys if config.load_strategy=='UPSERT' else ())
        manifest=mapped.complete(validated_rows=result.validated_rows)
    return PreparedDataset(manifest,mapped.manifest_sha256,binding_sha256,run_uuid,target.physical_identity,
        source.fingerprint,target.fingerprint,mapping_hash,raw.rows,result.validated_rows,config.canonical_sha256())


def execute_database(config,source_engine,target_engine,*,root,quota,run_uuid,dataset_id,binding_sha256,pins,
                     support_consent=False,admission=None,project=None,on_prepared=None,prepared=None,old_session_id=None,cancelled=None,
                     on_writer_owned=None,retry_count_override=None):
    """Standalone DB execution. Runtime bind/persistence is supplied by the caller.

    A final marker is checked before source extraction. A partial run requires
    its already pinned preparation; no path silently re-extracts changed data.
    """
    if not isinstance(config,ETLConfig):config=ETLConfig.model_validate(config)
    factory=lambda:prepare_database(config,source_engine,target_engine,root=root,quota=quota,run_uuid=run_uuid,
        dataset_id=dataset_id,binding_sha256=binding_sha256,pins=pins)
    return _execute(config,target_engine,factory,quota=quota,run_uuid=run_uuid,binding_sha256=binding_sha256,
        support_consent=support_consent,admission=admission,project=project,on_prepared=on_prepared,prepared=prepared,old_session_id=old_session_id,cancelled=cancelled,
        on_writer_owned=on_writer_owned,retry_count_override=retry_count_override)


def execute_file(config,reference,target_engine,*,root,quota,run_uuid,dataset_id,binding_sha256,pins,
                 support_consent=False,admission=None,project=None,on_prepared=None,prepared=None,old_session_id=None,cancelled=None,
                 on_writer_owned=None,retry_count_override=None):
    from .readers.file_source import prepare_file
    if not isinstance(config,ETLConfig):config=ETLConfig.model_validate(config)
    factory=lambda:prepare_file(config,reference,target_engine,root=root,quota=quota,run_uuid=run_uuid,dataset_id=dataset_id,binding_sha256=binding_sha256,pins=pins)
    return _execute(config,target_engine,factory,quota=quota,run_uuid=run_uuid,binding_sha256=binding_sha256,
        support_consent=support_consent,admission=admission,project=project,on_prepared=on_prepared,prepared=prepared,old_session_id=old_session_id,cancelled=cancelled,
        on_writer_owned=on_writer_owned,retry_count_override=retry_count_override)


def _execute(config,target_engine,prepare,*,quota,run_uuid,binding_sha256,support_consent,admission,project,on_prepared,prepared,old_session_id=None,cancelled=None,
             on_writer_owned=None,retry_count_override=None):
    import time
    from sqlalchemy import select,func
    from .loaders.session import TargetSession
    from .loaders.ledger import ensure_support
    from .loaders.batches import write_batches
    from .loaders.full_refresh import execute as replace,ProjectionPending
    from .metrics import snapshot_from_ledger,MetricSnapshot
    from .recovery.coordinator import execute_with_recovery,NeedsReconciliation
    from .contracts.cancellation import check_cancelled,TransferCancelled
    from .loaders.batches import CommitUncertain
    from .loaders.session import SessionLost
    from .readers.database import SourceReadError
    def close_known_terminal(error):
        if admission is not None and not isinstance(error,(CommitUncertain,ProjectionPending,NeedsReconciliation,SessionLost,SourceReadError)):
            admission.close_terminal(terminal_verified=True,retry_possible=False,writer_finished=True)
    started=time.monotonic();run_uuid=UUID(str(run_uuid))
    if config.load_strategy=='FULL_REFRESH' and admission is None:raise ValueError('Replacement requires a persisted scoped admission adapter.')
    authorization_sha=digest([str(admission.request['authorization_id']),admission.request['scope_sha256']]) if admission else None
    def publish(snapshot):
        if project:
            try:project(snapshot)
            except Exception:raise ProjectionPending('Target commit is verified; metric projection remains pending. Do not replay target data.') from None
        return snapshot
    def session_factory():return TargetSession(target_engine,schema=config.target.schema_,table=config.target.table)
    with session_factory() as target:
        if target.physical_identity!=config.target.physical_target_id:raise ValueError('Configured target identity changed.')
        ledger=ensure_support(target.connection,schema=target.schema,consent=support_consent);target.connection.commit()
        run_key=run_uuid if target.connection.dialect.name=='postgresql' else str(run_uuid)
        final=target.connection.execute(select(ledger.run).where(ledger.run.c.target_identity==target.physical_identity,ledger.run.c.run_uuid==run_key)).mappings().first()
        if final:
            if final['binding_sha']!=binding_sha256 or final['replacement_authorization_sha']!=authorization_sha:
                raise NeedsReconciliation('Final marker has a different binding or replacement scope.')
            if admission:admission.reconcile_committed(final['dataset_sha'])
            count=final['total_loaded_rows']
            return publish(MetricSnapshot(count,count,count,0,quota.usage(run_uuid)['run_reserved_bytes'],int((time.monotonic()-started)*1000),'COMPLETE'))
        partial=target.connection.scalar(select(func.count()).select_from(ledger.batch).where(ledger.batch.c.target_identity==target.physical_identity,ledger.batch.c.run_uuid==run_key))
        if partial:
            if prepared is None:raise NeedsReconciliation('Partial target commit requires the original pinned staging; extraction is blocked.')
            if old_session_id is None:raise NeedsReconciliation('The prior target writer must be verified finished before resuming partial data.')
            from .recovery.coordinator import reconcile_batches
            reconcile_batches(prepared,target,ledger,old_session_id=old_session_id,strategy=config.load_strategy,
                batch_rows=config.batch_size,replacement_authorization_sha=authorization_sha)
    try:
        check_cancelled(cancelled)
        if prepared is None:prepared=prepare()
    except ValueError as error:
        close_known_terminal(error)
        raise
    if prepared.run_uuid!=run_uuid or prepared.binding_sha256!=binding_sha256:raise ValueError('Prepared run/binding identity mismatch.')
    if prepared.config_sha256!=config.canonical_sha256():raise ValueError('Prepared configuration does not match the immutable execution config.')
    if on_prepared:on_prepared(prepared)
    snapshots=[]
    def writer(dataset,session,ledger):
        try:
            if on_writer_owned:on_writer_owned(dataset,session,ledger)
            if config.load_strategy=='FULL_REFRESH':
                replace(dataset,session,ledger,admission,owner_process_id=str(UUID(str(run_uuid)))+'-'+str(uuid5(run_uuid,str(session.session_id))),batch_rows=config.batch_size,cancelled=cancelled)
            else:write_batches(dataset,session,ledger,strategy=config.load_strategy,batch_rows=config.batch_size,conflict_keys=config.conflict_keys,cancelled=cancelled)
        except ValueError as error:
            close_known_terminal(error)
            raise
        try:
            snapshot=snapshot_from_ledger(session,ledger,target_identity=dataset.target_identity,run_uuid=dataset.run_uuid,
                dataset_sha=dataset.manifest_sha256,binding_sha=dataset.binding_sha256,extracted_rows=dataset.extracted_rows,
                validated_rows=dataset.extracted_rows,failed_rows=0,phase='COMPLETE',staging_bytes=quota.usage(run_uuid)['run_reserved_bytes'],
                duration_ms=int((time.monotonic()-started)*1000))
        except Exception:raise ProjectionPending('Target commit is verified; metric reconciliation is pending.') from None
        snapshots.append(publish(snapshot));return snapshot.loaded_rows
    def after_reconcile(decision,old_session_id,session):
        if admission:
            if decision.state=='COMMIT_VERIFIED':admission.reconcile_committed(prepared.manifest_sha256)
            elif decision.state=='ROLLBACK_VERIFIED':admission.reconcile_rollback(prepared.manifest_sha256,session,old_session_id)
    loaded=execute_with_recovery(prepared,session_factory=session_factory,
        ledger_factory=lambda c:ensure_support(c,schema=config.target.schema_,consent=False),writer=writer,strategy=config.load_strategy,
        retry_count=config.retry_count if retry_count_override is None else retry_count_override,retry_delay=config.retry_delay,batch_rows=config.batch_size,
        replacement_authorization_sha=authorization_sha,after_reconcile=after_reconcile)
    if snapshots:return snapshots[-1]
    return publish(MetricSnapshot(prepared.extracted_rows,prepared.extracted_rows,loaded,0,
        quota.usage(run_uuid)['run_reserved_bytes'],int((time.monotonic()-started)*1000),'COMPLETE'))
