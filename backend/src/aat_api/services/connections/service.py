"""Short metadata transactions, immutable revisions and explicit safe projections."""
from contextlib import contextmanager
from datetime import datetime,timezone
import os
from pathlib import Path
from sqlalchemy import func,or_,select
from sqlalchemy.exc import DataError,IntegrityError,OperationalError
from sqlalchemy.orm import Session
from aat_metadata.models import registry
from aat_metadata.models.connections import Connection,ConnectionRevision,ConnectionSecret
from aat_metadata.repositories.base import create_app_engine
from aat_metadata.repositories.revisions import StaleRevision
from aat_metadata.secrets.codec import SecretCodec
from aat_api.errors import APIError
from aat_api.logging import logger
from aat_api.schemas.connections import ConnectionCreate,ConnectionPatch
from . import dependencies,mysql,postgres

_ENDPOINT=('database_type','host','port','database_name','schema_name','username')
_LOCATION=('database_type','host','port','database_name','schema_name')


@contextmanager
def transaction():
    engine=create_app_engine()
    try:
        with Session(engine,expire_on_commit=False) as session,session.begin():yield session
    except OperationalError:
        raise APIError('METADATA_UNAVAILABLE','Application metadata is unavailable.',503,True) from None
    except DataError:
        raise APIError('INVALID_CONNECTION','Connection metadata is not valid.',422) from None
    except IntegrityError as error:
        if getattr(error.orig,'sqlstate',None)=='23505':
            raise APIError('CONNECTION_CONFLICT','Connection code is already in use.',409) from None
        raise
    finally:engine.dispose()


def codec() -> SecretCodec:
    try:return SecretCodec(Path(os.environ.get('AAT_APP_KEYRING','/secrets/app_keyring')))
    except (ValueError,RuntimeError):
        raise APIError('ENCRYPTION_UNAVAILABLE','Encryption keys are unavailable.',503) from None


def active(session:Session,identity,*,lock=False):
    statement=select(Connection).where(Connection.id==identity,Connection.deleted_at.is_(None))
    if lock:statement=statement.with_for_update()
    connection=session.scalar(statement)
    if connection is None:raise APIError('CONNECTION_NOT_FOUND','Connection not found.',404)
    return connection,session.get(ConnectionRevision,connection.current_revision_id)


def project(session:Session,connection:Connection,revision:ConnectionRevision) -> dict:
    return {**{field:getattr(connection,field) for field in ('id','code','name','description','created_at','updated_at')},
            **{field:getattr(revision,field) for field in _ENDPOINT},
            'revision':revision.revision,'has_password':revision.secret_id is not None,
            'test_status':revision.test_status,'tested_at':revision.tested_at,
            'needs_revalidation':revision.test_status!='SUCCESS',
            'dependencies':dependencies.list_dependencies(session,connection.id)}


def create(value:ConnectionCreate) -> dict:
    with transaction() as session:
        secret=ConnectionSecret.from_plaintext(codec(),value.password)
        connection=Connection(code=value.code,name=value.name,database_type=value.database_type,description=value.description)
        session.add_all([secret,connection]);session.flush()
        revision=ConnectionRevision(connection_id=connection.id,revision=1,secret_id=secret.id,
                                    **{field:getattr(value,field) for field in _ENDPOINT})
        session.add(revision);session.flush();connection.current_revision_id=revision.id;session.flush()
        return project(session,connection,revision)


def detail(identity) -> dict:
    with transaction() as session:return project(session,*active(session,identity))


def listing(*,search:str|None,database_type:str|None,status:str|None,limit:int,offset:int) -> dict:
    with transaction() as session:
        statement=select(Connection,ConnectionRevision).join(ConnectionRevision,Connection.current_revision_id==ConnectionRevision.id).where(Connection.deleted_at.is_(None))
        if search:
            literal=search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            statement=statement.where(or_(*(field.ilike('%'+literal+'%',escape='\\') for field in (Connection.code,Connection.name,ConnectionRevision.host))))
        if database_type:statement=statement.where(ConnectionRevision.database_type==database_type)
        if status:statement=statement.where(ConnectionRevision.test_status==status)
        total=session.scalar(select(func.count()).select_from(statement.subquery()))
        rows=session.execute(statement.order_by(Connection.created_at,Connection.id).limit(limit).offset(offset)).all()
        items=[project(session,*row) for row in rows]
        return {'items':items,'total':total,'next_offset':offset+len(items) if offset+len(items)<total else None}


def patch(identity,expected_revision:int,value:ConnectionPatch) -> dict:
    changes=value.model_dump(exclude_unset=True)
    with transaction() as session:
        connection,old=active(session,identity,lock=True)
        if old.revision!=expected_revision:raise StaleRevision('Connection revision changed')
        if not changes:return project(session,connection,old)
        if 'code' in changes and changes['code']!=connection.code and dependencies.list_dependencies(session,identity):
            raise APIError('CONNECTION_DEPENDENCY','Connection code is referenced by existing resources.',409)
        endpoint={field:changes.get(field,getattr(old,field)) for field in _ENDPOINT}
        location_changed=any(endpoint[field]!=getattr(old,field) for field in _LOCATION)
        if location_changed and dependencies.has_active_binding(session,identity):
            raise APIError('CONNECTION_ACTIVE_RUN','Connection location cannot change while a run is active or unreconciled.',409)
        credential_changed=bool(changes.get('password'))
        needs_test=credential_changed or any(endpoint[field]!=getattr(old,field) for field in _ENDPOINT)
        secret_id=old.secret_id
        if credential_changed:
            secret=ConnectionSecret.from_plaintext(codec(),changes['password']);session.add(secret);session.flush();secret_id=secret.id
        revision=ConnectionRevision(connection_id=identity,revision=old.revision+1,secret_id=secret_id,**endpoint,
            test_status='UNTESTED' if needs_test else old.test_status,
            tested_at=None if needs_test else old.tested_at,
            physical_server_fingerprint=None if needs_test else old.physical_server_fingerprint)
        session.add(revision);session.flush()
        if needs_test:dependencies.invalidate_dependents(session,identity)
        for field in ('code','name','description'):
            if field in changes:setattr(connection,field,changes[field])
        connection.database_type=endpoint['database_type'];connection.current_revision_id=revision.id
        connection.updated_at=datetime.now(timezone.utc);session.flush()
        return project(session,connection,revision)


def delete(identity,expected_revision:int) -> None:
    with transaction() as session:
        connection,revision=active(session,identity,lock=True)
        if revision.revision!=expected_revision:raise StaleRevision('Connection revision changed')
        if dependencies.list_dependencies(session,identity):
            raise APIError('CONNECTION_DEPENDENCY','Connection is referenced by existing resources.',409)
        connection.deleted_at=datetime.now(timezone.utc);connection.updated_at=connection.deleted_at


def test(identity) -> dict:
    with transaction() as session:
        connection,revision=active(session,identity)
        revision_id=revision.id
        settings={field:getattr(revision,field) for field in _ENDPOINT}
        secret=session.get(ConnectionSecret,revision.secret_id)
        try:password=codec().decrypt(secret.key_id,secret.ciphertext)
        except ValueError:raise APIError('ENCRYPTION_UNAVAILABLE','Required encryption key is unavailable.',503) from None
    adapter=postgres if settings['database_type']=='POSTGRESQL' else mysql
    result=adapter.test_connection(settings,password)
    password=None
    stamp=datetime.now(timezone.utc)
    with transaction() as session:
        connection,revision=active(session,identity,lock=True)
        if revision.id!=revision_id:raise StaleRevision('Connection changed during test')
        revision.test_status=result.status;revision.tested_at=stamp
        revision.physical_server_fingerprint=result.server_fingerprint
    logger.info('connection_test_completed connection_id=%s status=%s code=%s',identity,result.status,result.code)
    messages={'AUTHENTICATION_FAILED':'Authentication failed. Check the username and password.',
              'DATABASE_NOT_FOUND':'The database does not exist.', 'SCHEMA_NOT_FOUND':'The schema does not exist.',
              'PORT_UNREACHABLE':'The database port could not be reached.', 'HOST_UNREACHABLE':'The database host could not be reached.',
              'HOST_NOT_ALLOWED':'The database host is not allowed.', 'TIMEOUT':'The database connection timed out.',
              'PERMISSION_DENIED':'The database account does not have the required permission.',
              'UNKNOWN_DATABASE_ERROR':'The database error could not be classified. Check the connection details.'}
    return {'status':result.status,'tested_at':stamp,'latency_ms':result.latency_ms,
            'error':None if result.status=='SUCCESS' else {'scope':'resource','code':result.code,
                      'message':messages.get(result.code,'Database connection could not be verified.')}}
