"""T017 real-PG tests. No CREATE TABLE/create_all, mock DB or product substitute.

Internal T031 test-first seam: AuthorizationRepository(psycopg_connection),
reserve_once(**request)->dict, admit(**request)->dict, revoke(id), invalidate(id),
reconcile(id, outcome=...), schedule_intent(**request)->dict.
Methods use caller transaction and never commit it. Business refusal is ValueError.
Public error mapping remains T032 responsibility. Fixtures insert only into actual
T029 tables; absence of T031 is an explicit RED assertion after a real DB probe.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
import threading
import time
import unittest
from uuid import uuid4

from tests.unit.test_authorization_states import authorization_module


class AuthorizationRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        cls.dsn = os.environ.get('AAT_FOUNDATION_TEST_DSN')
        if not cls.dsn or os.environ.get('AAT_FOUNDATION_DISPOSABLE') != '1':
            raise RuntimeError('T017 requires explicit disposable PostgreSQL; never use existing volumes')

    def connect(self):
        connection = self.psycopg.connect(self.dsn, connect_timeout=5)
        connection.execute("SET statement_timeout='5s'")
        connection.execute("SET lock_timeout='3s'")
        return connection

    def setUp(self):
        # Probe actual PG before the missing-product assertion, not an import error at collect.
        with self.connect() as c:
            self.assertEqual(c.execute('SELECT current_database()').fetchone()[0], 'app_metadata')
        self.module = authorization_module()
        self.assertTrue(hasattr(self.module, 'AuthorizationRepository'), 'T031 repository class missing')

    def repo(self, connection):
        return self.module.AuthorizationRepository(connection)

    def insert(self, c, table, **values):
        from psycopg import sql
        from psycopg.types.json import Jsonb
        columns = {r[0] for r in c.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s', ('public', table))}
        self.assertTrue(columns, 'T029 actual migration table missing: ' + table)
        for stamp in ('created_at', 'updated_at'):
            if stamp in columns:
                values.setdefault(stamp, datetime.now(timezone.utc))
        self.assertTrue(set(values) <= columns, 'Fixture/Data Model columns drift: ' + table)
        statement = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
            sql.Identifier(table), sql.SQL(',').join(map(sql.Identifier, values)),
            sql.SQL(',').join(sql.Placeholder() for _ in values))
        c.execute(statement, [Jsonb(v) if isinstance(v, (dict, list)) else v for v in values.values()])

    def case(self, c, scope='ONCE', allow_empty=False):
        """DML only, against real migrations. No dependency/model mock or DDL."""
        from aat_metadata.secrets.codec import SecretCodec
        from pathlib import Path
        ids = {k: uuid4() for k in ('connection', 'secret', 'revision', 'file', 'upload', 'definition', 'etl_revision', 'authorization')}
        dag = 't017_' + uuid4().hex
        digest = hashlib.sha256(dag.encode()).hexdigest()
        key_id,ciphertext=SecretCodec(Path(os.environ['AAT_APP_KEYRING'])).encrypt('synthetic')
        self.insert(c, 'connection_secrets', id=ids['secret'], key_id=key_id,ciphertext=ciphertext)
        self.insert(c, 'connections', id=ids['connection'], code=dag,
                    name='T017 synthetic fixture', database_type='POSTGRESQL')
        self.insert(c, 'connection_revisions', id=ids['revision'], connection_id=ids['connection'],
                    revision=1, database_type='POSTGRESQL', host='fixture.invalid', port=5432, database_name='synthetic', schema_name='public',
                    username='synthetic', secret_id=ids['secret'], physical_server_fingerprint=digest,
                    test_status='SUCCESS', tested_at=datetime.now(timezone.utc))
        c.execute('UPDATE connections SET current_revision_id=%s WHERE id=%s', (ids['revision'], ids['connection']))
        self.insert(c, 'uploaded_files', id=ids['file'], original_name='synthetic.xlsx',
                    safe_storage_key=uuid4().hex, sha256=digest, bytes=0, extension='.xlsx',
                    parser_revision=1, validation_status='VALID')
        self.insert(c, 'definition_uploads', id=ids['upload'], kind='ETL', uploaded_file_id=ids['file'],
                    template_version='1.0', workbook_sha256=digest, status='VALIDATED')
        self.insert(c, 'etl_definitions', id=ids['definition'], dag_id=dag, owner='aat', lifecycle='DRAFT')
        self.insert(c, 'etl_definition_revisions', id=ids['etl_revision'], definition_id=ids['definition'],
                    revision=1, upload_id=ids['upload'], config_json={'strategy': 'FULL_REFRESH'},
                    schema_fingerprint_source=digest, schema_fingerprint_target=digest,
                    dependency_fingerprint=digest, status='VALIDATED')
        c.execute('UPDATE etl_definitions SET current_revision_id=%s WHERE id=%s', (ids['etl_revision'], ids['definition']))
        self.insert(c, 'replacement_authorizations', id=ids['authorization'], dag_id=dag,
                    etl_revision_id=ids['etl_revision'], physical_target_id=digest, scope=scope,
                    scope_sha256=digest, schedule_sha256=digest if scope == 'SCHEDULED' else None,
                    allow_empty=allow_empty,
                    allow_empty_acknowledged_at=datetime.now(timezone.utc) if allow_empty else None,
                    acknowledged_at=datetime.now(timezone.utc), state='GRANTED', revision=1)
        return dict(ids, dag=dag, digest=digest)

    def request(self, case, **changes):
        values = dict(authorization_id=case['authorization'], dag_id=case['dag'],
                      etl_revision_id=case['etl_revision'], physical_target_id=case['digest'],
                      scope_sha256=case['digest'], idempotency_key=uuid4(), request_sha256=case['digest'],
                      run_uuid=uuid4(), airflow_run_id='manual__t017_' + uuid4().hex)
        values.update(changes)
        return values

    def binding(self, c, case, intent, dataset_rows=1):
        binding_id = uuid4()
        self.insert(c, 'execution_bindings', id=binding_id, dag_id=case['dag'], airflow_run_id=intent['airflow_run_id'],
                    task_id='transfer', airflow_dag_version_id=str(uuid4()), etl_revision_id=case['etl_revision'],
                    source_revision_id=case['revision'], target_revision_id=case['revision'],
                    authorization_id=case['authorization'], run_intent_id=intent['id'], airflow_run_type='manual',
                    runtime_build='t017', binding_hash=case['digest'], state='BOUND', commit_uncertain=False)
        dataset = uuid4()
        self.insert(c, 'dataset_manifests', id=dataset, execution_binding_id=binding_id, generation=1,
                    snapshot_started_at=datetime.now(timezone.utc), schema_hash=case['digest'], mapping_hash=case['digest'],
                    path_key='t017/' + uuid4().hex, manifest_sha256=case['digest'], extracted_rows=dataset_rows,
                    validated_rows=dataset_rows, total_bytes=1, state='COMPLETE')
        c.execute('UPDATE execution_bindings SET dataset_id=%s WHERE id=%s', (dataset, binding_id))
        return dict(authorization_id=case['authorization'], run_intent_id=intent['id'], binding_id=binding_id,
                    scope_sha256=case['digest'], dataset_sha256=case['digest'], target_identity=case['digest'],
                    owner_process_id='t017', target_session_identity='synthetic-native-lock-session')

    def test_reservation_idempotency_and_payload_conflict(self):
        with self.connect() as c:
            case = self.case(c); request = self.request(case)
            first = self.repo(c).reserve_once(**request)
            self.assertEqual(self.repo(c).reserve_once(**request), first)
            self.assertEqual(first['run_uuid'], request['run_uuid'])
            self.assertEqual(first['airflow_run_id'], request['airflow_run_id'])
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).reserve_once(**dict(request, request_sha256='f' * 64))

    def test_two_transactions_compete_for_once_exactly_one_reservation(self):
        with self.connect() as setup:
            case = self.case(setup)
        barrier = threading.Barrier(2)
        def reserve(_):
            with self.connect() as c:
                barrier.wait(timeout=5)
                try:
                    return self.repo(c).reserve_once(**self.request(case))['id']
                except ValueError:
                    c.rollback(); return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(reserve, range(2)))
        self.assertEqual(sum(x is not None for x in outcomes), 1)
        with self.connect() as c:
            row = c.execute('SELECT state,reserved_intent_id FROM replacement_authorizations WHERE id=%s', (case['authorization'],)).fetchone()
            self.assertEqual(row, ('RESERVED', next(x for x in outcomes if x is not None)))
            self.assertEqual(c.execute('SELECT count(*) FROM run_intents WHERE authorization_id=%s', (case['authorization'],)).fetchone()[0], 1)

    def test_reserved_once_cannot_move_to_new_run(self):
        with self.connect() as c:
            case = self.case(c); first = self.repo(c).reserve_once(**self.request(case))
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).reserve_once(**self.request(case))
            self.assertEqual(c.execute('SELECT reserved_intent_id FROM replacement_authorizations WHERE id=%s', (case['authorization'],)).fetchone()[0], first['id'])

    def test_concurrent_same_request_reuses_one_stable_intent(self):
        with self.connect() as setup:
            case = self.case(setup)
        request = self.request(case)
        barrier = threading.Barrier(2)
        def reserve(_):
            with self.connect() as c:
                barrier.wait(timeout=5)
                return self.repo(c).reserve_once(**request)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(reserve, range(2)))
        self.assertEqual(first, second)
        with self.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM run_intents WHERE authorization_id=%s', (case['authorization'],)).fetchone()[0], 1)

    def test_terminal_authorizations_reject_new_reservation(self):
        for state in ('REVOKED', 'INVALIDATED', 'CONSUMED', 'CLOSED'):
            with self.subTest(state=state), self.connect() as c:
                case = self.case(c)
                c.execute('UPDATE replacement_authorizations SET state=%s WHERE id=%s', (state, case['authorization']))
                with self.assertRaises(ValueError), c.transaction():
                    self.repo(c).reserve_once(**self.request(case))

    def prepared_admission(self, c, dataset_rows=1):
        case = self.case(c)
        intent = self.repo(c).reserve_once(**self.request(case))
        return case, self.binding(c, case, intent, dataset_rows=dataset_rows)

    def test_revoke_before_admission_denies_new_write_and_preserves_evidence(self):
        with self.connect() as c:
            case, request = self.prepared_admission(c)
            self.repo(c).revoke(case['authorization'])
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).admit(**request)
            self.assertEqual(c.execute('SELECT count(*) FROM execution_bindings WHERE id=%s', (request['binding_id'],)).fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM run_intents WHERE id=%s', (request['run_intent_id'],)).fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM dataset_manifests WHERE execution_binding_id=%s', (request['binding_id'],)).fetchone()[0], 1)
            self.assertIsNotNone(c.execute('SELECT revoked_at FROM replacement_authorizations WHERE id=%s', (case['authorization'],)).fetchone()[0])

    def test_admission_before_revoke_can_reconcile_but_not_be_reused(self):
        with self.connect() as c:
            case, request = self.prepared_admission(c)
            admission = self.repo(c).admit(**request)
            self.repo(c).revoke(case['authorization'])
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).admit(**dict(request, owner_process_id='new-writer'))
            self.repo(c).reconcile(admission['id'], outcome='COMMIT_VERIFIED')
            row = c.execute('SELECT state,revoked_at FROM replacement_authorizations WHERE id=%s', (case['authorization'],)).fetchone()
            self.assertEqual(row[0], 'CONSUMED'); self.assertIsNotNone(row[1])

    def test_unknown_commit_blocks_new_epoch_and_protects_binding(self):
        with self.connect() as c:
            case, request = self.prepared_admission(c)
            admission = self.repo(c).admit(**request)
            self.repo(c).reconcile(admission['id'], outcome='NEEDS_RECONCILIATION')
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).admit(**dict(request, owner_process_id='retry-writer'))
            self.assertEqual(c.execute('SELECT state FROM replacement_admissions WHERE id=%s', (admission['id'],)).fetchone()[0], 'NEEDS_RECONCILIATION')

    def test_verified_rollback_requires_new_epoch_and_live_grant(self):
        with self.connect() as c:
            case, request = self.prepared_admission(c)
            first = self.repo(c).admit(**request)
            self.repo(c).reconcile(first['id'], outcome='ROLLBACK_VERIFIED', writer_finished=True)
            second = self.repo(c).admit(**dict(request, owner_process_id='retry-writer'))
            self.assertGreater(second['admission_epoch'], first['admission_epoch'])
            self.repo(c).revoke(case['authorization'])
            self.repo(c).reconcile(second['id'], outcome='ROLLBACK_VERIFIED', writer_finished=True)
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).admit(**dict(request, owner_process_id='third-writer'))

    def test_lock_order_authorization_before_intent_and_binding(self):
        with self.connect() as setup:
            case, request = self.prepared_admission(setup)
        with self.connect() as blocker:
            blocker.execute('SELECT id FROM replacement_authorizations WHERE id=%s FOR UPDATE', (case['authorization'],))
            ready = threading.Event(); pid = []; outcome = []
            def admit():
                with self.connect() as c:
                    pid.append(c.info.backend_pid); ready.set()
                    outcome.append(self.repo(c).admit(**request))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(admit)
                try:
                    self.assertTrue(ready.wait(2))
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        blocked = blocker.execute('SELECT %s=ANY(pg_blocking_pids(%s))', (blocker.info.backend_pid, pid[0])).fetchone()[0]
                        if blocked: break
                        time.sleep(0.02)
                    else: self.fail('Admission did not wait on authorization row')
                    # If repository locks intent/binding first, NOWAIT fails here.
                    blocker.execute('SELECT id FROM run_intents WHERE id=%s FOR UPDATE NOWAIT', (request['run_intent_id'],))
                    blocker.execute('SELECT id FROM execution_bindings WHERE id=%s FOR UPDATE NOWAIT', (request['binding_id'],))
                finally:
                    blocker.commit()
                future.result(timeout=5)
            self.assertEqual(len(outcome), 1)

    def test_scheduled_grant_rejects_manual_and_scope_schedule_drift(self):
        with self.connect() as c:
            case = self.case(c, scope='SCHEDULED')
            request = dict(self.request(case), run_type='scheduled', schedule_sha256=case['digest'])
            for change in ({'run_type': 'manual'}, {'run_type': 'backfill'},
                           {'scope_sha256': 'f' * 64}, {'schedule_sha256': 'f' * 64}):
                with self.subTest(change=change), self.assertRaises(ValueError), c.transaction():
                    self.repo(c).schedule_intent(**dict(request, **change))
            first = self.repo(c).schedule_intent(**request)
            self.assertEqual(self.repo(c).schedule_intent(**request), first)
            self.repo(c).invalidate(case['authorization'])
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).schedule_intent(**dict(request, idempotency_key=uuid4(), run_uuid=uuid4()))

    def test_scheduled_runs_get_distinct_intents_without_consuming_grant(self):
        with self.connect() as c:
            case = self.case(c, scope='SCHEDULED')
            one = dict(self.request(case), run_type='scheduled', schedule_sha256=case['digest'])
            two = dict(self.request(case), run_type='scheduled', schedule_sha256=case['digest'])
            first = self.repo(c).schedule_intent(**one)
            second = self.repo(c).schedule_intent(**two)
            self.assertNotEqual(first['id'], second['id'])
            self.assertEqual(c.execute('SELECT state FROM replacement_authorizations WHERE id=%s', (case['authorization'],)).fetchone()[0], 'GRANTED')

    def test_lock_order_intent_before_binding_after_authorization(self):
        with self.connect() as setup:
            case, request = self.prepared_admission(setup)
        with self.connect() as blocker:
            blocker.execute('SELECT id FROM run_intents WHERE id=%s FOR UPDATE', (request['run_intent_id'],))
            ready = threading.Event(); pid = []
            def admit():
                with self.connect() as c:
                    pid.append(c.info.backend_pid); ready.set()
                    return self.repo(c).admit(**request)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(admit)
                try:
                    self.assertTrue(ready.wait(2))
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        if blocker.execute('SELECT %s=ANY(pg_blocking_pids(%s))', (blocker.info.backend_pid, pid[0])).fetchone()[0]:
                            break
                        time.sleep(0.02)
                    else: self.fail('Admission did not wait on intent row')
                    with self.assertRaises(self.psycopg.errors.LockNotAvailable), blocker.transaction():
                        blocker.execute('SELECT id FROM replacement_authorizations WHERE id=%s FOR UPDATE NOWAIT', (case['authorization'],))
                    blocker.execute('SELECT id FROM execution_bindings WHERE id=%s FOR UPDATE NOWAIT', (request['binding_id'],))
                finally:
                    blocker.commit()
                future.result(timeout=5)

    def test_empty_replacement_needs_explicit_scoped_acknowledgment(self):
        with self.connect() as c:
            case, request = self.prepared_admission(c, dataset_rows=0)
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).admit(**dict(request, dataset_rows=0))
            self.assertFalse(c.execute('SELECT allow_empty FROM replacement_authorizations WHERE id=%s', (case['authorization'],)).fetchone()[0])

    def test_acknowledged_empty_permission_only_applies_to_reserved_run(self):
        with self.connect() as c:
            case = self.case(c, allow_empty=True)
            intent = self.repo(c).reserve_once(**self.request(case))
            request = self.binding(c, case, intent, dataset_rows=0)
            admission = self.repo(c).admit(**dict(request, dataset_rows=0))
            self.assertEqual(admission['state'], 'ADMITTED')
            with self.assertRaises(ValueError), c.transaction():
                self.repo(c).reserve_once(**self.request(case))

    def test_runtime_role_cannot_grant_change_scope_or_delete_evidence(self):
        from psycopg import sql
        role = os.environ.get('AAT_AUTH_RUNTIME_ROLE', 'aat_etl')
        with self.connect() as c:
            self.case(c)
            # A deny-everything role is not accepted as a working runtime role.
            self.assertTrue(c.execute('SELECT has_table_privilege(%s,%s,%s)', (role, 'replacement_authorizations', 'SELECT')).fetchone()[0])
            for table in ('replacement_authorizations', 'run_intents', 'execution_bindings', 'replacement_admissions', 'dataset_manifests', 'staging_artifacts'):
                self.assertFalse(c.execute('SELECT has_table_privilege(%s,%s,%s)', (role, table, 'DELETE')).fetchone()[0])
            self.assertFalse(c.execute('SELECT has_table_privilege(%s,%s,%s)', (role, 'replacement_authorizations', 'INSERT')).fetchone()[0])
            for column in ('scope', 'scope_sha256', 'allow_empty', 'allow_empty_acknowledged_at'):
                self.assertFalse(c.execute('SELECT has_column_privilege(%s,%s,%s,%s)', (role, 'replacement_authorizations', column, 'UPDATE')).fetchone()[0])
            for column in ('state','authorization_id','run_uuid','etl_revision_id'):
                self.assertFalse(c.execute('SELECT has_column_privilege(%s,%s,%s,%s)',(role,'run_intents',column,'UPDATE')).fetchone()[0])
            c.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), c.transaction():
                c.execute('INSERT INTO replacement_authorizations SELECT * FROM replacement_authorizations')
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), c.transaction():
                c.execute('UPDATE replacement_authorizations SET allow_empty=true')
            with self.assertRaises(self.psycopg.errors.InsufficientPrivilege), c.transaction():
                c.execute('DELETE FROM replacement_admissions')


if __name__ == '__main__':
    unittest.main()
