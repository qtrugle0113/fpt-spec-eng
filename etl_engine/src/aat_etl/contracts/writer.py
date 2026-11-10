"""Immutable verified preparation output, bounded batches and writer protocol."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Protocol
from uuid import UUID
from ..staging.manager import StagingReader,encoded
from ..staging.codec import row as encode_row


@dataclass(frozen=True)
class PreparedBatch:
    index:int
    rows:tuple
    payload_sha256:str


@dataclass(frozen=True)
class PreparedDataset:
    manifest:Path
    manifest_sha256:str
    binding_sha256:str
    run_uuid:UUID
    target_identity:str
    source_schema_hash:str
    target_schema_hash:str
    mapping_hash:str
    extracted_rows:int
    validated_rows:int
    config_sha256:str|None=None

    def reader(self):
        return StagingReader(self.manifest,manifest_sha256=self.manifest_sha256,binding_sha256=self.binding_sha256,
            source_schema_hash=self.source_schema_hash,target_schema_hash=self.target_schema_hash,mapping_hash=self.mapping_hash)

    def batches(self,batch_rows=1000):
        if type(batch_rows) is not int or not 1<=batch_rows<=10000:raise ValueError('Batch rows must be between 1 and 10000.')
        reader=self.reader();columns=reader.manifest['columns'];batch=[];size=0;index=0;hasher=hashlib.sha256()
        for values in reader.rows():
            payload=encoded(encode_row(values,columns))+b'\n'
            if batch and (len(batch)>=batch_rows or size+len(payload)>8*1024**2):
                yield PreparedBatch(index,tuple(batch),hasher.hexdigest())
                index+=1;batch=[];size=0;hasher=hashlib.sha256()
            batch.append(dict(zip((c['name'] for c in columns),values)));size+=len(payload);hasher.update(payload)
        if batch:yield PreparedBatch(index,tuple(batch),hasher.hexdigest())


class Writer(Protocol):
    def execute(self,dataset:PreparedDataset,*,batch_rows:int=1000)->int: ...
