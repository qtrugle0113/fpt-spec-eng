"""Initialize only the isolated foundation profile database, then run selectors."""
import os
from pathlib import Path
import runpy
import sys
import psycopg

if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Explicit isolated fixture required')
password=Path('/run/fixture/password').read_text()
os.environ['AAT_FOUNDATION_TEST_DSN']='postgresql://postgres:'+password+'@foundation-postgres/app_metadata'
with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN'],autocommit=True) as c:
    if c.execute('SELECT current_database()').fetchone()[0]!='app_metadata':raise RuntimeError('Wrong fixture database')
    c.execute('CREATE DATABASE airflow_metadata')
    for role in ('aat_app_owner','aat_app_runtime','aat_airflow','aat_etl'):c.execute('CREATE ROLE '+role+' LOGIN')
    c.execute('REVOKE ALL ON DATABASE app_metadata,airflow_metadata FROM PUBLIC')
    c.execute('GRANT CONNECT ON DATABASE app_metadata TO aat_app_owner,aat_app_runtime,aat_etl')
    c.execute('GRANT CONNECT ON DATABASE airflow_metadata TO aat_airflow')
selectors=['tests/integration/test_metadata_foundation.py','tests/unit/test_authorization_states.py',
    'tests/integration/test_authorization_repository.py','tests/integration/test_phase2_repositories.py',
    'tests/integration/test_phase2_operations.py','tests/integration/test_phase2_api.py',
    'tests/integration/test_foundation_ready.py','tests/unit/test_bootstrap_secrets.py']
sys.argv=['prepare_foundation_keyring.py','-p','no:cacheprovider',*selectors,'-v','--tb=short']
runpy.run_path(str(Path(__file__).with_name('prepare_foundation_keyring.py')),run_name='__main__')
