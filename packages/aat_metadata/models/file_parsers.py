"""Immutable delimited-parser snapshots; service/admission checks remain T067."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, DDL, FetchedValue, ForeignKey, Integer, String, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .connections import immutable_guard


class FileParserRevision(Base):
    __tablename__ = 'file_parser_revisions'
    __table_args__ = (
        UniqueConstraint('file_id', 'revision', name='uq_file_parser_revision'),
        CheckConstraint('revision>=1', name='ck_file_parser_revision'),
        CheckConstraint('length(btrim(encoding))>0', name='ck_file_parser_encoding'),
        CheckConstraint('length(delimiter)=1', name='ck_file_parser_delimiter'),
        CheckConstraint('length(quote_char)=1', name='ck_file_parser_quote'),
        CheckConstraint("config_sha256 ~ '^[0-9a-f]{64}$'", name='ck_file_parser_hash'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_id: Mapped[UUID] = mapped_column(ForeignKey('uploaded_files.id', ondelete='RESTRICT'))
    revision: Mapped[int] = mapped_column(Integer)
    encoding: Mapped[str] = mapped_column(String(64))
    delimiter: Mapped[str] = mapped_column(String(8))
    header_present: Mapped[bool] = mapped_column(Boolean)
    quote_char: Mapped[str] = mapped_column(String(8))
    escape_char: Mapped[str | None] = mapped_column(String)
    null_token: Mapped[str] = mapped_column(String)
    config_sha256: Mapped[str] = mapped_column(String(64), server_default=FetchedValue())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


immutable_guard('file_parser_revisions', ('id', 'file_id', 'revision', 'encoding', 'delimiter',
                'header_present', 'quote_char', 'escape_char', 'null_token', 'config_sha256', 'created_at'))

_SNAPSHOT_GUARD = """CREATE OR REPLACE FUNCTION public.aat_parser_snapshot()
RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE file public.uploaded_files; expected text;
BEGIN
 SELECT * INTO file FROM public.uploaded_files WHERE id=NEW.file_id FOR KEY SHARE;
 IF FOUND THEN
   IF file.extension NOT IN ('.csv','.txt') THEN
     RAISE EXCEPTION 'Delimited parser requires CSV or TXT' USING ERRCODE='23514';
   END IF;
   IF NEW.revision=1 AND
      ROW(NEW.encoding,NEW.delimiter,NEW.header_present,NEW.quote_char,NEW.escape_char,NEW.null_token)
      IS DISTINCT FROM ROW(file.encoding,file.delimiter,file.header_present,file.quote_char,file.escape_char,file.null_token) THEN
     RAISE EXCEPTION 'Initial parser must match original file snapshot' USING ERRCODE='23514';
   END IF;
 END IF;
 expected=encode(sha256(convert_to(jsonb_build_array(NEW.encoding,NEW.delimiter,NEW.header_present,
            NEW.quote_char,NEW.escape_char,NEW.null_token)::text,'UTF8')),'hex');
 IF NEW.config_sha256 IS NOT NULL AND NEW.config_sha256<>expected THEN
   RAISE EXCEPTION 'Parser configuration hash mismatch' USING ERRCODE='23514';
 END IF;
 NEW.config_sha256=expected;
 RETURN NEW;
END $$;
CREATE TRIGGER aat_parser_snapshot BEFORE INSERT ON public.file_parser_revisions
FOR EACH ROW EXECUTE FUNCTION public.aat_parser_snapshot();"""
event.listen(FileParserRevision.__table__, 'after_create', DDL(_SNAPSHOT_GUARD).execute_if(dialect='postgresql'))
