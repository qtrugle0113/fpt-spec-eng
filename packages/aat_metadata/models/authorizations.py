"""Authorization identity and reservation constraints; grants are T031."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import CheckConstraint,DateTime,ForeignKey,ForeignKeyConstraint,Integer,String,UniqueConstraint,DDL,event
from sqlalchemy.orm import Mapped,mapped_column
from .definitions import Record
from .connections import immutable_guard
from .guards import state_guard


class DataReplacementAuthorization(Record):
    __tablename__='replacement_authorizations'
    __table_args__=(
        CheckConstraint("scope IN ('ONCE','SCHEDULED')",name='ck_auth_scope'),
        CheckConstraint("state IN ('GRANTED','RESERVED','CONSUMED','CLOSED','REVOKED','INVALIDATED')",name='ck_auth_state'),
        CheckConstraint("scope_sha256 ~ '^[0-9a-f]{64}$' AND physical_target_id ~ '^[0-9a-f]{64}$'",name='ck_auth_hash'),
        CheckConstraint("(scope='SCHEDULED' AND schedule_sha256 ~ '^[0-9a-f]{64}$' AND schedule_sha256 IS NOT NULL) OR (scope='ONCE' AND schedule_sha256 IS NULL)",name='ck_auth_schedule'),
        CheckConstraint('NOT allow_empty OR allow_empty_acknowledged_at IS NOT NULL',name='ck_auth_empty_ack'),
        CheckConstraint('revision>=1',name='ck_auth_revision'),
        CheckConstraint("state<>'RESERVED' OR scope='ONCE' AND reserved_intent_id IS NOT NULL",name='ck_auth_reserved'),
        ForeignKeyConstraint(['id','reserved_intent_id'],['run_intents.authorization_id','run_intents.id'],
            name='fk_auth_reserved_intent',ondelete='RESTRICT',deferrable=True,initially='DEFERRED',use_alter=True))
    dag_id:Mapped[str]=mapped_column(ForeignKey('etl_definitions.dag_id',ondelete='RESTRICT'))
    etl_revision_id:Mapped[UUID]=mapped_column(ForeignKey('etl_definition_revisions.id',ondelete='RESTRICT'))
    physical_target_id:Mapped[str]=mapped_column(String(64))
    scope:Mapped[str]=mapped_column(String(16))
    scope_sha256:Mapped[str]=mapped_column(String(64))
    schedule_sha256:Mapped[str|None]=mapped_column(String(64))
    allow_empty:Mapped[bool]=mapped_column(default=False,server_default='false')
    allow_empty_acknowledged_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    acknowledged_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    state:Mapped[str]=mapped_column(String(16),default='GRANTED',server_default='GRANTED')
    reserved_intent_id:Mapped[UUID|None]
    consumed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    closed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    revoked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    invalidated_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    revision:Mapped[int]=mapped_column(Integer,default=1,server_default='1')


immutable_guard('replacement_authorizations',('id','dag_id','etl_revision_id','physical_target_id','scope','scope_sha256',
    'schedule_sha256','allow_empty','allow_empty_acknowledged_at','acknowledged_at'))
_RESERVATION="""CREATE OR REPLACE FUNCTION public.aat_auth_reservation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF OLD.reserved_intent_id IS NOT NULL AND NEW.reserved_intent_id IS DISTINCT FROM OLD.reserved_intent_id THEN
  RAISE EXCEPTION 'ONCE reservation cannot be transferred or released' USING ERRCODE='23514'; END IF;
 IF OLD.state<>'GRANTED' AND NEW.state='GRANTED' THEN
  RAISE EXCEPTION 'Authorization cannot be regranted' USING ERRCODE='23514'; END IF;
 NEW.revision=OLD.revision+1; RETURN NEW; END $$;
 CREATE TRIGGER aat_reservation BEFORE UPDATE ON replacement_authorizations FOR EACH ROW EXECUTE FUNCTION public.aat_auth_reservation();"""
event.listen(DataReplacementAuthorization.__table__,'after_create',DDL(_RESERVATION).execute_if(dialect='postgresql'))
_DAG_SCOPE="""CREATE OR REPLACE FUNCTION public.aat_authorization_dag() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM etl_definition_revisions r JOIN etl_definitions d ON d.id=r.definition_id
 WHERE r.id=NEW.etl_revision_id AND d.dag_id=NEW.dag_id) THEN
 RAISE EXCEPTION 'Authorization DAG and revision mismatch' USING ERRCODE='23514';END IF;
 RETURN NEW;END $$;
 CREATE TRIGGER aat_authorization_dag BEFORE INSERT ON replacement_authorizations FOR EACH ROW EXECUTE FUNCTION public.aat_authorization_dag();"""
event.listen(DataReplacementAuthorization.__table__,'after_create',DDL(_DAG_SCOPE).execute_if(dialect='postgresql'))
