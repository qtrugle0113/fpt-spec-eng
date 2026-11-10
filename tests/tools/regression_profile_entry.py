"""Initialize only the private Compose regression database before container tests."""
import os
from pathlib import Path
import sys
import psycopg
from psycopg import sql
from cryptography.fernet import Fernet
import json
from uuid import uuid4

if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':
    raise RuntimeError('Disposable regression profile required')
host=os.environ.get('AAT_REGRESSION_POSTGRES_HOST','regression-postgres')
if host!='regression-postgres':raise RuntimeError('Only the isolated regression database is allowed')
password=Path('/run/regression/password').read_text().strip()
os.environ['AAT_FOUNDATION_TEST_DSN']='postgresql://postgres:'+password+'@'+host+'/app_metadata'
with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN'],autocommit=True) as connection:
    if connection.execute('SELECT current_database()').fetchone()[0]!='app_metadata':
        raise RuntimeError('Unexpected regression database')
    if not connection.execute("SELECT 1 FROM pg_database WHERE datname='airflow_metadata'").fetchone():
        connection.execute('CREATE DATABASE airflow_metadata')
    for role in ('aat_app_owner','aat_app_runtime','aat_airflow','aat_etl'):
        if not connection.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
            connection.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
    connection.execute('REVOKE ALL ON DATABASE app_metadata,airflow_metadata FROM PUBLIC')
    connection.execute('GRANT CONNECT ON DATABASE app_metadata TO aat_app_owner,aat_app_runtime,aat_etl')
    connection.execute('GRANT CONNECT ON DATABASE airflow_metadata TO aat_airflow')
root=Path(os.environ['AAT_APP_KEYRING']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
if not (root/'current.json').exists():
    key_id=uuid4().hex
    key=root/(key_id+'.key');key.write_bytes(Fernet.generate_key());key.chmod(0o600)
    (root/'current.json').write_text(json.dumps({'key_id':key_id}))
from docker.bootstrap.app_init import initialize
initialize()
arguments=sys.argv[1:] or ['pytest','-p','no:cacheprovider','tests/unit','tests/api','-v']
if arguments[0]=='pytest':os.execv(sys.executable,[sys.executable,'-m','pytest',*arguments[1:]])
os.execvp(arguments[0],arguments)
