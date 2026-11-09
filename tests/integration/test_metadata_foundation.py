"""T016: real PostgreSQL foundation expectations, deliberately RED before T018–T034.

Use only a disposable database via AAT_FOUNDATION_TEST_DSN; no mock DB, no
connect during collection. The harness owns the database/container, not this file.
Missing infrastructure fails explicitly rather than skipping requirements.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


class MetadataFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        cls.dsn = os.environ.get('AAT_FOUNDATION_TEST_DSN')
        if not cls.dsn or os.environ.get('AAT_FOUNDATION_DISPOSABLE') != '1':
            raise RuntimeError('T016 requires explicit disposable PostgreSQL fixture; never use existing volumes')

    def connect(self):
        return self.psycopg.connect(self.dsn, connect_timeout=5)

    def require_tables(self, connection, *names):
        for name in names:
            exists = connection.execute('SELECT to_regclass(%s)', ('public.' + name,)).fetchone()[0]
            self.assertIsNotNone(exists, f'T029 foundation migration missing table public.{name}')

    def test_application_and_airflow_database_access_are_isolated(self):
        with self.connect() as c:
            self.assertEqual(c.execute('SELECT current_database()').fetchone()[0], 'app_metadata')
            self.assertFalse(c.execute("SELECT has_database_privilege('aat_app_runtime','airflow_metadata','CONNECT')").fetchone()[0])
            self.assertFalse(c.execute("SELECT has_database_privilege('aat_airflow','app_metadata','CONNECT')").fetchone()[0])
            self.assertIsNone(c.execute("SELECT to_regclass('public.dag_run')").fetchone()[0])
            self.assertIsNone(c.execute("SELECT to_regclass('public.task_instance')").fetchone()[0])

    def test_all_dependency_foreign_keys_restrict_history_deletion(self):
        with self.connect() as c:
            self.require_tables(c, 'connections', 'connection_revisions', 'operations', 'execution_bindings')
            rows = c.execute("""SELECT conrelid::regclass::text, confdeltype
                FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace""").fetchall()
            self.assertTrue(rows, 'T019–T029 must create actual foreign keys')
            self.assertTrue(all(action == 'r' for _, action in rows), 'Dependency FK must use RESTRICT, not CASCADE')

    def test_00_two_migration_initializers_serialize_and_keep_same_head(self):
        entry = ROOT / 'docker/bootstrap/app_init.py'
        self.assertTrue(entry.exists(), 'T030 app-init with advisory migration lock is not implemented')
        def initialize():
            return subprocess.run([sys.executable, str(entry)], cwd=ROOT,
                                  env=os.environ.copy(), capture_output=True, text=True, timeout=120)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: initialize(), range(2)))
        for result in results:
            # Do not include raw stdout/DSNs in the assertion or published logs.
            self.assertEqual(result.returncode, 0, 'Concurrent app-init failed; inspect redacted diagnostics')
        with self.connect() as c:
            self.require_tables(c, 'alembic_version', 'connections')
            self.assertEqual(len(c.execute('SELECT version_num FROM alembic_version').fetchall()), 1)
            before = c.execute('SELECT id,code,current_revision_id FROM connections ORDER BY id').fetchall()
        result = initialize()
        self.assertEqual(result.returncode, 0)
        with self.connect() as c:
            self.assertEqual(c.execute('SELECT id,code,current_revision_id FROM connections ORDER BY id').fetchall(), before)

    def test_operation_idempotency_is_enforced_by_database(self):
        with self.connect() as c:
            self.require_tables(c, 'operations')
            key = uuid4()
            statement = """INSERT INTO operations
                (id,kind,idempotency_key,request_sha256,state,deadline_at,attempt)
                VALUES (%s,'TABLE_CREATE',%s,%s,'QUEUED',now()+interval '10 minutes',0)"""
            c.execute(statement, (uuid4(), key, 'a' * 64))
            with self.assertRaises(self.psycopg.errors.UniqueViolation):
                with c.transaction():
                    c.execute(statement, (uuid4(), key, 'b' * 64))
            c.rollback()  # Every fixture row remains test-owned and transient.

    def test_operation_claim_skip_locked_and_reconnect_preserves_reconciliation(self):
        with self.connect() as c:
            self.require_tables(c, 'operations')
            operation_id = uuid4()
            c.execute("""INSERT INTO operations
                (id,kind,idempotency_key,request_sha256,state,deadline_at,attempt,lease_owner,lease_until)
                VALUES (%s,'TABLE_CREATE',%s,%s,'NEEDS_RECONCILIATION',now()+interval '10 minutes',1,
                        'dead-test-worker',now()-interval '1 minute')""", (operation_id, uuid4(), 'a' * 64))
            c.commit()
        try:
            with self.connect() as owner, self.connect() as contender:
                owner.execute('SELECT id FROM operations WHERE id=%s FOR UPDATE', (operation_id,))
                self.assertIsNone(contender.execute('SELECT id FROM operations WHERE id=%s FOR UPDATE SKIP LOCKED', (operation_id,)).fetchone())
            # Close/reconnect models DB-session loss, not a whole worker recovery PASS.
            with self.connect() as reopened:
                state, attempt = reopened.execute('SELECT state,attempt FROM operations WHERE id=%s', (operation_id,)).fetchone()
                self.assertEqual((state, attempt), ('NEEDS_RECONCILIATION', 1))
        finally:
            with self.connect() as c:
                c.execute('DELETE FROM operations WHERE id=%s', (operation_id,))

    def test_worker_restart_does_not_replay_unknown_side_effect(self):
        entry = ROOT / 'backend/src/aat_api/workers/main.py'
        self.assertTrue(entry.exists(), 'T033 durable Operation worker is not implemented; bootstrap heartbeat is insufficient')
        with self.connect() as c:
            self.require_tables(c, 'operations')
            operation_id = uuid4()
            c.execute("""INSERT INTO operations
                (id,kind,idempotency_key,request_sha256,state,deadline_at,attempt,lease_owner,lease_until)
                VALUES (%s,'TABLE_CREATE',%s,%s,'NEEDS_RECONCILIATION',now()+interval '10 minutes',1,
                        'crashed-worker',now()-interval '1 minute')""", (operation_id, uuid4(), 'c' * 64))
        command = json.loads(os.environ.get('AAT_FOUNDATION_WORKER_COMMAND',
                                           json.dumps([sys.executable, '-m', 'aat_api.workers.main'])))
        heartbeat = Path(os.environ.get('AAT_FOUNDATION_HEARTBEAT', '/tmp/aat-worker-heartbeat.json'))
        worker = None
        try:
            with tempfile.TemporaryFile() as private_log:
                pids = []
                for _ in range(2):
                    worker = subprocess.Popen(command, cwd=ROOT, env=os.environ.copy(),
                                              stdout=private_log, stderr=private_log)
                    pids.append(worker.pid)
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        self.assertIsNone(worker.poll(), 'Worker exited before heartbeat; fixture DB wiring must be explicit')
                        if heartbeat.exists():
                            try:
                                if json.loads(heartbeat.read_text())['pid'] == worker.pid:
                                    break
                            except (json.JSONDecodeError, KeyError):
                                pass  # A partially replaced heartbeat is retried within the bounded deadline.
                        time.sleep(0.1)
                    else:
                        self.fail('T033/T034 worker did not publish a live process heartbeat')
                    # Give a real restarted worker a chance to make an invalid claim.
                    time.sleep(1)
                    with self.connect() as c:
                        state = c.execute('SELECT state,attempt FROM operations WHERE id=%s', (operation_id,)).fetchone()
                        self.assertEqual(state, ('NEEDS_RECONCILIATION', 1), 'Unknown side effect was claimed/replayed')
                    worker.kill()
                    worker.wait(timeout=10)
                    worker = None
                self.assertNotEqual(*pids)
        finally:
            if worker is not None:
                worker.kill()
                worker.wait(timeout=10)
            with self.connect() as c:
                c.execute('DELETE FROM operations WHERE id=%s', (operation_id,))

    def test_unknown_error_uses_safe_contract_envelope(self):
        import httpx
        from aat_api.main import app
        # Use the real app in process; no mocked repository, DB or external response.
        import asyncio
        async def request():
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
                return await client.get('/api/v1/operations/' + str(uuid4()))
        response = asyncio.run(request())
        self.assertGreaterEqual(response.status_code, 400)
        body = response.json()
        self.assertIn('error', body, 'T018/T032 safe ErrorResponse missing; framework detail is insufficient')
        self.assertTrue({'code', 'message', 'request_id', 'retryable'} <= body['error'].keys())
        self.assertNotIn('postgresql://', response.text)
        self.assertNotIn('Traceback', response.text)


if __name__ == '__main__':
    unittest.main()
