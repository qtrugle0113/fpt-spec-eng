"""Runtime identity and recovery artifacts; no target ledger implementation."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger,CheckConstraint,DateTime,ForeignKey,ForeignKeyConstraint,Integer,String,UniqueConstraint,DDL,event,text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from .definitions import Record
from .connections import immutable_guard
from .guards import state_guard


class ExecutionBinding(Record):
    __tablename__='execution_bindings'
    __table_args__=(UniqueConstraint('dag_id','airflow_run_id'),CheckConstraint("airflow_run_type IN ('manual','scheduled')",name='ck_binding_run_type'),
        CheckConstraint("binding_hash ~ '^[0-9a-f]{64}$'",name='ck_binding_hash'),
        ForeignKeyConstraint(['id','dataset_id'],['dataset_manifests.execution_binding_id','dataset_manifests.id'],
            name='fk_binding_dataset',ondelete='RESTRICT',use_alter=True))
    dag_id:Mapped[str]=mapped_column(ForeignKey('etl_definitions.dag_id',ondelete='RESTRICT'))
    airflow_run_id:Mapped[str]=mapped_column(String(255))
    task_id:Mapped[str]=mapped_column(String(200))
    airflow_dag_version_id:Mapped[str]=mapped_column(String(64))
    etl_revision_id:Mapped[UUID]=mapped_column(ForeignKey('etl_definition_revisions.id',ondelete='RESTRICT'))
    source_revision_id:Mapped[UUID|None]=mapped_column(ForeignKey('connection_revisions.id',ondelete='RESTRICT'))
    target_revision_id:Mapped[UUID]=mapped_column(ForeignKey('connection_revisions.id',ondelete='RESTRICT'))
    file_parser_revision:Mapped[UUID|None]=mapped_column(ForeignKey('file_parser_revisions.id',ondelete='RESTRICT'))
    source_file_sha256:Mapped[str|None]=mapped_column(String(64))
    authorization_id:Mapped[UUID|None]=mapped_column(ForeignKey('replacement_authorizations.id',ondelete='RESTRICT'))
    run_intent_id:Mapped[UUID]=mapped_column(ForeignKey('run_intents.id',ondelete='RESTRICT',use_alter=True,name='fk_binding_intent'),unique=True)
    airflow_run_type:Mapped[str]=mapped_column(String(16))
    dataset_id:Mapped[UUID|None]
    runtime_build:Mapped[str]=mapped_column(String(128))
    binding_hash:Mapped[str]=mapped_column(String(64))
    state:Mapped[str]=mapped_column(String(32),default='BOUND',server_default='BOUND')
    commit_uncertain:Mapped[bool]=mapped_column(default=False,server_default='false')
    last_reconciled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))


class DatasetManifest(Record):
    __tablename__='dataset_manifests'
    __table_args__=(UniqueConstraint('execution_binding_id','generation'),UniqueConstraint('execution_binding_id','id'),
        CheckConstraint('generation>=1 AND extracted_rows>=0 AND validated_rows>=0 AND total_bytes>=0',name='ck_dataset_counts'),
        CheckConstraint("state IN ('INCOMPLETE','COMPLETE','CORRUPT','PROTECTED','EXPIRED')",name='ck_dataset_state'),
        CheckConstraint(r"path_key !~ '(^/|(^|/)\.\.(/|$)|[\\\\])'",name='ck_dataset_path'))
    execution_binding_id:Mapped[UUID]=mapped_column(ForeignKey('execution_bindings.id',ondelete='RESTRICT'))
    generation:Mapped[int]=mapped_column(Integer)
    snapshot_started_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))
    schema_hash:Mapped[str]=mapped_column(String(64))
    mapping_hash:Mapped[str]=mapped_column(String(64))
    path_key:Mapped[str]=mapped_column(String(255),unique=True)
    manifest_sha256:Mapped[str|None]=mapped_column(String(64))
    extracted_rows:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    validated_rows:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    total_bytes:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    state:Mapped[str]=mapped_column(String(16),default='INCOMPLETE',server_default='INCOMPLETE')


class StagingArtifact(Record):
    __tablename__='staging_artifacts'
    __table_args__=(UniqueConstraint('dataset_id','file_ordinal'),CheckConstraint('rows>=0 AND bytes>=0 AND file_ordinal>=1',name='ck_artifact_counts'),
        CheckConstraint(r"length(path_key)>0 AND path_key !~ '(^/|(^|/)\.\.(/|$)|[\\\\])'",name='ck_artifact_path'))
    dataset_id:Mapped[UUID]=mapped_column(ForeignKey('dataset_manifests.id',ondelete='RESTRICT'))
    attempt_id:Mapped[UUID]
    file_ordinal:Mapped[int]=mapped_column(Integer)
    path_key:Mapped[str]=mapped_column(String(255),unique=True)
    file_sha256:Mapped[str|None]=mapped_column(String(64))
    rows:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    bytes:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    min_record_index:Mapped[int|None]=mapped_column(BigInteger)
    max_record_index:Mapped[int|None]=mapped_column(BigInteger)
    state:Mapped[str]=mapped_column(String(16),default='INCOMPLETE',server_default='INCOMPLETE')
    expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    recovery_protected:Mapped[bool]=mapped_column(default=False,server_default='false')


class ExecutionMetric(Record):
    __tablename__='execution_metrics'
    __table_args__=(CheckConstraint('extracted_rows>=0 AND validated_rows>=0 AND loaded_rows>=0 AND (failed_rows_nullable IS NULL OR failed_rows_nullable>=0) AND staging_bytes_current>=0 AND staging_bytes_peak>=staging_bytes_current AND duration_ms>=0',name='ck_metric_counts'),)
    binding_id:Mapped[UUID]=mapped_column(ForeignKey('execution_bindings.id',ondelete='RESTRICT'),unique=True)
    extracted_rows:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    validated_rows:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    loaded_rows:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    failed_rows_nullable:Mapped[int|None]=mapped_column(BigInteger)
    staging_bytes_current:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    staging_bytes_peak:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    duration_ms:Mapped[int]=mapped_column(BigInteger,default=0,server_default='0')
    phase:Mapped[str]=mapped_column(String(32),default='PENDING',server_default='PENDING')
    metric_updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))


class RuntimeLease(Record):
    __tablename__='runtime_leases'
    binding_id:Mapped[UUID]=mapped_column(ForeignKey('execution_bindings.id',ondelete='RESTRICT'),unique=True)
    owner_process_id:Mapped[str]=mapped_column(String(128))
    heartbeat_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))
    target_identity:Mapped[str]=mapped_column(String(255))
    target_lock_identity:Mapped[str]=mapped_column(String(255))
    recovery_state:Mapped[str]=mapped_column(String(32))


immutable_guard('execution_bindings',('id','dag_id','airflow_run_id','task_id','airflow_dag_version_id','etl_revision_id',
    'source_revision_id','target_revision_id','file_parser_revision','source_file_sha256','authorization_id','run_intent_id','airflow_run_type','runtime_build','binding_hash'))
_COMPLETE="""CREATE OR REPLACE FUNCTION public.aat_complete_manifest() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF OLD.state IN ('COMPLETE','CORRUPT','PROTECTED','EXPIRED') AND
 ROW(NEW.id,NEW.execution_binding_id,NEW.generation,NEW.schema_hash,NEW.mapping_hash,NEW.path_key,NEW.manifest_sha256,NEW.extracted_rows,NEW.validated_rows,NEW.total_bytes)
 IS DISTINCT FROM ROW(OLD.id,OLD.execution_binding_id,OLD.generation,OLD.schema_hash,OLD.mapping_hash,OLD.path_key,OLD.manifest_sha256,OLD.extracted_rows,OLD.validated_rows,OLD.total_bytes) THEN
 RAISE EXCEPTION 'Complete dataset is immutable' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
 CREATE TRIGGER aat_complete BEFORE UPDATE ON dataset_manifests FOR EACH ROW EXECUTE FUNCTION public.aat_complete_manifest();"""
event.listen(DatasetManifest.__table__,'after_create',DDL(_COMPLETE).execute_if(dialect='postgresql'))
state_guard(DatasetManifest.__table__,{'INCOMPLETE':['COMPLETE','CORRUPT','EXPIRED'],
    'COMPLETE':['PROTECTED','CORRUPT','EXPIRED'],'PROTECTED':['COMPLETE','CORRUPT','EXPIRED'],'CORRUPT':['PROTECTED','EXPIRED']})

_DATASET_POINTER="""CREATE OR REPLACE FUNCTION public.aat_binding_dataset_once() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF OLD.dataset_id IS NOT NULL AND NEW.dataset_id IS DISTINCT FROM OLD.dataset_id AND EXISTS(
 SELECT 1 FROM dataset_manifests WHERE id=OLD.dataset_id AND state<>'INCOMPLETE') THEN
 RAISE EXCEPTION 'Complete binding dataset cannot change' USING ERRCODE='23514'; END IF;
 RETURN NEW;END $$;
 CREATE TRIGGER aat_dataset_once BEFORE UPDATE ON execution_bindings FOR EACH ROW EXECUTE FUNCTION public.aat_binding_dataset_once();"""
event.listen(ExecutionBinding.__table__,'after_create',DDL(_DATASET_POINTER).execute_if(dialect='postgresql'))
