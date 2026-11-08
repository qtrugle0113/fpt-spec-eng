"""Probe bootstrap: truy vấn thật, lỗi được che secret; không giả product readiness."""

import json
import os
from pathlib import Path
import sys
import time
import urllib.request


def postgres() -> None:
    import psycopg
    root = Path(os.environ.get('AAT_BACKEND_SECRETS', '/secrets/backend'))
    with psycopg.connect(host='postgres', dbname='app_metadata', user='aat_app_runtime',
                        password=(root / 'app_runtime').read_text(), connect_timeout=3) as connection:
        assert connection.execute('SELECT 1').fetchone()[0] == 1


def mysql() -> None:
    import pymysql
    root = Path(os.environ.get('AAT_BACKEND_SECRETS', '/secrets/backend'))
    with pymysql.connect(host='mysql', database='etl_test', user='aat_etl',
                         password=(root / 'mysql_etl').read_text(), connect_timeout=3) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            assert cursor.fetchone()[0] == 1


def airflow() -> None:
    url = os.environ.get('AAT_AIRFLOW_HEALTH_URL', 'http://airflow-apiserver:8080/api/v2/monitor/health')
    with urllib.request.urlopen(url, timeout=3) as response:
        payload = json.load(response)
    for component in ('metadatabase', 'scheduler', 'dag_processor'):
        if payload.get(component, {}).get('status') != 'healthy':
            raise RuntimeError('Airflow component unavailable')


def live() -> None:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3) as response:
        assert json.load(response) == {'status': 'live', 'stage': 'bootstrap'}


def worker() -> None:
    payload = json.loads(Path('/tmp/aat-worker-heartbeat.json').read_text())
    assert payload['stage'] == 'bootstrap' and time.time() - payload['timestamp'] < 20


def databases() -> None:
    postgres()
    mysql()


if __name__ == '__main__':
    probes = {'postgres': postgres, 'mysql': mysql, 'databases': databases,
              'airflow': airflow, 'live': live, 'worker': worker}
    try:
        probes[sys.argv[1]]()
    except Exception:
        raise SystemExit('Bootstrap probe failed; dependency unavailable; credentials suppressed')
