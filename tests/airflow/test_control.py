"""T121/T125: app monitoring reads and controls on the real public Airflow API."""
from pathlib import Path
import time
from uuid import uuid4
from tests.airflow.test_execution import WorkflowFixture


class RealMonitoringTests(WorkflowFixture):
    def test_real_inventory_run_task_metrics_and_logs(self):
        context=self.workflow();dag=context['dag'];run=context['run_id']
        inventory=self.response(self.client.get('/api/v1/dags',params={'search':dag,'ownership':'MANAGED','limit':1}),
            'get','/dags',200)
        self.assertEqual(inventory['total'],1);self.assertIsNone(inventory['next_offset'])
        self.assertEqual(inventory['items'][0]['dag_id'],dag)
        detail=self.response(self.client.get('/api/v1/dags/'+dag),'get','/dags/{dag_id}',200)
        self.assertEqual(detail['ownership'],'MANAGED');self.assertIsNotNone(detail['definition_id'])
        self.assertEqual(detail['latest_run_status'],'success')
        self.assertEqual(detail['last_successful_run']['run_id'],run)
        self.assertEqual(detail['last_successful_run_availability'],'AVAILABLE')
        runs=self.response(self.client.get('/api/v1/dags/'+dag+'/runs'),'get','/dags/{dag_id}/runs',200)
        self.assertEqual(runs['total'],1);self.assertEqual(runs['items'][0]['run_id'],run)
        actual=self.response(self.client.get('/api/v1/dags/'+dag+'/runs/'+run),'get','/dags/{dag_id}/runs/{run_id}',200)
        self.assertEqual((actual['state'],actual['run_type']),('success','manual'))
        self.assertEqual(actual['metrics']['loaded_rows'],2)
        self.assertEqual(actual['metrics']['validated_rows'],2)
        self.assertEqual(actual['tasks'][0]['task_id'],'execute_etl')
        self.assertEqual(actual['tasks'][0]['state'],'success')
        logs=self.response(self.client.get('/api/v1/dags/'+dag+'/runs/'+run+'/tasks/execute_etl/logs',params={'attempt':1,'map_index':-1}),
            'get','/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs',200)
        self.assertTrue(logs['available']);self.assertTrue(logs['content'])
        self.assertTrue(all(isinstance(line,str) for line in logs['content']))
        self.assertLessEqual(sum(len(line.encode()) for line in logs['content']),1024**2)
        replay=self.client.post('/api/v1/dags/'+dag+'/trigger',headers={'Idempotency-Key':context['trigger_key']},json=context['trigger_body'])
        self.assertEqual(replay.status_code,202);self.assertEqual(replay.json()['id'],context['command']['id'])
        response=self.client.get('/api/v1/dags/'+dag)
        command=self.response(self.client.patch('/api/v1/dags/'+dag+'/state',headers={'Idempotency-Key':str(uuid4()),'If-Match':response.headers['etag']},
            json={'expected_revision':detail['revision_id'],'confirmation_token':context['confirmation_token'],'is_paused':True}),
            'patch','/dags/{dag_id}/state',202)
        from aat_api.workers import dag_activation
        self.assertEqual(dag_activation.execute(self.claim(command,'monitoring-pause'),'monitoring-pause'),('SUCCEEDED',None));self.finish(command)
        from aat_api.services.runtime_binding import airflow
        self.assertTrue(airflow().dag(dag)['is_paused']);self.assertEqual(airflow().run(dag,run)['state'],'success')

    def test_external_tag_does_not_create_ownership_or_mutation_rights(self):
        from aat_api.services.runtime_binding import airflow
        context=self.workflow();external='external_'+uuid4().hex
        source="from datetime import datetime,timezone\nfrom airflow.sdk import DAG,task\ndef noop():pass\nwith DAG("+repr(external)+",schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),is_paused_upon_creation=True,tags=['aat']):\n    task(task_id='noop')(noop)()\n"
        (Path('/tmp/aat-contract-dags')/(uuid4().hex+'.py')).write_text(source)
        deadline=time.monotonic()+120
        while True:
            try:airflow().dag(external);break
            except Exception:
                if time.monotonic()>deadline:self.fail('External fixture did not register')
                time.sleep(1)
        detail=self.response(self.client.get('/api/v1/dags/'+external),'get','/dags/{dag_id}',200)
        self.assertEqual(detail['ownership'],'EXTERNAL');self.assertIsNone(detail.get('definition_id'))
        denied=self.client.post('/api/v1/dags/'+external+'/trigger',headers={'Idempotency-Key':str(uuid4())},
            json={'expected_revision':context['item']['id'],'confirmation_token':context['confirmation_token']})
        self.assertEqual(denied.status_code,404)
        self.assertTrue(airflow().dag(external)['is_paused'])
