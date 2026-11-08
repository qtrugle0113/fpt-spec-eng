"""Bootstrap MySQL với password file và grants giới hạn trong sample DB."""

import os
from pathlib import Path

import pymysql

SECRETS = Path(os.environ.get('AAT_BOOTSTRAP_SECRETS', '/secrets/bootstrap_secrets'))


def connect(user: str = 'root', secret: str = 'mysql_admin', database: str | None = None):
    return pymysql.connect(host='mysql', user=user, password=(SECRETS / secret).read_text(),
                           database=database, charset='utf8mb4', autocommit=True, connect_timeout=5)


def initialize() -> None:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute('CREATE DATABASE IF NOT EXISTS etl_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci')
        cursor.execute("CREATE USER IF NOT EXISTS 'aat_etl'@'%%' IDENTIFIED BY %s", ((SECRETS / 'mysql_etl').read_text(),))
        cursor.execute("GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,INDEX,REFERENCES ON etl_test.* TO 'aat_etl'@'%'")
    with connect('aat_etl', 'mysql_etl', 'etl_test') as connection, connection.cursor() as cursor:
        for statement in Path(__file__).with_name('samples.sql').read_text().split(';'):
            if statement.strip():
                cursor.execute(statement)
        cursor.execute('SELECT version,signature FROM _aat_support_schema_version')
        if cursor.fetchall() != ((1, 'aat-support/1'),):
            raise RuntimeError('Unsupported sample support schema signature')
    print('MySQL bootstrap complete; existing sample data preserved')


if __name__ == '__main__':
    try:
        initialize()
    except Exception:
        raise SystemExit('MySQL bootstrap failed; check connectivity, grants and persistent secret volumes')
