"""T132: aggregates agree with the public API after actual SDK execution."""
from datetime import datetime,timezone
from tests.airflow.test_execution import WorkflowFixture


class DashboardTruthTests(WorkflowFixture):
    def test_real_history_inventory_lifetime_and_date_filter(self):
        context=self.workflow()
        from aat_api.services.runtime_binding import airflow
        from aat_api.services.dashboard import counts,clear_cache
        client=airflow()
        inventory=client.dags()
        history=client.runs(context['dag'])
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['state'],'success')
        clear_cache()
        today=datetime.now(timezone.utc).date().isoformat()
        result=self.response(self.client.get('/api/v1/dashboard',params={
            'from':today,'to':today,'timezone':'UTC','scope':'MANAGED','force_refresh':True}),
            'get','/dashboard',200)
        self.assertEqual(result['inventory']['total'],1)
        self.assertEqual(result['inventory']['paused'],1)
        self.assertEqual(result['run_metrics'],counts(history))
        self.assertEqual(result['lifetime_metrics'],counts(history))
        self.assertEqual(result['last_successful_run']['run_id'],context['run_id'])
        self.assertEqual(result['last_successful_run_availability'],'AVAILABLE')
        self.assertFalse(result['stale'])
        self.assertTrue(any(row['run_id']==context['run_id'] for row in result['recent_runs']))
        past=self.response(self.client.get('/api/v1/dashboard',params={
            'from':'2001-01-01','to':'2001-01-01','timezone':'Asia/Seoul','scope':'MANAGED'}),
            'get','/dashboard',200)
        self.assertEqual(past['run_metrics']['total'],0)
        self.assertIsNone(past['run_metrics']['success_rate'])
        self.assertEqual(past['lifetime_metrics'],result['lifetime_metrics'])
        self.assertEqual(past['last_successful_run'],result['last_successful_run'])
        external=self.response(self.client.get('/api/v1/dashboard',params={'scope':'EXTERNAL'}),
            'get','/dashboard',200)
        self.assertEqual(external['inventory']['total'],len(inventory)-1)
        self.assertEqual(external['run_metrics']['total'],0)
        self.verify_external_history_spans_pages()

    def verify_external_history_spans_pages(self):
        from pathlib import Path
        import time
        from uuid import uuid4
        from aat_api.services.runtime_binding import airflow
        from aat_api.services.dashboard import counts,clear_cache
        client=airflow();dag='dashboard_pages_'+uuid4().hex
        source="from datetime import datetime,timezone\nfrom airflow.sdk import DAG,task\ndef noop():pass\nwith DAG("+repr(dag)+",schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),is_paused_upon_creation=True):\n    task(task_id='noop')(noop)()\n"
        (Path('/tmp/aat-contract-dags')/(dag+'.py')).write_text(source)
        deadline=time.monotonic()+120
        while True:
            try:client.dag(dag);break
            except Exception:
                if time.monotonic()>deadline:self.fail('Dashboard external fixture did not register')
                time.sleep(1)
        for index in range(205):
            identity='manual__dashboard_'+str(index)
            client.client.request('POST','/dags/'+dag+'/dagRuns',json={'dag_run_id':identity,'logical_date':None})
            if index<4:
                client.client.request('PATCH','/dags/'+dag+'/dagRuns/'+identity,json={'state':'success' if index<2 else 'failed'})
        history=client.runs(dag)
        self.assertEqual(len(history),205)
        expected=counts(history)
        self.assertEqual((expected['successful'],expected['failed'],expected['queued']),(2,2,201))
        clear_cache()
        result=self.response(self.client.get('/api/v1/dashboard',params={'scope':'EXTERNAL','force_refresh':True}),
            'get','/dashboard',200)
        self.assertEqual(result['run_metrics'],expected)
        self.assertEqual(result['lifetime_metrics'],expected)
        self.assertEqual(result['run_metrics']['success_rate'],50)
        self.assertEqual(result['inventory']['total'],1)
        self.assertIn('historical_schedule',result['unavailable_fields'])
        self.assertEqual(result['completeness'],'INCOMPLETE')
        # A separate real task supplies RUNNING without unpausing the 201
        # queued pagination fixtures or pretending a patched state executed.
        running_dag='dashboard_running_'+uuid4().hex
        source="from datetime import datetime,timezone\nfrom airflow.sdk import DAG,task\ndef work():\n    import time\n    time.sleep(90)\nwith DAG("+repr(running_dag)+",schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),is_paused_upon_creation=True):\n    task(task_id='work')(work)()\n"
        (Path('/tmp/aat-contract-dags')/(running_dag+'.py')).write_text(source)
        deadline=time.monotonic()+120
        while True:
            try:client.dag(running_dag);break
            except Exception:
                if time.monotonic()>deadline:self.fail('Running fixture did not register')
                time.sleep(1)
        client.client.request('POST','/dags/'+running_dag+'/dagRuns',json={'dag_run_id':'manual__running','logical_date':None})
        client.client.request('PATCH','/dags/'+running_dag,json={'is_paused':False})
        while True:
            run=client.run(running_dag,'manual__running')
            if run['state']=='running':break
            if time.monotonic()>deadline:self.fail('Running fixture never entered running')
            time.sleep(1)
        client.client.request('PATCH','/dags/'+running_dag,json={'is_paused':True})
        self.assertTrue(client.dag(running_dag)['is_paused'])
        result=self.response(self.client.get('/api/v1/dashboard',params={'scope':'EXTERNAL','force_refresh':True}),
            'get','/dashboard',200)
        self.assertEqual(result['run_metrics'],counts([*history,run]))
        self.assertEqual(result['run_metrics']['running'],1)
        self.assertEqual(client.run(running_dag,'manual__running')['state'],'running')
