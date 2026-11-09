"""Frozen initial app metadata DDL; no live model imports."""
from alembic import op
revision="0001_metadata"
down_revision=None
branch_labels=None
depends_on=None

STATEMENTS=('CREATE OR REPLACE FUNCTION public.aat_json_no_credentials(value jsonb)\n'
 'RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$ DECLARE k text; v jsonb; BEGIN\n'
 " IF jsonb_typeof(value)='object' THEN\n"
 '  FOR k,v IN SELECT * FROM jsonb_each(value) LOOP\n'
 '   IF lower(k) IN '
 "('password','passwd','ciphertext','credentials','credential','secret','token','dsn','access_token','private_key')\n"
 '    OR NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;\n'
 '  END LOOP;\n'
 " ELSIF jsonb_typeof(value)='array' THEN\n"
 '  FOR v IN SELECT * FROM jsonb_array_elements(value) LOOP\n'
 '   IF NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;\n'
 '  END LOOP;\n'
 " ELSIF jsonb_typeof(value)='string' AND value#>>'{}' ~* '(postgres(ql)?|mysql)://|-----BEGIN "
 ".*PRIVATE KEY' THEN RETURN false;\n"
 ' END IF; RETURN true;\n'
 'END $$;',
 '\n'
 'CREATE TABLE application_settings (\n'
 '\tkey VARCHAR(64) NOT NULL, \n'
 '\tvalue_json JSONB NOT NULL, \n'
 '\tvalue_type VARCHAR(16) NOT NULL, \n'
 "\trevision INTEGER DEFAULT '1' NOT NULL, \n"
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (key), \n'
 '\tCONSTRAINT ck_setting_revision CHECK (revision>=1), \n'
 '\tCONSTRAINT ck_setting_key CHECK (key IN '
 "('default_batch_size','dashboard_refresh_interval','default_timezone','staging_retention_days'))\n"
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_setting_validate() RETURNS trigger LANGUAGE plpgsql AS $$\n'
 'DECLARE n integer; BEGIN\n'
 " IF NEW.key='default_timezone' THEN\n"
 "  IF NEW.value_type<>'string' OR jsonb_typeof(NEW.value_json)<>'string' OR NOT EXISTS(\n"
 "    SELECT 1 FROM pg_timezone_names WHERE name=NEW.value_json#>>'{}') THEN\n"
 "   RAISE EXCEPTION 'Invalid timezone' USING ERRCODE='23514'; END IF;\n"
 ' ELSE\n'
 "  IF NEW.value_type<>'integer' OR jsonb_typeof(NEW.value_json)<>'number' OR NEW.value_json::text "
 "!~ '^[0-9]+$' THEN\n"
 "   RAISE EXCEPTION 'Invalid integer setting' USING ERRCODE='23514'; END IF;\n"
 '  n=(NEW.value_json::text)::integer;\n'
 "  IF (NEW.key='default_batch_size' AND n NOT BETWEEN 1 AND 10000)\n"
 "     OR (NEW.key='dashboard_refresh_interval' AND n NOT BETWEEN 5 AND 3600)\n"
 "     OR (NEW.key='staging_retention_days' AND n NOT BETWEEN 1 AND 365) THEN\n"
 "   RAISE EXCEPTION 'Setting outside range' USING ERRCODE='23514'; END IF;\n"
 ' END IF;\n'
 " IF TG_OP='UPDATE' THEN NEW.revision=OLD.revision+1;NEW.updated_at=now();END IF;\n"
 ' RETURN NEW; END $$;\n'
 ' CREATE TRIGGER aat_setting_validate BEFORE INSERT OR UPDATE ON application_settings\n'
 ' FOR EACH ROW EXECUTE FUNCTION public.aat_setting_validate();',
 '\n'
 'CREATE TABLE connection_secrets (\n'
 '\tid UUID NOT NULL, \n'
 '\tciphertext TEXT NOT NULL, \n'
 '\tkey_id VARCHAR(32) NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tretired_at TIMESTAMP WITH TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 "\tCONSTRAINT ck_connection_secret_key_id CHECK (key_id ~ '^[0-9a-f]{32}$'), \n"
 "\tCONSTRAINT ck_connection_secret_token CHECK (ciphertext ~ '^gA[A-Za-z0-9_-]+={0,2}$' AND "
 'length(ciphertext)>=100)\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_connection_secrets() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.ciphertext IS DISTINCT FROM OLD.ciphertext OR '
 'NEW.key_id IS DISTINCT FROM OLD.key_id THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON connection_secrets\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_connection_secrets();',
 '\n'
 'CREATE TABLE connections (\n'
 '\tid UUID NOT NULL, \n'
 '\tcode VARCHAR(64) NOT NULL, \n'
 '\tnormalized_code VARCHAR(64) GENERATED ALWAYS AS (lower(btrim(code))) STORED NOT NULL, \n'
 '\tname VARCHAR(255) NOT NULL, \n'
 '\tdatabase_type VARCHAR(16) NOT NULL, \n'
 '\tcurrent_revision_id UUID, \n'
 '\tdescription TEXT, \n'
 '\tdeleted_at TIMESTAMP WITH TIME ZONE, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_connections_normalized_code UNIQUE (normalized_code), \n'
 '\tCONSTRAINT ck_connections_code CHECK (length(btrim(code))>0), \n'
 '\tCONSTRAINT ck_connections_name CHECK (length(btrim(name))>0), \n'
 "\tCONSTRAINT ck_connections_database_type CHECK (database_type IN ('POSTGRESQL','MYSQL'))\n"
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE etl_definitions (\n'
 '\tdag_id VARCHAR(200) NOT NULL, \n'
 '\tcurrent_revision_id UUID, \n'
 "\towner VARCHAR(16) DEFAULT 'aat' NOT NULL, \n"
 "\tlifecycle VARCHAR(32) DEFAULT 'DRAFT' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (dag_id), \n'
 "\tCONSTRAINT ck_etl_dag CHECK (dag_id ~ '^[A-Za-z0-9_.-]{1,200}$'), \n"
 "\tCONSTRAINT ck_etl_owner CHECK (owner='aat')\n"
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE operations (\n'
 '\tkind VARCHAR(64) NOT NULL, \n'
 '\tidempotency_key VARCHAR(128) NOT NULL, \n'
 '\trequest_sha256 VARCHAR(64) NOT NULL, \n'
 "\tstate VARCHAR(32) DEFAULT 'QUEUED' NOT NULL, \n"
 "\tprogress_json JSONB DEFAULT '{}'::jsonb NOT NULL, \n"
 '\tresult_ref VARCHAR(255), \n'
 '\tdeadline_at TIMESTAMP WITH TIME ZONE, \n'
 '\tlease_owner VARCHAR(128), \n'
 '\tlease_until TIMESTAMP WITH TIME ZONE, \n'
 '\theartbeat_at TIMESTAMP WITH TIME ZONE, \n'
 "\tattempt INTEGER DEFAULT '0' NOT NULL, \n"
 '\terror_code VARCHAR(64), \n'
 '\terror_summary VARCHAR(255), \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (kind, idempotency_key), \n'
 '\tCONSTRAINT ck_operation_state CHECK (state IN '
 "('QUEUED','RUNNING','SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION')), \n"
 '\tCONSTRAINT ck_operation_attempt CHECK (attempt>=0), \n'
 "\tCONSTRAINT ck_operation_hash CHECK (request_sha256 ~ '^[0-9a-f]{64}$'), \n"
 '\tCONSTRAINT ck_operation_key CHECK (length(btrim(kind))>0 AND '
 'length(btrim(idempotency_key))>0), \n'
 '\tCONSTRAINT ck_operation_safe_progress CHECK (public.aat_json_no_credentials(progress_json))\n'
 ')\n'
 '\n',
 'CREATE INDEX ix_operation_claim ON operations (state, lease_until, created_at)',
 'CREATE OR REPLACE FUNCTION public.aat_state_operations() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 "    IF NEW.state<>OLD.state AND NOT ((OLD.state='QUEUED' AND NEW.state IN ('RUNNING','FAILED')) "
 "OR (OLD.state='RUNNING' AND NEW.state IN "
 "('SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION')) OR "
 "(OLD.state='NEEDS_RECONCILIATION' AND NEW.state IN "
 "('SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED'))) THEN\n"
 "      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 '    CREATE TRIGGER aat_state BEFORE UPDATE ON operations FOR EACH ROW EXECUTE FUNCTION '
 'public.aat_state_operations();',
 'CREATE OR REPLACE FUNCTION public.aat_guard_operations() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.kind IS DISTINCT FROM OLD.kind OR '
 'NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key OR NEW.request_sha256 IS DISTINCT FROM '
 'OLD.request_sha256 THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON operations\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_operations();',
 '\n'
 'CREATE TABLE uploaded_files (\n'
 '\toriginal_name VARCHAR(255) NOT NULL, \n'
 "\tsafe_storage_key VARCHAR(32) DEFAULT replace(gen_random_uuid()::text,'-','') NOT NULL, \n"
 '\tsha256 VARCHAR(64) NOT NULL, \n'
 '\tbytes BIGINT NOT NULL, \n'
 '\textension VARCHAR(8) NOT NULL, \n'
 '\tencoding VARCHAR(64), \n'
 '\tdelimiter VARCHAR(8), \n'
 '\theader_present BOOLEAN, \n'
 '\tquote_char VARCHAR(8), \n'
 '\tescape_char VARCHAR(8), \n'
 '\tnull_token VARCHAR(255), \n'
 "\tparser_revision INTEGER DEFAULT '1' NOT NULL, \n"
 "\tparser_file_id UUID GENERATED ALWAYS AS (CASE WHEN extension IN ('.csv','.txt') THEN id ELSE "
 'NULL END) STORED, \n'
 "\trevision INTEGER DEFAULT '1' NOT NULL, \n"
 "\tvalidation_status VARCHAR(16) DEFAULT 'PENDING' NOT NULL, \n"
 '\texpires_at TIMESTAMP WITH TIME ZONE, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_uploaded_files_storage UNIQUE (safe_storage_key), \n'
 '\tCONSTRAINT uq_uploaded_files_identity_checksum UNIQUE (id, sha256), \n'
 "\tCONSTRAINT ck_uploaded_files_storage CHECK (safe_storage_key ~ '^[0-9a-f]{32}$'), \n"
 "\tCONSTRAINT ck_uploaded_files_checksum CHECK (sha256 ~ '^[0-9a-f]{64}$'), \n"
 '\tCONSTRAINT ck_uploaded_files_bytes CHECK (bytes>=0), \n'
 "\tCONSTRAINT ck_uploaded_files_extension CHECK (extension IN ('.csv','.txt','.xlsx')), \n"
 '\tCONSTRAINT ck_uploaded_files_parser_revision CHECK (parser_revision>=1), \n'
 '\tCONSTRAINT ck_uploaded_files_revision CHECK (revision>=1), \n'
 '\tCONSTRAINT ck_uploaded_files_validation CHECK (validation_status IN '
 "('PENDING','VALID','INVALID'))\n"
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_uploaded_files() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.safe_storage_key IS DISTINCT FROM '
 'OLD.safe_storage_key OR NEW.sha256 IS DISTINCT FROM OLD.sha256 OR NEW.bytes IS DISTINCT FROM '
 'OLD.bytes OR NEW.original_name IS DISTINCT FROM OLD.original_name OR NEW.extension IS DISTINCT '
 'FROM OLD.extension OR NEW.encoding IS DISTINCT FROM OLD.encoding OR NEW.delimiter IS DISTINCT '
 'FROM OLD.delimiter OR NEW.header_present IS DISTINCT FROM OLD.header_present OR NEW.quote_char '
 'IS DISTINCT FROM OLD.quote_char OR NEW.escape_char IS DISTINCT FROM OLD.escape_char OR '
 'NEW.null_token IS DISTINCT FROM OLD.null_token THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON uploaded_files\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_uploaded_files();',
 'CREATE OR REPLACE FUNCTION public.aat_file_version()\n'
 'RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\n'
 " IF TG_OP='INSERT' THEN\n"
 '   IF NEW.revision<>1 OR NEW.parser_revision<>1 THEN\n'
 "     RAISE EXCEPTION 'File versions must start at one' USING ERRCODE='23514';\n"
 '   END IF;\n'
 ' ELSE\n'
 '   IF NEW.parser_revision<OLD.parser_revision\n'
 '      OR NEW.revision NOT IN (OLD.revision,OLD.revision+1) THEN\n'
 "     RAISE EXCEPTION 'File version cannot rewind or be forged' USING ERRCODE='23514';\n"
 '   END IF;\n'
 '   NEW.revision=OLD.revision+1;\n'
 ' END IF;\n'
 ' RETURN NEW;\n'
 'END $$;\n'
 'CREATE TRIGGER aat_file_version BEFORE INSERT OR UPDATE ON public.uploaded_files\n'
 'FOR EACH ROW EXECUTE FUNCTION public.aat_file_version();',
 '\n'
 'CREATE TABLE worker_heartbeats (\n'
 '\towner_process_id VARCHAR(128) NOT NULL, \n'
 '\theartbeat_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (owner_process_id)\n'
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE audit_events (\n'
 '\toperation_id UUID, \n'
 '\tsubject_type VARCHAR(64) NOT NULL, \n'
 '\tsubject_id UUID NOT NULL, \n'
 '\taction VARCHAR(64) NOT NULL, \n'
 '\trevision_before INTEGER, \n'
 '\trevision_after INTEGER, \n'
 "\tacknowledgment_scope JSONB DEFAULT '{}'::jsonb NOT NULL, \n"
 '\ttimestamp TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tsafe_summary VARCHAR(255) NOT NULL, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT ck_audit_safe_scope CHECK (public.aat_json_no_credentials(acknowledgment_scope)), \n'
 "\tCONSTRAINT ck_audit_summary_key CHECK (safe_summary ~ '^[A-Za-z][A-Za-z0-9_.-]{0,254}$'), \n"
 '\tFOREIGN KEY(operation_id) REFERENCES operations (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE INDEX ix_audit_timestamp ON audit_events (timestamp)',
 'CREATE OR REPLACE FUNCTION public.aat_guard_audit_events() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.operation_id IS DISTINCT FROM OLD.operation_id OR NEW.subject_type IS DISTINCT FROM '
 'OLD.subject_type OR NEW.subject_id IS DISTINCT FROM OLD.subject_id OR NEW.action IS DISTINCT '
 'FROM OLD.action OR NEW.revision_before IS DISTINCT FROM OLD.revision_before OR '
 'NEW.revision_after IS DISTINCT FROM OLD.revision_after OR NEW.acknowledgment_scope IS DISTINCT '
 'FROM OLD.acknowledgment_scope OR NEW.timestamp IS DISTINCT FROM OLD.timestamp OR '
 'NEW.safe_summary IS DISTINCT FROM OLD.safe_summary OR NEW.id IS DISTINCT FROM OLD.id OR '
 'NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.updated_at IS DISTINCT FROM OLD.updated_at '
 'THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON audit_events\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_audit_events();',
 '\n'
 'CREATE TABLE connection_revisions (\n'
 '\tid UUID NOT NULL, \n'
 '\tconnection_id UUID NOT NULL, \n'
 '\trevision INTEGER NOT NULL, \n'
 '\tdatabase_type VARCHAR(16) NOT NULL, \n'
 '\thost VARCHAR(255) NOT NULL, \n'
 '\tport INTEGER NOT NULL, \n'
 '\tdatabase_name VARCHAR(255) NOT NULL, \n'
 '\tschema_name VARCHAR(255), \n'
 '\tusername VARCHAR(255) NOT NULL, \n'
 '\tsecret_id UUID NOT NULL, \n'
 '\tphysical_server_fingerprint VARCHAR(64), \n'
 "\ttest_status VARCHAR(16) DEFAULT 'UNTESTED' NOT NULL, \n"
 '\ttested_at TIMESTAMP WITH TIME ZONE, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_connection_revisions_number UNIQUE (connection_id, revision), \n'
 '\tCONSTRAINT uq_connection_revisions_owner_id UNIQUE (connection_id, id), \n'
 '\tCONSTRAINT ck_connection_revisions_number CHECK (revision>=1), \n'
 '\tCONSTRAINT ck_connection_revisions_port CHECK (port BETWEEN 1 AND 65535), \n'
 '\tCONSTRAINT ck_connection_revisions_database_type CHECK (database_type IN '
 "('POSTGRESQL','MYSQL')), \n"
 '\tCONSTRAINT ck_connection_revisions_required_endpoint CHECK (length(btrim(host))>0 AND '
 'length(btrim(database_name))>0 AND length(btrim(username))>0), \n'
 '\tCONSTRAINT ck_connection_revisions_test_status CHECK (test_status IN '
 "('UNTESTED','SUCCESS','FAILED')), \n"
 '\tFOREIGN KEY(connection_id) REFERENCES connections (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(secret_id) REFERENCES connection_secrets (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_connection_revisions() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.connection_id IS DISTINCT FROM OLD.connection_id '
 'OR NEW.revision IS DISTINCT FROM OLD.revision OR NEW.database_type IS DISTINCT FROM '
 'OLD.database_type OR NEW.host IS DISTINCT FROM OLD.host OR NEW.port IS DISTINCT FROM OLD.port OR '
 'NEW.database_name IS DISTINCT FROM OLD.database_name OR NEW.schema_name IS DISTINCT FROM '
 'OLD.schema_name OR NEW.username IS DISTINCT FROM OLD.username OR NEW.secret_id IS DISTINCT FROM '
 'OLD.secret_id THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON connection_revisions\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_connection_revisions();',
 'CREATE OR REPLACE FUNCTION public.aat_guard_connection_code()\n'
 'RETURNS trigger LANGUAGE plpgsql AS $$\n'
 'DECLARE ref record; found boolean;\n'
 'BEGIN\n'
 '  IF NEW.code IS NOT DISTINCT FROM OLD.code THEN RETURN NEW; END IF;\n'
 '  FOR ref IN\n'
 '    SELECT fk.conrelid::regclass AS relation, child.attname AS column_name,\n'
 "           fk.confrelid='public.connections'::regclass AS direct\n"
 '    FROM pg_constraint fk\n'
 "    JOIN pg_attribute parent ON parent.attrelid=fk.confrelid AND parent.attname='id'\n"
 '    JOIN pg_attribute child ON child.attrelid=fk.conrelid\n'
 '      AND child.attnum=fk.conkey[array_position(fk.confkey,parent.attnum)]\n'
 "    WHERE fk.contype='f' AND parent.attnum=ANY(fk.confkey)\n"
 '      AND fk.confrelid IN '
 "('public.connections'::regclass,'public.connection_revisions'::regclass)\n"
 '      AND fk.conrelid NOT IN '
 "('public.connections'::regclass,'public.connection_revisions'::regclass)\n"
 '  LOOP\n'
 '    IF ref.direct THEN\n'
 "      EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s WHERE %I=$1)',ref.relation,ref.column_name) "
 'INTO found USING OLD.id;\n'
 '    ELSE\n'
 "      EXECUTE format('SELECT EXISTS(SELECT 1 FROM %s WHERE %I IN (SELECT id FROM "
 "public.connection_revisions WHERE connection_id=$1))',ref.relation,ref.column_name) INTO found "
 'USING OLD.id;\n'
 '    END IF;\n'
 "    IF found THEN RAISE EXCEPTION 'Connection code has dependencies' USING ERRCODE='23514'; END "
 'IF;\n'
 '  END LOOP;\n'
 '  RETURN NEW;\n'
 'END $$;\n'
 'CREATE TRIGGER aat_code_dependency BEFORE UPDATE OF code ON public.connections\n'
 'FOR EACH ROW EXECUTE FUNCTION public.aat_guard_connection_code();',
 '\n'
 'CREATE TABLE definition_uploads (\n'
 '\tkind VARCHAR(8) NOT NULL, \n'
 '\tuploaded_file_id UUID NOT NULL, \n'
 '\ttemplate_version VARCHAR(8), \n'
 '\tworkbook_sha256 VARCHAR(64) NOT NULL, \n'
 "\tstatus VARCHAR(16) DEFAULT 'UPLOADED' NOT NULL, \n"
 '\tvalidation_report_key VARCHAR(255), \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 "\tCONSTRAINT ck_definition_upload_kind CHECK (kind IN ('TABLE','ETL')), \n"
 '\tCONSTRAINT ck_definition_upload_version CHECK (template_version IS NULL OR '
 "template_version='1.0'), \n"
 '\tCONSTRAINT ck_definition_upload_status CHECK (status IN '
 "('UPLOADED','VALIDATING','VALIDATED','INVALID')), \n"
 "\tCONSTRAINT ck_definition_upload_validated_version CHECK (status<>'VALIDATED' OR "
 "template_version='1.0' AND template_version IS NOT NULL), \n"
 '\tCONSTRAINT fk_definition_upload_file_checksum FOREIGN KEY(uploaded_file_id, workbook_sha256) '
 'REFERENCES uploaded_files (id, sha256) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_definition_uploads() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.kind IS DISTINCT FROM OLD.kind OR '
 'NEW.uploaded_file_id IS DISTINCT FROM OLD.uploaded_file_id OR NEW.workbook_sha256 IS DISTINCT '
 'FROM OLD.workbook_sha256 THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON definition_uploads\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_definition_uploads();',
 '\n'
 'CREATE TABLE file_parser_revisions (\n'
 '\tid UUID NOT NULL, \n'
 '\tfile_id UUID NOT NULL, \n'
 '\trevision INTEGER NOT NULL, \n'
 '\tencoding VARCHAR(64) NOT NULL, \n'
 '\tdelimiter VARCHAR(8) NOT NULL, \n'
 '\theader_present BOOLEAN NOT NULL, \n'
 '\tquote_char VARCHAR(8) NOT NULL, \n'
 '\tescape_char VARCHAR, \n'
 '\tnull_token VARCHAR NOT NULL, \n'
 '\tconfig_sha256 VARCHAR(64) NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_file_parser_revision UNIQUE (file_id, revision), \n'
 '\tCONSTRAINT ck_file_parser_revision CHECK (revision>=1), \n'
 '\tCONSTRAINT ck_file_parser_encoding CHECK (length(btrim(encoding))>0), \n'
 '\tCONSTRAINT ck_file_parser_delimiter CHECK (length(delimiter)=1), \n'
 '\tCONSTRAINT ck_file_parser_quote CHECK (length(quote_char)=1), \n'
 "\tCONSTRAINT ck_file_parser_hash CHECK (config_sha256 ~ '^[0-9a-f]{64}$'), \n"
 '\tFOREIGN KEY(file_id) REFERENCES uploaded_files (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_file_parser_revisions() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.file_id IS DISTINCT FROM OLD.file_id OR '
 'NEW.revision IS DISTINCT FROM OLD.revision OR NEW.encoding IS DISTINCT FROM OLD.encoding OR '
 'NEW.delimiter IS DISTINCT FROM OLD.delimiter OR NEW.header_present IS DISTINCT FROM '
 'OLD.header_present OR NEW.quote_char IS DISTINCT FROM OLD.quote_char OR NEW.escape_char IS '
 'DISTINCT FROM OLD.escape_char OR NEW.null_token IS DISTINCT FROM OLD.null_token OR '
 'NEW.config_sha256 IS DISTINCT FROM OLD.config_sha256 OR NEW.created_at IS DISTINCT FROM '
 'OLD.created_at THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON file_parser_revisions\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_file_parser_revisions();',
 'CREATE OR REPLACE FUNCTION public.aat_parser_snapshot()\n'
 'RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE file public.uploaded_files; expected text;\n'
 'BEGIN\n'
 ' SELECT * INTO file FROM public.uploaded_files WHERE id=NEW.file_id FOR KEY SHARE;\n'
 ' IF FOUND THEN\n'
 "   IF file.extension NOT IN ('.csv','.txt') THEN\n"
 "     RAISE EXCEPTION 'Delimited parser requires CSV or TXT' USING ERRCODE='23514';\n"
 '   END IF;\n'
 '   IF NEW.revision=1 AND\n'
 '      '
 'ROW(NEW.encoding,NEW.delimiter,NEW.header_present,NEW.quote_char,NEW.escape_char,NEW.null_token)\n'
 '      IS DISTINCT FROM '
 'ROW(file.encoding,file.delimiter,file.header_present,file.quote_char,file.escape_char,file.null_token) '
 'THEN\n'
 "     RAISE EXCEPTION 'Initial parser must match original file snapshot' USING ERRCODE='23514';\n"
 '   END IF;\n'
 ' END IF;\n'
 ' '
 'expected=encode(sha256(convert_to(jsonb_build_array(NEW.encoding,NEW.delimiter,NEW.header_present,\n'
 "            NEW.quote_char,NEW.escape_char,NEW.null_token)::text,'UTF8')),'hex');\n"
 ' IF NEW.config_sha256 IS NOT NULL AND NEW.config_sha256<>expected THEN\n'
 "   RAISE EXCEPTION 'Parser configuration hash mismatch' USING ERRCODE='23514';\n"
 ' END IF;\n'
 ' NEW.config_sha256=expected;\n'
 ' RETURN NEW;\n'
 'END $$;\n'
 'CREATE TRIGGER aat_parser_snapshot BEFORE INSERT ON public.file_parser_revisions\n'
 'FOR EACH ROW EXECUTE FUNCTION public.aat_parser_snapshot();',
 '\n'
 'CREATE TABLE definition_issues (\n'
 '\tupload_id UUID NOT NULL, \n'
 '\tcode VARCHAR(128) NOT NULL, \n'
 '\tscope VARCHAR(16) NOT NULL, \n'
 '\tsheet VARCHAR(255), \n'
 '\trow INTEGER, \n'
 '\t"column" INTEGER, \n'
 '\tcolumn_name VARCHAR(255), \n'
 '\tseverity VARCHAR(8) NOT NULL, \n'
 '\tmessage_key VARCHAR(128) NOT NULL, \n'
 "\tsafe_context JSONB DEFAULT '{}'::jsonb NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 "\tCONSTRAINT ck_issue_scope CHECK (scope IN ('workbook','sheet','cell','resource')), \n"
 '\tCONSTRAINT ck_issue_row CHECK (row IS NULL OR row>=1), \n'
 '\tCONSTRAINT ck_issue_column CHECK ("column" IS NULL OR "column">=1), \n'
 "\tCONSTRAINT ck_issue_workbook_location CHECK (scope<>'workbook' OR sheet IS NULL AND row IS "
 'NULL AND "column" IS NULL AND column_name IS NULL), \n'
 "\tCONSTRAINT ck_issue_cell_location CHECK (scope<>'cell' OR sheet IS NOT NULL AND row IS NOT "
 'NULL AND "column" IS NOT NULL), \n'
 "\tCONSTRAINT ck_issue_severity CHECK (severity IN ('ERROR','WARNING','INFO')), \n"
 "\tCONSTRAINT ck_issue_message_key CHECK (message_key ~ '^[A-Za-z][A-Za-z0-9_.-]*$'), \n"
 "\tCONSTRAINT ck_issue_safe_context_keys CHECK (jsonb_typeof(safe_context)='object' AND "
 "safe_context - ARRAY['count','limit','expected_type','actual_type'] = '{}'::jsonb), \n"
 "\tCONSTRAINT ck_issue_safe_context_counts CHECK ((NOT safe_context ? 'count' OR "
 "jsonb_typeof(safe_context->'count')='number' AND safe_context->>'count' ~ '^[0-9]+$') AND (NOT "
 "safe_context ? 'limit' OR jsonb_typeof(safe_context->'limit')='number' AND "
 "safe_context->>'limit' ~ '^[0-9]+$')), \n"
 "\tCONSTRAINT ck_issue_safe_context_types CHECK ((NOT safe_context ? 'expected_type' OR "
 "safe_context->>'expected_type' IN "
 "('string','number','boolean','null','object','array','integer','bigint','decimal','varchar','text','date','timestamp')) "
 "AND (NOT safe_context ? 'actual_type' OR safe_context->>'actual_type' IN "
 "('string','number','boolean','null','object','array','integer','bigint','decimal','varchar','text','date','timestamp'))), \n"
 '\tFOREIGN KEY(upload_id) REFERENCES definition_uploads (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE etl_definition_revisions (\n'
 '\tdefinition_id UUID NOT NULL, \n'
 '\trevision INTEGER NOT NULL, \n'
 '\tupload_id UUID NOT NULL, \n'
 '\tconfig_json JSONB NOT NULL, \n'
 '\tconfig_sha256 VARCHAR(64) NOT NULL, \n'
 '\tschema_fingerprint_source VARCHAR(64), \n'
 '\tschema_fingerprint_target VARCHAR(64), \n'
 '\tdependency_fingerprint VARCHAR(64), \n'
 "\tstatus VARCHAR(32) DEFAULT 'DRAFT' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (definition_id, revision), \n'
 '\tUNIQUE (definition_id, id), \n'
 '\tUNIQUE (definition_id, config_sha256), \n'
 '\tCONSTRAINT ck_etl_revision CHECK (revision>=1), \n'
 "\tCONSTRAINT ck_etl_config_hash CHECK (config_sha256 ~ '^[0-9a-f]{64}$'), \n"
 '\tFOREIGN KEY(definition_id) REFERENCES etl_definitions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(upload_id) REFERENCES definition_uploads (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_json_no_credentials(value jsonb)\n'
 '    RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$ DECLARE k text; v jsonb; BEGIN\n'
 "      IF jsonb_typeof(value)='object' THEN\n"
 '        FOR k,v IN SELECT * FROM jsonb_each(value) LOOP\n'
 '          IF lower(k) IN '
 "('password','passwd','ciphertext','credential','credentials','secret','token','dsn','access_token','private_key')\n"
 '            OR NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;\n'
 '        END LOOP;\n'
 "      ELSIF jsonb_typeof(value)='array' THEN\n"
 '        FOR v IN SELECT * FROM jsonb_array_elements(value) LOOP\n'
 '          IF NOT public.aat_json_no_credentials(v) THEN RETURN false; END IF;\n'
 '        END LOOP;\n'
 "      ELSIF jsonb_typeof(value)='string' AND value#>>'{}' ~* "
 "'(postgres(ql)?|mysql)://|-----BEGIN .*PRIVATE KEY' THEN\n"
 '        RETURN false;\n'
 '      END IF;\n'
 '      RETURN true;\n'
 '    END $$;\n'
 '    CREATE OR REPLACE FUNCTION public.aat_hash_etl_definition_revisions() RETURNS trigger '
 'LANGUAGE plpgsql AS $$\n'
 '    DECLARE expected text; BEGIN\n'
 "      IF jsonb_typeof(NEW.config_json)<>'object' OR NOT "
 'public.aat_json_no_credentials(NEW.config_json) THEN\n'
 "        RAISE EXCEPTION 'Unsafe canonical metadata' USING ERRCODE='23514'; END IF;\n"
 "      expected=encode(sha256(convert_to(NEW.config_json::text,'UTF8')),'hex');\n"
 '      IF NEW.config_sha256 IS NOT NULL AND NEW.config_sha256<>expected THEN\n'
 "        RAISE EXCEPTION 'Canonical metadata hash mismatch' USING ERRCODE='23514'; END IF;\n"
 '      NEW.config_sha256=expected; RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_hash BEFORE INSERT ON etl_definition_revisions\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_hash_etl_definition_revisions();',
 'CREATE OR REPLACE FUNCTION public.aat_guard_etl_definition_revisions() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.definition_id IS DISTINCT FROM OLD.definition_id '
 'OR NEW.revision IS DISTINCT FROM OLD.revision OR NEW.upload_id IS DISTINCT FROM OLD.upload_id OR '
 'NEW.config_json IS DISTINCT FROM OLD.config_json OR NEW.config_sha256 IS DISTINCT FROM '
 'OLD.config_sha256 OR NEW.schema_fingerprint_source IS DISTINCT FROM '
 'OLD.schema_fingerprint_source OR NEW.schema_fingerprint_target IS DISTINCT FROM '
 'OLD.schema_fingerprint_target OR NEW.dependency_fingerprint IS DISTINCT FROM '
 'OLD.dependency_fingerprint OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON etl_definition_revisions\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_etl_definition_revisions();',
 '\n'
 'CREATE TABLE table_creation_jobs (\n'
 '\toperation_id UUID NOT NULL, \n'
 '\tupload_id UUID NOT NULL, \n'
 '\tconfirmation_hash VARCHAR(64) NOT NULL, \n'
 '\ttarget_revision_id UUID NOT NULL, \n'
 '\tstarted_at TIMESTAMP WITH TIME ZONE, \n'
 '\tfinished_at TIMESTAMP WITH TIME ZONE, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (operation_id), \n'
 '\tFOREIGN KEY(operation_id) REFERENCES operations (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(upload_id) REFERENCES definition_uploads (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(target_revision_id) REFERENCES connection_revisions (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_job_validated() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 " IF NOT EXISTS(SELECT 1 FROM definition_uploads WHERE id=NEW.upload_id AND status='VALIDATED') "
 'THEN\n'
 " RAISE EXCEPTION 'Validated upload required' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;\n"
 ' CREATE TRIGGER aat_job_validated BEFORE INSERT ON table_creation_jobs FOR EACH ROW EXECUTE '
 'FUNCTION public.aat_job_validated();',
 '\n'
 'CREATE TABLE table_definitions (\n'
 '\tupload_id UUID NOT NULL, \n'
 '\ttarget_connection_revision_id UUID NOT NULL, \n'
 '\ttarget_schema VARCHAR(255) NOT NULL, \n'
 '\ttable_name VARCHAR(255) NOT NULL, \n'
 '\tphysical_table_identity TEXT NOT NULL, \n'
 '\tdescription TEXT, \n'
 '\tdefinition_hash VARCHAR(64) NOT NULL, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_table_definition_upload_physical UNIQUE (upload_id, physical_table_identity), \n'
 '\tCONSTRAINT ck_table_definition_names CHECK (length(btrim(target_schema))>0 AND '
 'length(btrim(table_name))>0), \n'
 "\tCONSTRAINT ck_table_definition_hash CHECK (definition_hash ~ '^[0-9a-f]{64}$'), \n"
 '\tFOREIGN KEY(upload_id) REFERENCES definition_uploads (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(target_connection_revision_id) REFERENCES connection_revisions (id) ON DELETE '
 'RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_table_physical_identity()\n'
 'RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE fingerprint text; database_name text;\n'
 'BEGIN\n'
 ' SELECT r.physical_server_fingerprint,r.database_name INTO fingerprint,database_name\n'
 ' FROM public.connection_revisions r WHERE r.id=NEW.target_connection_revision_id;\n'
 " IF fingerprint IS NULL OR fingerprint !~ '^[0-9a-f]{64}$' THEN\n"
 "   RAISE EXCEPTION 'Verified physical server identity required' USING ERRCODE='23514';\n"
 ' END IF;\n'
 ' '
 'NEW.physical_table_identity=jsonb_build_array(fingerprint,database_name,NEW.target_schema,NEW.table_name)::text;\n'
 ' RETURN NEW;\n'
 'END $$;\n'
 'CREATE TRIGGER aat_physical_identity BEFORE INSERT OR UPDATE ON public.table_definitions\n'
 'FOR EACH ROW EXECUTE FUNCTION public.aat_table_physical_identity();',
 '\n'
 'CREATE TABLE column_mappings (\n'
 '\tetl_revision_id UUID NOT NULL, \n'
 '\tordinal INTEGER NOT NULL, \n'
 '\tsource_column VARCHAR(255), \n'
 '\ttarget_column VARCHAR(255) NOT NULL, \n'
 '\ttransformation VARCHAR(32) NOT NULL, \n'
 '\tdefault_literal JSONB, \n'
 '\tenabled BOOLEAN NOT NULL, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (etl_revision_id, ordinal), \n'
 '\tCONSTRAINT ck_mapping_ordinal CHECK (ordinal>=1), \n'
 '\tCONSTRAINT ck_mapping_target CHECK (length(btrim(target_column))>0), \n'
 '\tCONSTRAINT ck_mapping_transform CHECK (transformation IN '
 "('DIRECT','CONSTANT','NULL_HANDLING','TYPE_CONVERSION')), \n"
 "\tCONSTRAINT ck_mapping_source CHECK (NOT enabled OR transformation='CONSTANT' OR source_column "
 'IS NOT NULL AND length(btrim(source_column))>0), \n'
 '\tCONSTRAINT ck_mapping_literal CHECK (NOT enabled OR transformation NOT IN '
 "('CONSTANT','NULL_HANDLING') OR default_literal IS NOT NULL), \n"
 '\tCONSTRAINT ck_mapping_tagged_literal CHECK (default_literal IS NULL OR '
 "jsonb_typeof(default_literal)='object' AND default_literal ?& ARRAY['logical_type','value'] AND "
 "default_literal-ARRAY['logical_type','value']='{}'::jsonb), \n"
 '\tFOREIGN KEY(etl_revision_id) REFERENCES etl_definition_revisions (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE UNIQUE INDEX uq_mapping_enabled_target ON column_mappings (etl_revision_id, '
 'target_column) WHERE enabled',
 'CREATE OR REPLACE FUNCTION public.aat_guard_column_mappings() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.etl_revision_id IS DISTINCT FROM '
 'OLD.etl_revision_id OR NEW.ordinal IS DISTINCT FROM OLD.ordinal OR NEW.source_column IS DISTINCT '
 'FROM OLD.source_column OR NEW.target_column IS DISTINCT FROM OLD.target_column OR '
 'NEW.transformation IS DISTINCT FROM OLD.transformation OR NEW.default_literal IS DISTINCT FROM '
 'OLD.default_literal OR NEW.enabled IS DISTINCT FROM OLD.enabled THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON column_mappings\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_column_mappings();',
 '\n'
 'CREATE TABLE dag_deployments (\n'
 '\toperation_id UUID NOT NULL, \n'
 '\tetl_revision_id UUID NOT NULL, \n'
 '\tdag_id VARCHAR(200) NOT NULL, \n'
 '\tprevious_deployment_id UUID, \n'
 '\tstate VARCHAR(32) NOT NULL, \n'
 '\trevision_sha256 VARCHAR(64) NOT NULL, \n'
 '\tgenerated_file_key VARCHAR(255), \n'
 '\tfile_sha256 VARCHAR(64), \n'
 '\tprevious_file_sha256 VARCHAR(64), \n'
 "\texpected_owner_tag VARCHAR(64) DEFAULT 'aat' NOT NULL, \n"
 '\tparsed_at TIMESTAMP WITH TIME ZONE, \n'
 '\tairflow_version_id UUID, \n'
 '\tairflow_version_number INTEGER, \n'
 '\tlast_verified_at TIMESTAMP WITH TIME ZONE, \n'
 '\tprevious_paused BOOLEAN, \n'
 "\treconcile_required BOOLEAN DEFAULT 'false' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT ck_deployment_state CHECK (state IN '
 "('VALIDATION_FAILED','READY_TO_DEPLOY','DEPLOYMENT_PENDING','DEPLOYED','DEPLOYMENT_FAILED','PARSE_ERROR')), \n"
 '\tUNIQUE (operation_id), \n'
 '\tFOREIGN KEY(operation_id) REFERENCES operations (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(etl_revision_id) REFERENCES etl_definition_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(dag_id) REFERENCES etl_definitions (dag_id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(previous_deployment_id) REFERENCES dag_deployments (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE INDEX ix_deployment_dag_created ON dag_deployments (dag_id, created_at)',
 'CREATE UNIQUE INDEX uq_deployment_active_dag ON dag_deployments (dag_id) WHERE state IN '
 "('READY_TO_DEPLOY','DEPLOYMENT_PENDING')",
 'CREATE OR REPLACE FUNCTION public.aat_state_dag_deployments() RETURNS trigger LANGUAGE plpgsql '
 'AS $$ BEGIN\n'
 "    IF NEW.state<>OLD.state AND NOT ((OLD.state='VALIDATION_FAILED' AND NEW.state IN "
 "('READY_TO_DEPLOY')) OR (OLD.state='READY_TO_DEPLOY' AND NEW.state IN "
 "('DEPLOYMENT_PENDING','VALIDATION_FAILED','DEPLOYMENT_FAILED')) OR "
 "(OLD.state='DEPLOYMENT_PENDING' AND NEW.state IN "
 "('DEPLOYED','DEPLOYMENT_FAILED','PARSE_ERROR'))) THEN\n"
 "      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 '    CREATE TRIGGER aat_state BEFORE UPDATE ON dag_deployments FOR EACH ROW EXECUTE FUNCTION '
 'public.aat_state_dag_deployments();',
 'CREATE OR REPLACE FUNCTION public.aat_deployment_dag() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 ' SELECT d.dag_id INTO NEW.dag_id FROM etl_definitions d JOIN etl_definition_revisions r ON '
 'r.definition_id=d.id WHERE r.id=NEW.etl_revision_id;\n'
 ' RETURN NEW; END $$;\n'
 ' CREATE TRIGGER aat_deployment_dag BEFORE INSERT OR UPDATE ON dag_deployments FOR EACH ROW '
 'EXECUTE FUNCTION public.aat_deployment_dag();',
 '\n'
 'CREATE TABLE replacement_authorizations (\n'
 '\tdag_id VARCHAR(200) NOT NULL, \n'
 '\tetl_revision_id UUID NOT NULL, \n'
 '\tphysical_target_id VARCHAR(64) NOT NULL, \n'
 '\tscope VARCHAR(16) NOT NULL, \n'
 '\tscope_sha256 VARCHAR(64) NOT NULL, \n'
 '\tschedule_sha256 VARCHAR(64), \n'
 "\tallow_empty BOOLEAN DEFAULT 'false' NOT NULL, \n"
 '\tallow_empty_acknowledged_at TIMESTAMP WITH TIME ZONE, \n'
 '\tacknowledged_at TIMESTAMP WITH TIME ZONE NOT NULL, \n'
 "\tstate VARCHAR(16) DEFAULT 'GRANTED' NOT NULL, \n"
 '\treserved_intent_id UUID, \n'
 '\tconsumed_at TIMESTAMP WITH TIME ZONE, \n'
 '\tclosed_at TIMESTAMP WITH TIME ZONE, \n'
 '\trevoked_at TIMESTAMP WITH TIME ZONE, \n'
 '\tinvalidated_at TIMESTAMP WITH TIME ZONE, \n'
 "\trevision INTEGER DEFAULT '1' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 "\tCONSTRAINT ck_auth_scope CHECK (scope IN ('ONCE','SCHEDULED')), \n"
 '\tCONSTRAINT ck_auth_state CHECK (state IN '
 "('GRANTED','RESERVED','CONSUMED','CLOSED','REVOKED','INVALIDATED')), \n"
 "\tCONSTRAINT ck_auth_hash CHECK (scope_sha256 ~ '^[0-9a-f]{64}$' AND physical_target_id ~ "
 "'^[0-9a-f]{64}$'), \n"
 "\tCONSTRAINT ck_auth_schedule CHECK ((scope='SCHEDULED' AND schedule_sha256 ~ '^[0-9a-f]{64}$' "
 "AND schedule_sha256 IS NOT NULL) OR (scope='ONCE' AND schedule_sha256 IS NULL)), \n"
 '\tCONSTRAINT ck_auth_empty_ack CHECK (NOT allow_empty OR allow_empty_acknowledged_at IS NOT '
 'NULL), \n'
 '\tCONSTRAINT ck_auth_revision CHECK (revision>=1), \n'
 "\tCONSTRAINT ck_auth_reserved CHECK (state<>'RESERVED' OR scope='ONCE' AND reserved_intent_id IS "
 'NOT NULL), \n'
 '\tFOREIGN KEY(dag_id) REFERENCES etl_definitions (dag_id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(etl_revision_id) REFERENCES etl_definition_revisions (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_replacement_authorizations() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.dag_id IS DISTINCT FROM OLD.dag_id OR '
 'NEW.etl_revision_id IS DISTINCT FROM OLD.etl_revision_id OR NEW.physical_target_id IS DISTINCT '
 'FROM OLD.physical_target_id OR NEW.scope IS DISTINCT FROM OLD.scope OR NEW.scope_sha256 IS '
 'DISTINCT FROM OLD.scope_sha256 OR NEW.schedule_sha256 IS DISTINCT FROM OLD.schedule_sha256 OR '
 'NEW.allow_empty IS DISTINCT FROM OLD.allow_empty OR NEW.allow_empty_acknowledged_at IS DISTINCT '
 'FROM OLD.allow_empty_acknowledged_at OR NEW.acknowledged_at IS DISTINCT FROM OLD.acknowledged_at '
 'THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON replacement_authorizations\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_replacement_authorizations();',
 'CREATE OR REPLACE FUNCTION public.aat_auth_reservation() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 ' IF OLD.reserved_intent_id IS NOT NULL AND NEW.reserved_intent_id IS DISTINCT FROM '
 'OLD.reserved_intent_id THEN\n'
 "  RAISE EXCEPTION 'ONCE reservation cannot be transferred or released' USING ERRCODE='23514'; "
 'END IF;\n'
 " IF OLD.state<>'GRANTED' AND NEW.state='GRANTED' THEN\n"
 "  RAISE EXCEPTION 'Authorization cannot be regranted' USING ERRCODE='23514'; END IF;\n"
 ' NEW.revision=OLD.revision+1; RETURN NEW; END $$;\n'
 ' CREATE TRIGGER aat_reservation BEFORE UPDATE ON replacement_authorizations FOR EACH ROW EXECUTE '
 'FUNCTION public.aat_auth_reservation();',
 'CREATE OR REPLACE FUNCTION public.aat_authorization_dag() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 ' IF NOT EXISTS(SELECT 1 FROM etl_definition_revisions r JOIN etl_definitions d ON '
 'd.id=r.definition_id\n'
 ' WHERE r.id=NEW.etl_revision_id AND d.dag_id=NEW.dag_id) THEN\n'
 " RAISE EXCEPTION 'Authorization DAG and revision mismatch' USING ERRCODE='23514';END IF;\n"
 ' RETURN NEW;END $$;\n'
 ' CREATE TRIGGER aat_authorization_dag BEFORE INSERT ON replacement_authorizations FOR EACH ROW '
 'EXECUTE FUNCTION public.aat_authorization_dag();',
 '\n'
 'CREATE TABLE table_columns (\n'
 '\ttable_definition_id UUID NOT NULL, \n'
 '\tname VARCHAR(255) NOT NULL, \n'
 '\tordinal INTEGER NOT NULL, \n'
 '\tlogical_type VARCHAR(16) NOT NULL, \n'
 '\tlength INTEGER, \n'
 '\tprecision INTEGER, \n'
 '\tscale INTEGER, \n'
 '\tnullable BOOLEAN NOT NULL, \n'
 '\tprimary_key_ordinal INTEGER, \n'
 '\tdefault_literal JSONB, \n'
 '\tdescription TEXT, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT uq_table_column_name UNIQUE (table_definition_id, name), \n'
 '\tCONSTRAINT uq_table_column_ordinal UNIQUE (table_definition_id, ordinal), \n'
 '\tCONSTRAINT uq_table_column_pk_ordinal UNIQUE (table_definition_id, primary_key_ordinal), \n'
 '\tCONSTRAINT ck_table_column_ordinal CHECK (ordinal BETWEEN 1 AND 1000), \n'
 '\tCONSTRAINT ck_table_column_name CHECK (length(btrim(name))>0), \n'
 '\tCONSTRAINT ck_table_column_type CHECK (logical_type IN '
 "('integer','bigint','varchar','text','decimal','boolean','date','timestamp')), \n"
 "\tCONSTRAINT ck_table_column_length CHECK ((logical_type='varchar' AND length IS NOT NULL AND "
 "length BETWEEN 1 AND 65535) OR (logical_type<>'varchar' AND length IS NULL)), \n"
 "\tCONSTRAINT ck_table_column_decimal CHECK ((logical_type='decimal' AND precision IS NOT NULL "
 'AND scale IS NOT NULL AND precision BETWEEN 1 AND 38 AND scale BETWEEN 0 AND precision) OR '
 "(logical_type<>'decimal' AND precision IS NULL AND scale IS NULL)), \n"
 '\tCONSTRAINT ck_table_column_pk CHECK (primary_key_ordinal IS NULL OR primary_key_ordinal>=1 AND '
 'NOT nullable), \n'
 '\tCONSTRAINT ck_table_column_default CHECK (default_literal IS NULL OR (\n'
 " jsonb_typeof(default_literal)='object'\n"
 " AND default_literal ?& ARRAY['logical_type','value']\n"
 " AND default_literal - ARRAY['logical_type','value']='{}'::jsonb\n"
 " AND jsonb_typeof(default_literal->'logical_type')='string'\n"
 " AND default_literal->>'logical_type'=logical_type\n"
 " AND CASE WHEN default_literal->'value'='null'::jsonb THEN nullable\n"
 " WHEN logical_type IN ('integer','bigint') THEN jsonb_typeof(default_literal->'value')='number' "
 "AND default_literal->>'value' ~ '^-?[0-9]+$'\n"
 " WHEN logical_type='boolean' THEN jsonb_typeof(default_literal->'value')='boolean'\n"
 " ELSE jsonb_typeof(default_literal->'value')='string' END)), \n"
 '\tFOREIGN KEY(table_definition_id) REFERENCES table_definitions (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_table_pk_order()\n'
 'RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN\n'
 ' IF NEW.primary_key_ordinal IS NOT NULL AND EXISTS(\n'
 '   SELECT 1 FROM public.table_columns c WHERE c.table_definition_id=NEW.table_definition_id\n'
 '    AND c.id<>NEW.id AND c.primary_key_ordinal IS NOT NULL\n'
 '    AND ((c.ordinal<NEW.ordinal AND c.primary_key_ordinal>=NEW.primary_key_ordinal)\n'
 '      OR (c.ordinal>NEW.ordinal AND c.primary_key_ordinal<=NEW.primary_key_ordinal))) THEN\n'
 "   RAISE EXCEPTION 'Primary key order must follow column order' USING ERRCODE='23514';\n"
 ' END IF;\n'
 ' RETURN NEW;\n'
 'END $$;\n'
 'CREATE TRIGGER aat_pk_order BEFORE INSERT OR UPDATE ON public.table_columns\n'
 'FOR EACH ROW EXECUTE FUNCTION public.aat_table_pk_order();',
 '\n'
 'CREATE TABLE table_creation_results (\n'
 '\tjob_id UUID NOT NULL, \n'
 '\ttable_definition_id UUID NOT NULL, \n'
 "\tstate VARCHAR(32) DEFAULT 'PENDING' NOT NULL, \n"
 '\tddl_text TEXT, \n'
 '\tddl_sha256 VARCHAR(64), \n'
 '\tstarted_at TIMESTAMP WITH TIME ZONE, \n'
 '\tfinished_at TIMESTAMP WITH TIME ZONE, \n'
 '\terror_code VARCHAR(64), \n'
 '\tsafe_error VARCHAR(255), \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (job_id, table_definition_id), \n'
 '\tCONSTRAINT ck_table_result_state CHECK (state IN '
 "('PENDING','CREATING','CREATED','ALREADY_EXISTS','FAILED','UNKNOWN')), \n"
 '\tFOREIGN KEY(job_id) REFERENCES table_creation_jobs (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(table_definition_id) REFERENCES table_definitions (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_state_table_creation_results() RETURNS trigger LANGUAGE '
 'plpgsql AS $$ BEGIN\n'
 "    IF NEW.state<>OLD.state AND NOT ((OLD.state='PENDING' AND NEW.state IN ('CREATING')) OR "
 "(OLD.state='CREATING' AND NEW.state IN ('CREATED','ALREADY_EXISTS','FAILED','UNKNOWN')) OR "
 "(OLD.state='UNKNOWN' AND NEW.state IN ('CREATED','ALREADY_EXISTS','FAILED'))) THEN\n"
 "      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 '    CREATE TRIGGER aat_state BEFORE UPDATE ON table_creation_results FOR EACH ROW EXECUTE '
 'FUNCTION public.aat_state_table_creation_results();',
 '\n'
 'CREATE TABLE dag_admission (\n'
 '\tdag_id VARCHAR(200) NOT NULL, \n'
 "\tgeneration INTEGER DEFAULT '1' NOT NULL, \n"
 "\tdesired_paused BOOLEAN DEFAULT 'true' NOT NULL, \n"
 "\tgate_state VARCHAR(16) DEFAULT 'BLOCKED' NOT NULL, \n"
 '\treason VARCHAR(128), \n'
 '\tetl_revision_id UUID, \n'
 '\tdeployment_id UUID, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 "\tCONSTRAINT ck_dag_gate CHECK (gate_state IN ('OPEN','BLOCKED')), \n"
 '\tCONSTRAINT ck_dag_generation CHECK (generation>=1), \n'
 '\tUNIQUE (dag_id), \n'
 '\tFOREIGN KEY(dag_id) REFERENCES etl_definitions (dag_id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(etl_revision_id) REFERENCES etl_definition_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(deployment_id) REFERENCES dag_deployments (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE execution_bindings (\n'
 '\tdag_id VARCHAR(200) NOT NULL, \n'
 '\tairflow_run_id VARCHAR(255) NOT NULL, \n'
 '\ttask_id VARCHAR(200) NOT NULL, \n'
 '\tairflow_dag_version_id VARCHAR(64) NOT NULL, \n'
 '\tetl_revision_id UUID NOT NULL, \n'
 '\tsource_revision_id UUID, \n'
 '\ttarget_revision_id UUID NOT NULL, \n'
 '\tfile_parser_revision UUID, \n'
 '\tsource_file_sha256 VARCHAR(64), \n'
 '\tauthorization_id UUID, \n'
 '\trun_intent_id UUID NOT NULL, \n'
 '\tairflow_run_type VARCHAR(16) NOT NULL, \n'
 '\tdataset_id UUID, \n'
 '\truntime_build VARCHAR(128) NOT NULL, \n'
 '\tbinding_hash VARCHAR(64) NOT NULL, \n'
 "\tstate VARCHAR(32) DEFAULT 'BOUND' NOT NULL, \n"
 "\tcommit_uncertain BOOLEAN DEFAULT 'false' NOT NULL, \n"
 '\tlast_reconciled_at TIMESTAMP WITH TIME ZONE, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (dag_id, airflow_run_id), \n'
 "\tCONSTRAINT ck_binding_run_type CHECK (airflow_run_type IN ('manual','scheduled')), \n"
 "\tCONSTRAINT ck_binding_hash CHECK (binding_hash ~ '^[0-9a-f]{64}$'), \n"
 '\tFOREIGN KEY(dag_id) REFERENCES etl_definitions (dag_id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(etl_revision_id) REFERENCES etl_definition_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(source_revision_id) REFERENCES connection_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(target_revision_id) REFERENCES connection_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(file_parser_revision) REFERENCES file_parser_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(authorization_id) REFERENCES replacement_authorizations (id) ON DELETE RESTRICT, \n'
 '\tUNIQUE (run_intent_id)\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_execution_bindings() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.dag_id IS DISTINCT FROM OLD.dag_id OR '
 'NEW.airflow_run_id IS DISTINCT FROM OLD.airflow_run_id OR NEW.task_id IS DISTINCT FROM '
 'OLD.task_id OR NEW.airflow_dag_version_id IS DISTINCT FROM OLD.airflow_dag_version_id OR '
 'NEW.etl_revision_id IS DISTINCT FROM OLD.etl_revision_id OR NEW.source_revision_id IS DISTINCT '
 'FROM OLD.source_revision_id OR NEW.target_revision_id IS DISTINCT FROM OLD.target_revision_id OR '
 'NEW.file_parser_revision IS DISTINCT FROM OLD.file_parser_revision OR NEW.source_file_sha256 IS '
 'DISTINCT FROM OLD.source_file_sha256 OR NEW.authorization_id IS DISTINCT FROM '
 'OLD.authorization_id OR NEW.run_intent_id IS DISTINCT FROM OLD.run_intent_id OR '
 'NEW.airflow_run_type IS DISTINCT FROM OLD.airflow_run_type OR NEW.runtime_build IS DISTINCT FROM '
 'OLD.runtime_build OR NEW.binding_hash IS DISTINCT FROM OLD.binding_hash THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON execution_bindings\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_execution_bindings();',
 'CREATE OR REPLACE FUNCTION public.aat_binding_dataset_once() RETURNS trigger LANGUAGE plpgsql AS '
 '$$ BEGIN\n'
 ' IF OLD.dataset_id IS NOT NULL AND NEW.dataset_id IS DISTINCT FROM OLD.dataset_id AND EXISTS(\n'
 " SELECT 1 FROM dataset_manifests WHERE id=OLD.dataset_id AND state<>'INCOMPLETE') THEN\n"
 " RAISE EXCEPTION 'Complete binding dataset cannot change' USING ERRCODE='23514'; END IF;\n"
 ' RETURN NEW;END $$;\n'
 ' CREATE TRIGGER aat_dataset_once BEFORE UPDATE ON execution_bindings FOR EACH ROW EXECUTE '
 'FUNCTION public.aat_binding_dataset_once();',
 '\n'
 'CREATE TABLE run_intents (\n'
 '\toperation_id UUID NOT NULL, \n'
 '\trun_uuid UUID NOT NULL, \n'
 '\tdag_id VARCHAR(200) NOT NULL, \n'
 '\tairflow_run_id VARCHAR(255) NOT NULL, \n'
 '\trun_type VARCHAR(16) NOT NULL, \n'
 '\tetl_revision_id UUID NOT NULL, \n'
 '\tauthorization_id UUID NOT NULL, \n'
 '\trequest_sha256 VARCHAR(64) NOT NULL, \n'
 "\tstate VARCHAR(32) DEFAULT 'RESERVED' NOT NULL, \n"
 '\treserved_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tlast_reconciled_at TIMESTAMP WITH TIME ZONE, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (dag_id, airflow_run_id), \n'
 '\tUNIQUE (authorization_id, id), \n'
 "\tCONSTRAINT ck_intent_type CHECK (run_type IN ('manual','scheduled')), \n"
 '\tCONSTRAINT ck_intent_state CHECK (state IN '
 "('RESERVED','SUBMITTING','CREATED','NEEDS_RECONCILIATION','REJECTED')), \n"
 '\tUNIQUE (operation_id), \n'
 '\tFOREIGN KEY(operation_id) REFERENCES operations (id) ON DELETE RESTRICT, \n'
 '\tUNIQUE (run_uuid), \n'
 '\tFOREIGN KEY(dag_id) REFERENCES etl_definitions (dag_id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(etl_revision_id) REFERENCES etl_definition_revisions (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(authorization_id) REFERENCES replacement_authorizations (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_guard_run_intents() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.operation_id IS DISTINCT FROM OLD.operation_id OR '
 'NEW.run_uuid IS DISTINCT FROM OLD.run_uuid OR NEW.dag_id IS DISTINCT FROM OLD.dag_id OR '
 'NEW.airflow_run_id IS DISTINCT FROM OLD.airflow_run_id OR NEW.run_type IS DISTINCT FROM '
 'OLD.run_type OR NEW.etl_revision_id IS DISTINCT FROM OLD.etl_revision_id OR NEW.authorization_id '
 'IS DISTINCT FROM OLD.authorization_id OR NEW.request_sha256 IS DISTINCT FROM OLD.request_sha256 '
 'OR NEW.reserved_at IS DISTINCT FROM OLD.reserved_at THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON run_intents\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_run_intents();',
 'CREATE OR REPLACE FUNCTION public.aat_state_run_intents() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 "    IF NEW.state<>OLD.state AND NOT ((OLD.state='RESERVED' AND NEW.state IN "
 "('SUBMITTING','REJECTED','CREATED')) OR (OLD.state='SUBMITTING' AND NEW.state IN "
 "('CREATED','NEEDS_RECONCILIATION','REJECTED')) OR (OLD.state='NEEDS_RECONCILIATION' AND "
 "NEW.state IN ('CREATED','REJECTED'))) THEN\n"
 "      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 '    CREATE TRIGGER aat_state BEFORE UPDATE ON run_intents FOR EACH ROW EXECUTE FUNCTION '
 'public.aat_state_run_intents();',
 '\n'
 'CREATE TABLE dataset_manifests (\n'
 '\texecution_binding_id UUID NOT NULL, \n'
 '\tgeneration INTEGER NOT NULL, \n'
 '\tsnapshot_started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tschema_hash VARCHAR(64) NOT NULL, \n'
 '\tmapping_hash VARCHAR(64) NOT NULL, \n'
 '\tpath_key VARCHAR(255) NOT NULL, \n'
 '\tmanifest_sha256 VARCHAR(64), \n'
 "\textracted_rows BIGINT DEFAULT '0' NOT NULL, \n"
 "\tvalidated_rows BIGINT DEFAULT '0' NOT NULL, \n"
 "\ttotal_bytes BIGINT DEFAULT '0' NOT NULL, \n"
 "\tstate VARCHAR(16) DEFAULT 'INCOMPLETE' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (execution_binding_id, generation), \n'
 '\tUNIQUE (execution_binding_id, id), \n'
 '\tCONSTRAINT ck_dataset_counts CHECK (generation>=1 AND extracted_rows>=0 AND validated_rows>=0 '
 'AND total_bytes>=0), \n'
 '\tCONSTRAINT ck_dataset_state CHECK (state IN '
 "('INCOMPLETE','COMPLETE','CORRUPT','PROTECTED','EXPIRED')), \n"
 "\tCONSTRAINT ck_dataset_path CHECK (path_key !~ '(^/|(^|/)\\.\\.(/|$)|[\\\\\\\\])'), \n"
 '\tFOREIGN KEY(execution_binding_id) REFERENCES execution_bindings (id) ON DELETE RESTRICT, \n'
 '\tUNIQUE (path_key)\n'
 ')\n'
 '\n',
 'CREATE OR REPLACE FUNCTION public.aat_complete_manifest() RETURNS trigger LANGUAGE plpgsql AS $$ '
 'BEGIN\n'
 " IF OLD.state IN ('COMPLETE','CORRUPT','PROTECTED','EXPIRED') AND\n"
 ' '
 'ROW(NEW.id,NEW.execution_binding_id,NEW.generation,NEW.schema_hash,NEW.mapping_hash,NEW.path_key,NEW.manifest_sha256,NEW.extracted_rows,NEW.validated_rows,NEW.total_bytes)\n'
 ' IS DISTINCT FROM '
 'ROW(OLD.id,OLD.execution_binding_id,OLD.generation,OLD.schema_hash,OLD.mapping_hash,OLD.path_key,OLD.manifest_sha256,OLD.extracted_rows,OLD.validated_rows,OLD.total_bytes) '
 'THEN\n'
 " RAISE EXCEPTION 'Complete dataset is immutable' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 ' CREATE TRIGGER aat_complete BEFORE UPDATE ON dataset_manifests FOR EACH ROW EXECUTE FUNCTION '
 'public.aat_complete_manifest();',
 'CREATE OR REPLACE FUNCTION public.aat_state_dataset_manifests() RETURNS trigger LANGUAGE plpgsql '
 'AS $$ BEGIN\n'
 "    IF NEW.state<>OLD.state AND NOT ((OLD.state='INCOMPLETE' AND NEW.state IN "
 "('COMPLETE','CORRUPT','EXPIRED')) OR (OLD.state='COMPLETE' AND NEW.state IN "
 "('PROTECTED','CORRUPT','EXPIRED')) OR (OLD.state='PROTECTED' AND NEW.state IN "
 "('COMPLETE','CORRUPT','EXPIRED')) OR (OLD.state='CORRUPT' AND NEW.state IN "
 "('PROTECTED','EXPIRED'))) THEN\n"
 "      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 '    CREATE TRIGGER aat_state BEFORE UPDATE ON dataset_manifests FOR EACH ROW EXECUTE FUNCTION '
 'public.aat_state_dataset_manifests();',
 '\n'
 'CREATE TABLE execution_metrics (\n'
 '\tbinding_id UUID NOT NULL, \n'
 "\textracted_rows BIGINT DEFAULT '0' NOT NULL, \n"
 "\tvalidated_rows BIGINT DEFAULT '0' NOT NULL, \n"
 "\tloaded_rows BIGINT DEFAULT '0' NOT NULL, \n"
 '\tfailed_rows_nullable BIGINT, \n'
 "\tstaging_bytes_current BIGINT DEFAULT '0' NOT NULL, \n"
 "\tstaging_bytes_peak BIGINT DEFAULT '0' NOT NULL, \n"
 "\tduration_ms BIGINT DEFAULT '0' NOT NULL, \n"
 "\tphase VARCHAR(32) DEFAULT 'PENDING' NOT NULL, \n"
 '\tmetric_updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tCONSTRAINT ck_metric_counts CHECK (extracted_rows>=0 AND validated_rows>=0 AND loaded_rows>=0 '
 'AND (failed_rows_nullable IS NULL OR failed_rows_nullable>=0) AND staging_bytes_current>=0 AND '
 'staging_bytes_peak>=staging_bytes_current AND duration_ms>=0), \n'
 '\tUNIQUE (binding_id), \n'
 '\tFOREIGN KEY(binding_id) REFERENCES execution_bindings (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE replacement_admissions (\n'
 '\tbinding_id UUID NOT NULL, \n'
 '\trun_intent_id UUID NOT NULL, \n'
 '\tauthorization_id UUID NOT NULL, \n'
 '\tadmission_epoch INTEGER NOT NULL, \n'
 '\tauthorization_revision INTEGER NOT NULL, \n'
 '\tscope_sha256 VARCHAR(64) NOT NULL, \n'
 '\tdataset_sha256 VARCHAR(64) NOT NULL, \n'
 '\ttarget_identity VARCHAR(255) NOT NULL, \n'
 '\towner_process_id VARCHAR(128) NOT NULL, \n'
 '\ttarget_session_identity VARCHAR(255) NOT NULL, \n'
 "\tstate VARCHAR(32) DEFAULT 'ADMITTED' NOT NULL, \n"
 '\tadmitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\treconciled_at TIMESTAMP WITH TIME ZONE, \n'
 "\twriter_finished BOOLEAN DEFAULT 'false' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (binding_id, admission_epoch), \n'
 '\tCONSTRAINT ck_admission_epoch CHECK (admission_epoch>=1 AND authorization_revision>=1), \n'
 '\tCONSTRAINT ck_admission_state CHECK (state IN '
 "('ADMITTED','COMMIT_VERIFIED','ROLLBACK_VERIFIED','NEEDS_RECONCILIATION')), \n"
 '\tCONSTRAINT ck_admission_identity CHECK (length(owner_process_id)>0 AND '
 "length(target_session_identity)>0 AND scope_sha256 ~ '^[0-9a-f]{64}$' AND dataset_sha256 ~ "
 "'^[0-9a-f]{64}$'), \n"
 '\tFOREIGN KEY(binding_id) REFERENCES execution_bindings (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(run_intent_id) REFERENCES run_intents (id) ON DELETE RESTRICT, \n'
 '\tFOREIGN KEY(authorization_id) REFERENCES replacement_authorizations (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 'CREATE UNIQUE INDEX uq_admission_unreconciled ON replacement_admissions (binding_id) WHERE state '
 "IN ('ADMITTED','NEEDS_RECONCILIATION')",
 'CREATE OR REPLACE FUNCTION public.aat_guard_replacement_admissions() RETURNS trigger\n'
 '    LANGUAGE plpgsql AS $$ BEGIN\n'
 '      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.binding_id IS DISTINCT FROM OLD.binding_id OR '
 'NEW.run_intent_id IS DISTINCT FROM OLD.run_intent_id OR NEW.authorization_id IS DISTINCT FROM '
 'OLD.authorization_id OR NEW.admission_epoch IS DISTINCT FROM OLD.admission_epoch OR '
 'NEW.authorization_revision IS DISTINCT FROM OLD.authorization_revision OR NEW.scope_sha256 IS '
 'DISTINCT FROM OLD.scope_sha256 OR NEW.dataset_sha256 IS DISTINCT FROM OLD.dataset_sha256 OR '
 'NEW.target_identity IS DISTINCT FROM OLD.target_identity OR NEW.owner_process_id IS DISTINCT '
 'FROM OLD.owner_process_id OR NEW.target_session_identity IS DISTINCT FROM '
 'OLD.target_session_identity OR NEW.admitted_at IS DISTINCT FROM OLD.admitted_at THEN\n'
 "        RAISE EXCEPTION 'Stored revision or credential is immutable' USING ERRCODE='23514';\n"
 '      END IF;\n'
 '      RETURN NEW;\n'
 '    END $$;\n'
 '    CREATE TRIGGER aat_immutable BEFORE UPDATE ON replacement_admissions\n'
 '    FOR EACH ROW EXECUTE FUNCTION public.aat_guard_replacement_admissions();',
 'CREATE OR REPLACE FUNCTION public.aat_state_replacement_admissions() RETURNS trigger LANGUAGE '
 'plpgsql AS $$ BEGIN\n'
 "    IF NEW.state<>OLD.state AND NOT ((OLD.state='ADMITTED' AND NEW.state IN "
 "('COMMIT_VERIFIED','ROLLBACK_VERIFIED','NEEDS_RECONCILIATION')) OR "
 "(OLD.state='NEEDS_RECONCILIATION' AND NEW.state IN ('COMMIT_VERIFIED','ROLLBACK_VERIFIED'))) "
 'THEN\n'
 "      RAISE EXCEPTION 'Illegal state transition' USING ERRCODE='23514'; END IF; RETURN NEW; END "
 '$$;\n'
 '    CREATE TRIGGER aat_state BEFORE UPDATE ON replacement_admissions FOR EACH ROW EXECUTE '
 'FUNCTION public.aat_state_replacement_admissions();',
 '\n'
 'CREATE TABLE runtime_leases (\n'
 '\tbinding_id UUID NOT NULL, \n'
 '\towner_process_id VARCHAR(128) NOT NULL, \n'
 '\theartbeat_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\ttarget_identity VARCHAR(255) NOT NULL, \n'
 '\ttarget_lock_identity VARCHAR(255) NOT NULL, \n'
 '\trecovery_state VARCHAR(32) NOT NULL, \n'
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (binding_id), \n'
 '\tFOREIGN KEY(binding_id) REFERENCES execution_bindings (id) ON DELETE RESTRICT\n'
 ')\n'
 '\n',
 '\n'
 'CREATE TABLE staging_artifacts (\n'
 '\tdataset_id UUID NOT NULL, \n'
 '\tattempt_id UUID NOT NULL, \n'
 '\tfile_ordinal INTEGER NOT NULL, \n'
 '\tpath_key VARCHAR(255) NOT NULL, \n'
 '\tfile_sha256 VARCHAR(64), \n'
 "\trows BIGINT DEFAULT '0' NOT NULL, \n"
 "\tbytes BIGINT DEFAULT '0' NOT NULL, \n"
 '\tmin_record_index BIGINT, \n'
 '\tmax_record_index BIGINT, \n'
 "\tstate VARCHAR(16) DEFAULT 'INCOMPLETE' NOT NULL, \n"
 '\texpires_at TIMESTAMP WITH TIME ZONE, \n'
 "\trecovery_protected BOOLEAN DEFAULT 'false' NOT NULL, \n"
 '\tid UUID NOT NULL, \n'
 '\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n'
 '\tPRIMARY KEY (id), \n'
 '\tUNIQUE (dataset_id, file_ordinal), \n'
 '\tCONSTRAINT ck_artifact_counts CHECK (rows>=0 AND bytes>=0 AND file_ordinal>=1), \n'
 '\tCONSTRAINT ck_artifact_path CHECK (length(path_key)>0 AND path_key !~ '
 "'(^/|(^|/)\\.\\.(/|$)|[\\\\\\\\])'), \n"
 '\tFOREIGN KEY(dataset_id) REFERENCES dataset_manifests (id) ON DELETE RESTRICT, \n'
 '\tUNIQUE (path_key)\n'
 ')\n'
 '\n',
 'ALTER TABLE connections ADD CONSTRAINT fk_connections_current_revision FOREIGN KEY(id, '
 'current_revision_id) REFERENCES connection_revisions (connection_id, id) ON DELETE RESTRICT',
 'ALTER TABLE etl_definitions ADD CONSTRAINT fk_etl_current_revision FOREIGN KEY(id, '
 'current_revision_id) REFERENCES etl_definition_revisions (definition_id, id) ON DELETE RESTRICT',
 'ALTER TABLE uploaded_files ADD CONSTRAINT fk_uploaded_file_current_parser FOREIGN '
 'KEY(parser_file_id, parser_revision) REFERENCES file_parser_revisions (file_id, revision) ON '
 'DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED',
 'ALTER TABLE replacement_authorizations ADD CONSTRAINT fk_auth_reserved_intent FOREIGN KEY(id, '
 'reserved_intent_id) REFERENCES run_intents (authorization_id, id) ON DELETE RESTRICT DEFERRABLE '
 'INITIALLY DEFERRED',
 'ALTER TABLE execution_bindings ADD CONSTRAINT fk_binding_dataset FOREIGN KEY(id, dataset_id) '
 'REFERENCES dataset_manifests (execution_binding_id, id) ON DELETE RESTRICT',
 'ALTER TABLE execution_bindings ADD CONSTRAINT fk_binding_intent FOREIGN KEY(run_intent_id) '
 'REFERENCES run_intents (id) ON DELETE RESTRICT')

def upgrade():
    for statement in STATEMENTS:op.execute(statement)

def downgrade():
    raise RuntimeError("Automatic metadata downgrade is unsupported; restore a verified backup")
