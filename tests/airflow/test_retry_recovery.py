"""T144: real SDK APPEND retry and committed-response reconciliation."""
from sqlalchemy import text
from pathlib import Path
import time
from uuid import uuid4
from tests.airflow.test_execution import WorkflowFixture as _WorkflowFixture


class RetryRecoveryTests(_WorkflowFixture):
    def verify(self,kind,mode):
        from aat_api.services.connections.service import transaction
        from aat_api.services.runtime_binding import airflow
        result=self.workflow(target_kind=kind,strategy='APPEND',fault_mode=mode)
        with transaction() as session:
            counts=session.execute(text('SELECT count(DISTINCT i.id),count(DISTINCT b.id) FROM run_intents i JOIN execution_bindings b ON b.run_intent_id=i.id WHERE b.dag_id=:dag AND b.airflow_run_id=:run'),{'dag':result['dag'],'run':result['run_id']}).one()
            self.assertEqual(tuple(counts),(1,1),'A retry must not create a new intent or binding')
            binding=session.execute(text('SELECT state,commit_uncertain FROM execution_bindings WHERE dag_id=:dag AND airflow_run_id=:run'),{'dag':result['dag'],'run':result['run_id']}).one()
            self.assertEqual(tuple(binding),('COMMIT_VERIFIED',False))
            identity=session.scalar(text('SELECT id FROM execution_bindings WHERE dag_id=:dag AND airflow_run_id=:run'),{'dag':result['dag'],'run':result['run_id']})
            self.assertTrue((Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(identity)+'-'+mode)).exists(),'Fault must execute for this exact binding')
        if mode=='extraction-kill':
            task=airflow().task(result['dag'],result['run_id'],'execute_etl')
            self.assertGreater(task['try_number'],1,'The reaped extraction must actually retry through Airflow')
        print('APPEND_RECOVERY_VERIFIED target='+kind+' mode='+mode+' one_binding=true exact_rows=true',flush=True)

    def test_postgres_reaped_extraction_retries_same_binding(self):self.verify('POSTGRESQL','extraction-kill')
    def test_mysql_reaped_extraction_retries_same_binding(self):self.verify('MYSQL','extraction-kill')
    def test_postgres_committed_response_loss_does_not_duplicate(self):self.verify('POSTGRESQL','target-commit-loss')
    def test_mysql_committed_response_loss_does_not_duplicate(self):self.verify('MYSQL','target-commit-loss')


class DependencyRecoveryTests(_WorkflowFixture):
    verify=RetryRecoveryTests.verify

    def test_postgres_source_session_loss_retries_without_partial_dataset(self):self.verify('POSTGRESQL','source-disconnect')
    def test_mysql_source_session_loss_retries_without_partial_dataset(self):self.verify('MYSQL','source-disconnect')
    def test_postgres_target_session_loss_never_blindly_duplicates(self):self.verify('POSTGRESQL','target-disconnect')
    def test_mysql_target_session_loss_never_blindly_duplicates(self):self.verify('MYSQL','target-disconnect')
    def test_postgres_application_projection_loss_reconciles_committed_target(self):self.verify('POSTGRESQL','app-metrics-fail')
    def test_mysql_application_projection_loss_reconciles_committed_target(self):self.verify('MYSQL','app-metrics-fail')


class AppendRerunTests(_WorkflowFixture):
    def rerun(self,kind):
        from sqlalchemy import inspect
        from aat_api.services.table_preview import target_engine
        from aat_api.services.runtime_binding import airflow
        from aat_api.services.connections.service import transaction
        from aat_api.workers import dag_control
        def without_key(book,connection,source,target,revision):
            with target_engine(revision) as engine,engine.begin() as cursor:
                quote=engine.dialect.identifier_preparer.quote_identifier
                primary=inspect(cursor).get_pk_constraint(target)['name']
                cursor.exec_driver_sql('ALTER TABLE '+quote(target)+(' DROP CONSTRAINT '+quote(primary) if kind=='POSTGRESQL' else ' DROP PRIMARY KEY'))
        first=self.workflow(target_kind=kind,strategy='APPEND',workbook_edit=without_key)
        self.assertTrue(any('duplicate' in warning.lower() for warning in first['item']['warnings']),'APPEND risk must be disclosed before deployment')
        client=airflow();client.pause(first['dag'],False)
        self.addCleanup(lambda:client.pause(first['dag'],True))
        command=self.response(self.client.post('/api/v1/dags/'+first['dag']+'/trigger',headers={'Idempotency-Key':str(uuid4())},
            json=first['trigger_body']),'post','/dags/{dag_id}/trigger',202)
        self.assertNotEqual(command['id'],first['command']['id'])
        self.assertEqual(dag_control.execute(self.claim(command,'rerun-trigger'),'rerun-trigger'),('SUCCEEDED',None))
        self.finish(command)
        run_id='manual__aat_'+command['id'];deadline=time.monotonic()+180
        while True:
            state=client.run(first['dag'],run_id)['state']
            if state in ('success','failed'):break
            if time.monotonic()>deadline:self.fail('New APPEND rerun did not reach terminal state')
            time.sleep(1)
        self.assertEqual(state,'success')
        with target_engine(first['target_revision']) as engine,engine.connect() as cursor:
            self.assertEqual(list(cursor.execute(text('SELECT id,note FROM '+first['target']+' ORDER BY id'))),[(1,'first'),(1,'first'),(2,None),(2,None)])
        with transaction() as session:
            count=session.execute(text('SELECT count(DISTINCT i.id),count(DISTINCT b.id) FROM run_intents i JOIN execution_bindings b ON b.run_intent_id=i.id WHERE b.dag_id=:dag'),{'dag':first['dag']}).one()
            self.assertEqual(tuple(count),(2,2),'New rerun must have its own immutable identity')
        print('APPEND_NEW_RUN_VERIFIED target='+kind+' warning=true two_bindings=true expected_duplicates=true',flush=True)

    def test_postgres_new_append_run_has_new_identity_and_disclosed_duplicates(self):self.rerun('POSTGRESQL')
    def test_mysql_new_append_run_has_new_identity_and_disclosed_duplicates(self):self.rerun('MYSQL')


class UncertainCommitTests(_WorkflowFixture):
    def uncertain(self,kind,strategy,worker_restart=False):
        import os
        import psycopg
        from aat_api.services.connections.service import transaction
        from aat_api.services.table_preview import target_engine
        from aat_api.workers.recovery import recover_pending
        records=[(1,'first'),(2,None)]+([(99,'old protected row')] if strategy=='APPEND' else [])
        result=self.workflow(target_kind=kind,strategy=strategy,fault_mode='commit-unresolved',expect_failure=True,failure_records=records)
        with transaction() as session:
            binding=session.execute(text('SELECT b.id,b.commit_uncertain,b.state,d.path_key FROM execution_bindings b JOIN dataset_manifests d ON d.id=b.dataset_id WHERE b.dag_id=:dag'),{'dag':result['dag']}).one()
            self.assertTrue(binding.commit_uncertain)
            self.assertNotEqual(binding.state,'COMMIT_VERIFIED')
            protected=session.scalar(text("SELECT count(*) FROM staging_reservations r JOIN run_intents i ON i.run_uuid=r.run_uuid JOIN execution_bindings b ON b.run_intent_id=i.id WHERE b.id=:id AND r.state='PROTECTED'"),{'id':binding.id})
            self.assertGreater(protected,0,'Uncertain commit must retain protected staging')
        self.assertTrue((Path(os.environ['AAT_STAGING_ROOT'])/binding.path_key/'manifest.json').is_file())
        if strategy=='FULL_REFRESH':
            detail=self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id'])
            self.assertEqual(detail.json()['state'],'RESERVED')
            revoked=self.client.post('/api/v1/replacement-authorizations/'+result['authority']['id']+'/revoke',
                headers={'If-Match':detail.headers['etag'],'Idempotency-Key':str(uuid4())},json={'acknowledged':True})
            self.assertEqual(revoked.status_code,200)
            self.assertEqual(revoked.json()['state'],'REVOKED')
        with target_engine(result['target_revision']) as engine,engine.begin() as cursor:
            cursor.execute(text('INSERT INTO '+result['target']+" VALUES (77,'later independent row')"))
        began=time.monotonic()
        if worker_restart:
            import subprocess
            import sys
            old_pid=self.runtime_api_process.pid
            self.runtime_api_process.terminate();self.runtime_api_process.wait(timeout=10)
            self.runtime_backend()
            self.assertNotEqual(self.runtime_api_process.pid,old_pid)
            worker=subprocess.Popen([sys.executable,'-m','aat_api.workers.main'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.addCleanup(lambda:(worker.kill(),worker.wait(timeout=10)) if worker.poll() is None else None)
            while True:
                with transaction() as session:
                    state=session.scalar(text('SELECT state FROM execution_bindings WHERE id=:id'),{'id':binding.id})
                if state=='COMMIT_VERIFIED':break
                if worker.poll() is not None or time.monotonic()-began>=120:self.fail('Restarted worker did not reconcile the protected target within120seconds')
                time.sleep(.25)
            recovered={'state':state}
        else:
            rows=recover_pending(lambda:psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']),root=os.environ['AAT_STAGING_ROOT'])
            recovered=next(row for row in rows if row['binding_id']==str(binding.id))
        self.assertEqual(recovered['state'],'COMMIT_VERIFIED')
        self.assertLess(time.monotonic()-began,120)
        with target_engine(result['target_revision']) as engine,engine.connect() as cursor:
            self.assertEqual(list(cursor.execute(text('SELECT id,note FROM '+result['target']+' ORDER BY id'))),sorted([*records,(77,'later independent row')]))
        with transaction() as session:
            current=session.execute(text('SELECT state,commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding.id}).one()
            self.assertEqual(tuple(current),('COMMIT_VERIFIED',False))
        if strategy=='FULL_REFRESH':
            detail=self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id']).json()
            self.assertEqual(detail['state'],'CONSUMED')
            self.assertIsNotNone(detail['revoked_at'])
        print('UNCERTAIN_COMMIT_VERIFIED target='+kind+' strategy='+strategy+' protected=true recovery_under_120s=true later_row_preserved=true worker_restart='+str(worker_restart),flush=True)

    def test_postgres_uncertain_append_keeps_protected_evidence_until_reconciliation(self):self.uncertain('POSTGRESQL','APPEND')
    def test_mysql_uncertain_append_keeps_protected_evidence_until_reconciliation(self):self.uncertain('MYSQL','APPEND')
    def test_postgres_revoked_refresh_reconciles_without_replacement_replay(self):self.uncertain('POSTGRESQL','FULL_REFRESH')
    def test_mysql_revoked_refresh_reconciles_without_replacement_replay(self):self.uncertain('MYSQL','FULL_REFRESH')


class WorkerRestartRecoveryTests(_WorkflowFixture):
    uncertain=UncertainCommitTests.uncertain

    def test_postgres_append_recovers_on_actual_worker_startup(self):self.uncertain('POSTGRESQL','APPEND',True)
    def test_mysql_append_recovers_on_actual_worker_startup(self):self.uncertain('MYSQL','APPEND',True)
    def test_postgres_revoked_refresh_recovers_on_actual_worker_startup(self):self.uncertain('POSTGRESQL','FULL_REFRESH',True)
    def test_mysql_revoked_refresh_recovers_on_actual_worker_startup(self):self.uncertain('MYSQL','FULL_REFRESH',True)

