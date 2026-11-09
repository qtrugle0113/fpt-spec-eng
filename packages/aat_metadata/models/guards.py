"""Reusable PostgreSQL guards, installed by production model DDL/migrations."""
from sqlalchemy import DDL, event
from .base import Base

SAFE_JSON_FUNCTION = """CREATE OR REPLACE FUNCTION public.aat_json_no_credentials(value jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$ DECLARE k text; v jsonb; BEGIN
 IF jsonb_typeof(value)='object' THEN
  FOR k,v IN SELECT * FROM jsonb_each(value) LOOP
   IF lower(k) IN ('password','passwd','ciphertext','credentials','credential','secret','token','dsn','access_token','private_key')
    OR NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;
  END LOOP;
 ELSIF jsonb_typeof(value)='array' THEN
  FOR v IN SELECT * FROM jsonb_array_elements(value) LOOP
   IF NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;
  END LOOP;
 ELSIF jsonb_typeof(value)='string' AND value#>>'{}' ~* '(postgres(ql)?|mysql)://|-----BEGIN .*PRIVATE KEY' THEN RETURN false;
 END IF; RETURN true;
END $$;"""
event.listen(Base.metadata,'before_create',DDL(SAFE_JSON_FUNCTION).execute_if(dialect='postgresql'))


def state_guard(table, transitions):
    """Database state graph; services still validate evidence before transitions."""
    clauses=' OR '.join("(OLD.state='"+old+"' AND NEW.state IN ("+','.join("'"+s+"'" for s in states)+"))" for old,states in transitions.items())
    ddl=f"""CREATE OR REPLACE FUNCTION public.aat_state_{table.name}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF NEW.state<>OLD.state AND NOT ({clauses}) THEN
      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
    CREATE TRIGGER aat_state BEFORE UPDATE ON {table.name} FOR EACH ROW EXECUTE FUNCTION public.aat_state_{table.name}();"""
    event.listen(table,'after_create',DDL(ddl).execute_if(dialect='postgresql'))


def safe_json_hash(table, config='config_json', digest='config_sha256'):
    ddl = f"""CREATE OR REPLACE FUNCTION public.aat_json_no_credentials(value jsonb)
    RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$ DECLARE k text; v jsonb; BEGIN
      IF jsonb_typeof(value)='object' THEN
        FOR k,v IN SELECT * FROM jsonb_each(value) LOOP
          IF lower(k) IN ('password','passwd','ciphertext','credential','credentials','secret','token','dsn','access_token','private_key')
            OR NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;
        END LOOP;
      ELSIF jsonb_typeof(value)='array' THEN
        FOR v IN SELECT * FROM jsonb_array_elements(value) LOOP
          IF NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;
        END LOOP;
      ELSIF jsonb_typeof(value)='string' AND value#>>'{{}}' ~* '(postgres(ql)?|mysql)://|-----BEGIN .*PRIVATE KEY' THEN
        RETURN false;
      END IF;
      RETURN true;
    END $$;
    CREATE OR REPLACE FUNCTION public.aat_hash_{table.name}() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE expected text; BEGIN
      IF jsonb_typeof(NEW.{config})<>'object' OR NOT public.aat_json_no_credentials(NEW.{config}) THEN
        RAISE EXCEPTION 'Unsafe canonical metadata' USING ERRCODE='23514'; END IF;
      expected=encode(sha256(convert_to(NEW.{config}::text,'UTF8')),'hex');
      IF NEW.{digest} IS NOT NULL AND NEW.{digest}<>expected THEN
        RAISE EXCEPTION 'Canonical metadata hash mismatch' USING ERRCODE='23514'; END IF;
      NEW.{digest}=expected; RETURN NEW;
    END $$;
    CREATE TRIGGER aat_hash BEFORE INSERT ON {table.name}
    FOR EACH ROW EXECUTE FUNCTION public.aat_hash_{table.name}();"""
    event.listen(table,'after_create',DDL(ddl).execute_if(dialect='postgresql'))
