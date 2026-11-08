"""Kiểm chứng bootstrap DB thật; chỉ chạy trong namespace sample test riêng."""

import importlib.util
from pathlib import Path


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / name / 'initialize.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check() -> None:
    pg, mysql = load('postgres'), load('mysql')
    pg.initialize()
    mysql.initialize()
    with pg.connect('etl_test', 'aat_etl', 'pg_etl') as connection:
        assert connection.execute('SELECT count(*) FROM sample.customers_source').fetchone()[0] == 3
        connection.execute("UPDATE sample.customers_source SET customer_name='Test edit' WHERE customer_id=1")
    with mysql.connect('aat_etl', 'mysql_etl', 'etl_test') as connection, connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM customers_source')
        assert cursor.fetchone()[0] == 3
        cursor.execute("UPDATE customers_source SET customer_name='Test edit' WHERE customer_id=1")
    pg.initialize()
    mysql.initialize()
    with pg.connect('etl_test', 'aat_etl', 'pg_etl') as connection:
        assert connection.execute('SELECT customer_name FROM sample.customers_source WHERE customer_id=1').fetchone()[0] == 'Test edit'
        assert connection.execute('SELECT version,signature FROM _aat_control.support_schema_version').fetchone() == (1, 'aat-support/1')
    try:
        pg.connect('airflow_metadata', 'aat_app_runtime', 'app_runtime')
    except Exception:
        pass
    else:
        raise AssertionError('App runtime must not connect to Airflow metadata')
    with mysql.connect('aat_etl', 'mysql_etl', 'etl_test') as connection, connection.cursor() as cursor:
        cursor.execute('SELECT customer_name FROM customers_source WHERE customer_id=1')
        assert cursor.fetchone()[0] == 'Test edit'
        cursor.execute("SELECT ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='etl_test'")
        assert all(engine == 'InnoDB' and collation.startswith('utf8mb4') for engine, collation in cursor.fetchall())
        cursor.execute('SELECT @@sql_mode')
        assert 'STRICT_TRANS_TABLES' in cursor.fetchone()[0]
        cursor.execute('SHOW GRANTS')
        grants = str(cursor.fetchall())
        assert 'ALL PRIVILEGES' not in grants and 'GRANT OPTION' not in grants
        cursor.execute('UPDATE _aat_support_schema_version SET version=2 WHERE singleton=1')
    try:
        mysql.initialize()
    except RuntimeError:
        pass
    else:
        raise AssertionError('Incompatible MySQL support signature must fail')
    finally:
        with mysql.connect('aat_etl', 'mysql_etl', 'etl_test') as connection, connection.cursor() as cursor:
            cursor.execute('UPDATE _aat_support_schema_version SET version=1 WHERE singleton=1')
    with pg.connect('etl_test', 'aat_etl', 'pg_etl') as connection:
        connection.execute('UPDATE _aat_control.support_schema_version SET version=2')
    try:
        pg.initialize()
    except RuntimeError:
        pass
    else:
        raise AssertionError('Incompatible PostgreSQL support signature must fail')
    finally:
        with pg.connect('etl_test', 'aat_etl', 'pg_etl') as connection:
            connection.execute('UPDATE _aat_control.support_schema_version SET version=1')
    print('DB_INIT_IDEMPOTENCE_GRANTS_ENGINE_PASS')


if __name__ == '__main__':
    check()
