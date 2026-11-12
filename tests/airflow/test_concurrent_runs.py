"""T146: different managed DAGs/aliases serialize one physical target."""
from datetime import datetime,timedelta,timezone
import io
import re
import time
from uuid import UUID,uuid4
from sqlalchemy import text
from tests.airflow.test_execution import WorkflowFixture as _WorkflowFixture


class ConcurrentRunTests(_WorkflowFixture):
    def second_scheduled(self,first,kind):
        from tests.unit.test_etl_workbook import workbook
        from aat_api.services.connections.service import transaction
        from aat_api.services.table_preview import target_engine
        from aat_api.services.etl_validation import execute as validate
        from aat_api.services.etl_preview import preview
        from aat_api.workers import deployments
        alias=self.target(kind)
        source=first['item']['config']['source']
        with transaction() as session:
            code=session.scalar(text('SELECT c.code FROM connections c JOIN connection_revisions r ON r.connection_id=c.id WHERE r.id=:id'),{'id':source['connection_revision_id']})
        source_table='parallel_source_'+uuid4().hex
        with target_engine(UUID(source['connection_revision_id'])) as engine,engine.begin() as connection:
            quote=engine.dialect.identifier_preparer.quote_identifier
            connection.exec_driver_sql('CREATE TABLE '+quote(source['schema'])+'.'+quote(source_table)+' (id INTEGER PRIMARY KEY,note VARCHAR(40))')
            connection.exec_driver_sql('INSERT INTO '+quote(source['schema'])+'.'+quote(source_table)+" VALUES (3,'B writer'),(4,NULL)")
            connection.exec_driver_sql('UPDATE '+quote(source['schema'])+'.'+quote(source['table'])+" SET note='A writer' WHERE id=1")
        dag='parallel_'+uuid4().hex
        book=workbook();sheet=book['ETL_Definitions']
        target=first['item']['config']['target']
        values={'A2':dag,'D2':code,'E2':source['schema'],'F2':source_table,'H2':alias['code'],
            'I2':target['schema'],'J2':target['table'],'K2':'* * * * *',
            'L2':datetime.now(timezone.utc).isoformat(),
                'O2':'UPSERT','P2':'id','Q2':1,'R2':0}
        for cell,value in values.items():sheet[cell]=value
        buffer=io.BytesIO();book.save(buffer);book.close()
        uploaded=self.response(self.client.post('/api/v1/definition-uploads',data={'kind':'ETL'},
            files={'file':('parallel.xlsx',buffer.getvalue(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}),
            'post','/definition-uploads',201)
        command=self.response(self.client.post('/api/v1/definition-uploads/'+uploaded['id']+'/validate',
            headers={'Idempotency-Key':str(uuid4())},json={'expected_sha256':uploaded['sha256']}),
            'post','/definition-uploads/{id}/validate',202)
        self.assertEqual(validate(self.claim(command,'parallel-validate'),'parallel-validate'),('SUCCEEDED',None));self.finish(command)
        reviewed=preview(UUID(uploaded['id']));item=reviewed['items'][0]
        self.assertEqual(item['config']['target']['physical_target_id'],target['physical_target_id'])
        self.assertNotEqual(item['config']['target']['connection_revision_id'],target['connection_revision_id'])
        command=self.response(self.client.post('/api/v1/dag-deployments',headers={'Idempotency-Key':str(uuid4())},
            json={'upload_id':uploaded['id'],'dag_ids':[dag],'confirmation_token':reviewed['confirmation_token'],'support_objects_acknowledged':True}),
            'post','/dag-deployments',202)
        self.assertEqual(deployments.execute(self.claim(command,'parallel-deploy'),'parallel-deploy'),('SUCCEEDED',None));self.finish(command)
        return dag,item

    def simultaneous(self,kind):
        from aat_api.services.connections.service import transaction
        from aat_api.services.table_preview import target_engine
        from aat_api.services.runtime_binding import airflow
        from aat_api.workers import dag_control
        from aat_etl.loaders.session import TargetSession
        def upsert(book,*args):book['ETL_Definitions']['P2']='id'
        first=self.workflow(target_kind=kind,strategy='UPSERT',workbook_edit=upsert)
        second,item=self.second_scheduled(first,kind)
        client=airflow()
        self.addCleanup(lambda:client.pause(first['dag'],True));self.addCleanup(lambda:client.pause(second,True))
        # Both DAGs are paused while the manual request is durably queued.
        command=self.response(self.client.post('/api/v1/dags/'+first['dag']+'/trigger',
            headers={'Idempotency-Key':str(uuid4())},json=first['trigger_body']),'post','/dags/{dag_id}/trigger',202)
        self.assertEqual(dag_control.execute(self.claim(command,'parallel-trigger'),'parallel-trigger'),('SUCCEEDED',None));self.finish(command)
        manual='manual__aat_'+command['id']
        target=first['item']['config']['target']
        with target_engine(first['target_revision']) as engine:
            quote=engine.dialect.identifier_preparer.quote_identifier
            with engine.begin() as connection:
                connection.exec_driver_sql('INSERT INTO '+quote(target['schema'])+'.'+quote(target['table'])+" (id,note) VALUES (3,'old C'),(4,'old D')")
            target_table=quote(target['schema'])+'.'+quote(target['table'])
            maximum=0;observed=False;scheduled=None
            with engine.connect() as row_lock:
                with row_lock.begin():
                    row_lock.execute(text('SELECT id FROM '+target_table+' ORDER BY id FOR UPDATE')).all()
                    with TargetSession(engine,schema=target['schema'],table=target['table'],timeout=0):
                        client.pause(first['dag'],False);client.pause(second,False)
                        deadline=time.monotonic()+120
                        while True:
                            candidates=[run for run in client.runs(second) if run['run_type']=='scheduled']
                            if candidates and scheduled is None:
                                scheduled=candidates[0]['dag_run_id'];client.pause(second,True)
                            if scheduled:
                                try:states=[client.task(first['dag'],manual,'execute_etl')['state'],client.task(second,scheduled,'execute_etl')['state']]
                                except Exception:states=[]
                                self.assertNotIn('failed',states,'A queued contender must wait for the physical target lock')
                                if states==['running','running']:break
                            if time.monotonic()>deadline:self.fail('Both actual SDK tasks did not enter RUNNING while the target was held')
                            time.sleep(.25)
                    stable_since=None;deadline=time.monotonic()+120
                    while True:
                        with transaction() as session:
                            writers=session.scalar(text("SELECT count(*) FROM runtime_leases l JOIN execution_bindings b ON b.id=l.binding_id WHERE b.dag_id IN (:a,:b) AND l.recovery_state='WRITING'"),{'a':first['dag'],'b':second})
                        maximum=max(maximum,writers);observed=observed or writers==1
                        self.assertLessEqual(writers,1,'Managed DAG aliases must not become simultaneous writers')
                        if writers==1:
                            stable_since=stable_since or time.monotonic()
                            if time.monotonic()-stable_since>=.5:break
                        else:stable_since=None
                        if time.monotonic()>deadline:self.fail('A single writer did not reach the row-lock barrier')
                        time.sleep(.025)
            deadline=time.monotonic()+120
            while True:
                runs=[client.run(first['dag'],manual),client.run(second,scheduled)]
                if all(run['state'] in ('success','failed') for run in runs):break
                if time.monotonic()>deadline:self.fail('Serialized managed runs did not finish')
                time.sleep(.025)
            if any(run['state']=='failed' for run in runs):
                from aat_api.airflow_client.monitoring import MonitoringClient
                monitor=MonitoringClient(client.client)
                for dag_id,run_id,run in ((first['dag'],manual,runs[0]),(second,scheduled,runs[1])):
                    if run['state']!='failed':continue
                    try:
                        page=monitor.client.request('GET','/dags/'+dag_id+'/dagRuns/'+run_id+
                            '/taskInstances/execute_etl/logs/1',params={'map_index':-1,'full_content':True})
                        content=' '.join(str(line) for line in page.get('content',[]))
                    except Exception:content=''
                    error_types=sorted(set(re.findall(r'\b[A-Za-z][A-Za-z0-9]*(?:Error|Exception)\b',content)))
                    sqlstates=sorted(set(re.findall(r'\b[0-9A-Z]{5}\b',content)))
                    messages=re.findall(r'(?:AirflowFailException|RuntimeRejected|RuntimeTaskFailed): ([^\r\n]{1,200})',content)
                    print('CONCURRENT_RUN_FAILURE dag='+dag_id+' error_types='+','.join(error_types)+' sqlstates='+','.join(sqlstates)+' messages='+' | '.join(messages),flush=True)
            self.assertTrue(observed,'The observer must witness an actual writer, not only idle snapshots')
            self.assertEqual([run['state'] for run in runs],['success','success'])
            with engine.connect() as reader:
                self.assertEqual(list(reader.execute(text('SELECT id,note FROM '+target['table']+' ORDER BY id'))),[(1,'A writer'),(2,None),(3,'B writer'),(4,None)])
        with transaction() as session:
            bindings=session.execute(text('SELECT b.airflow_run_type,b.target_revision_id,b.state FROM execution_bindings b WHERE (b.dag_id=:a AND b.airflow_run_id=:manual) OR (b.dag_id=:b AND b.airflow_run_id=:scheduled)'),
                {'a':first['dag'],'b':second,'manual':manual,'scheduled':scheduled}).all()
        self.assertEqual(len(bindings),2)
        self.assertEqual({row.airflow_run_type for row in bindings},{'manual','scheduled'})
        self.assertEqual(len({row.target_revision_id for row in bindings}),2)
        self.assertTrue(all(row.state=='COMMIT_VERIFIED' for row in bindings))
        print('CONCURRENT_RUNS_VERIFIED target='+kind+' manual_and_scheduled=true distinct_aliases=true maximum_writers='+str(maximum)+' four_exact_rows=true',flush=True)

    def test_postgres_manual_and_scheduled_aliases_share_one_physical_writer(self):self.simultaneous('POSTGRESQL')
    def test_mysql_manual_and_scheduled_aliases_share_one_physical_writer(self):self.simultaneous('MYSQL')
