"""Actual scheduler/SDK -> private HTTP bind -> encrypted revisions -> target data."""
import json
from datetime import datetime,timedelta,timezone
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from uuid import UUID,uuid4
import httpx
import psycopg
from psycopg import sql
from sqlalchemy import select,text
from sqlalchemy.engine import make_url
from tests.api import test_dag_builder as api


class RealRuntimeExecutionTests(unittest.TestCase):
    setUp=api.ETLPreviewIntegrationTests.setUp
    target=api.ETLPreviewIntegrationTests.target
    wait=api.ETLPreviewIntegrationTests.wait
    response=api.ETLPreviewIntegrationTests.response
    scenario=api.ETLPreviewIntegrationTests.scenario

    def execute_case(self,mode):
        from aat_api.services.connections.service import transaction
        from aat_api.services.table_preview import target_engine
        from aat_api.airflow_client.client import AirflowClient
        from aat_api.airflow_client.deployment import DeploymentClient
        from aat_metadata.models.etl import ETLDefinitionRevision
        from aat_metadata.models.operations import Operation,DAGDeployment,AdmissionState
        from aat_etl.loaders.ledger import ensure_support
        uploaded,operation,dag,target,revision=self.scenario()
        self.assertEqual(operation['state'],'SUCCEEDED')
        with target_engine(revision) as engine,engine.begin() as c:ensure_support(c,schema='public',consent=True)
        with transaction() as session:
            config=session.scalar(select(ETLDefinitionRevision).where(ETLDefinitionRevision.upload_id==UUID(uploaded['id'])))
            config_id=str(config.id);config_sha=config.config_sha256
        private=Path('/tmp/aat-runtime-private')
        token='e'*64;(private/'runtime_token').write_text(token)
        (private/'airflow_password').write_text(os.environ['AAT_TEST_AIRFLOW_PASSWORD'])
        for path in (private/'runtime_token',private/'airflow_password'):path.chmod(0o600)
        runtime_url=make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(username='aat_etl',password='synthetic-sdk-runtime')
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            c.execute(sql.SQL('ALTER ROLE aat_etl PASSWORD {}').format(sql.Literal('synthetic-sdk-runtime')))
        environment={key:os.environ[key] for key in ('AAT_FOUNDATION_DISPOSABLE','AAT_APP_KEYRING','AAT_DB_ALLOWED_HOSTS','AAT_UPLOADS_ROOT','AAT_STAGING_ROOT')}
        environment.update(AAT_FOUNDATION_TEST_DSN=runtime_url.render_as_string(hide_password=False),
            AAT_RUNTIME_BIND_URL=os.environ['AAT_TEST_RUNTIME_BACKEND']+'/internal/runtime/bind',AAT_RUNTIME_TOKEN_FILE=str(private/'runtime_token'))
        (private/'runtime-env.json').write_text(json.dumps(environment));(private/'runtime-env.json').chmod(0o600)
        backend_env=dict(os.environ,AAT_RUNTIME_TOKEN_FILE=str(private/'runtime_token'),AAT_AIRFLOW_PASSWORD_FILE=str(private/'airflow_password'),AAT_AIRFLOW_ORIGIN=os.environ['AAT_TEST_AIRFLOW_ORIGIN'])
        server_log=subprocess.DEVNULL
        server=subprocess.Popen([sys.executable,'-m','uvicorn','aat_api.main:app','--host','0.0.0.0','--port','8000','--no-access-log'],env=backend_env,stdout=server_log,stderr=server_log)
        self.addCleanup(lambda:(server.terminate(),server.wait(timeout=10)) if server.poll() is None else None)
        deadline=time.monotonic()+20
        while True:
            try:
                if httpx.get('http://127.0.0.1:8000/api/v1/health/live',timeout=2,trust_env=False).status_code==200:break
            except httpx.HTTPError:pass
            if time.monotonic()>deadline:self.fail('Private fixture backend did not start')
            time.sleep(.2)
        retries=1 if mode=='extraction-retry' else 0
        source="from datetime import datetime,timedelta,timezone\nfrom airflow.sdk import DAG,task\ndef execute():\n    from tests.airflow.runtime_sdk_fixture import execute\n    execute("+repr(config_id)+","+repr(mode)+")\nwith DAG("+repr(dag)+",schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),catchup=False,max_active_runs=1,is_paused_upon_creation=True,tags=['aat','aat_revision:"+config_sha+"']):\n    task(task_id='execute_etl',retries="+str(retries)+",retry_delay=timedelta(seconds=0),do_xcom_push=False)(execute)()\n"
        published_at=datetime.now(timezone.utc).isoformat()
        path=Path('/tmp/aat-contract-dags')/(str(uuid4())+'.py');path.write_text(source)
        with AirflowClient(os.environ['AAT_TEST_AIRFLOW_ORIGIN'],username='aat_service',password=os.environ['AAT_TEST_AIRFLOW_PASSWORD']) as http:
            airflow=DeploymentClient(http);deadline=time.monotonic()+120
            while True:
                try:
                    details=airflow.details(dag)
                    if details['latest_dag_version']:break
                except Exception:pass
                if time.monotonic()>deadline:self.fail('SDK fixture DAG was not registered')
                time.sleep(1)
            version=details['latest_dag_version']
            from aat_api.deployments.registration import wait as wait_registration
            registered=wait_registration(dict(dag_id=dag,owner_tag='aat',revision_sha256=config_sha,
                fileloc=str(path),published_at=published_at),airflow)
            self.assertEqual(registered['version_id'],version['id'])
            with transaction() as session:
                operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256=config_sha,state='SUCCEEDED');session.add(operation);session.flush()
                deployment=DAGDeployment(operation_id=operation.id,etl_revision_id=UUID(config_id),state='DEPLOYED',revision_sha256=config_sha,
                    generated_file_key=path.name,file_sha256='a'*64,airflow_version_id=UUID(version['id']),airflow_version_number=version['version_number'])
                session.add(deployment);session.flush();session.add(AdmissionState(dag_id=dag,gate_state='OPEN',etl_revision_id=UUID(config_id),deployment_id=deployment.id))
            airflow.pause(dag,False);run_id='manual__sdk_'+uuid4().hex
            http.request('POST','/dags/'+dag+'/dagRuns',json={'dag_run_id':run_id,'logical_date':None,'conf':{}})
            deadline=time.monotonic()+180
            while True:
                run=airflow.run(dag,run_id)
                if run['state'] in ('success','failed'):break
                if time.monotonic()>deadline:self.fail('SDK fixture execution deadline exceeded')
                time.sleep(1)
            task=airflow.task(dag,run_id,'execute_etl')
            if run['state']!='success':
                import re
                origins=Path('/tmp/aat-runtime-staging/import-origins.json')
                if origins.exists():print('SDK_IMPORT_ORIGINS '+origins.read_text(),flush=True)
                try:
                    logs=http.request('GET','/dags/'+dag+'/dagRuns/'+run_id+'/taskInstances/execute_etl/logs/'+str(task['try_number']),params={'full_content':True})
                    # Emit only exception names and frame locations, never log
                    # messages/SQL/locals or arbitrary exception values.
                    serialized=json.dumps(logs)
                    names=sorted(set(re.findall(r'\b[A-Za-z_]*(?:Error|Exception|Unavailable|Rejected|Failed)\b',serialized)))
                    missing=sorted(set(re.findall(r"No module named ['\"]([A-Za-z0-9_.]+)",serialized)))
                    frames=re.findall(r'"(?:filename|lineno|name)":\s*(?:"[A-Za-z0-9_./-]+"|[0-9]+)',serialized)
                    print('SDK_FAILURE_CLASSES '+','.join(names)+' MISSING_MODULES '+','.join(missing)+' FRAMES '+str(frames[-24:]),flush=True)
                except Exception:print('SDK_FAILURE_LOGS_UNAVAILABLE',flush=True)
            self.assertEqual(run['state'],'success','Real SDK task failed; target/metadata evidence retained in fixture log')
            self.assertEqual(task['try_number'],2 if retries else 1)
            self.assertEqual(task['dag_version']['id'],version['id'])
            if mode=='normal':
                from aat_api.deployments.admission import prepare,assert_ready
                with transaction() as session:
                    operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256=config_sha)
                    session.add(operation);session.flush()
                    candidate=DAGDeployment(operation_id=operation.id,etl_revision_id=UUID(config_id),
                        state='READY_TO_DEPLOY',revision_sha256=config_sha,previous_deployment_id=deployment.id)
                    session.add(candidate);session.flush();candidate_id=candidate.id
                prepared=prepare(candidate_id,airflow,airflow_dags_root='/tmp/aat-contract-dags')
                assert_ready(prepared,airflow)
                self.assertFalse(prepared.previous_paused)
                self.assertTrue(airflow.dag(dag)['is_paused'])
                self.assertEqual(airflow.run(dag,run_id)['state'],'success')
                print('REAL_REDEPLOY_ADMISSION_VERIFIED paused=true existing_run=success gate=blocked',flush=True)
        with target_engine(revision) as engine,engine.connect() as c:
            self.assertEqual(list(c.execute(text(f'SELECT id,note FROM {target} ORDER BY id'))),[(1,'first'),(2,None)])
        with transaction() as session:
            row=session.execute(text('SELECT b.id,b.state,b.commit_uncertain,i.run_uuid FROM execution_bindings b JOIN run_intents i ON i.id=b.run_intent_id WHERE b.dag_id=:dag AND b.airflow_run_id=:run'),{'dag':dag,'run':run_id}).one()
            self.assertEqual((row.state,row.commit_uncertain),('COMMIT_VERIFIED',False))
            self.assertEqual(session.scalar(text('SELECT loaded_rows FROM execution_metrics WHERE binding_id=:id'),{'id':row.id}),2)
            generations=session.execute(text('SELECT state FROM dataset_manifests WHERE execution_binding_id=:id ORDER BY generation'),{'id':row.id}).scalars().all()
            self.assertEqual(generations,['EXPIRED','COMPLETE'] if retries else ['COMPLETE'])
        print('SDK_EXECUTION_VERIFIED mode='+mode+' attempts='+str(task['try_number'])+' target_rows=2 dataset_states='+','.join(generations),flush=True)

    def test_real_sdk_executes_through_canonical_bind(self):self.execute_case('normal')
    def test_real_sdk_retries_reaped_extraction_with_same_binding(self):self.execute_case('extraction-retry')

    def deployment_case(self,lost_ack=False,trigger=False):
        from unittest.mock import patch
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinitionRevision
        from aat_metadata.models.operations import Operation,DAGDeployment,AdmissionState
        from aat_api.workers import deployments as worker
        from aat_api.services.runtime_binding import close_airflow,airflow
        uploaded,result,dag,target,target_revision=self.scenario()
        self.assertEqual(result['state'],'SUCCEEDED')
        self.worker.kill();self.worker.wait(timeout=10)
        private=Path('/tmp/aat-runtime-private')
        password=private/'deployment-airflow-password'
        password.write_text(os.environ['AAT_TEST_AIRFLOW_PASSWORD']);password.chmod(0o600)
        from aat_api.services.etl_preview import preview
        current=preview(UUID(uploaded['id']))
        accepted=self.client.post('/api/v1/dag-deployments',headers={'Idempotency-Key':str(uuid4())},json={
            'upload_id':uploaded['id'],'dag_ids':[dag],'confirmation_token':current['confirmation_token'],
            'support_objects_acknowledged':True})
        command=self.response(accepted,'post','/dag-deployments',202)
        identity=UUID(command['result_links'][0].rsplit('/',1)[1])
        with transaction() as session:
            revision=session.scalar(select(ETLDefinitionRevision).where(ETLDefinitionRevision.upload_id==UUID(uploaded['id'])))
            operation=session.get(Operation,UUID(command['id']));operation.state='RUNNING'
            operation.lease_owner='real-deployment-worker';operation.lease_until=datetime.now(timezone.utc)+timedelta(seconds=300)
            work={'id':operation.id,'progress_json':operation.progress_json}
        with patch.dict(os.environ,{'AAT_DAGS_ROOT':'/tmp/aat-contract-dags',
                'AAT_AIRFLOW_DAGS_ROOT':'/tmp/aat-contract-dags','AAT_AIRFLOW_ORIGIN':os.environ['AAT_TEST_AIRFLOW_ORIGIN'],
                'AAT_AIRFLOW_PASSWORD_FILE':str(password)}):
            self.addCleanup(close_airflow)
            if lost_ack:
                actual_write=worker.storage.write
                def lose_response(*args,**kwargs):
                    actual_write(*args,**kwargs)
                    raise OSError('injected durable publication response loss')
                with patch.object(worker.storage,'write',side_effect=lose_response):
                    self.assertEqual(worker.execute(work,'real-deployment-worker')[0],'NEEDS_RECONCILIATION')
                with transaction() as session:
                    session.get(Operation,operation.id).state='NEEDS_RECONCILIATION'
                accepted=self.client.post('/api/v1/dag-deployments/'+str(identity)+'/reconcile',headers={'Idempotency-Key':str(uuid4())})
                recovery_command=self.response(accepted,'post','/dag-deployments/{id}/reconcile',202)
                with transaction() as session:
                    recovery=session.get(Operation,UUID(recovery_command['id']));recovery.state='RUNNING'
                    recovery.lease_owner='real-deployment-worker';recovery.lease_until=datetime.now(timezone.utc)+timedelta(seconds=300)
                    recover={'id':recovery.id,'progress_json':recovery.progress_json}
                with patch.object(worker.storage,'write',side_effect=AssertionError('Reconcile must not republish')):
                    state,code=worker.reconcile(recover,'real-deployment-worker')
            else:state,code=worker.execute(work,'real-deployment-worker')
            self.assertEqual((state,code),('SUCCEEDED',None))
            actual=airflow().dag(dag);self.assertTrue(actual['is_paused'])
            self.assertEqual(airflow().runs(dag),[])
            if trigger:
                token_file=private/'runtime_token';token_file.write_text('e'*64);token_file.chmod(0o600)
                secrets=private/'runtime-secrets';secrets.mkdir(mode=0o700,exist_ok=True)
                runtime_password=secrets/'pg_etl';runtime_password.write_text('synthetic-sdk-runtime');runtime_password.chmod(0o600)
                with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as connection:
                    connection.execute(sql.SQL('ALTER ROLE aat_etl PASSWORD {}').format(sql.Literal('synthetic-sdk-runtime')))
                backend_env=dict(os.environ,AAT_RUNTIME_TOKEN_FILE=str(token_file))
                server=subprocess.Popen([sys.executable,'-m','uvicorn','aat_api.main:app','--host','0.0.0.0','--port','8000','--no-access-log'],
                    env=backend_env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.addCleanup(lambda:(server.terminate(),server.wait(timeout=10)) if server.poll() is None else None)
                deadline=time.monotonic()+20
                while True:
                    try:
                        if httpx.get('http://127.0.0.1:8000/api/v1/health/live',timeout=2,trust_env=False).status_code==200:break
                    except httpx.HTTPError:pass
                    if time.monotonic()>deadline:self.fail('Private runtime backend failed to start')
                    time.sleep(.2)
                from aat_api.services.etl_preview import preview
                from aat_api.workers.dag_control import execute as execute_trigger
                from aat_api.services.table_preview import target_engine
                current=preview(UUID(uploaded['id']))
                from aat_api.workers.dag_activation import execute as execute_activation
                with transaction() as session:
                    generation=session.scalar(select(AdmissionState.generation).where(AdmissionState.dag_id==dag))
                activation=self.client.patch('/api/v1/dags/'+dag+'/state',headers={
                    'Idempotency-Key':str(uuid4()),'If-Match':'"'+str(generation)+'"'},
                    json={'expected_revision':str(revision.id),'confirmation_token':current['confirmation_token'],'is_paused':False})
                state_command=self.response(activation,'patch','/dags/{dag_id}/state',202)
                with transaction() as session:
                    pending=session.get(Operation,UUID(state_command['id']));pending.state='RUNNING'
                    pending.lease_owner='real-state-worker';pending.lease_until=datetime.now(timezone.utc)+timedelta(seconds=300)
                    state_work={'id':pending.id,'progress_json':pending.progress_json}
                self.assertEqual(execute_activation(state_work,'real-state-worker'),('SUCCEEDED',None))
                with transaction() as session:session.get(Operation,UUID(state_command['id'])).state='SUCCEEDED'
                self.assertFalse(airflow().dag(dag)['is_paused'])
                accepted=self.client.post('/api/v1/dags/'+dag+'/trigger',headers={'Idempotency-Key':str(uuid4())},
                    json={'expected_revision':str(revision.id),'confirmation_token':current['confirmation_token']})
                command=self.response(accepted,'post','/dags/{dag_id}/trigger',202)
                with transaction() as session:
                    pending=session.get(Operation,UUID(command['id']));pending.state='RUNNING'
                    pending.lease_owner='real-trigger-worker';pending.lease_until=datetime.now(timezone.utc)+timedelta(seconds=300)
                    trigger_work={'id':pending.id,'progress_json':pending.progress_json}
                self.assertEqual(execute_trigger(trigger_work,'real-trigger-worker'),('SUCCEEDED',None))
                run_id='manual__aat_'+command['id'];deadline=time.monotonic()+180
                while True:
                    execution=airflow().run(dag,run_id)
                    if execution['state'] in ('success','failed'):break
                    if time.monotonic()>deadline:self.fail('Generated DAG runtime deadline exceeded')
                    time.sleep(1)
                self.assertEqual(execution['state'],'success','Generated fixed wrapper runtime did not complete')
                with target_engine(target_revision) as engine,engine.connect() as connection:
                    self.assertEqual(list(connection.execute(text(f'SELECT id,note FROM {target} ORDER BY id'))),[(1,'first'),(2,None)])
                with transaction() as session:
                    binding=session.execute(text('SELECT b.state,b.run_intent_id,i.operation_id FROM execution_bindings b JOIN run_intents i ON i.id=b.run_intent_id WHERE b.dag_id=:dag AND b.airflow_run_id=:run'),{'dag':dag,'run':run_id}).one()
                    self.assertEqual(binding.state,'COMMIT_VERIFIED');self.assertEqual(str(binding.operation_id),command['id'])
                print('PUBLIC_TRIGGER_FIXED_FACTORY_ETL_VERIFIED role=aat_etl target_rows=2 stable_intent=true',flush=True)
        with transaction() as session:
            deployed=session.get(DAGDeployment,identity)
            self.assertEqual(deployed.state,'DEPLOYED');self.assertFalse(deployed.reconcile_required)
            self.assertIsNotNone(deployed.airflow_version_id)
            gate=session.scalar(select(AdmissionState).where(AdmissionState.dag_id==dag))
            self.assertEqual(gate.gate_state,'OPEN');self.assertEqual(gate.deployment_id,identity)
        print('REAL_FIXED_FACTORY_WORKER_VERIFIED lost_ack='+str(lost_ack)+' initial_paused=true initial_runs=0 registry=DEPLOYED gate=OPEN',flush=True)

    def test_real_worker_publishes_fixed_factory_and_verifies_registration(self):self.deployment_case()
    def test_real_worker_reconciles_lost_publication_ack(self):self.deployment_case(lost_ack=True)
    def test_generated_dag_runs_after_public_trigger(self):self.deployment_case(trigger=True)
