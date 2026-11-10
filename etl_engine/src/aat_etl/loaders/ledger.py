"""Signature-checked support objects and markers in the target transaction."""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import re
from uuid import UUID
from sqlalchemy import MetaData,Table,Column,Text,String,BigInteger,Boolean,DateTime,inspect,select,text
from sqlalchemy.dialects import postgresql,mysql

HEX=re.compile(r'^[a-f0-9]{64}$')


def identity_values(value):
    for field in ('target_identity','dataset_sha','binding_sha'):
        if not isinstance(getattr(value,field),str) or not HEX.fullmatch(getattr(value,field)):
            raise ValueError('A canonical ledger identity hash is required.')
    UUID(str(value.run_uuid))


@dataclass(frozen=True)
class BatchMarker:
    target_identity:str
    run_uuid:UUID
    dataset_sha:str
    batch_index:int
    binding_sha:str
    row_count:int
    payload_sha:str
    strategy:str

    def __post_init__(self):
        identity_values(self)
        if type(self.batch_index) is not int or self.batch_index<0 or type(self.row_count) is not int or self.row_count<0:
            raise ValueError('Invalid batch ledger counts.')
        if not HEX.fullmatch(self.payload_sha) or self.strategy not in ('APPEND','UPSERT'):
            raise ValueError('Invalid batch ledger payload or strategy.')


@dataclass(frozen=True)
class RunMarker:
    target_identity:str
    run_uuid:UUID
    dataset_sha:str
    binding_sha:str
    total_loaded_rows:int
    replacement_authorization_sha:str|None=None

    def __post_init__(self):
        identity_values(self)
        if type(self.total_loaded_rows) is not int or self.total_loaded_rows<0:raise ValueError('Invalid final row count.')
        if self.replacement_authorization_sha is not None and not HEX.fullmatch(self.replacement_authorization_sha):
            raise ValueError('Invalid replacement authorization hash.')


class TargetLedger:
    def __init__(self,dialect,schema):
        pg=dialect=='postgresql'
        if dialect not in ('postgresql','mysql'):raise ValueError('Unsupported ledger adapter.')
        self.dialect=dialect
        self.metadata=MetaData(schema='_aat_control' if pg else schema)
        bounded=lambda size:Text() if pg else String(size)
        run_type=postgresql.UUID(as_uuid=True) if pg else mysql.CHAR(36)
        stamp=DateTime(timezone=True) if pg else mysql.DATETIME(fsp=6)
        self.batch=Table('batch_commits' if pg else '_aat_batch_commits',self.metadata,
            Column('target_identity',bounded(255),primary_key=True),Column('run_uuid',run_type,primary_key=True),
            Column('dataset_sha',bounded(64),primary_key=True),Column('batch_index',BigInteger,primary_key=True),
            Column('binding_sha',bounded(64),nullable=False),Column('row_count',BigInteger,nullable=False),
            Column('payload_sha',bounded(64),nullable=False),Column('strategy',bounded(16),nullable=False),
            Column('committed_at',stamp,nullable=False),mysql_engine='InnoDB',mysql_charset='utf8mb4')
        self.run=Table('run_commits' if pg else '_aat_run_commits',self.metadata,
            Column('target_identity',bounded(255),primary_key=True),Column('run_uuid',run_type,primary_key=True),
            Column('dataset_sha',bounded(64),nullable=False),Column('binding_sha',bounded(64),nullable=False),
            Column('total_loaded_rows',BigInteger,nullable=False),Column('replacement_authorization_sha',bounded(64)),
            Column('completed_at',stamp,nullable=False),mysql_engine='InnoDB',mysql_charset='utf8mb4')
        self.version=Table('support_schema_version' if pg else '_aat_support_schema_version',self.metadata,
            Column('singleton',Boolean if pg else mysql.TINYINT(),primary_key=True),
            Column('version',BigInteger,nullable=False),Column('signature',bounded(64),nullable=False),
            mysql_engine='InnoDB',mysql_charset='utf8mb4')

    def values(self,marker):
        values=asdict(marker)
        values['run_uuid']=UUID(str(marker.run_uuid)) if self.dialect=='postgresql' else str(marker.run_uuid)
        return values

    def record_batch(self,connection,marker):
        if not connection.in_transaction():raise ValueError('A target DML transaction is required.')
        now=datetime.now(timezone.utc)
        connection.execute(self.batch.insert().values(**self.values(marker),committed_at=now if self.dialect=='postgresql' else now.replace(tzinfo=None)))

    def record_run(self,connection,marker):
        if not connection.in_transaction():raise ValueError('A target DML transaction is required.')
        now=datetime.now(timezone.utc)
        connection.execute(self.run.insert().values(**self.values(marker),completed_at=now if self.dialect=='postgresql' else now.replace(tzinfo=None)))

    def verify(self,connection,table,marker,keys):
        values=self.values(marker)
        row=connection.execute(select(table).where(*(table.c[k]==values[k] for k in keys))).mappings().first()
        if row is None:return False
        if any(row[k]!=v for k,v in values.items()):
            raise ValueError('Ledger marker conflicts with the pinned execution or payload; reconciliation is required.')
        return True

    def verify_batch(self,connection,marker):
        return self.verify(connection,self.batch,marker,('target_identity','run_uuid','dataset_sha','batch_index'))

    def verify_run(self,connection,marker):
        return self.verify(connection,self.run,marker,('target_identity','run_uuid'))


def ensure_support(connection,*,schema,consent=False):
    """Create only with consent. Never adopt partially present or altered objects."""
    ledger=TargetLedger(connection.dialect.name,schema)
    inspector=inspect(connection)
    tables=list(ledger.metadata.tables.values())
    existing=[inspector.has_table(t.name,schema=t.schema) for t in tables]
    if not any(existing):
        if consent is not True:raise ValueError('Target support creation requires explicit consent.')
        if ledger.dialect=='postgresql':connection.execute(text('CREATE SCHEMA IF NOT EXISTS _aat_control'))
        ledger.metadata.create_all(connection,checkfirst=True)
        connection.execute(ledger.version.insert().values(singleton=True if ledger.dialect=='postgresql' else 1,version=1,signature='aat-support/1'))
        inspector=inspect(connection)
    elif not all(existing):raise ValueError('Target support names collide with an incomplete support schema.')
    for table in tables:
        actual=inspector.get_columns(table.name,schema=table.schema)
        if [c['name'] for c in actual]!=list(table.c.keys()):raise ValueError('Target support columns do not match signature 1.')
        for column,expected in zip(actual,table.c):
            if column['nullable']!=expected.nullable or column['type'].compile(dialect=connection.dialect)!=expected.type.compile(dialect=connection.dialect):
                raise ValueError('Target support types/nullability do not match signature 1.')
        if inspector.get_pk_constraint(table.name,schema=table.schema)['constrained_columns']!=[c.name for c in table.primary_key]:
            raise ValueError('Target support primary key does not match signature 1.')
        if ledger.dialect=='mysql' and inspector.get_table_options(table.name,schema=table.schema).get('mysql_engine')!='InnoDB':
            raise ValueError('Target ledger requires transactional InnoDB support objects.')
    versions=connection.execute(select(ledger.version)).all()
    if len(versions)!=1 or tuple(versions[0])!=(True,1,'aat-support/1'):
        raise ValueError('Target support version/signature is invalid.')
    return ledger
