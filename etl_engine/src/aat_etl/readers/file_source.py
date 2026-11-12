"""Immutable file extraction, full-format staging and per-row typed file loads."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import re
import stat
from uuid import UUID,uuid5
from sqlalchemy import inspect
from .delimited import ParserConfig,read
from .schema import inspect_table,digest
from ..mapping.mapper import map_row
from ..mapping.validation import validate_rows
from ..staging.manager import StagingWriter,StagingReader,encoded,MAX_ROW_BYTES,MAX_MANIFEST_BYTES
from ..staging.codec import row as encode_row
from ..staging.quota import RUN_LIMIT
from ..contracts.writer import PreparedDataset,PreparedBatch


@dataclass(frozen=True)
class FileReference:
    file_id:UUID
    parser_revision:int
    sha256:str
    bytes:int
    path:Path
    parser:ParserConfig|dict

    def __post_init__(self):
        object.__setattr__(self,'file_id',UUID(str(self.file_id)))
        object.__setattr__(self,'path',Path(self.path))
        object.__setattr__(self,'parser',self.parser if isinstance(self.parser,ParserConfig) else ParserConfig.model_validate(self.parser))
        if type(self.parser_revision) is not int or self.parser_revision<1 or not re.fullmatch(r'[a-f0-9]{64}',self.sha256):raise ValueError('Invalid immutable file/parser reference.')
        if type(self.bytes) is not int or not 0<self.bytes<=256*1024**2:raise ValueError('Source file exceeds its upload bound or is empty.')


@dataclass(frozen=True)
class FileSchema:
    physical_identity:str
    fingerprint:str
    columns:tuple


@dataclass(frozen=True)
class FilePins:
    source_schema_hash:str
    target_identity:str
    target_schema_hash:str


@contextmanager
def open_reference(reference):
    fd=os.open(reference.path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size!=reference.bytes:raise ValueError('Source file is missing or changed.')
        with os.fdopen(fd,'rb') as stream:
            fd=None;yield stream
    finally:
        if fd is not None:os.close(fd)


def checksum(stream,expected):
    stream.seek(0);hasher=hashlib.sha256()
    while data:=stream.read(65536):hasher.update(data)
    if hasher.hexdigest()!=expected:raise ValueError('Source checksum does not match the pinned immutable file.')
    stream.seek(0)


def file_schema(reference,columns):
    profiles=tuple(dict(name=n,logical_type='text',nullable=True) for n in columns)
    identity=digest(['FILE',str(reference.file_id),reference.sha256,reference.parser_revision])
    return FileSchema(identity,digest([identity,reference.parser.model_dump(),profiles]),profiles)


def inspect_file_inputs(config,reference,target_engine):
    if config.source.type not in ('CSV','TXT') or config.source.file_id!=reference.file_id or config.source.parser_revision!=reference.parser_revision or config.source.file_sha256!=reference.sha256:
        raise ValueError('File reference does not match the deployed source/parser revision.')
    with open_reference(reference) as stream:
        checksum(stream,reference.sha256);reader=read(stream,reference.parser)
        try:source=file_schema(reference,reader.columns)
        finally:reader.close()
    target_columns=inspect(target_engine).get_columns(config.target.table,schema=config.target.schema_)
    enabled=[m for m in config.mappings if m.enabled]
    mapped=[m.target_column for m in enabled] if enabled else [c['name'] for c in target_columns if c['name'] in {p['name'] for p in source.columns}]
    if not mapped:raise ValueError('At least one file column must map to the target.')
    for column in target_columns:
        if column['name'] not in mapped and not column['nullable'] and column.get('default') is None and not column.get('computed') and not column.get('identity'):
            raise ValueError('A required target column has no mapping or default.')
    return source,inspect_table(target_engine,schema=config.target.schema_,table=config.target.table,used_columns=mapped)


class FileDataset:
    """Format-verified raw file staging. Typed non-key errors may be late.

    Only file execution uses this seam; DB preparation always validates the
    complete mapped dataset. UPSERT keys are checked globally before creation.
    """
    def __init__(self,raw,config,source,target,run_uuid):
        self.manifest=raw.path/'manifest.json';self.manifest_sha256=raw.manifest_sha256
        self.binding_sha256=raw.manifest['binding_sha256'];self.run_uuid=run_uuid
        self.target_identity=target.physical_identity;self.source_schema_hash=source.fingerprint
        self.target_schema_hash=target.fingerprint;self.mapping_hash=raw.manifest['mapping_hash']
        self.extracted_rows=raw.rows;self.validated_rows=0;self.target_columns=target.columns
        self.config=config;self.source_columns=source.columns
        self.config_sha256=config.canonical_sha256()

    def reader(self):
        return StagingReader(self.manifest,manifest_sha256=self.manifest_sha256,binding_sha256=self.binding_sha256,
            source_schema_hash=self.source_schema_hash,target_schema_hash=self.target_schema_hash,mapping_hash=self.mapping_hash)

    @classmethod
    def from_manifest(cls,manifest,*,manifest_sha256,binding_sha256,config,source_schema_hash,target,run_uuid):
        from types import SimpleNamespace
        reader=StagingReader(manifest,manifest_sha256=manifest_sha256,binding_sha256=binding_sha256,
            source_schema_hash=source_schema_hash,target_schema_hash=target.fingerprint,
            mapping_hash=digest([m.model_dump(mode='json') for m in config.mappings]))
        if reader.manifest['validated_rows']!=0:raise ValueError('Raw file preparation must preserve extraction-only validation state.')
        raw=SimpleNamespace(path=Path(manifest).parent,manifest_sha256=manifest_sha256,manifest=reader.manifest,rows=reader.manifest['extracted_rows'])
        return cls(raw,config,FileSchema('',source_schema_hash,tuple(reader.manifest['columns'])),target,UUID(str(run_uuid)))

    def batches(self,batch_rows=1000):
        if type(batch_rows) is not int or not 1<=batch_rows<=10000:raise ValueError('Invalid file batch size.')
        batch=[];size=0;index=0;hasher=hashlib.sha256();self.validated_rows=0
        for number,values in enumerate(self.reader().rows(),1):
            source=dict(zip((p['name'] for p in self.source_columns),values))
            mapped=map_row(source,source_schema=self.source_columns,target_schema=self.target_columns,mappings=self.config.mappings,row_number=number)
            payload=encoded(encode_row([mapped[p['name']] for p in self.target_columns],self.target_columns))+b'\n'
            if len(payload)>1024**2:raise ValueError('Mapped file row exceeds 1 MiB.')
            if batch and size+len(payload)>8*1024**2:
                yield PreparedBatch(index,tuple(batch),hasher.hexdigest());index+=1;batch=[];size=0;hasher=hashlib.sha256()
            batch.append(mapped);size+=len(payload);hasher.update(payload);self.validated_rows=number
            if len(batch)>=batch_rows:
                yield PreparedBatch(index,tuple(batch),hasher.hexdigest());index+=1;batch=[];size=0;hasher=hashlib.sha256()
        if batch:yield PreparedBatch(index,tuple(batch),hasher.hexdigest())


def prepare_file(config,reference,target_engine,*,root,quota,run_uuid,dataset_id,binding_sha256,pins):
    source,target=inspect_file_inputs(config,reference,target_engine)
    if source.fingerprint!=pins.source_schema_hash or target.fingerprint!=pins.target_schema_hash or target.physical_identity!=pins.target_identity or config.target.physical_target_id!=target.physical_identity:
        raise ValueError('Pinned file/target schema changed.')
    run_uuid=UUID(str(run_uuid));dataset_id=UUID(str(dataset_id))
    common=dict(root=root,dag_id=config.dag_id,run_id=str(run_uuid),binding_sha256=binding_sha256,
        source_schema_hash=source.fingerprint,target_schema_hash=target.fingerprint,mapping_hash=digest([m.model_dump(mode='json') for m in config.mappings]),
        source_snapshot_time=datetime.now(timezone.utc),quota=quota,run_uuid=run_uuid)
    capacity=lambda:RUN_LIMIT-quota.usage(run_uuid)['run_reserved_bytes']
    raw_id=uuid5(dataset_id,'source') if config.load_strategy=='FULL_REFRESH' else dataset_id
    with open_reference(reference) as stream:
        checksum(stream,reference.sha256);reader=read(stream,reference.parser)
        try:
            if file_schema(reference,reader.columns).fingerprint!=source.fingerprint:raise ValueError('Source header changed.')
            with StagingWriter(**common,dataset_id=raw_id,columns=list(source.columns),reservation_bytes=capacity()) as raw:
                for record in reader:raw.append(record.values)
                reader.close();checksum(stream,reference.sha256);raw.complete()
        finally:reader.close()
    dataset=FileDataset(raw,config,source,target,run_uuid)
    if config.load_strategy=='UPSERT':
        keys=config.conflict_keys
        if not set(keys)<={p['name'] for p in target.columns}:raise ValueError('All UPSERT keys must be mapped.')
        key_columns=tuple(p for p in target.columns if p['name'] in keys)
        mappings=[m for m in config.mappings if m.enabled and m.target_column in keys]
        def key_rows():
            for number,values in enumerate(dataset.reader().rows(),1):
                yield map_row(dict(zip((p['name'] for p in source.columns),values)),source_schema=source.columns,target_schema=key_columns,mappings=mappings,row_number=number)
        with target_engine.connect() as c:validate_rows(c,schema=target.schema,table=target.table,columns=[p['name'] for p in key_columns],rows=key_rows(),conflict_keys=keys)
    if config.load_strategy!='FULL_REFRESH':return dataset
    # Each mapped row and the manifest already have enforced serialized bounds.
    # A failed tiny mapping must not pin an otherwise unused 10 GiB reservation.
    # Keep the artifacts protected and reserve their conservative maximum size.
    mapped_capacity=min(capacity(),raw.rows*MAX_ROW_BYTES+MAX_MANIFEST_BYTES)
    with StagingWriter(**common,dataset_id=dataset_id,columns=list(target.columns),reservation_bytes=mapped_capacity) as mapped:
        def mapped_rows():
            for batch in dataset.batches():
                for value in batch.rows:
                    mapped.append([value[p['name']] for p in target.columns]);yield value
        with target_engine.connect() as c:
            result=validate_rows(c,schema=target.schema,table=target.table,columns=[p['name'] for p in target.columns],rows=mapped_rows())
        manifest=mapped.complete(validated_rows=result.validated_rows)
    return PreparedDataset(manifest,mapped.manifest_sha256,binding_sha256,run_uuid,target.physical_identity,source.fingerprint,target.fingerprint,common['mapping_hash'],raw.rows,result.validated_rows,config.canonical_sha256())
