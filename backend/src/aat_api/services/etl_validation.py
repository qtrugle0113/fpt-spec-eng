"""Durable whole-workbook ETL validation; publish revisions atomically."""
import hashlib
from uuid import UUID
from sqlalchemy import select,delete,func
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
from aat_metadata.models.connections import Connection,ConnectionRevision
from aat_metadata.models.definitions import UploadedFile,DefinitionIssue
from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision,ColumnMapping
from aat_metadata.models.settings import ApplicationSetting
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services import definition_uploads as uploads
from aat_api.services.etl_preview import compile_definition,digest
from aat_api.validation.etl_definitions import validate


def request_validation(identity,value,key):
    if value.target_connection_id is not None or value.parser_revision is not None:
        raise APIError('INVALID_ETL_VALIDATION','ETL connections and file parser revisions are resolved from workbook references.',422)
    with transaction() as session:
        upload=uploads.require(session,identity,True)
        if value.expected_sha256 and value.expected_sha256!=upload.workbook_sha256:
            raise APIError('CHECKSUM_MISMATCH','Workbook checksum changed.',409)
        payload=dict(upload_id=str(identity),sha256=upload.workbook_sha256,phase='VALIDATION')
        operation,created=uploads.enqueue(session,'ETL_VALIDATE',key,payload)
        if created:
            if upload.status not in ('UPLOADED','INVALID'):raise APIError('VALIDATION_CONFLICT','Workbook validation is already running or complete.',409)
            if session.scalar(select(ETLDefinitionRevision.id).where(ETLDefinitionRevision.upload_id==identity).limit(1)):
                raise APIError('REUPLOAD_REQUIRED','Upload a new workbook to preserve revision history.',409)
            session.execute(delete(DefinitionIssue).where(DefinitionIssue.upload_id==identity))
            upload.status='VALIDATING'
        return operation.id


def recheck_dependencies(session,dependency):
    for role in ('source','target'):
        identity=dependency.get(role+'_revision_id')
        if identity:
            revision=session.get(ConnectionRevision,UUID(identity))
            connection=session.scalar(select(Connection).where(Connection.id==revision.connection_id).with_for_update())
            if connection.deleted_at or connection.current_revision_id!=revision.id or revision.test_status!='SUCCESS' or revision.physical_server_fingerprint!=dependency[role+'_server']:
                raise APIError('DEPENDENCY_CHANGED','A referenced connection changed during validation.',409)
    if dependency.get('file_id'):
        from aat_api.services import files
        file=files.require(session,UUID(dependency['file_id']),True)
        parser=files.current_parser(session,file)
        if files.expired(file) or file.validation_status!='VALID' or file.sha256!=dependency['file_sha256'] or str(parser.id)!=dependency['parser_id']:
            raise APIError('DEPENDENCY_CHANGED','The source file changed during validation.',409)


def publish(session,identity,compiled):
    for spec,item in sorted(compiled,key=lambda entry:entry[1].config.dag_id):
        # Serialize creation too: SELECT FOR UPDATE cannot lock an absent DAG.
        session.execute(select(func.pg_advisory_xact_lock(718423100,func.hashtext(item.config.dag_id))))
        definition=session.scalar(select(ETLDefinition).where(ETLDefinition.dag_id==item.config.dag_id).with_for_update())
        if definition is None:
            definition=ETLDefinition(dag_id=item.config.dag_id);session.add(definition);session.flush()
        number=(session.scalar(select(func.max(ETLDefinitionRevision.revision)).where(ETLDefinitionRevision.definition_id==definition.id)) or 0)+1
        config=item.config.model_dump(mode='json',by_alias=True,exclude_none=True)
        duplicate=session.scalar(select(ETLDefinitionRevision.id).where(ETLDefinitionRevision.definition_id==definition.id,ETLDefinitionRevision.config_json==config))
        if duplicate is not None:raise APIError('ETL_REVISION_EXISTS','Reuse the upload that already owns this immutable configuration.',409)
        revision=ETLDefinitionRevision(definition_id=definition.id,revision=number,upload_id=identity,config_json=config,
            schema_fingerprint_source=item.source_hash,schema_fingerprint_target=item.target_hash,
            dependency_fingerprint=digest(item.dependency),status='VALIDATED')
        session.add(revision);session.flush()
        if definition.current_revision_id is None:definition.current_revision_id=revision.id
        for ordinal,mapping in enumerate(item.config.mappings,1):
            session.add(ColumnMapping(etl_revision_id=revision.id,ordinal=ordinal,source_column=mapping.source_column,
                target_column=mapping.target_column,transformation=mapping.transformation,
                default_literal=mapping.default_literal.model_dump(mode='json') if mapping.default_literal else None,enabled=mapping.enabled))
    session.flush()


def execute(operation,owner):
    identity=UUID(operation['progress_json']['upload_id'])
    with transaction() as session:
        upload=uploads.require(session,identity)
        file=session.get(UploadedFile,upload.uploaded_file_id)
        path=uploads.storage()/file.safe_storage_key;expected=file.sha256
        setting=session.get(ApplicationSetting,'default_batch_size')
        default_batch_size=setting.value_json if setting is not None else 1000
    issues=[];compiled=[]
    try:
        with path.open('rb') as source:actual=hashlib.file_digest(source,'sha256').hexdigest()
        if actual!=expected:raise APIError('CHECKSUM_MISMATCH','Stored workbook checksum changed.',409)
        parsed=validate(path,default_batch_size=default_batch_size);issues=list(parsed.issues)
        if not issues:
            for spec in parsed.definitions:
                try:compiled.append((spec,compile_definition(spec)))
                except (APIError,ValueError,SQLAlchemyError,OSError) as error:
                    issues.append(dict(scope='cell',sheet='ETL_Definitions',row=spec.row,column=1,column_name='DAG ID',
                        code=error.code if isinstance(error,APIError) else 'ETL_DEPENDENCY_INVALID'))
    except (APIError,OSError) as error:
        issues=[dict(scope='workbook',code=error.code if isinstance(error,APIError) else 'WORKBOOK_UNAVAILABLE')]
    with transaction() as session:
        uploads.fence(session,operation,owner);upload=uploads.require(session,identity,True)
        if not issues:
            try:
                # Metadata row locking fences referenced revisions before publication.
                for _,item in sorted(compiled,key=lambda value:value[0].values['dag_id']):recheck_dependencies(session,item.dependency)
            except APIError:issues=[dict(scope='resource',code='DEPENDENCY_CHANGED')]
        if not issues:
            try:
                with session.begin_nested():publish(session,identity,compiled)
            except (APIError,IntegrityError) as error:
                issues=[dict(scope='resource',code=error.code if isinstance(error,APIError) else 'ETL_PUBLICATION_CONFLICT')]
        for issue in issues:
            session.add(DefinitionIssue(upload_id=identity,code=issue['code'],scope=issue['scope'],sheet=issue.get('sheet'),
                row=issue.get('row'),column=issue.get('column'),column_name=issue.get('column_name'),severity='ERROR',
                message_key='etl.'+issue['code'],safe_context={}))
        upload.status='INVALID' if issues else 'VALIDATED'
        if not issues:upload.template_version='1.0'
    return ('FAILED','WORKBOOK_INVALID') if issues else ('SUCCEEDED',None)
