"""T084/T085: real metadata admission is verified under the native target lock."""
import importlib
import unittest
from uuid import uuid4
from sqlalchemy import text
from tests.etl import test_target_ledger as targets
from tests.integration import test_authorization_repository as fixtures


class ReplacementAdmissionTests(unittest.TestCase):
    setUp=targets.TargetLedgerTests.setUp
    engine=targets.TargetLedgerTests.engine
    isolated=targets.TargetLedgerTests.isolated

    def run_case(self,kind,revoke=False,lost_response=False,terminal=False):
        try:module=importlib.import_module('aat_etl.loaders.replacement_admission')
        except ModuleNotFoundError:raise AssertionError('T085 admission adapter missing') from None
        from aat_etl.loaders.session import TargetSession
        helper=fixtures.AuthorizationRepositoryTests();helper.setUpClass();helper.setUp()
        engine,schema=self.isolated(kind)
        with TargetSession(engine,schema=schema,table='output_rows') as target:
            original=helper.insert
            def insert(c,table,**values):
                if table=='replacement_authorizations':values['physical_target_id']=target.physical_identity
                original(c,table,**values)
            helper.insert=insert
            with helper.connect() as c:
                case=helper.case(c)
                intent=helper.repo(c).reserve_once(**helper.request(case,physical_target_id=target.physical_identity))
                request=helper.binding(c,case,intent)
                request['target_identity']=target.physical_identity
                dataset_id=c.execute('SELECT dataset_id FROM execution_bindings WHERE id=%s',(request['binding_id'],)).fetchone()[0]
                if revoke:helper.repo(c).revoke(case['authorization'])
            factory=helper.connect
            if lost_response:
                from contextlib import contextmanager
                calls=[]
                @contextmanager
                def factory():
                    with helper.connect() as c:
                        calls.append(1);yield c
                        c.commit()
                        if len(calls)==1:raise helper.psycopg.OperationalError('Synthetic metadata COMMIT response lost')
            adapter=module.AdmissionAdapter(factory,authorization_id=request['authorization_id'],
                run_intent_id=request['run_intent_id'],binding_id=request['binding_id'],scope_sha256=request['scope_sha256'])
            dataset=module.AdmissionDataset(dataset_id,case['digest'],case['digest'],intent['run_uuid'],1)
            if revoke:
                with self.assertRaises(ValueError):adapter.admit(target,dataset,owner_process_id='fixture')
            else:
                admitted=adapter.admit(target,dataset,owner_process_id='fixture')
                again=adapter.admit(target,dataset,owner_process_id='fixture')
                self.assertEqual(admitted['id'],again['id'])
                self.assertEqual(admitted['target_session_identity'],str(target.session_id))
                with helper.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM replacement_admissions WHERE binding_id=%s',(request['binding_id'],)).fetchone()[0],1)
                if terminal:
                    with self.assertRaises(ValueError):adapter.close_terminal(terminal_verified=True,retry_possible=False,writer_finished=True)
                    adapter.reconcile(admitted['id'],outcome='ROLLBACK_VERIFIED',writer_finished=True)
                    with self.assertRaises(ValueError):adapter.close_terminal(terminal_verified=True,retry_possible=True,writer_finished=True)
                    closed=adapter.close_terminal(terminal_verified=True,retry_possible=False,writer_finished=True)
                    self.assertEqual(closed['state'],'CLOSED');self.assertEqual(closed['reserved_intent_id'],request['run_intent_id'])
                    with self.assertRaises(ValueError):adapter.admit(target,dataset,owner_process_id='new-writer')
            target.connection.rollback()
            self.assertEqual(target.connection.scalar(text('SELECT count(*) FROM output_rows')),0)

    def test_postgres_native_lock_precedes_committed_idempotent_admission(self):self.run_case('postgres')
    def test_mysql_native_lock_precedes_committed_idempotent_admission(self):self.run_case('mysql')
    def test_revoked_authorization_cannot_admit_either_target(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,True)

    def test_lost_metadata_commit_response_reads_back_same_admission(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,lost_response=True)

    def test_terminal_rollback_closes_once_only_after_recovery_and_no_retry(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,terminal=True)
