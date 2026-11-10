"""T119: an actual FULL_REFRESH SDK run consumes exactly its reserved ONCE."""
from uuid import uuid4
from unittest.mock import patch
import time
from sqlalchemy import text
from tests.airflow.test_execution import WorkflowFixture


class OnceExecutionLifecycleTests(WorkflowFixture):
    def once(self,kind):
        from aat_api.services import dag_control
        from aat_api.services.runtime_binding import airflow
        context=self.workflow(target_kind=kind,strategy='FULL_REFRESH')
        dag=context['dag'];authority=context['authority']
        response=self.client.get('/api/v1/replacement-authorizations/'+authority['id'])
        self.assertEqual(response.status_code,200)
        detail=response.json();self.assertEqual(detail['state'],'CONSUMED')
        self.assertEqual(detail['reserved_run_id'],context['run_id'])
        before=airflow().runs(dag)
        # Replaying the persisted request must not need another valid confirmation,
        # allocate another intent, or contact Airflow to post again.
        with patch.object(dag_control,'preview',side_effect=AssertionError('Replay must not revalidate confirmation')):
            replay=self.client.post('/api/v1/dags/'+dag+'/trigger',headers={'Idempotency-Key':context['trigger_key']},json=context['trigger_body'])
        self.assertEqual(replay.status_code,202)
        self.assertEqual(replay.json()['id'],context['command']['id'])
        another=self.client.post('/api/v1/dags/'+dag+'/trigger',headers={'Idempotency-Key':str(uuid4())},json=context['trigger_body'])
        self.assertEqual(another.status_code,409)
        self.assertEqual(len(airflow().runs(dag)),len(before))
        # Clearing a successful TI is the same reserved run, not permission to
        # replace the table a second time. Preserve a later independent row.
        from aat_api.services.table_preview import target_engine
        from aat_api.airflow_client.client import segment
        with target_engine(context['target_revision']) as engine,engine.begin() as connection:
            connection.execute(text('INSERT INTO '+context['target']+" VALUES (99,'later independent row')"))
        client=airflow()
        previous_attempt=client.task(dag,context['run_id'],'execute_etl')['try_number']
        client.client.request('POST','/dags/'+segment(dag)+'/dagRuns/'+segment(context['run_id'])+'/clear',
            json={'dry_run':False,'only_failed':False,'run_on_latest_version':False})
        client.pause(dag,False);self.addCleanup(lambda:client.pause(dag,True))
        deadline=time.monotonic()+180
        while True:
            run=client.run(dag,context['run_id'])
            task=client.task(dag,context['run_id'],'execute_etl')
            if run['state'] in ('success','failed') and task['try_number']>previous_attempt:break
            if time.monotonic()>deadline:self.fail('Cleared successful FULL_REFRESH run exceeded deadline')
            time.sleep(1)
        self.assertEqual(run['state'],'success')
        with target_engine(context['target_revision']) as engine,engine.connect() as connection:
            self.assertEqual(list(connection.execute(text('SELECT id,note FROM '+context['target']+' ORDER BY id'))),
                [(1,'first'),(2,None),(99,'later independent row')])
        self.assertEqual(len(client.runs(dag)),len(before))
        print('ONCE_CLEAR_VERIFIED target='+kind+' same_run=true no_second_replacement=true',flush=True)

    def test_once_postgresql_run_consumes_only_its_reservation(self):self.once('POSTGRESQL')
    def test_once_mysql_run_consumes_only_its_reservation(self):self.once('MYSQL')

    def test_scheduled_mysql_authority_cannot_be_used_for_a_manual_run(self):
        context=self.workflow(target_kind='MYSQL',strategy='FULL_REFRESH',scheduled=True)
        response=self.client.post('/api/v1/dags/'+context['dag']+'/trigger',headers={'Idempotency-Key':str(uuid4())},json={
            'expected_revision':context['item']['id'],'confirmation_token':context['confirmation_token'],
            'authorization_id':context['authority']['id']})
        self.assertEqual(response.status_code,409)

    def test_backfill_cannot_use_scheduled_authority(self):
        from datetime import datetime,timedelta,timezone
        from aat_api.services.runtime_binding import airflow
        from aat_api.services.connections.service import transaction
        context=self.workflow(strategy='FULL_REFRESH',scheduled=True)
        client=airflow()
        client.client.request('POST','/backfills',json={'dag_id':context['dag'],
            'from_date':context['item']['config']['start_date'],
            'to_date':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),
            'max_active_runs':1,'reprocess_behavior':'completed','run_on_latest_version':True})
        client.pause(context['dag'],False);self.addCleanup(lambda:client.pause(context['dag'],True))
        deadline=time.monotonic()+120
        while True:
            backfills=[run for run in client.runs(context['dag']) if run['run_type']=='backfill']
            if backfills and all(run['state'] in ('success','failed') for run in backfills):break
            if time.monotonic()>deadline:self.fail('Real backfill did not reach a terminal result')
            time.sleep(1)
        self.assertTrue(all(run['state']=='failed' for run in backfills))
        with transaction() as session:
            self.assertEqual(session.scalar(text("SELECT count(*) FROM execution_bindings WHERE dag_id=:dag AND airflow_run_type='backfill'"),{'dag':context['dag']}),0)
        print('BACKFILL_SCOPE_VERIFIED scheduled_authority_rejected=true no_binding=true',flush=True)


class AuthorizationFaultLifecycleTests(WorkflowFixture):
    def check(self,mode,kind):
        from pathlib import Path
        from aat_api.services.connections.service import transaction
        context=self.workflow(target_kind=kind,strategy='FULL_REFRESH',fault_mode=mode)
        detail=self.client.get('/api/v1/replacement-authorizations/'+context['authority']['id']).json()
        if mode in ('terminal-extraction','revoke-before-admission'):
            self.assertEqual(detail['state'],'CLOSED')
        else:self.assertEqual(detail['state'],'CONSUMED')
        with transaction() as session:
            binding=session.scalar(text('SELECT id FROM execution_bindings WHERE dag_id=:dag'),{'dag':context['dag']})
            self.assertTrue((Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(binding)+'-'+mode)).exists(),'Fault must execute for this exact binding')
            admissions=session.execute(text('SELECT a.state FROM replacement_admissions a JOIN execution_bindings b ON b.id=a.binding_id WHERE b.dag_id=:dag'),{'dag':context['dag']}).scalars().all()
            if mode in ('terminal-extraction','revoke-before-admission'):self.assertEqual(admissions,[])
            else:self.assertEqual(admissions,['COMMIT_VERIFIED'])
        print('AUTHORIZATION_FAULT_VERIFIED mode='+mode+' target='+kind+' state='+detail['state'],flush=True)

    def test_admission_response_loss_pg(self):self.check('admission-ack-loss','POSTGRESQL')
    def test_admission_response_loss_mysql(self):self.check('admission-ack-loss','MYSQL')
    def test_target_commit_loss_pg(self):self.check('target-commit-loss','POSTGRESQL')
    def test_target_commit_loss_mysql(self):self.check('target-commit-loss','MYSQL')
    def test_revocation_after_admission_pg(self):self.check('revoke-after-admission','POSTGRESQL')
    def test_revocation_after_admission_mysql(self):self.check('revoke-after-admission','MYSQL')
    def test_revocation_before_admission_pg(self):self.check('revoke-before-admission','POSTGRESQL')
    def test_revocation_before_admission_mysql(self):self.check('revoke-before-admission','MYSQL')
    def test_full_refresh_extraction_retry_pg(self):self.check('extraction-kill','POSTGRESQL')
    def test_full_refresh_extraction_retry_mysql(self):self.check('extraction-kill','MYSQL')
    def test_terminal_extraction_closes_once_pg(self):self.check('terminal-extraction','POSTGRESQL')
    def test_terminal_extraction_closes_once_mysql(self):self.check('terminal-extraction','MYSQL')
