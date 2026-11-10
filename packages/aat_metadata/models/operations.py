"""Durable operations and audit metadata, without side-effect handlers."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import CheckConstraint,DateTime,ForeignKey,FetchedValue,Index,Integer,String,Text,UniqueConstraint,text,DDL,event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from .definitions import Record
from .connections import immutable_guard
from .guards import state_guard


class Operation(Record):
    __tablename__='operations'
    __table_args__=(UniqueConstraint('kind','idempotency_key'),CheckConstraint("state IN ('QUEUED','RUNNING','SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION')",name='ck_operation_state'),
        CheckConstraint('attempt>=0',name='ck_operation_attempt'),CheckConstraint("request_sha256 ~ '^[0-9a-f]{64}$'",name='ck_operation_hash'),
        CheckConstraint("length(btrim(kind))>0 AND length(btrim(idempotency_key))>0",name='ck_operation_key'),
        CheckConstraint("public.aat_json_no_credentials(progress_json)",name='ck_operation_safe_progress'))
    kind:Mapped[str]=mapped_column(String(64))
    idempotency_key:Mapped[str]=mapped_column(String(128))
    request_sha256:Mapped[str]=mapped_column(String(64))
    state:Mapped[str]=mapped_column(String(32),default='QUEUED',server_default='QUEUED')
    progress_json:Mapped[dict]=mapped_column(JSONB,default=dict,server_default=text("'{}'::jsonb"))
    result_ref:Mapped[str|None]=mapped_column(String(255))
    deadline_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    lease_owner:Mapped[str|None]=mapped_column(String(128))
    lease_until:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    heartbeat_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    attempt:Mapped[int]=mapped_column(Integer,default=0,server_default='0')
    error_code:Mapped[str|None]=mapped_column(String(64))
    error_summary:Mapped[str|None]=mapped_column(String(255))


class TableCreationJob(Record):
    __tablename__='table_creation_jobs'
    operation_id:Mapped[UUID]=mapped_column(ForeignKey('operations.id',ondelete='RESTRICT'),unique=True)
    upload_id:Mapped[UUID]=mapped_column(ForeignKey('definition_uploads.id',ondelete='RESTRICT'))
    confirmation_hash:Mapped[str]=mapped_column(String(64))
    target_revision_id:Mapped[UUID]=mapped_column(ForeignKey('connection_revisions.id',ondelete='RESTRICT'))
    started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    finished_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))


class TableCreationResult(Record):
    __tablename__='table_creation_results'
    __table_args__=(UniqueConstraint('job_id','table_definition_id'),CheckConstraint("state IN ('PENDING','CREATING','CREATED','ALREADY_EXISTS','FAILED','UNKNOWN')",name='ck_table_result_state'))
    job_id:Mapped[UUID]=mapped_column(ForeignKey('table_creation_jobs.id',ondelete='RESTRICT'))
    table_definition_id:Mapped[UUID]=mapped_column(ForeignKey('table_definitions.id',ondelete='RESTRICT'))
    state:Mapped[str]=mapped_column(String(32),default='PENDING',server_default='PENDING')
    ddl_text:Mapped[str|None]=mapped_column(Text)
    ddl_sha256:Mapped[str|None]=mapped_column(String(64))
    started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    finished_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    error_code:Mapped[str|None]=mapped_column(String(64))
    safe_error:Mapped[str|None]=mapped_column(String(255))


class DAGDeployment(Record):
    __tablename__='dag_deployments'
    __table_args__=(UniqueConstraint('operation_id','dag_id',name='uq_deployment_operation_dag'),
        Index('uq_deployment_active_dag','dag_id',unique=True,postgresql_where=text("state IN ('READY_TO_DEPLOY','DEPLOYMENT_PENDING')")),
        CheckConstraint("state IN ('VALIDATION_FAILED','READY_TO_DEPLOY','DEPLOYMENT_PENDING','DEPLOYED','DEPLOYMENT_FAILED','PARSE_ERROR')",name='ck_deployment_state'))
    operation_id:Mapped[UUID]=mapped_column(ForeignKey('operations.id',ondelete='RESTRICT'))
    etl_revision_id:Mapped[UUID]=mapped_column(ForeignKey('etl_definition_revisions.id',ondelete='RESTRICT'))
    dag_id:Mapped[str]=mapped_column(ForeignKey('etl_definitions.dag_id',ondelete='RESTRICT'),server_default=FetchedValue())
    previous_deployment_id:Mapped[UUID|None]=mapped_column(ForeignKey('dag_deployments.id',ondelete='RESTRICT'))
    state:Mapped[str]=mapped_column(String(32))
    revision_sha256:Mapped[str]=mapped_column(String(64))
    generated_file_key:Mapped[str|None]=mapped_column(String(255))
    file_sha256:Mapped[str|None]=mapped_column(String(64))
    previous_file_sha256:Mapped[str|None]=mapped_column(String(64))
    expected_owner_tag:Mapped[str]=mapped_column(String(64),default='aat',server_default='aat')
    parsed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    airflow_version_id:Mapped[UUID|None]
    airflow_version_number:Mapped[int|None]=mapped_column(Integer)
    last_verified_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    previous_paused:Mapped[bool|None]
    reconcile_required:Mapped[bool]=mapped_column(default=False,server_default='false')


class AdmissionState(Record):
    __tablename__='dag_admission'
    __table_args__=(CheckConstraint("gate_state IN ('OPEN','BLOCKED')",name='ck_dag_gate'),CheckConstraint('generation>=1',name='ck_dag_generation'))
    dag_id:Mapped[str]=mapped_column(ForeignKey('etl_definitions.dag_id',ondelete='RESTRICT'),unique=True)
    generation:Mapped[int]=mapped_column(Integer,default=1,server_default='1')
    desired_paused:Mapped[bool]=mapped_column(default=True,server_default='true')
    gate_state:Mapped[str]=mapped_column(String(16),default='BLOCKED',server_default='BLOCKED')
    reason:Mapped[str|None]=mapped_column(String(128))
    etl_revision_id:Mapped[UUID|None]=mapped_column(ForeignKey('etl_definition_revisions.id',ondelete='RESTRICT'))
    deployment_id:Mapped[UUID|None]=mapped_column(ForeignKey('dag_deployments.id',ondelete='RESTRICT'))


class AuditEvent(Record):
    __tablename__='audit_events'
    __table_args__=(CheckConstraint('public.aat_json_no_credentials(acknowledgment_scope)',name='ck_audit_safe_scope'),
        CheckConstraint("safe_summary ~ '^[A-Za-z][A-Za-z0-9_.-]{0,254}$'",name='ck_audit_summary_key'))
    operation_id:Mapped[UUID|None]=mapped_column(ForeignKey('operations.id',ondelete='RESTRICT'))
    subject_type:Mapped[str]=mapped_column(String(64))
    subject_id:Mapped[UUID]
    action:Mapped[str]=mapped_column(String(64))
    revision_before:Mapped[int|None]=mapped_column(Integer)
    revision_after:Mapped[int|None]=mapped_column(Integer)
    acknowledgment_scope:Mapped[dict]=mapped_column(JSONB,default=dict,server_default=text("'{}'::jsonb"))
    timestamp:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))
    safe_summary:Mapped[str]=mapped_column(String(255))


state_guard(Operation.__table__,{'QUEUED':['RUNNING','FAILED'],'RUNNING':['SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION'],
    'NEEDS_RECONCILIATION':['SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED']})
state_guard(TableCreationResult.__table__,{'PENDING':['CREATING'],'CREATING':['CREATED','ALREADY_EXISTS','FAILED','UNKNOWN'],
    'UNKNOWN':['CREATED','ALREADY_EXISTS','FAILED']})
state_guard(DAGDeployment.__table__,{'VALIDATION_FAILED':['READY_TO_DEPLOY'],
    'READY_TO_DEPLOY':['DEPLOYMENT_PENDING','VALIDATION_FAILED','DEPLOYMENT_FAILED'],
    'DEPLOYMENT_PENDING':['DEPLOYED','DEPLOYMENT_FAILED','PARSE_ERROR']})
immutable_guard('operations',('id','kind','idempotency_key','request_sha256'))
immutable_guard('audit_events',tuple(c.name for c in AuditEvent.__table__.columns))
_JOB="""CREATE OR REPLACE FUNCTION public.aat_job_validated() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM definition_uploads WHERE id=NEW.upload_id AND status='VALIDATED') THEN
 RAISE EXCEPTION 'Validated upload required' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
 CREATE TRIGGER aat_job_validated BEFORE INSERT ON table_creation_jobs FOR EACH ROW EXECUTE FUNCTION public.aat_job_validated();"""
event.listen(TableCreationJob.__table__,'after_create',DDL(_JOB).execute_if(dialect='postgresql'))

_DEPLOY="""CREATE OR REPLACE FUNCTION public.aat_deployment_dag() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 SELECT d.dag_id INTO NEW.dag_id FROM etl_definitions d JOIN etl_definition_revisions r ON r.definition_id=d.id WHERE r.id=NEW.etl_revision_id;
 RETURN NEW; END $$;
 CREATE TRIGGER aat_deployment_dag BEFORE INSERT OR UPDATE ON dag_deployments FOR EACH ROW EXECUTE FUNCTION public.aat_deployment_dag();"""
event.listen(DAGDeployment.__table__,'after_create',DDL(_DEPLOY).execute_if(dialect='postgresql'))
Index('ix_operation_claim',Operation.state,Operation.lease_until,Operation.created_at)
Index('ix_deployment_dag_created',DAGDeployment.dag_id,DAGDeployment.created_at)
Index('ix_audit_timestamp',AuditEvent.timestamp)


class WorkerHeartbeat(Record):
    __tablename__='worker_heartbeats'
    owner_process_id:Mapped[str]=mapped_column(String(128),unique=True)
    heartbeat_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))
