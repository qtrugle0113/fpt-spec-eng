"""Durable full-file validation bound to immutable bytes and parser snapshots."""
import hashlib
from uuid import UUID
from sqlalchemy import select
from aat_metadata.models.operations import Operation
from aat_metadata.models.file_parsers import FileParserRevision
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import digest,enqueue,fence
from aat_api.services import files
from aat_etl.readers.delimited import read,DelimitedError


def request_validation(identity,value,key):
    request_hash=digest(dict(file_id=str(identity),validation_request=value.model_dump(mode='json',exclude_none=True)))
    with transaction() as session:
        previous=session.scalar(select(Operation).where(Operation.kind=='FILE_VALIDATE',Operation.idempotency_key==str(key)))
        if previous:
            if previous.request_sha256!=request_hash:raise APIError('IDEMPOTENCY_CONFLICT','Idempotency key was used for another request.',409)
            return previous.id
        file=files.require(session,identity,lock=True)
        # A concurrent identical submission may have committed while this
        # request waited for the file lock. Avoid taking its operation row lock
        # in the reverse order to the worker's operation→file fence.
        previous=session.scalar(select(Operation).where(Operation.kind=='FILE_VALIDATE',Operation.idempotency_key==str(key)))
        if previous:
            if previous.request_sha256!=request_hash:raise APIError('IDEMPOTENCY_CONFLICT','Idempotency key was used for another request.',409)
            return previous.id
        parser=files.current_parser(session,file)
        if value.expected_sha256 and value.expected_sha256!=file.sha256:
            raise APIError('CHECKSUM_MISMATCH','Source checksum does not match the selected file.',409)
        if value.parser_revision is not None and value.parser_revision!=parser.revision:
            raise APIError('PARSER_REVISION_MISMATCH','Parser revision changed. Refresh the source file.',409)
        with files.open_source(file):pass
        payload=dict(file_id=str(file.id),sha256=file.sha256,parser_id=str(parser.id),parser_revision=parser.revision,phase='FILE_VALIDATION')
        operation,created=enqueue(session,'FILE_VALIDATE',key,payload,request_fingerprint=request_hash)
        if created:file.validation_status='PENDING'
        operation.result_ref='/api/v1/files/'+str(file.id)
        return operation.id


class HashingSource:
    def __init__(self,source):self.source=source;self.checksum=hashlib.sha256();self.bytes=0
    def read(self,size):
        chunk=self.source.read(size);self.checksum.update(chunk);self.bytes+=len(chunk)
        return chunk


def execute(operation,owner):
    payload=operation['progress_json'];identity=UUID(payload['file_id'])
    with transaction() as session:
        file=files.require(session,identity)
        parser=session.get(FileParserRevision,UUID(payload['parser_id']))
        if parser is None:raise APIError('FILE_PARSER_UNAVAILABLE','Required parser history is unavailable.',409)
        config=files.parser_config(files.parser_public(parser))
    issue=None;completed=0;reader=None
    try:
        with files.open_source(file) as source:
            hashed=HashingSource(source);reader=read(hashed,config)
            for _ in reader:completed+=1
            if hashed.bytes!=file.bytes or hashed.checksum.hexdigest()!=payload['sha256']:
                raise APIError('SOURCE_CHECKSUM_MISMATCH','Source bytes do not match the immutable upload.',409)
    except DelimitedError as error:
        issue=dict(scope='resource',code=error.code,message=str(error)+' Record '+str(error.record)+'.',row=error.line)
        if error.column is not None:issue['column']=error.column
    except APIError as error:
        issue=dict(scope='resource',code=error.code,message=error.message)
    finally:
        if reader is not None:reader.close()
    with transaction() as session:
        current=fence(session,operation,owner)
        file=files.require(session,identity,lock=True)
        stale=file.parser_revision!=payload['parser_revision'] or file.sha256!=payload['sha256']
        if stale:
            issue=dict(scope='resource',code='FILE_VALIDATION_STALE',message='Parser changed during validation. Validate the current revision.')
        elif files.expired(file):
            issue=dict(scope='resource',code='FILE_SOURCE_EXPIRED',message='Source file expired during validation.')
        if not stale:file.validation_status='INVALID' if issue else 'VALID'
        progress={**current.progress_json,'completed':completed,'total':None if issue else completed}
        if issue:progress['validation_issue']=issue
        current.progress_json=progress
    return ('FAILED',issue['code']) if issue else ('SUCCEEDED',None)
