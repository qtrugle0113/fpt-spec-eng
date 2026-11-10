"""Real API/TI → backend bind → metadata. Fixture task does not perform ETL."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import UUID,uuid4
from fastapi.testclient import TestClient
from tests.airflow.binding_fixture import configuration,DAG_ID,REVISION_ID,CONNECTION_REVISION_ID


class RealTaskBindingTests(unittest.TestCase):
    def test_running_sdk_task_binds_once_with_actual_version_and_no_credentials(self):
        from aat_api.airflow_client.client import AirflowClient
        from aat_api.airflow_client.deployment import DeploymentClient
        origin=os.environ['AAT_TEST_AIRFLOW_ORIGIN'];password=os.environ['AAT_TEST_AIRFLOW_PASSWORD']
        with AirflowClient(origin,username='aat_service',password=password) as http:
            airflow=DeploymentClient(http);deadline=time.monotonic()+120
            while True:
                try:details=airflow.details(DAG_ID);break
                except Exception:
                    if time.monotonic()>=deadline:raise AssertionError('Fixture DAG was not registered') from None
                    time.sleep(1)
            version=details['latest_dag_version'];self.seed(version)
            airflow.pause(DAG_ID,False)
            run_id='manual__aat_binding_'+uuid4().hex
            created=http.request('POST','/dags/'+DAG_ID+'/dagRuns',json={'dag_run_id':run_id,'logical_date':None,'conf':{}})
            self.assertEqual(created['dag_run_id'],run_id)
            deadline=time.monotonic()+90
            while True:
                task=airflow.task(DAG_ID,run_id,'execute_etl')
                if task['state']=='running':break
                if task['state'] in ('failed','success'):self.fail('Fixture SDK task ended before runtime identity test: '+task['state'])
                if time.monotonic()>=deadline:self.fail('Fixture SDK task did not start within the bounded deadline')
                time.sleep(.5)
            self.assertEqual(task['dag_version']['id'],version['id'])
            from aat_api.main import app
            with tempfile.TemporaryDirectory() as root:
                root=Path(root);(root/'runtime_token').write_text('c'*64);(root/'airflow_password').write_text(password)
                env=dict(AAT_RUNTIME_TOKEN_FILE=str(root/'runtime_token'),AAT_AIRFLOW_PASSWORD_FILE=str(root/'airflow_password'),AAT_AIRFLOW_ORIGIN=origin)
                with patch.dict(os.environ,env),TestClient(app,raise_server_exceptions=False) as client:
                    request=dict(dag_id=DAG_ID,run_id=run_id,task_id='execute_etl',expected_revision=REVISION_ID,dag_version_id=version['id'])
                    headers={'Authorization':'Bearer '+'c'*64}
                    response=client.post('/internal/runtime/bind',json=request,headers=headers)
                    self.assertEqual(response.status_code,200,'Real Airflow identity did not bind')
                    first=response.json();self.assertEqual(first['config_revision_id'],REVISION_ID)
                    self.assertEqual(first['target_revision_id'],CONNECTION_REVISION_ID)
                    self.assertIsNone(first['authorization_id']);self.assertNotIn(password,response.text)
                    self.assertNotIn('credentials',response.text);self.assertNotIn('password',response.text)
                    repeated=client.post('/internal/runtime/bind',json=request,headers=headers)
                    self.assertEqual(repeated.status_code,200);self.assertEqual(repeated.json(),first)
                    rejected=client.post('/internal/runtime/bind',json={**request,'dag_version_id':str(uuid4())},headers=headers)
                    self.assertEqual(rejected.status_code,409)
                from aat_api.services import runtime_binding
                self.assertIsNone(runtime_binding._client,'Shared HTTP client must close at application shutdown')

    def seed(self,version):
        from aat_api.services.connections.service import transaction,codec
        from aat_metadata.models.connections import Connection,ConnectionRevision,ConnectionSecret
        from aat_metadata.models.definitions import UploadedFile,DefinitionUpload
        from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
        from aat_metadata.models.operations import Operation,DAGDeployment,AdmissionState
        with transaction() as session:
            secret=ConnectionSecret.from_plaintext(codec(),'synthetic-target-not-executed');session.add(secret);session.flush()
            connection=Connection(code='binding_contract_target',name='Binding contract only',database_type='POSTGRESQL');session.add(connection);session.flush()
            revision=ConnectionRevision(id=UUID(CONNECTION_REVISION_ID),connection_id=connection.id,revision=1,database_type='POSTGRESQL',
                host='postgres',port=5432,database_name='app_metadata',schema_name='public',username='postgres',secret_id=secret.id,
                test_status='SUCCESS',physical_server_fingerprint='b'*64)
            session.add(revision);session.flush();connection.current_revision_id=revision.id
            file=UploadedFile(original_name='binding-fixture.xlsx',safe_storage_key=uuid4().hex,sha256='a'*64,bytes=0,extension='.xlsx')
            session.add(file);session.flush()
            upload=DefinitionUpload(kind='ETL',uploaded_file_id=file.id,workbook_sha256='a'*64,status='VALIDATED',template_version='1.0')
            session.add(upload);session.flush()
            definition=ETLDefinition(dag_id=DAG_ID);session.add(definition);session.flush()
            config=ETLDefinitionRevision(id=UUID(REVISION_ID),definition_id=definition.id,revision=1,upload_id=upload.id,config_json=configuration(),
                schema_fingerprint_source='a'*64,schema_fingerprint_target='a'*64,dependency_fingerprint='a'*64,status='VALIDATED')
            session.add(config);session.flush();definition.current_revision_id=config.id
            operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256='a'*64,state='SUCCEEDED');session.add(operation);session.flush()
            deployment=DAGDeployment(operation_id=operation.id,etl_revision_id=config.id,state='DEPLOYED',revision_sha256=config.config_sha256,
                expected_owner_tag='aat',generated_file_key='contract_fixture.py',file_sha256='a'*64,airflow_version_id=UUID(version['id']),airflow_version_number=version['version_number'])
            session.add(deployment);session.flush()
            session.add(AdmissionState(dag_id=DAG_ID,gate_state='OPEN',etl_revision_id=config.id,deployment_id=deployment.id))
