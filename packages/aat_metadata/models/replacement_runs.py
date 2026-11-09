"""Immutable trigger intent and replacement admission epochs."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import CheckConstraint,DateTime,ForeignKey,Index,Integer,String,UniqueConstraint,text
from sqlalchemy.orm import Mapped,mapped_column
from .definitions import Record
from .connections import immutable_guard
from .guards import state_guard


class RunIntent(Record):
    __tablename__='run_intents'
    __table_args__=(UniqueConstraint('dag_id','airflow_run_id'),UniqueConstraint('authorization_id','id'),
        CheckConstraint("run_type IN ('manual','scheduled')",name='ck_intent_type'),
        CheckConstraint("state IN ('RESERVED','SUBMITTING','CREATED','NEEDS_RECONCILIATION','REJECTED')",name='ck_intent_state'))
    operation_id:Mapped[UUID]=mapped_column(ForeignKey('operations.id',ondelete='RESTRICT'),unique=True)
    run_uuid:Mapped[UUID]=mapped_column(unique=True)
    dag_id:Mapped[str]=mapped_column(ForeignKey('etl_definitions.dag_id',ondelete='RESTRICT'))
    airflow_run_id:Mapped[str]=mapped_column(String(255))
    run_type:Mapped[str]=mapped_column(String(16))
    etl_revision_id:Mapped[UUID]=mapped_column(ForeignKey('etl_definition_revisions.id',ondelete='RESTRICT'))
    authorization_id:Mapped[UUID]=mapped_column(ForeignKey('replacement_authorizations.id',ondelete='RESTRICT'))
    request_sha256:Mapped[str]=mapped_column(String(64))
    state:Mapped[str]=mapped_column(String(32),default='RESERVED',server_default='RESERVED')
    reserved_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))
    last_reconciled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))


class ReplacementAdmission(Record):
    __tablename__='replacement_admissions'
    __table_args__=(UniqueConstraint('binding_id','admission_epoch'),
        Index('uq_admission_unreconciled','binding_id',unique=True,postgresql_where=text("state IN ('ADMITTED','NEEDS_RECONCILIATION')")),
        CheckConstraint('admission_epoch>=1 AND authorization_revision>=1',name='ck_admission_epoch'),
        CheckConstraint("state IN ('ADMITTED','COMMIT_VERIFIED','ROLLBACK_VERIFIED','NEEDS_RECONCILIATION')",name='ck_admission_state'),
        CheckConstraint("length(owner_process_id)>0 AND length(target_session_identity)>0 AND scope_sha256 ~ '^[0-9a-f]{64}$' AND dataset_sha256 ~ '^[0-9a-f]{64}$'",name='ck_admission_identity'))
    binding_id:Mapped[UUID]=mapped_column(ForeignKey('execution_bindings.id',ondelete='RESTRICT'))
    run_intent_id:Mapped[UUID]=mapped_column(ForeignKey('run_intents.id',ondelete='RESTRICT'))
    authorization_id:Mapped[UUID]=mapped_column(ForeignKey('replacement_authorizations.id',ondelete='RESTRICT'))
    admission_epoch:Mapped[int]=mapped_column(Integer)
    authorization_revision:Mapped[int]=mapped_column(Integer)
    scope_sha256:Mapped[str]=mapped_column(String(64))
    dataset_sha256:Mapped[str]=mapped_column(String(64))
    target_identity:Mapped[str]=mapped_column(String(255))
    owner_process_id:Mapped[str]=mapped_column(String(128))
    target_session_identity:Mapped[str]=mapped_column(String(255))
    state:Mapped[str]=mapped_column(String(32),default='ADMITTED',server_default='ADMITTED')
    admitted_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))
    reconciled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    writer_finished:Mapped[bool]=mapped_column(default=False,server_default='false')


immutable_guard('run_intents',('id','operation_id','run_uuid','dag_id','airflow_run_id','run_type','etl_revision_id','authorization_id','request_sha256','reserved_at'))
immutable_guard('replacement_admissions',('id','binding_id','run_intent_id','authorization_id','admission_epoch','authorization_revision',
    'scope_sha256','dataset_sha256','target_identity','owner_process_id','target_session_identity','admitted_at'))
state_guard(RunIntent.__table__,{'RESERVED':['SUBMITTING','REJECTED','CREATED'],'SUBMITTING':['CREATED','NEEDS_RECONCILIATION','REJECTED'],
    'NEEDS_RECONCILIATION':['CREATED','REJECTED']})
state_guard(ReplacementAdmission.__table__,{'ADMITTED':['COMMIT_VERIFIED','ROLLBACK_VERIFIED','NEEDS_RECONCILIATION'],
    'NEEDS_RECONCILIATION':['COMMIT_VERIFIED','ROLLBACK_VERIFIED']})
