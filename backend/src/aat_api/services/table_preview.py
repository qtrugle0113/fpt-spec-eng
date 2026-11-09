"""Read-only live preflight, typed stored definitions and scope confirmations."""
import base64
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
import hashlib
from uuid import UUID
from sqlalchemy import create_engine, inspect, select, text
import json
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from aat_metadata.models.connections import Connection, ConnectionRevision, ConnectionSecret
from aat_metadata.models.definitions import TableDefinition, TableColumn
from aat_api.errors import APIError
from aat_api.services.connections import postgres, mysql
from aat_api.services.connections.policy import resolve_host
from aat_api.services.connections.service import transaction, codec
from aat_api.services.confirmation import ConfirmationSigner
from aat_api.services.definition_uploads import require, digest
from aat_api.validation.tables import TableSpec, ColumnSpec
from aat_api.ddl import postgres as pg_ddl, mysql as my_ddl


def spec(session, definition):
    columns = session.scalars(select(TableColumn).where(TableColumn.table_definition_id == definition.id).order_by(TableColumn.ordinal)).all()
    fields = ('name','ordinal','logical_type','nullable','length','precision','scale','primary_key_ordinal','default_literal','description')
    return TableSpec(definition.table_name, definition.target_schema,
                     [ColumnSpec(**{name:getattr(column,name) for name in fields},has_default=column.default_literal is not None) for column in columns], definition.description)


def columns_public(definition):
    result=[]
    for column in definition.columns:
        value=asdict(column)
        if not column.has_default: value.pop('default_literal')
        result.append(value)
    return result


def snapshot(session, upload_id):
    upload=require(session,upload_id)
    if upload.status!='VALIDATED' or upload.kind!='TABLE':
        raise APIError('PREVIEW_UNAVAILABLE','Validate the Table Definition workbook first.',409)
    definitions=session.scalars(select(TableDefinition).where(TableDefinition.upload_id==upload_id).order_by(TableDefinition.created_at,TableDefinition.id)).all()
    if not definitions: raise APIError('PREVIEW_UNAVAILABLE','No validated table definitions are available.',409)
    revision=session.get(ConnectionRevision,definitions[0].target_connection_revision_id)
    connection=session.get(Connection,revision.connection_id)
    if connection.deleted_at or connection.current_revision_id!=revision.id or revision.test_status!='SUCCESS':
        raise APIError('TARGET_CHANGED','Target connection changed. Validate a new workbook.',409)
    if any(definition.target_connection_revision_id!=revision.id for definition in definitions):
        raise APIError('INVALID_TARGET_SET','Workbook targets must refer to one connection revision.',409)
    scope=dict(upload_id=str(upload_id),sha256=upload.workbook_sha256,target_revision_id=str(revision.id),
               server_fingerprint=revision.physical_server_fingerprint,
               definitions=[dict(id=str(d.id),hash=d.definition_hash,physical_target_id=d.physical_table_identity) for d in definitions])
    return definitions,revision,scope


def signer():
    ring=codec()
    raw=(ring.keyring/(ring.current+'.key')).read_bytes()
    key=hashlib.sha256(b'aat.table-confirmation.v1\0'+base64.urlsafe_b64decode(raw)).digest()
    return ConfirmationSigner(key)


@contextmanager
def target_engine(revision_id):
    with transaction() as session:
        revision=session.get(ConnectionRevision,revision_id)
        if revision is None: raise APIError('TARGET_NOT_FOUND','Target revision not found.',404)
        config={field:getattr(revision,field) for field in ('database_type','host','port','database_name','schema_name','username')}
        secret=session.get(ConnectionSecret,revision.secret_id)
        password=codec().decrypt(secret.key_id,secret.ciphertext)
        expected=revision.physical_server_fingerprint
    probe=(postgres if config['database_type']=='POSTGRESQL' else mysql).test_connection(config,password)
    if probe.status!='SUCCESS' or probe.server_fingerprint!=expected:
        raise APIError('TARGET_UNAVAILABLE','Target identity or connection could not be verified.',409)
    address=resolve_host(config['host'],config['port'])[0]
    if config['database_type']=='POSTGRESQL':
        url=URL.create('postgresql+psycopg',username=config['username'],password=password,host=config['host'],port=config['port'],
                       database=config['database_name'],query={'hostaddr':address,'connect_timeout':'10'})
        args={'options':'-c statement_timeout=10000 -c lock_timeout=3000'}
    else:
        url=URL.create('mysql+pymysql',username=config['username'],password=password,host=address,port=config['port'],database=config['database_name'],query={'charset':'utf8mb4'})
        args=dict(connect_timeout=10,read_timeout=10,write_timeout=10)
    engine=create_engine(url,poolclass=NullPool,hide_parameters=True,connect_args=args)
    try:
        # Verify the actual pinned endpoint too; the preliminary probe and DNS
        # policy must not authorize a different address returned by another lookup.
        with engine.connect() as connection:
            if config['database_type']=='POSTGRESQL':
                identity=connection.execute(text('SELECT inet_server_addr()::text, inet_server_port(), oid::text FROM pg_database WHERE datname=current_database()')).one()
                fingerprint=hashlib.sha256(json.dumps(['POSTGRESQL',*identity],separators=(',',':')).encode()).hexdigest()
            else:
                identity=connection.scalar(text('SELECT @@server_uuid'))
                fingerprint=hashlib.sha256(('MYSQL:'+identity).encode()).hexdigest()
            if fingerprint!=expected:raise APIError('TARGET_IDENTITY_CHANGED','The pinned target identity changed.',409)
        yield engine
    finally: engine.dispose(); password=None


def preview(upload_id):
    with transaction() as session:
        definitions,revision,scope=snapshot(session,upload_id)
        values=[(d,spec(session,d)) for d in definitions]
        revision_id=revision.id;adapter=pg_ddl if revision.database_type=='POSTGRESQL' else my_ddl
    items=[]
    with target_engine(revision_id) as engine:
        inspector=inspect(engine)
        for definition,definition_spec in values:
            exists=inspector.has_table(definition_spec.name,schema=definition_spec.target_schema)
            items.append(dict(id=str(definition.id),target=definition_spec.target_schema+'.'+definition_spec.name,
                ddl=adapter.compile_table(definition_spec),columns=columns_public(definition_spec),primary_key=definition_spec.primary_key,
                table_name=definition_spec.name,target_schema=definition_spec.target_schema,target_connection_revision_id=revision_id,
                physical_target_id=definition.physical_table_identity,existing_table=exists,
                warnings=['Existing table will not be modified.'] if exists else []))
    # Recheck dependencies after live I/O, before issuing a confirmation.
    with transaction() as session:
        if snapshot(session,upload_id)[2]!=scope: raise APIError('TARGET_CHANGED','Target changed during preview.',409)
    scope['existence']={item['id']:item['existing_table'] for item in items}
    stamp=int(datetime.now(timezone.utc).timestamp())
    return dict(upload_id=upload_id,items=items,confirmation_token=signer().issue(scope,now=stamp),
                expires_at=datetime.fromtimestamp(stamp,timezone.utc)+timedelta(seconds=600),dependency_fingerprint=digest(scope))
