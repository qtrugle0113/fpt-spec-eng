"""Actual scheduler/SDK -> private HTTP bind -> encrypted revisions -> target data."""
import json
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
        path=Path('/tmp/aat-contract-dags')/(uuid4().hex+'.py');path.write_text(source)
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
