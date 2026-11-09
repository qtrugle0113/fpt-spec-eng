"""Whitelisted application defaults; deployed config remains immutable."""
from datetime import datetime
from sqlalchemy import CheckConstraint,DateTime,Integer,String,DDL,event,text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from .base import Base


class ApplicationSetting(Base):
    __tablename__='application_settings'
    __table_args__=(CheckConstraint('revision>=1',name='ck_setting_revision'),
        CheckConstraint("key IN ('default_batch_size','dashboard_refresh_interval','default_timezone','staging_retention_days')",name='ck_setting_key'))
    key:Mapped[str]=mapped_column(String(64),primary_key=True)
    value_json:Mapped[object]=mapped_column(JSONB)
    value_type:Mapped[str]=mapped_column(String(16))
    revision:Mapped[int]=mapped_column(Integer,default=1,server_default='1')
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=text('now()'))


_SETTINGS="""CREATE OR REPLACE FUNCTION public.aat_setting_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE n integer; BEGIN
 IF NEW.key='default_timezone' THEN
  IF NEW.value_type<>'string' OR jsonb_typeof(NEW.value_json)<>'string' OR NOT EXISTS(
    SELECT 1 FROM pg_timezone_names WHERE name=NEW.value_json#>>'{}') THEN
   RAISE EXCEPTION 'Invalid timezone' USING ERRCODE='23514'; END IF;
 ELSE
  IF NEW.value_type<>'integer' OR jsonb_typeof(NEW.value_json)<>'number' OR NEW.value_json::text !~ '^[0-9]+$' THEN
   RAISE EXCEPTION 'Invalid integer setting' USING ERRCODE='23514'; END IF;
  n=(NEW.value_json::text)::integer;
  IF (NEW.key='default_batch_size' AND n NOT BETWEEN 1 AND 10000)
     OR (NEW.key='dashboard_refresh_interval' AND n NOT BETWEEN 5 AND 3600)
     OR (NEW.key='staging_retention_days' AND n NOT BETWEEN 1 AND 365) THEN
   RAISE EXCEPTION 'Setting outside range' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_OP='UPDATE' THEN NEW.revision=OLD.revision+1;NEW.updated_at=now();END IF;
 RETURN NEW; END $$;
 CREATE TRIGGER aat_setting_validate BEFORE INSERT OR UPDATE ON application_settings
 FOR EACH ROW EXECUTE FUNCTION public.aat_setting_validate();"""
event.listen(ApplicationSetting.__table__,'after_create',DDL(_SETTINGS).execute_if(dialect='postgresql'))
