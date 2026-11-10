"""Short metadata transactions around a fenced runtime owner and pinned dataset."""
from datetime import datetime,timezone
import os
from pathlib import Path
from uuid import UUID,uuid4
from sqlalchemy import text,inspect
from dataclasses import replace
from aat_metadata.repositories.metrics import project
from .contracts.writer import PreparedDataset
from .metrics import snapshot_from_ledger
from .readers.schema import digest,inspect_table
from .readers.file_source import FileDataset
from .staging.manager import StagingReader,hashed
from .recovery.coordinator import NeedsReconciliation


class RuntimeState:
    def __init__(self,metadata,binding_id,root):
        self.metadata=metadata;self.binding_id=UUID(str(binding_id));self.root=Path(root).absolute()
        if self.root.is_symlink() or not self.root.is_dir():raise ValueError('An existing persistent staging root is required.')
        self.owner=str(os.getpid())+':'+uuid4().hex

    def load(self):
        with self.metadata.connect() as c:
            row=c.execute(text("""SELECT b.*,r.config_json,r.schema_fingerprint_source,r.schema_fingerprint_target,
                i.run_uuid,a.scope_sha256 FROM execution_bindings b JOIN etl_definition_revisions r ON r.id=b.etl_revision_id
                JOIN run_intents i ON i.id=b.run_intent_id LEFT JOIN replacement_authorizations a ON a.id=b.authorization_id
                WHERE b.id=:id"""),{'id':self.binding_id}).mappings().first()
            if row is None:raise ValueError('Persisted runtime binding is unavailable.')
            self.binding=dict(row)
            prior=c.execute(text('SELECT * FROM runtime_leases WHERE binding_id=:id'),{'id':self.binding_id}).mappings().first()
            self.old_session_id=int(prior['target_lock_identity']) if prior and prior['target_lock_identity'].isdigit() else None
            self.dataset=dict(c.execute(text('SELECT * FROM dataset_manifests WHERE id=:id'),{'id':row['dataset_id']}).mappings().one()) if row['dataset_id'] else None
        return self.binding

    def claim(self):
        with self.metadata.begin() as c:
            c.execute(text('SELECT id FROM execution_bindings WHERE id=:id FOR UPDATE'),{'id':self.binding_id}).one()
            c.execute(text("""INSERT INTO runtime_leases(id,binding_id,owner_process_id,target_identity,target_lock_identity,recovery_state)
                VALUES(:id,:binding,:owner,:target,'PREPARING','EXTRACTING') ON CONFLICT(binding_id) DO UPDATE SET
                owner_process_id=EXCLUDED.owner_process_id,heartbeat_at=now(),updated_at=now()"""),
                dict(id=uuid4(),binding=self.binding_id,owner=self.owner,target=self.binding['config_json']['target']['physical_target_id']))
            c.execute(text("""UPDATE runtime_leases SET recovery_state='EXTRACTING' WHERE binding_id=:id
                AND target_lock_identity='PREPARING' AND EXISTS(SELECT 1 FROM execution_bindings
                WHERE id=:id AND dataset_id IS NULL AND NOT commit_uncertain)"""),{'id':self.binding_id})
            c.execute(text("UPDATE execution_bindings SET state='BOUND',updated_at=now() WHERE id=:id"),{'id':self.binding_id})
        self.load()

    def fence(self,c):
        c.execute(text('SELECT id FROM execution_bindings WHERE id=:id FOR UPDATE'),{'id':self.binding_id}).one()
        current=c.execute(text('SELECT owner_process_id FROM runtime_leases WHERE binding_id=:id FOR UPDATE'),{'id':self.binding_id}).scalar_one()
        if current!=self.owner:raise NeedsReconciliation('Runtime owner changed; artifact publication and target writes are blocked.')

    def begin_dataset(self,config):
        if self.dataset is not None:
            if self.dataset['state']=='COMPLETE':return self.dataset['id']
            raise NeedsReconciliation('An incomplete prior generation requires confirmed writer termination before extraction retry.')
        identity=uuid4();relative=Path(hashed(config.dag_id))/hashed(str(self.binding['run_uuid']))/str(identity)
        with self.metadata.begin() as c:
            self.fence(c)
            generation=c.scalar(text('SELECT COALESCE(max(generation),0)+1 FROM dataset_manifests WHERE execution_binding_id=:id'),{'id':self.binding_id})
            c.execute(text("""INSERT INTO dataset_manifests(id,execution_binding_id,generation,snapshot_started_at,schema_hash,mapping_hash,path_key,state)
                VALUES(:dataset,:binding,:generation,now(),:schema,:mapping,:path,'INCOMPLETE')"""),dict(dataset=identity,binding=self.binding_id,generation=generation,
                schema=self.binding['schema_fingerprint_target'],mapping=digest([m.model_dump(mode='json') for m in config.mappings]),path=relative.as_posix()))
            c.execute(text('UPDATE execution_bindings SET dataset_id=:dataset,updated_at=now() WHERE id=:binding'),{'dataset':identity,'binding':self.binding_id})
        self.binding['dataset_id']=identity
        return identity

    def prepared(self,dataset):
        reader=dataset.reader();reader.verify()
        relative=dataset.manifest.parent.relative_to(self.root).as_posix()
        expected=(Path(hashed(self.binding['dag_id']))/hashed(str(self.binding['run_uuid']))/str(self.binding['dataset_id'])).as_posix()
        if relative!=expected or dataset.binding_sha256!=self.binding['binding_hash']:
            raise NeedsReconciliation('Prepared dataset does not match the bound canonical staging path.')
        manifest=reader.manifest
        with self.metadata.begin() as c:
            self.fence(c)
            row=c.execute(text('SELECT state,manifest_sha256 FROM dataset_manifests WHERE id=:id FOR UPDATE'),{'id':self.binding['dataset_id']}).one()
            if row.state=='COMPLETE':
                if row.manifest_sha256!=dataset.manifest_sha256:raise NeedsReconciliation('Immutable dataset changed.')
                return
            if row.state!='INCOMPLETE':raise NeedsReconciliation('Dataset cannot be published from its current recovery state.')
            start=1
            for ordinal,part in enumerate(manifest['files'],1):
                c.execute(text("""INSERT INTO staging_artifacts(id,dataset_id,attempt_id,file_ordinal,path_key,file_sha256,rows,bytes,min_record_index,max_record_index,state,recovery_protected)
                    VALUES(:id,:dataset,:attempt,:ordinal,:path,:sha,:rows,:bytes,:first,:last,'COMPLETE',false)"""),dict(id=uuid4(),dataset=self.binding['dataset_id'],
                    attempt=UUID(Path(part['name']).parts[1]),ordinal=ordinal,path=(Path(relative)/part['name']).as_posix(),sha=part['sha256'],rows=part['rows'],bytes=part['bytes'],first=start,last=start+part['rows']-1))
                start+=part['rows']
            c.execute(text("""UPDATE dataset_manifests SET state='COMPLETE',manifest_sha256=:sha,extracted_rows=:extracted,
                validated_rows=:validated,total_bytes=:bytes,updated_at=now() WHERE id=:id"""),dict(id=self.binding['dataset_id'],sha=dataset.manifest_sha256,
                extracted=dataset.extracted_rows,validated=dataset.validated_rows,bytes=dataset.manifest.stat().st_size+sum(p['bytes'] for p in manifest['files'])))

    def writer_owned(self,dataset,session,ledger):
        session.require_owned()
        snapshot=snapshot_from_ledger(session,ledger,target_identity=dataset.target_identity,run_uuid=dataset.run_uuid,dataset_sha=dataset.manifest_sha256,
            binding_sha=dataset.binding_sha256,extracted_rows=dataset.extracted_rows,validated_rows=dataset.extracted_rows,failed_rows=None,phase='LOADING',staging_bytes=0,duration_ms=0)
        with self.metadata.begin() as c:
            self.fence(c)
            unresolved=c.scalar(text("""SELECT count(*) FROM runtime_leases l JOIN execution_bindings b ON b.id=l.binding_id
                WHERE l.target_identity=:target AND b.id<>:binding AND (b.commit_uncertain OR l.recovery_state='WRITING')"""),
                {'target':session.physical_identity,'binding':self.binding_id})
            if unresolved:raise NeedsReconciliation('Another binding on this physical target still requires commit reconciliation.')
            c.execute(text("""UPDATE runtime_leases SET target_lock_identity=:native,target_identity=:target,
                recovery_state='WRITING',heartbeat_at=now(),updated_at=now() WHERE binding_id=:binding"""),dict(native=str(session.session_id),target=session.physical_identity,binding=self.binding_id))
            c.execute(text("UPDATE execution_bindings SET state='RUNNING',commit_uncertain=true,updated_at=now() WHERE id=:id"),{'id':self.binding_id})
            capacity=int(c.scalar(text("SELECT COALESCE(sum(reserved_bytes),0) FROM staging_reservations WHERE run_uuid=:run AND state<>'RELEASED'"),{'run':self.binding['run_uuid']}))
            project(c,self.binding_id,replace(snapshot,validated_rows=max(dataset.validated_rows,snapshot.loaded_rows),staging_bytes=capacity))

    def project(self,snapshot):
        with self.metadata.begin() as c:
            self.fence(c);project(c,self.binding_id,snapshot)
            c.execute(text("UPDATE execution_bindings SET state='COMMIT_VERIFIED',commit_uncertain=false,last_reconciled_at=now(),updated_at=now() WHERE id=:id"),{'id':self.binding_id})
            c.execute(text("UPDATE runtime_leases SET recovery_state='COMMIT_VERIFIED',heartbeat_at=now(),updated_at=now() WHERE binding_id=:id"),{'id':self.binding_id})

    def restore(self,config,target):
        row=self.dataset
        if row is None:return None
        path=self.root/row['path_key']/'manifest.json'
        expected=self.root/hashed(config.dag_id)/hashed(str(self.binding['run_uuid']))/str(row['id'])/'manifest.json'
        if path!=expected or not path.resolve().is_relative_to(self.root.resolve()):raise NeedsReconciliation('Invalid protected staging location.')
        generic=PreparedDataset(path,row['manifest_sha256'],self.binding['binding_hash'],self.binding['run_uuid'],config.target.physical_target_id,
            self.binding['schema_fingerprint_source'],self.binding['schema_fingerprint_target'],row['mapping_hash'],row['extracted_rows'],row['validated_rows'],config.canonical_sha256())
        from .loaders.session import TargetSession
        from .loaders.ledger import ensure_support
        with TargetSession(target,schema=config.target.schema_,table=config.target.table,timeout=0) as session:
            if session.physical_identity!=config.target.physical_target_id:raise NeedsReconciliation('Protected dataset target identity changed.')
            ledger=ensure_support(session.connection,schema=config.target.schema_,consent=False)
            run=self.binding['run_uuid'] if session.connection.dialect.name=='postgresql' else str(self.binding['run_uuid'])
            from sqlalchemy import select
            final=session.connection.execute(select(ledger.run).where(ledger.run.c.target_identity==session.physical_identity,ledger.run.c.run_uuid==run)).mappings().first()
            if final:
                if final['dataset_sha']!=row['manifest_sha256'] or final['binding_sha']!=self.binding['binding_hash'] or final['total_loaded_rows']!=row['extracted_rows']:
                    raise NeedsReconciliation('Final target marker differs from the pinned dataset.')
                return generic
        if row['state']!='COMPLETE':raise NeedsReconciliation('Pinned dataset is not complete and no final marker proves this run committed.')
        try:
            generic.reader().verify()
        except (ValueError,OSError):raise NeedsReconciliation('Protected staging is unavailable or corrupt; extraction and replay are blocked.') from None
        if config.source.type!='DB' and config.load_strategy!='FULL_REFRESH':
            reader=StagingReader(path,manifest_sha256=row['manifest_sha256'],binding_sha256=self.binding['binding_hash'])
            names=[m.target_column for m in config.mappings if m.enabled] or [column['name'] for column in inspect(target).get_columns(config.target.table,schema=config.target.schema_) if column['name'] in {raw['name'] for raw in reader.manifest['columns']}]
            profile=inspect_table(target,schema=config.target.schema_,table=config.target.table,used_columns=names)
            profile.require_fingerprint(self.binding['schema_fingerprint_target'])
            return FileDataset.from_manifest(path,manifest_sha256=row['manifest_sha256'],binding_sha256=self.binding['binding_hash'],
                config=config,source_schema_hash=self.binding['schema_fingerprint_source'],target=profile,run_uuid=self.binding['run_uuid'])
        return generic
