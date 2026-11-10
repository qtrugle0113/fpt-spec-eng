"""Read immutable encrypted revisions directly; no backend HTTP credential lookup."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from aat_metadata.network import resolve_host
from aat_metadata.secrets.codec import SecretCodec


@contextmanager
def revision_engine(metadata,revision_id):
    with metadata.connect() as connection:
        revision=connection.execute(text("""SELECT r.database_type,r.host,r.port,r.database_name,r.schema_name,r.username,
            r.physical_server_fingerprint,s.key_id,s.ciphertext FROM connection_revisions r JOIN connection_secrets s ON s.id=r.secret_id
            WHERE r.id=:id"""),{'id':UUID(str(revision_id))}).mappings().first()
        if revision is None:raise ValueError('Pinned connection revision is unavailable.')
        revision=dict(revision)
    codec=SecretCodec(Path(os.environ.get('AAT_APP_KEYRING','/secrets/app_keyring')))
    password=codec.decrypt(revision['key_id'],revision['ciphertext']);address=resolve_host(revision['host'],revision['port'])[0]
    if revision['database_type']=='POSTGRESQL':
        url=URL.create('postgresql+psycopg',username=revision['username'],password=password,host=revision['host'],port=revision['port'],database=revision['database_name'],
            query={'hostaddr':address,'connect_timeout':'3'})
        options={'options':'-c statement_timeout=30000 -c lock_timeout=3000'}
    elif revision['database_type']=='MYSQL':
        url=URL.create('mysql+pymysql',username=revision['username'],password=password,host=address,port=revision['port'],database=revision['database_name'],query={'charset':'utf8mb4'})
        options=dict(connect_timeout=3,read_timeout=30,write_timeout=30)
    else:raise ValueError('Unsupported pinned database adapter.')
    engine=create_engine(url,poolclass=NullPool,hide_parameters=True,connect_args=options)
    try:
        with engine.connect() as connection:
            if revision['database_type']=='POSTGRESQL':
                identity=connection.execute(text('SELECT inet_server_addr()::text,inet_server_port(),oid::text FROM pg_database WHERE datname=current_database()')).one()
                fingerprint=hashlib.sha256(json.dumps(['POSTGRESQL',*identity],separators=(',',':')).encode()).hexdigest()
            else:
                identity=connection.scalar(text('SELECT @@server_uuid'))
                fingerprint=hashlib.sha256(('MYSQL:'+identity).encode()).hexdigest()
            if fingerprint!=revision['physical_server_fingerprint']:raise ValueError('Pinned physical server identity changed.')
        yield engine
    finally:engine.dispose();password=None
