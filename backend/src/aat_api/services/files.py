"""Immutable delimited uploads, safe disk access and reference-aware retention."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import hashlib
import os
from pathlib import Path
import re
import stat
from uuid import uuid4
from pydantic import ValidationError
from sqlalchemy import select,func
from sqlalchemy.exc import SQLAlchemyError,IntegrityError,DataError
from sqlalchemy.orm import Session
from aat_metadata.models.definitions import UploadedFile
from aat_metadata.models.file_parsers import FileParserRevision
from aat_metadata.models.etl import ETLDefinitionRevision
from aat_metadata.models.runtime import ExecutionBinding
from aat_metadata.repositories.base import create_app_engine
from aat_api.errors import APIError
from aat_api.logging import logger
from aat_api.services.connections.service import transaction
from aat_etl.readers.delimited import ParserConfig,DelimitedError,preview as parse_preview

UPLOAD_LIMIT=256*1024*1024


def parser_config(value):
    if isinstance(value,dict) and not {'encoding','delimiter','header_present','quote_character','null_representation'}<=value.keys():
        raise APIError('INVALID_PARSER','Confirm all required parser configuration fields.',422)
    try:return ParserConfig.model_validate(value)
    except (ValidationError,ValueError,TypeError):
        raise APIError('INVALID_PARSER','Parser configuration is not valid.',422) from None


def storage():
    # Preserve the seed/legacy layout; existing files are never moved or reset.
    root=Path(os.environ.get('AAT_UPLOADS_ROOT','/data/uploads'))
    root.mkdir(parents=True,exist_ok=True,mode=0o750)
    return root


def source_path(key):
    if not re.fullmatch(r'[0-9a-f]{32}',key):raise APIError('FILE_SOURCE_UNAVAILABLE','Source file is no longer available.',410)
    return storage()/key


def require(session,identity,lock=False):
    statement=select(UploadedFile).where(UploadedFile.id==identity,UploadedFile.extension.in_(['.csv','.txt']))
    if lock:statement=statement.with_for_update()
    file=session.scalar(statement)
    if file is None:raise APIError('FILE_NOT_FOUND','Source file not found.',404)
    return file


def current_parser(session,file):
    revision=session.scalar(select(FileParserRevision).where(FileParserRevision.file_id==file.id,FileParserRevision.revision==file.parser_revision))
    if revision is None:raise APIError('FILE_PARSER_UNAVAILABLE','The required parser revision is unavailable.',409)
    return revision


def parser_public(revision):
    return dict(encoding=revision.encoding,delimiter=revision.delimiter,header_present=revision.header_present,
                quote_character=revision.quote_char,escape_character=revision.escape_char,null_representation=revision.null_token)


def parser_fields(config):
    return dict(encoding=config.encoding,delimiter=config.delimiter,header_present=config.header_present,
                quote_char=config.quote_character,escape_char=config.escape_character,null_token=config.null_representation)


def expired(file):return file.expires_at is not None and file.expires_at<=datetime.now(timezone.utc)


def project(session,file):
    return dict(id=file.id,file_name=file.original_name,file_type='CSV' if file.extension=='.csv' else 'TXT',
                size=file.bytes,sha256=file.sha256,parser=parser_public(current_parser(session,file)),
                parser_revision=file.parser_revision,revision=file.revision,
                needs_revalidation=file.validation_status!='VALID' or expired(file),validation_status=file.validation_status,
                uploaded_at=file.created_at,expires_at=file.expires_at)


async def store(file,parser):
    config=parser_config(parser)
    name=(file.filename or '').replace('\\','/').split('/')[-1]
    extension=Path(name).suffix.lower()
    if extension not in ('.csv','.txt') or not name or len(name)>255 or '\0' in name:
        raise APIError('INVALID_SOURCE_NAME','Upload a CSV or TXT file with a valid filename.',422)
    try:name.encode('utf-8')
    except UnicodeError:raise APIError('INVALID_SOURCE_NAME','Filename must contain valid Unicode text.',422) from None
    root=storage();key=uuid4().hex;partial=root/(key+'.part');destination=root/key
    identity=uuid4();checksum=hashlib.sha256();size=0;published=False;committed=False;uncertain=False
    partial_owned=False;metadata_started=False;rollback_confirmed=False
    try:
        with partial.open('xb') as output:
            partial_owned=True
            os.chmod(partial,0o600)
            while chunk:=await file.read(65536):
                size+=len(chunk)
                if size>UPLOAD_LIMIT:raise APIError('SOURCE_TOO_LARGE','Source upload exceeds 256 MiB.',413)
                checksum.update(chunk);output.write(chunk)
            output.flush();os.fsync(output.fileno())
        # Atomic publication without replacing any existing storage key.
        os.link(partial,destination);published=True;partial.unlink();partial_owned=False
        directory=os.open(root,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
        engine=create_app_engine()
        try:
            metadata_started=True
            with Session(engine,expire_on_commit=False) as session,session.begin():
                uploaded=UploadedFile(id=identity,original_name=name,safe_storage_key=key,sha256=checksum.hexdigest(),bytes=size,
                    extension=extension,validation_status='PENDING',expires_at=datetime.now(timezone.utc)+timedelta(days=30),**parser_fields(config))
                session.add(uploaded);session.flush()
                session.add(FileParserRevision(file_id=identity,revision=1,**parser_fields(config)));session.flush()
                result=project(session,uploaded)
            committed=True
        except (IntegrityError,DataError):
            rollback_confirmed=True
            raise APIError('FILE_METADATA_CONFLICT','Source metadata could not be published.',409) from None
        except SQLAlchemyError:
            # A lost COMMIT acknowledgement cannot justify deleting the complete
            # blob: a durable metadata reference might already exist.
            uncertain=True
            logger.error('file_publication_uncertain reference_id=%s',identity)
            raise APIError('UPLOAD_PUBLICATION_UNCERTAIN','Upload publication could not be confirmed. Check uploaded files before retrying.',503) from None
        finally:engine.dispose()
        return result
    except OSError:
        if metadata_started and not committed:
            uncertain=True
            raise APIError('UPLOAD_PUBLICATION_UNCERTAIN','Upload publication could not be confirmed. Check uploaded files before retrying.',503) from None
        raise APIError('UPLOAD_INTERRUPTED','Source upload could not be completed.',503,True) from None
    except BaseException:
        if metadata_started and not committed and not rollback_confirmed:uncertain=True
        raise
    finally:
        if partial_owned:partial.unlink(missing_ok=True)
        if published and not committed and not uncertain:destination.unlink(missing_ok=True)
        try:await file.close()
        except OSError:logger.error('upload_input_close_unavailable')


@contextmanager
def open_source(file):
    if expired(file):raise APIError('FILE_SOURCE_EXPIRED','Source file has expired. Upload and validate a new source.',410)
    path=source_path(file.safe_storage_key)
    try:
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            info=os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_size!=file.bytes:
                raise APIError('FILE_SOURCE_CHANGED','Source file no longer matches its immutable upload.',410)
            stream=os.fdopen(descriptor,'rb');descriptor=None
            with stream:yield stream
        finally:
            if descriptor is not None:os.close(descriptor)
    except OSError:
        raise APIError('FILE_SOURCE_UNAVAILABLE','Source file is no longer available.',410) from None


def detail(identity):
    with transaction() as session:return project(session,require(session,identity))


def listing(limit,offset):
    with transaction() as session:
        statement=select(UploadedFile).where(UploadedFile.extension.in_(['.csv','.txt']))
        total=session.scalar(select(func.count()).select_from(statement.subquery()))
        files=session.scalars(statement.order_by(UploadedFile.created_at,UploadedFile.id).offset(offset).limit(limit)).all()
        return dict(items=[project(session,file) for file in files],total=total,
                    next_offset=offset+len(files) if limit and offset+len(files)<total else None)


def preview(identity,max_rows,candidate=None):
    with transaction() as session:
        file=require(session,identity)
        config=parser_config(candidate if candidate is not None else parser_public(current_parser(session,file)))
    try:
        with open_source(file) as source:result=parse_preview(source,config,max_rows=max_rows)
    except DelimitedError as error:
        # Fixed parser messages and numeric positions; never echo a source cell.
        raise APIError(error.code,str(error)+' Record '+str(error.record)+', line '+str(error.line)+'.',422) from None
    return dict(columns=[dict(name=name,logical_type='text',nullable=True,ordinal=index,primary_key_ordinal=None,has_default=False)
                         for index,name in enumerate(result['columns'],1)],rows=result['rows'],limited=result['limited'],parser=config.model_dump())


def referenced(session,identity):
    if session.scalar(select(ETLDefinitionRevision.id).where(ETLDefinitionRevision.config_json['source']['file_id'].astext==str(identity)).limit(1)):
        return True
    parsers=select(FileParserRevision.id).where(FileParserRevision.file_id==identity)
    return session.scalar(select(ExecutionBinding.id).where(ExecutionBinding.file_parser_revision.in_(parsers)).limit(1)) is not None


def can_collect(identity):
    with transaction() as session:
        file=require(session,identity)
        return expired(file) and not referenced(session,identity)
