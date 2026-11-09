"""Immutable streamed workbook storage and durable validation metadata."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError,DataError
from aat_metadata.models.definitions import UploadedFile, DefinitionUpload, DefinitionIssue, TableDefinition, TableColumn
from aat_metadata.models.operations import Operation
from aat_api.errors import APIError
from aat_api.logging import logger
from aat_api.services.connections.service import transaction, active
from aat_api.validation.tables import TargetContext, validate
from aat_api.validation.messages import MESSAGES as VALIDATION_MESSAGES, message_key


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def storage():
    root = Path(os.environ.get('AAT_UPLOADS_ROOT', '/data/uploads')) / 'definitions'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def project(upload):
    return dict(id=upload.id, kind=upload.kind, sha256=upload.workbook_sha256,
                template_version=upload.template_version, status=upload.status, created_at=upload.created_at)


def require(session, identity, lock=False):
    statement = select(DefinitionUpload).where(DefinitionUpload.id == identity)
    if lock: statement = statement.with_for_update()
    upload = session.scalar(statement)
    if upload is None: raise APIError('UPLOAD_NOT_FOUND', 'Definition upload not found.', 404)
    return upload


async def store(file, kind):
    if kind != 'TABLE': raise APIError('UNSUPPORTED_DEFINITION_KIND', 'This definition kind is not implemented yet.', 422)
    name = (file.filename or '').replace('\\', '/').split('/')[-1]
    if not name.lower().endswith('.xlsx') or len(name) > 255 or '\0' in name:
        raise APIError('INVALID_WORKBOOK_NAME', 'An XLSX workbook filename is required.', 422)
    try: name.encode('utf-8')
    except UnicodeError: raise APIError('INVALID_WORKBOOK_NAME', 'Workbook filename must contain valid Unicode text.', 422) from None
    key = uuid4().hex
    path = storage() / key
    checksum = hashlib.sha256(); size = 0; created = False; metadata_started = False
    try:
        with path.open('xb') as output:
            created = True
            os.chmod(path, 0o600)
            while chunk := await file.read(65536):
                size += len(chunk)
                if size > 10*1024*1024: raise APIError('WORKBOOK_TOO_LARGE', 'Definition upload exceeds 10 MiB.', 413)
                checksum.update(chunk); output.write(chunk)
            output.flush(); os.fsync(output.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
        metadata_started = True
        with transaction() as session:
            uploaded = UploadedFile(original_name=name, safe_storage_key=key, sha256=checksum.hexdigest(), bytes=size, extension='.xlsx')
            session.add(uploaded); session.flush()
            upload = DefinitionUpload(kind=kind, uploaded_file_id=uploaded.id, workbook_sha256=uploaded.sha256)
            session.add(upload); session.flush()
            result = project(upload)
        return result
    except BaseException as error:
        rollback_confirmed = isinstance(error, (IntegrityError, DataError)) or isinstance(error, APIError) and error.code in ('CONNECTION_CONFLICT', 'INVALID_CONNECTION')
        uncertain = metadata_started and not rollback_confirmed
        if created and not uncertain:path.unlink(missing_ok=True)
        if uncertain and isinstance(error, Exception):
            logger.error('definition_upload_publication_uncertain')
            raise APIError('UPLOAD_PUBLICATION_UNCERTAIN','Workbook publication could not be confirmed. Check definition uploads before retrying.',503) from None
        raise
    finally:
        try: await file.close()
        except OSError: logger.error('definition_upload_input_close_unavailable')


def detail(identity):
    with transaction() as session: return project(require(session, identity))


def page(session, statement, limit, offset, projector):
    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = session.scalars(statement.limit(limit).offset(offset)).all()
    return dict(items=[projector(item) for item in rows], total=total,
                next_offset=offset+len(rows) if offset+len(rows) < total else None)


def listing(kind, status, from_, to, limit, offset):
    if from_ and to and from_ > to: raise APIError('INVALID_DATE_RANGE', 'From must not be after to.', 422)
    with transaction() as session:
        statement = select(DefinitionUpload)
        if kind: statement = statement.where(DefinitionUpload.kind == kind)
        if status: statement = statement.where(DefinitionUpload.status == status)
        if from_: statement = statement.where(DefinitionUpload.created_at >= from_)
        if to: statement = statement.where(DefinitionUpload.created_at <= to)
        return page(session, statement.order_by(DefinitionUpload.created_at, DefinitionUpload.id), limit, offset, project)


def enqueue(session, kind, key, payload, *, request_fingerprint=None):
    fingerprint = request_fingerprint or digest(payload)
    identity = session.scalar(insert(Operation).values(id=uuid4(), kind=kind, idempotency_key=str(key),
        request_sha256=fingerprint, state='QUEUED', progress_json=payload)
        .on_conflict_do_nothing(index_elements=['kind', 'idempotency_key']).returning(Operation.id))
    operation = session.get(Operation, identity) if identity else session.scalar(select(Operation).where(Operation.kind == kind, Operation.idempotency_key == str(key)))
    if operation.request_sha256 != fingerprint: raise APIError('IDEMPOTENCY_CONFLICT', 'Idempotency key was used for another request.', 409)
    return operation, identity is not None


def request_validation(identity, value, key):
    if value.target_connection_id is None: raise APIError('TARGET_REQUIRED', 'Select a target connection.', 422)
    with transaction() as session:
        upload = require(session, identity, True)
        connection, revision = active(session, value.target_connection_id, lock=True)
        if upload.kind != 'TABLE': raise APIError('INVALID_UPLOAD_KIND', 'A Table Definition upload is required.', 409)
        if value.expected_sha256 and value.expected_sha256 != upload.workbook_sha256:
            raise APIError('CHECKSUM_MISMATCH', 'Workbook checksum changed.', 409)
        if revision.test_status != 'SUCCESS' or not revision.physical_server_fingerprint:
            raise APIError('TARGET_NOT_VERIFIED', 'Test the selected target connection first.', 409)
        payload = dict(upload_id=str(identity), target_revision_id=str(revision.id), sha256=upload.workbook_sha256, phase='VALIDATION')
        operation, created = enqueue(session, 'TABLE_VALIDATE', key, payload)
        if created:
            if upload.status not in ('UPLOADED', 'INVALID'):
                raise APIError('VALIDATION_CONFLICT', 'Workbook validation is already running or complete.', 409)
            if session.scalar(select(TableDefinition.id).where(TableDefinition.upload_id == identity).limit(1)):
                raise APIError('REUPLOAD_REQUIRED', 'A previously validated definition changed dependencies. Upload a new workbook to preserve its history.', 409)
            session.execute(delete(DefinitionIssue).where(DefinitionIssue.upload_id == identity))
            upload.status = 'VALIDATING'
        return operation.id


def issues(identity, limit, offset):
    with transaction() as session:
        require(session, identity)
        def public(issue):
            # message_key resolves to a fixed safe English message; never echo cells.
            return dict(scope=issue.scope, code=issue.code, message=MESSAGES.get(issue.message_key, 'Invalid workbook field.'),
                        **{name:getattr(issue, name) for name in ('sheet', 'row', 'column', 'column_name') if getattr(issue, name) is not None})
        return page(session, select(DefinitionIssue).where(DefinitionIssue.upload_id == identity)
                    .order_by(DefinitionIssue.created_at, DefinitionIssue.id), limit, offset, public)


MESSAGES = {'workbook.invalid': 'Workbook validation failed. Check the indicated location and template requirements.',
            'target.changed': 'Target connection changed. Upload and validate the workbook again.',
            'workbook.checksum': 'Stored workbook checksum does not match the immutable upload.', **VALIDATION_MESSAGES}


def fence(session, operation, owner):
    current = session.scalar(select(Operation).where(Operation.id == operation['id']).with_for_update())
    if current is None or current.state != 'RUNNING' or current.lease_owner != owner or current.lease_until <= datetime.now(timezone.utc):
        raise APIError('OPERATION_LEASE_LOST', 'Operation ownership was lost.', 409)
    return current


def execute_validation(operation, owner):
    from aat_metadata.models.connections import ConnectionRevision, Connection
    payload = operation['progress_json']; identity = UUID(payload['upload_id'])
    with transaction() as session:
        upload = require(session, identity)
        file = session.get(UploadedFile, upload.uploaded_file_id)
        revision = session.get(ConnectionRevision, UUID(payload['target_revision_id']))
        connection = session.get(Connection, revision.connection_id)
        context = TargetContext(connection.code, revision.database_type, revision.database_name,
            revision.schema_name, str(revision.id), revision.physical_server_fingerprint)
        path = storage() / file.safe_storage_key
        expected = file.sha256
    with path.open('rb') as source: actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != expected:
        result_issues = [dict(scope='workbook', code='CHECKSUM_MISMATCH')]; tables = []
    else:
        result = validate(path, context); result_issues = result.issues; tables = result.tables
    with transaction() as session:
        fence(session, operation, owner)
        upload = require(session, identity, True)
        connection, current = active(session, revision.connection_id, lock=True)
        if str(current.id) != context.revision_id:
            result_issues = [dict(scope='resource', code='TARGET_CHANGED')]; tables = []
        for issue in result_issues:
            session.add(DefinitionIssue(upload_id=identity, code=issue['code'], scope=issue['scope'],
                sheet=issue.get('sheet'), row=issue.get('row'), column=issue.get('column'), severity='ERROR',
                message_key='target.changed' if issue['code'] == 'TARGET_CHANGED' else 'workbook.checksum' if issue['code'] == 'CHECKSUM_MISMATCH' else message_key(issue.get('message','')), safe_context={}))
        for spec in tables:
            table = TableDefinition(upload_id=identity, target_connection_revision_id=current.id, target_schema=spec.target_schema,
                table_name=spec.name, description=spec.description, definition_hash=digest(asdict(spec)))
            session.add(table); session.flush()
            for column in spec.columns:
                fields = asdict(column); fields.pop('has_default')
                session.add(TableColumn(table_definition_id=table.id, **fields))
        upload.status = 'INVALID' if result_issues else 'VALIDATED'
        if not result_issues: upload.template_version = '1.0'
    return ('FAILED', 'WORKBOOK_INVALID') if result_issues else ('SUCCEEDED', None)
