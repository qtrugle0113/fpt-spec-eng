"""aat-jsonl/1: bounded disk parts, checksums and atomic COMPLETE publication."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
from uuid import UUID,uuid4
from .codec import row

MAX_ROW_BYTES=1024*1024
MAX_PART_BYTES=8*1024*1024
MAX_MANIFEST_BYTES=8*1024*1024
RUN_BYTES=10*1024**3
MIN_FREE=1024**3
HEX=re.compile(r'^[a-f0-9]{64}$')
PART=re.compile(r'^attempts/[a-f0-9-]{36}/part-[0-9]{6}\.jsonl$')


def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def hashed(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()


def fsync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def directory(path):
    if path.is_symlink():raise ValueError('Staging directories cannot be symbolic links.')
    try:path.mkdir(mode=0o700)
    except FileExistsError:
        if not path.is_dir():raise ValueError('Staging path is not a directory.') from None


def open_read(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    if not stat.S_ISREG(os.fstat(fd).st_mode):os.close(fd);raise ValueError('Staging artifact is not a regular file.')
    return os.fdopen(fd,'rb')


class StagingWriter:
    def __init__(self,root,*,dag_id,run_id,dataset_id,binding_sha256,source_schema_hash,target_schema_hash,mapping_hash,columns,source_snapshot_time):
        for value in (binding_sha256,source_schema_hash,target_schema_hash,mapping_hash):
            if not HEX.fullmatch(value):raise ValueError('A canonical SHA-256 is required.')
        if not isinstance(source_snapshot_time,datetime) or source_snapshot_time.utcoffset() is None:raise ValueError('Snapshot time must be timezone aware.')
        self.root=Path(root).absolute();self.dag_hash=hashed(dag_id);self.run_hash=hashed(run_id);self.dataset_id=str(UUID(str(dataset_id)))
        self.path=self.root/self.dag_hash/self.run_hash/self.dataset_id
        self.attempt=Path('attempts')/str(uuid4());self.columns=json.loads(encoded(columns))
        if not 1<=len(self.columns)<=1000 or len({c['name'] for c in self.columns})!=len(self.columns):raise ValueError('Staging requires 1 to 1000 distinct ordered columns.')
        self.manifest=dict(format_version='aat-jsonl/1',dataset_id=self.dataset_id,binding_sha256=binding_sha256,
            dag_sha256=self.dag_hash,run_sha256=self.run_hash,source_snapshot_time=source_snapshot_time.isoformat(),
            source_schema_hash=source_schema_hash,target_schema_hash=target_schema_hash,mapping_hash=mapping_hash,columns=self.columns)
        self.part=None;self.parts=[];self.rows=0;self.bytes=0;self.part_rows=0;self.part_bytes=0;self.finished=False

    def __enter__(self):
        if self.root.is_symlink() or not self.root.is_dir():raise ValueError('An existing staging root directory is required.')
        parent=self.root
        for name in (self.dag_hash,self.run_hash):parent=parent/name;directory(parent)
        # An existing dataset is only reusable through the verified reader. A new
        # writer cannot overwrite or adopt another attempt's content.
        self.path.mkdir(mode=0o700)
        directory(self.path/'attempts');directory(self.path/self.attempt)
        fsync_directory(self.path.parent);fsync_directory(self.path);fsync_directory(self.path/'attempts')
        return self

    def append(self,values):
        if self.finished:raise ValueError('Completed staging is immutable.')
        payload=encoded(row(values,self.columns))+b'\n'
        if len(payload)>MAX_ROW_BYTES:raise ValueError('Serialized staging row exceeds 1 MiB.')
        if self.bytes+len(payload)>RUN_BYTES:raise ValueError('Staging dataset exceeds its 10 GiB cap.')
        if shutil.disk_usage(self.root).free-len(payload)<MIN_FREE:raise ValueError('Staging free disk reserve would be exceeded.')
        if self.part is not None and self.part_bytes+len(payload)>MAX_PART_BYTES:self.close_part()
        if self.part is None:
            number=len(self.parts)+1
            if number>999999:raise ValueError('Staging part count exceeds its limit.')
            self.part_name=self.attempt/f'part-{number:06d}.jsonl'
            fd=os.open(self.path/(str(self.part_name)+'.part'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            self.part=os.fdopen(fd,'wb');self.part_hash=hashlib.sha256();self.part_bytes=self.part_rows=0
        self.part.write(payload);self.part_hash.update(payload)
        self.part_rows+=1;self.part_bytes+=len(payload);self.rows+=1;self.bytes+=len(payload)

    def close_part(self):
        if self.part is None:return
        self.part.flush();os.fsync(self.part.fileno());self.part.close();self.part=None
        path=self.path/self.part_name
        os.rename(str(path)+'.part',path);os.chmod(path,0o400);fsync_directory(path.parent)
        self.parts.append(dict(name=self.part_name.as_posix(),sha256=self.part_hash.hexdigest(),rows=self.part_rows,bytes=self.part_bytes))

    def complete(self):
        if self.finished:raise ValueError('Completed staging is immutable.')
        self.close_part()
        manifest=dict(self.manifest,files=self.parts,extracted_rows=self.rows,validated_rows=0,state='COMPLETE')
        # COMPLETE means extraction durability. Full target-typed validation is
        # a separate gate and cannot be inferred from successful extraction.
        payload=encoded(manifest)
        if len(payload)>MAX_MANIFEST_BYTES:raise ValueError('Staging manifest exceeds its bounded size.')
        temporary=self.path/('manifest-'+str(uuid4())+'.part')
        with temporary.open('xb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
        final=self.path/'manifest.json'
        os.link(temporary,final);temporary.unlink();os.chmod(final,0o400);fsync_directory(self.path)
        self.finished=True
        self.manifest_sha256=hashlib.sha256(payload).hexdigest()
        return final

    def __exit__(self,*error):
        if self.part is not None:self.part.close();self.part=None
        # Incomplete artifacts remain un-loadable, for quota/recovery accounting.
        # No opportunistic recursive deletion of a run's protected data.


class StagingReader:
    def __init__(self,manifest,*,manifest_sha256,binding_sha256,source_schema_hash=None,target_schema_hash=None,mapping_hash=None):
        self.path=Path(manifest).absolute()
        try:
            if self.path.name!='manifest.json':raise ValueError()
            with open_read(self.path) as stream:payload=stream.read(MAX_MANIFEST_BYTES+1)
            if len(payload)>MAX_MANIFEST_BYTES or not HEX.fullmatch(manifest_sha256) or hashlib.sha256(payload).hexdigest()!=manifest_sha256:raise ValueError()
            self.manifest=json.loads(payload)
            m=self.manifest
            if m['format_version']!='aat-jsonl/1' or m['state']!='COMPLETE' or m['binding_sha256']!=binding_sha256:raise ValueError()
            if str(UUID(m['dataset_id']))!=self.path.parent.name:raise ValueError()
            if m['run_sha256']!=self.path.parent.parent.name or m['dag_sha256']!=self.path.parent.parent.parent.name:raise ValueError()
            for field,value in (('source_schema_hash',source_schema_hash),('target_schema_hash',target_schema_hash),('mapping_hash',mapping_hash)):
                if not HEX.fullmatch(m[field]) or value is not None and value!=m[field]:raise ValueError()
            if not 1<=len(m['columns'])<=1000 or len({c['name'] for c in m['columns']})!=len(m['columns']):raise ValueError()
            if type(m['extracted_rows']) is not int or m['extracted_rows']<0 or type(m['validated_rows']) is not int or not 0<=m['validated_rows']<=m['extracted_rows']:raise ValueError()
            seen=set();count=0
            for part in m['files']:
                name=part['name']
                if not PART.fullmatch(name) or name in seen or not HEX.fullmatch(part['sha256']):raise ValueError()
                if type(part['rows']) is not int or part['rows']<1 or type(part['bytes']) is not int or not 0<part['bytes']<=MAX_PART_BYTES:raise ValueError()
                seen.add(name);count+=part['rows']
            if count!=m['extracted_rows']:raise ValueError()
        except (OSError,ValueError,TypeError,KeyError,AttributeError):raise ValueError('Staging manifest is missing, invalid or does not match its pinned binding/schema.') from None

    def part_path(self,part):
        path=self.path.parent/part['name']
        for ancestor in (self.path.parent,self.path.parent/'attempts',path.parent):
            if ancestor.is_symlink():raise ValueError('Staging artifact path cannot contain symbolic links.')
        return path

    def verify(self):
        # Verify every part before yielding even the first row. A corrupt later
        # part cannot be discovered only after earlier rows reached a loader.
        for part in self.manifest['files']:
            try:
                h=hashlib.sha256();size=0;lines=0
                with open_read(self.part_path(part)) as stream:
                    while chunk:=stream.read(65536):h.update(chunk);size+=len(chunk);lines+=chunk.count(b'\n')
                if size!=part['bytes'] or h.hexdigest()!=part['sha256'] or lines!=part['rows']:raise ValueError()
            except (OSError,ValueError):raise ValueError('Staging part is missing, truncated or has an invalid checksum.') from None

    def rows(self):
        self.verify()
        for part in self.manifest['files']:
            count=0
            try:
                with open_read(self.part_path(part)) as stream:
                    while payload:=stream.readline(MAX_ROW_BYTES+1):
                        if len(payload)>MAX_ROW_BYTES or not payload.endswith(b'\n'):raise ValueError()
                        decoded=json.loads(payload)
                        yield row(decoded,self.manifest['columns'],decode=True)
                        count+=1
                if count!=part['rows']:raise ValueError()
            except (OSError,ValueError,TypeError,KeyError):raise ValueError('Staging row is invalid for its pinned ordered schema.') from None
