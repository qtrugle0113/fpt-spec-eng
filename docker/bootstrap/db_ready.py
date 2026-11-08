"""SELECT1 trên cả hai DB bằng credential bootstrap; không in DSN hoặc exception."""

from pathlib import Path
import psycopg
import pymysql

root = Path('/secrets/bootstrap_secrets')
try:
    with psycopg.connect(host='postgres', dbname='postgres', user='postgres',
                        password=(root / 'postgres_admin').read_text(), connect_timeout=3) as connection:
        assert connection.execute('SELECT 1').fetchone()[0] == 1
    with pymysql.connect(host='mysql', user='root', password=(root / 'mysql_admin').read_text(), connect_timeout=3) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            assert cursor.fetchone()[0] == 1
except Exception:
    raise SystemExit('Bootstrap DB query unavailable; credentials suppressed')
