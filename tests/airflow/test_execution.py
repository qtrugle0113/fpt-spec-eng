"""T118: public workflow commands execute all eight routes through the real SDK."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import UUID,uuid4
from unittest.mock import patch
import httpx
import psycopg
from psycopg import sql
from sqlalchemy import select,text
from tests.api import test_dag_builder as api


class WorkflowFixture(unittest.TestCase):
    setUp=api.ETLPreviewIntegrationTests.setUp
    target=api.ETLPreviewIntegrationTests.target
    wait=api.ETLPreviewIntegrationTests.wait
    response=api.ETLPreviewIntegrationTests.response
    scenario=api.ETLPreviewIntegrationTests.scenario

    def claim(self,command,owner):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation
        with transaction() as session:
            row=session.get(Operation,UUID(command['id']));row.state='RUNNING'
            row.lease_owner=owner;row.lease_until=datetime.now(timezone.utc)+timedelta(seconds=300)
            return {'id':row.id,'progress_json':row.progress_json}

    def finish(self,command):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation
        with transaction() as session:session.get(Operation,UUID(command['id'])).state='SUCCEEDED'

    def runtime_backend(self):
        private=Path('/tmp/aat-runtime-private')
        password=private/'route-airflow-password';password.write_text(os.environ['AAT_TEST_AIRFLOW_PASSWORD']);password.chmod(0o600)
        token=private/'runtime_token';token.write_text('f'*64);token.chmod(0o600)
        secrets=private/'runtime-secrets';secrets.mkdir(exist_ok=True,mode=0o700)
        role=secrets/'pg_etl';role.write_text('synthetic-sdk-runtime');role.chmod(0o600)
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as connection:
            connection.execute(sql.SQL('ALTER ROLE aat_etl PASSWORD {}').format(sql.Literal('synthetic-sdk-runtime')))
        environment={'AAT_DAGS_ROOT':'/tmp/aat-contract-dags','AAT_AIRFLOW_DAGS_ROOT':'/tmp/aat-contract-dags',
            'AAT_AIRFLOW_ORIGIN':os.environ['AAT_TEST_AIRFLOW_ORIGIN'],'AAT_AIRFLOW_PASSWORD_FILE':str(password),
            'AAT_RUNTIME_TOKEN_FILE':str(token)}
        self.environment=patch.dict(os.environ,environment);self.environment.start();self.addCleanup(self.environment.stop)
        from aat_api.services.runtime_binding import close_airflow
        close_airflow();self.addCleanup(close_airflow)
        server=subprocess.Popen([sys.executable,'-m','uvicorn','aat_api.main:app','--host','0.0.0.0','--port','8000','--no-access-log'],
            env=dict(os.environ),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda:(server.terminate(),server.wait(timeout=10)) if server.poll() is None else None)
        deadline=time.monotonic()+20
        while True:
            try:
                if httpx.get('http://127.0.0.1:8000/api/v1/health/live',timeout=2,trust_env=False).status_code==200:return
            except httpx.HTTPError:pass
            if time.monotonic()>deadline:self.fail('Private fixture backend readiness exceeded deadline')
            time.sleep(.2)

    def workflow(self,source_kind='POSTGRESQL',target_kind='POSTGRESQL',extension=None,scheduled=False,strategy='APPEND',fault_mode=None,workbook_edit=None,file_data=None,parser_options=None,expected_records=None,expect_failure=False,before_trigger=None,expect_trigger_error=None):
        from aat_api.services.connections.service import transaction,active
        from aat_api.services.table_preview import target_engine
        from aat_api.services.etl_preview import preview
        from aat_metadata.models.operations import AdmissionState
        from aat_api.workers import deployments,dag_activation,dag_control
        from aat_api.services.runtime_binding import airflow
        def edit(book,connection,source,target,revision):
            sheet=book['ETL_Definitions'];sheet['O2']=strategy
            if fault_mode=='extraction-kill':sheet['R2']=1;sheet['S2']=0
            if scheduled:
                sheet['K2']='* * * * *';sheet['L2']=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
            if extension:
                from tests.api.test_files import PARSER
                delimiter=',' if extension=='csv' else '|'
                data=file_data if file_data is not None else ('id'+delimiter+'note'+chr(10)+'1'+delimiter+'first'+chr(10)+'2'+delimiter+chr(92)+'N'+chr(10)).encode()
                parser={**PARSER,'delimiter':delimiter,**(parser_options or {})}
                uploaded=self.response(self.client.post('/api/v1/files',data={'parser_json':json.dumps(parser)},
                    files={'file':('sdk-source.'+extension,data,'text/plain')}),'post','/files',201)
                command=self.response(self.client.post('/api/v1/files/'+uploaded['id']+'/validate',
                    headers={'Idempotency-Key':str(uuid4())},json={'expected_sha256':uploaded['sha256'],'parser_revision':1}),
                    'post','/files/{id}/validate',202)
                self.assertEqual(self.wait(command['id'])['state'],'SUCCEEDED')
                sheet['C2']=None
                for cell in ('D2','E2','F2'):sheet[cell]=None
                sheet['G2']=uploaded['id']
                book['Column_Mappings'].append([sheet['A2'].value,'id' if parser['header_present'] else 'column_1','id','Type Conversion',None,'TRUE'])
                book['Column_Mappings'].append([sheet['A2'].value,'note' if parser['header_present'] else 'column_2','note','Direct Mapping',None,'TRUE'])
            elif source_kind!=target_kind:
                connection=self.target(source_kind)
                with transaction() as session:_,current=active(session,UUID(connection['id']));source_revision=current.id
                table='cross_source_'+uuid4().hex
                with target_engine(source_revision) as engine,engine.begin() as cursor:
                    cursor.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY,note VARCHAR(40))'))
                    cursor.execute(text(f"INSERT INTO {table} VALUES (1,'first'),(2,NULL)"))
                sheet['D2']=connection['code'];sheet['E2']='public' if source_kind=='POSTGRESQL' else 'etl_test';sheet['F2']=table
            if workbook_edit:workbook_edit(book,connection,source,target,revision)
        uploaded,validation,dag,target,target_revision=self.scenario(edit=edit,database_type=target_kind)
        self.assertEqual(validation['state'],'SUCCEEDED','Route workbook did not validate')
        expected_failure=expect_failure or fault_mode in ('terminal-extraction','revoke-before-admission')
        if expected_failure:
            with target_engine(target_revision) as engine,engine.begin() as cursor:
                cursor.execute(text(f"INSERT INTO {target} VALUES (99,'old protected row')"))
        self.worker.kill();self.worker.wait(timeout=10);self.runtime_backend()
        current=preview(UUID(uploaded['id']));item=current['items'][0]
        command=self.response(self.client.post('/api/v1/dag-deployments',headers={'Idempotency-Key':str(uuid4())},
            json={'upload_id':uploaded['id'],'dag_ids':[dag],'confirmation_token':current['confirmation_token'],'support_objects_acknowledged':True}),
            'post','/dag-deployments',202)
        from contextlib import nullcontext
        actual_render=deployments.factory.render
        def instrument(*args,**kwargs):
            source=actual_render(*args,**kwargs).decode()
            source=source.replace('from aat_etl.runtime_task import execute_task','from tests.airflow.runtime_authorization_fault_task import execute_task')
            source=source.replace('execute_task(expected_revision=expected_revision)','execute_task(expected_revision=expected_revision,mode='+repr(fault_mode)+')')
            return source.encode()
        with patch.object(deployments.factory,'render',side_effect=instrument) if fault_mode else nullcontext():
            self.assertEqual(deployments.execute(self.claim(command,'route-deploy'),'route-deploy'),('SUCCEEDED',None))
        self.finish(command)
        deployment_id=command['result_links'][0].rsplit('/',1)[1]
        current=preview(UUID(uploaded['id']));item=current['items'][0]
        authority=None
        if strategy=='FULL_REFRESH':
            authority=self.response(self.client.post('/api/v1/etl-definitions/'+item['definition_id']+'/replacement-authorizations',
                headers={'Idempotency-Key':str(uuid4())},json={'revision_id':item['id'],'physical_target_id':item['config']['target']['physical_target_id'],
                    'scope':'SCHEDULED' if scheduled else 'ONCE','allow_empty':False,'acknowledged':True,'confirmation_token':current['confirmation_token']}),
                'post','/etl-definitions/{id}/replacement-authorizations',201)
        def state(paused):
            result=self.client.get('/api/v1/dag-deployments/'+deployment_id)
            command=self.response(self.client.patch('/api/v1/dags/'+dag+'/state',
                headers={'Idempotency-Key':str(uuid4()),'If-Match':result.headers['etag']},json={
                    'expected_revision':item['id'],'confirmation_token':current['confirmation_token'],'is_paused':paused,
                    **({'authorization_id':authority['id']} if authority and scheduled and not paused else {})}),
                'patch','/dags/{dag_id}/state',202)
            self.assertEqual(dag_activation.execute(self.claim(command,'route-state'),'route-state'),('SUCCEEDED',None));self.finish(command)
        state(False)
        if before_trigger:before_trigger(item)
        trigger_key=None;trigger_body=None
        if not scheduled:
            trigger_key=str(uuid4());trigger_body={
                'expected_revision':item['id'],'confirmation_token':current['confirmation_token'],
                **({'authorization_id':authority['id']} if authority else {})}
            response=self.client.post('/api/v1/dags/'+dag+'/trigger',headers={'Idempotency-Key':trigger_key},json=trigger_body)
            if expect_trigger_error:
                failure=self.response(response,'post','/dags/{dag_id}/trigger',409)
                self.assertEqual(failure['error']['code'],expect_trigger_error)
                self.assertNotIn('/data/uploads',response.text)
                with transaction() as session:
                    self.assertEqual(session.scalar(text('SELECT count(*) FROM run_intents WHERE dag_id=:dag'),{'dag':dag}),0)
                    self.assertEqual(session.scalar(text('SELECT state FROM replacement_authorizations WHERE id=:id'),{'id':authority['id']}),'GRANTED')
                with target_engine(target_revision) as engine,engine.connect() as cursor:
                    self.assertEqual(list(cursor.execute(text(f'SELECT id,note FROM {target} ORDER BY id'))),[(99,'old protected row')])
                state(True)
                return dict(dag=dag,item=item,authority=authority)
            command=self.response(response,'post','/dags/{dag_id}/trigger',202)
            self.assertEqual(dag_control.execute(self.claim(command,'route-trigger'),'route-trigger'),('SUCCEEDED',None));self.finish(command)
            run_id='manual__aat_'+command['id']
        else:
            deadline=time.monotonic()+120
            while True:
                runs=[run for run in airflow().runs(dag) if run.get('run_type')=='scheduled']
                if runs:run_id=runs[0]['dag_run_id'];break
                if time.monotonic()>deadline:self.fail('Scheduled SDK run did not appear within deadline')
                time.sleep(1)
        deadline=time.monotonic()+180
        while True:
            run=airflow().run(dag,run_id)
            if run['state'] in ('success','failed'):break
            if time.monotonic()>deadline:self.fail('Real route execution deadline exceeded')
            time.sleep(1)
        if run['state']=='failed' and not expected_failure:
            from aat_api.airflow_client.monitoring import MonitoringClient
            import re
            diagnostic=MonitoringClient(airflow().client).logs(dag,run_id,'execute_etl',attempt=1)
            print('SDK_FAILURE_CODES '+','.join(sorted(set(re.findall(r'\b[A-Z][A-Z0-9_]{3,}\b',json.dumps(diagnostic))))),flush=True)
            if fault_mode=='file-diagnostic':
                with transaction() as session:
                    identity=session.scalar(text('SELECT id FROM execution_bindings WHERE dag_id=:dag AND airflow_run_id=:run'),{'dag':dag,'run':run_id})
                marker=Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(identity)+'-file-diagnostic')
                print('PRIVATE_FIXTURE_STACK '+(marker.read_text() if marker.exists() else 'NO_ENGINE_EXCEPTION_RECORDED'),flush=True)
        self.assertEqual(run['state'],'failed' if expected_failure else 'success','Real route ETL outcome differs; inspect sanitized fixture diagnostics')
        state(True)
        if expected_failure:
            with target_engine(target_revision) as engine,engine.connect() as cursor:
                self.assertEqual(list(cursor.execute(text(f'SELECT id,note FROM {target} ORDER BY id'))),[(99,'old protected row')])
            return dict(dag=dag,authority=authority,run_id=run_id,item=item)
        with target_engine(target_revision) as engine,engine.connect() as cursor:
            self.assertEqual(list(cursor.execute(text(f'SELECT id,note FROM {target} ORDER BY id'))),expected_records if expected_records is not None else [(1,'first'),(2,None)])
        row_count=len(expected_records) if expected_records is not None else 2
        with transaction() as session:
            binding=session.execute(text('SELECT b.state,b.commit_uncertain,b.airflow_run_type,d.state AS dataset_state,d.extracted_rows,d.validated_rows,d.total_bytes,m.extracted_rows AS metric_extracted,m.validated_rows AS metric_validated,m.loaded_rows,m.failed_rows_nullable,m.phase FROM execution_bindings b JOIN dataset_manifests d ON d.id=b.dataset_id JOIN execution_metrics m ON m.binding_id=b.id WHERE b.dag_id=:dag AND b.airflow_run_id=:run'),{'dag':dag,'run':run_id}).one()
            # File APPEND/UPSERT manifests pin raw extraction before typed streaming.
            # Their COMPLETE bytes/counts remain immutable; final validation and
            # verified target commits are projected into execution_metrics.
            manifest_validated=0 if extension and strategy!='FULL_REFRESH' else row_count
            self.assertEqual((binding.state,binding.commit_uncertain,binding.dataset_state,binding.extracted_rows,binding.validated_rows),('COMMIT_VERIFIED',False,'COMPLETE',row_count,manifest_validated))
            expected_phase='COMMIT_VERIFIED' if fault_mode=='target-commit-loss' else 'COMPLETE'
            self.assertEqual((binding.metric_extracted,binding.metric_validated,binding.loaded_rows,binding.failed_rows_nullable,binding.phase),(row_count,row_count,row_count,0,expected_phase))
            self.assertGreater(binding.total_bytes,0)
            self.assertEqual(binding.airflow_run_type,'scheduled' if scheduled else 'manual')
        print('SDK_ROUTE_VERIFIED source='+(extension.upper() if extension else source_kind)+' target='+target_kind+' strategy='+strategy+' scheduled='+str(scheduled)+' rows='+str(row_count)+' null_preserved=true disk_manifest=COMPLETE',flush=True)
        return dict(upload=uploaded,dag=dag,item=item,authority=authority,run_id=run_id,target=target,target_revision=target_revision,
            deployment_id=deployment_id,trigger_key=trigger_key,trigger_body=trigger_body,command=command,confirmation_token=current['confirmation_token'])


class RouteExecutionTests(WorkflowFixture):
    def test_pg_to_pg(self):self.workflow()
    def test_pg_to_mysql(self):self.workflow(target_kind='MYSQL')
    def test_mysql_to_pg(self):self.workflow(source_kind='MYSQL')
    def test_mysql_to_mysql(self):self.workflow(source_kind='MYSQL',target_kind='MYSQL')
    def test_csv_to_pg(self):self.workflow(extension='csv')
    def test_csv_to_mysql(self):self.workflow(target_kind='MYSQL',extension='csv')
    def test_txt_to_pg(self):self.workflow(extension='txt')
    def test_txt_to_mysql(self):self.workflow(target_kind='MYSQL',extension='txt')


class ScheduledExecutionTests(WorkflowFixture):
    def test_scheduled_append(self):self.workflow(scheduled=True)
    def test_scheduled_full_refresh(self):self.workflow(scheduled=True,strategy='FULL_REFRESH')
