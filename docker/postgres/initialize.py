"""Bootstrap PostgreSQL: DB/role riêng, không truy cập bảng nghiệp vụ Airflow."""

import os
from pathlib import Path

import psycopg
from psycopg import sql

SECRETS = Path(os.environ.get('AAT_BOOTSTRAP_SECRETS', '/secrets/bootstrap_secrets'))


def connect(database: str = 'postgres', user: str = 'postgres', secret: str = 'postgres_admin'):
    return psycopg.connect(host='postgres', dbname=database, user=user,
                           password=(SECRETS / secret).read_text(), autocommit=True, connect_timeout=5)


def initialize() -> None:
    roles = {'aat_app_owner': 'app_owner', 'aat_app_runtime': 'app_runtime',
             'aat_airflow': 'airflow_db', 'aat_etl': 'pg_etl'}
    with connect() as connection:
        for role, secret in roles.items():
            if not connection.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                connection.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(
                    sql.Identifier(role), sql.Literal((SECRETS / secret).read_text())))
        for database, owner in (('app_metadata', 'aat_app_owner'), ('airflow_metadata', 'aat_airflow'), ('etl_test', 'aat_etl')):
            if not connection.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone():
                connection.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database), sql.Identifier(owner)))
            connection.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
        connection.execute('GRANT CONNECT ON DATABASE app_metadata TO aat_app_runtime')
    with connect('app_metadata', 'aat_app_owner', 'app_owner') as connection:
        connection.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        connection.execute('GRANT USAGE ON SCHEMA public TO aat_app_runtime')
        connection.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO aat_app_runtime')
        connection.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO aat_app_runtime')
    with connect('etl_test', 'aat_etl', 'pg_etl') as connection:
        connection.execute((Path(__file__).with_name('samples.sql')).read_text())
        if connection.execute('SELECT version,signature FROM _aat_control.support_schema_version').fetchall() != [(1, 'aat-support/1')]:
            raise RuntimeError('Unsupported sample support schema signature')
    print('PostgreSQL bootstrap complete; existing sample data preserved')


if __name__ == '__main__':
    try:
        initialize()
    except Exception:
        raise SystemExit('PostgreSQL bootstrap failed; check connectivity, grants and persistent secret volumes')
