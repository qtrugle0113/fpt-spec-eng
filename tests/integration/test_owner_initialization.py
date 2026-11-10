"""Run production migrations as the real non-superuser owner on a fresh fixture."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import secrets
import subprocess
import sys
import unittest


class OwnerInitializationTests(unittest.TestCase):
    def test_owner_concurrent_migration_seed_and_runtime_grants(self):
        import psycopg
        from psycopg import sql
        from sqlalchemy.engine import make_url

        if os.environ.get('AAT_FOUNDATION_DISPOSABLE') != '1':
            raise RuntimeError('Disposable database required')
        dsn = os.environ['AAT_FOUNDATION_TEST_DSN']
        password = secrets.token_urlsafe(32)
        with psycopg.connect(dsn, autocommit=True) as c:
            self.assertIsNone(c.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0],
                              'Owner test needs an unmigrated fixture')
            c.execute(sql.SQL('ALTER ROLE aat_app_owner PASSWORD {}').format(sql.Literal(password)))
            c.execute('ALTER DATABASE app_metadata OWNER TO aat_app_owner')
        owner_dsn = make_url(dsn).set(username='aat_app_owner', password=password).render_as_string(hide_password=False)
        env = dict(os.environ, AAT_FOUNDATION_TEST_DSN=owner_dsn)
        root = Path(__file__).resolve().parents[2]

        def initialize(_):
            return subprocess.run([sys.executable, str(root/'docker/bootstrap/app_init.py')],
                                  env=env, capture_output=True, timeout=120)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(initialize, range(2)))
        self.assertTrue(all(p.returncode == 0 for p in outcomes),
                        'Non-superuser owner initialization failed; inspect private diagnostics')
        with psycopg.connect(owner_dsn) as c:
            self.assertFalse(c.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()[0])
            self.assertEqual(c.execute('SELECT version_num FROM alembic_version').fetchall(), [('0005_deployment_operation_dags',)])
            self.assertEqual(c.execute('SELECT code FROM connections ORDER BY code').fetchall(), [('mysql_etl',), ('pg_etl',)])
            self.assertEqual(c.execute('SELECT count(*) FROM uploaded_files').fetchone()[0], 2)
            owners = c.execute("SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname='public'").fetchall()
            self.assertEqual(owners, [('aat_app_owner',)])
        with psycopg.connect(dsn) as c:
            c.execute('SET ROLE aat_app_runtime')
            self.assertEqual(c.execute('SELECT count(*) FROM connections').fetchone()[0], 2)
            with self.assertRaises(psycopg.errors.InsufficientPrivilege), c.transaction():
                c.execute('CREATE TABLE public.forbidden_runtime_ddl(id integer)')
            with self.assertRaises(psycopg.errors.InsufficientPrivilege), c.transaction():
                c.execute('DELETE FROM audit_events')
