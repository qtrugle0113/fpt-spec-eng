"""T020 durable definition metadata, not parser, upload API or target DDL.

Only production model DDL is registered. T029 must reproduce constraints and
guard functions in actual migrations. No engine/schema initialization on import.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Computed, DateTime, DDL, ForeignKey,
    ForeignKeyConstraint, FetchedValue, Integer, String, Text, UniqueConstraint, event, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .connections import immutable_guard


class Record(Base):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UploadedFile(Record):
    __tablename__ = 'uploaded_files'
    __table_args__ = (
        UniqueConstraint('safe_storage_key', name='uq_uploaded_files_storage'),
        UniqueConstraint('id', 'sha256', name='uq_uploaded_files_identity_checksum'),
        CheckConstraint("safe_storage_key ~ '^[0-9a-f]{32}$'", name='ck_uploaded_files_storage'),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name='ck_uploaded_files_checksum'),
        CheckConstraint('bytes>=0', name='ck_uploaded_files_bytes'),
        CheckConstraint("extension IN ('.csv','.txt','.xlsx')", name='ck_uploaded_files_extension'),
        CheckConstraint('parser_revision>=1', name='ck_uploaded_files_parser_revision'),
        CheckConstraint('revision>=1', name='ck_uploaded_files_revision'),
        ForeignKeyConstraint(['parser_file_id', 'parser_revision'],
                             ['file_parser_revisions.file_id', 'file_parser_revisions.revision'],
                             name='fk_uploaded_file_current_parser', ondelete='RESTRICT',
                             deferrable=True, initially='DEFERRED', use_alter=True),
        CheckConstraint("validation_status IN ('PENDING','VALID','INVALID')", name='ck_uploaded_files_validation'),
    )
    original_name: Mapped[str] = mapped_column(String(255))
    safe_storage_key: Mapped[str] = mapped_column(String(32), server_default=text("replace(gen_random_uuid()::text,'-','')"))
    sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(BigInteger)
    extension: Mapped[str] = mapped_column(String(8))
    encoding: Mapped[str | None] = mapped_column(String(64))
    delimiter: Mapped[str | None] = mapped_column(String(8))
    header_present: Mapped[bool | None] = mapped_column(Boolean)
    quote_char: Mapped[str | None] = mapped_column(String(8))
    escape_char: Mapped[str | None] = mapped_column(String(8))
    null_token: Mapped[str | None] = mapped_column(String(255))
    parser_revision: Mapped[int] = mapped_column(Integer, default=1, server_default='1')
    parser_file_id: Mapped[UUID | None] = mapped_column(Computed(
        "CASE WHEN extension IN ('.csv','.txt') THEN id ELSE NULL END", persisted=True))
    revision: Mapped[int] = mapped_column(Integer, server_default='1', server_onupdate=FetchedValue())
    __mapper_args__ = {'version_id_col': revision, 'version_id_generator': False, 'eager_defaults': True}
    validation_status: Mapped[str] = mapped_column(String(16), default='PENDING', server_default='PENDING')
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DefinitionUpload(Record):
    __tablename__ = 'definition_uploads'
    __table_args__ = (
        CheckConstraint("kind IN ('TABLE','ETL')", name='ck_definition_upload_kind'),
        CheckConstraint("template_version IS NULL OR template_version='1.0'", name='ck_definition_upload_version'),
        CheckConstraint("status IN ('UPLOADED','VALIDATING','VALIDATED','INVALID')", name='ck_definition_upload_status'),
        CheckConstraint("status<>'VALIDATED' OR template_version='1.0' AND template_version IS NOT NULL", name='ck_definition_upload_validated_version'),
        ForeignKeyConstraint(['uploaded_file_id','workbook_sha256'], ['uploaded_files.id','uploaded_files.sha256'],
                             ondelete='RESTRICT', name='fk_definition_upload_file_checksum'),
    )
    kind: Mapped[str] = mapped_column(String(8))
    uploaded_file_id: Mapped[UUID]
    template_version: Mapped[str | None] = mapped_column(String(8))
    workbook_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default='UPLOADED', server_default='UPLOADED')
    validation_report_key: Mapped[str | None] = mapped_column(String(255))


class DefinitionIssue(Record):
    __tablename__ = 'definition_issues'
    __table_args__ = (
        CheckConstraint("scope IN ('workbook','sheet','cell','resource')", name='ck_issue_scope'),
        CheckConstraint('row IS NULL OR row>=1', name='ck_issue_row'),
        CheckConstraint('"column" IS NULL OR "column">=1', name='ck_issue_column'),
        CheckConstraint("scope<>'workbook' OR sheet IS NULL AND row IS NULL AND \"column\" IS NULL AND column_name IS NULL", name='ck_issue_workbook_location'),
        CheckConstraint("scope<>'cell' OR sheet IS NOT NULL AND row IS NOT NULL AND \"column\" IS NOT NULL", name='ck_issue_cell_location'),
        CheckConstraint("severity IN ('ERROR','WARNING','INFO')", name='ck_issue_severity'),
        CheckConstraint("message_key ~ '^[A-Za-z][A-Za-z0-9_.-]*$'", name='ck_issue_message_key'),
        CheckConstraint("jsonb_typeof(safe_context)='object' AND safe_context - ARRAY['count','limit','expected_type','actual_type'] = '{}'::jsonb", name='ck_issue_safe_context_keys'),
        CheckConstraint("(NOT safe_context ? 'count' OR jsonb_typeof(safe_context->'count')='number' AND safe_context->>'count' ~ '^[0-9]+$') AND (NOT safe_context ? 'limit' OR jsonb_typeof(safe_context->'limit')='number' AND safe_context->>'limit' ~ '^[0-9]+$')", name='ck_issue_safe_context_counts'),
        CheckConstraint("(NOT safe_context ? 'expected_type' OR safe_context->>'expected_type' IN ('string','number','boolean','null','object','array','integer','bigint','decimal','varchar','text','date','timestamp')) AND (NOT safe_context ? 'actual_type' OR safe_context->>'actual_type' IN ('string','number','boolean','null','object','array','integer','bigint','decimal','varchar','text','date','timestamp'))", name='ck_issue_safe_context_types'),
    )
    upload_id: Mapped[UUID] = mapped_column(ForeignKey('definition_uploads.id', ondelete='RESTRICT'))
    code: Mapped[str] = mapped_column(String(128))
    scope: Mapped[str] = mapped_column(String(16))
    sheet: Mapped[str | None] = mapped_column(String(255))
    row: Mapped[int | None] = mapped_column(Integer)
    column: Mapped[int | None] = mapped_column(Integer)
    column_name: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(8))
    message_key: Mapped[str] = mapped_column(String(128))
    safe_context: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))


class TableDefinition(Record):
    __tablename__ = 'table_definitions'
    __table_args__ = (
        UniqueConstraint('upload_id','physical_table_identity', name='uq_table_definition_upload_physical'),
        CheckConstraint("length(btrim(target_schema))>0 AND length(btrim(table_name))>0", name='ck_table_definition_names'),
        CheckConstraint("definition_hash ~ '^[0-9a-f]{64}$'", name='ck_table_definition_hash'),
    )
    upload_id: Mapped[UUID] = mapped_column(ForeignKey('definition_uploads.id', ondelete='RESTRICT'))
    target_connection_revision_id: Mapped[UUID] = mapped_column(ForeignKey('connection_revisions.id', ondelete='RESTRICT'))
    target_schema: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255))
    physical_table_identity: Mapped[str] = mapped_column(Text, server_default=FetchedValue(), server_onupdate=FetchedValue())
    description: Mapped[str | None] = mapped_column(Text)
    definition_hash: Mapped[str] = mapped_column(String(64))


_DEFAULT_CHECK = """default_literal IS NULL OR (
 jsonb_typeof(default_literal)='object'
 AND default_literal ?& ARRAY['logical_type','value']
 AND default_literal - ARRAY['logical_type','value']='{}'::jsonb
 AND jsonb_typeof(default_literal->'logical_type')='string'
 AND default_literal->>'logical_type'=logical_type
 AND CASE WHEN default_literal->'value'='null'::jsonb THEN nullable
 WHEN logical_type IN ('integer','bigint') THEN jsonb_typeof(default_literal->'value')='number' AND default_literal->>'value' ~ '^-?[0-9]+$'
 WHEN logical_type='boolean' THEN jsonb_typeof(default_literal->'value')='boolean'
 ELSE jsonb_typeof(default_literal->'value')='string' END)"""


class TableColumn(Record):
    __tablename__ = 'table_columns'
    __table_args__ = (
        UniqueConstraint('table_definition_id','name', name='uq_table_column_name'),
        UniqueConstraint('table_definition_id','ordinal', name='uq_table_column_ordinal'),
        UniqueConstraint('table_definition_id','primary_key_ordinal', name='uq_table_column_pk_ordinal'),
        CheckConstraint('ordinal BETWEEN 1 AND 1000', name='ck_table_column_ordinal'),
        CheckConstraint("length(btrim(name))>0", name='ck_table_column_name'),
        CheckConstraint("logical_type IN ('integer','bigint','varchar','text','decimal','boolean','date','timestamp')", name='ck_table_column_type'),
        CheckConstraint("(logical_type='varchar' AND length IS NOT NULL AND length BETWEEN 1 AND 65535) OR (logical_type<>'varchar' AND length IS NULL)", name='ck_table_column_length'),
        CheckConstraint("(logical_type='decimal' AND precision IS NOT NULL AND scale IS NOT NULL AND precision BETWEEN 1 AND 38 AND scale BETWEEN 0 AND precision) OR (logical_type<>'decimal' AND precision IS NULL AND scale IS NULL)", name='ck_table_column_decimal'),
        CheckConstraint('primary_key_ordinal IS NULL OR primary_key_ordinal>=1 AND NOT nullable', name='ck_table_column_pk'),
        CheckConstraint(_DEFAULT_CHECK, name='ck_table_column_default'),
    )
    table_definition_id: Mapped[UUID] = mapped_column(ForeignKey('table_definitions.id', ondelete='RESTRICT'))
    name: Mapped[str] = mapped_column(String(255))
    ordinal: Mapped[int] = mapped_column(Integer)
    logical_type: Mapped[str] = mapped_column(String(16))
    length: Mapped[int | None] = mapped_column(Integer)
    precision: Mapped[int | None] = mapped_column(Integer)
    scale: Mapped[int | None] = mapped_column(Integer)
    nullable: Mapped[bool] = mapped_column(Boolean)
    primary_key_ordinal: Mapped[int | None] = mapped_column(Integer)
    default_literal: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    description: Mapped[str | None] = mapped_column(Text)


immutable_guard('uploaded_files', ('id','safe_storage_key','sha256','bytes','original_name','extension',
                                 'encoding','delimiter','header_present','quote_char','escape_char','null_token'))
immutable_guard('definition_uploads', ('id','kind','uploaded_file_id','workbook_sha256'))

_PHYSICAL_GUARD = """CREATE OR REPLACE FUNCTION public.aat_table_physical_identity()
RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE fingerprint text; database_name text;
BEGIN
 SELECT r.physical_server_fingerprint,r.database_name INTO fingerprint,database_name
 FROM public.connection_revisions r WHERE r.id=NEW.target_connection_revision_id;
 IF fingerprint IS NULL OR fingerprint !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'Verified physical server identity required' USING ERRCODE='23514';
 END IF;
 NEW.physical_table_identity=jsonb_build_array(fingerprint,database_name,NEW.target_schema,NEW.table_name)::text;
 RETURN NEW;
END $$;
CREATE TRIGGER aat_physical_identity BEFORE INSERT OR UPDATE ON public.table_definitions
FOR EACH ROW EXECUTE FUNCTION public.aat_table_physical_identity();"""
event.listen(TableDefinition.__table__, 'after_create', DDL(_PHYSICAL_GUARD).execute_if(dialect='postgresql'))

_PK_ORDER_GUARD = """CREATE OR REPLACE FUNCTION public.aat_table_pk_order()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF NEW.primary_key_ordinal IS NOT NULL AND EXISTS(
   SELECT 1 FROM public.table_columns c WHERE c.table_definition_id=NEW.table_definition_id
    AND c.id<>NEW.id AND c.primary_key_ordinal IS NOT NULL
    AND ((c.ordinal<NEW.ordinal AND c.primary_key_ordinal>=NEW.primary_key_ordinal)
      OR (c.ordinal>NEW.ordinal AND c.primary_key_ordinal<=NEW.primary_key_ordinal))) THEN
   RAISE EXCEPTION 'Primary key order must follow column order' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER aat_pk_order BEFORE INSERT OR UPDATE ON public.table_columns
FOR EACH ROW EXECUTE FUNCTION public.aat_table_pk_order();"""
event.listen(TableColumn.__table__, 'after_create', DDL(_PK_ORDER_GUARD).execute_if(dialect='postgresql'))

_FILE_VERSION_GUARD = """CREATE OR REPLACE FUNCTION public.aat_file_version()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='INSERT' THEN
   IF NEW.revision<>1 OR NEW.parser_revision<>1 THEN
     RAISE EXCEPTION 'File versions must start at one' USING ERRCODE='23514';
   END IF;
 ELSE
   IF NEW.parser_revision<OLD.parser_revision
      OR NEW.revision NOT IN (OLD.revision,OLD.revision+1) THEN
     RAISE EXCEPTION 'File version cannot rewind or be forged' USING ERRCODE='23514';
   END IF;
   NEW.revision=OLD.revision+1;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER aat_file_version BEFORE INSERT OR UPDATE ON public.uploaded_files
FOR EACH ROW EXECUTE FUNCTION public.aat_file_version();"""
event.listen(UploadedFile.__table__, 'after_create', DDL(_FILE_VERSION_GUARD).execute_if(dialect='postgresql'))

# Register the real history table for the deferred current-parser FK. No engine,
# schema creation or parser/API work happens at import.
from . import file_parsers as _file_parsers  # noqa: E402,F401
