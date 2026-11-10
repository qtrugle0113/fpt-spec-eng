"""T109: durable identities and publication/reconciliation on real metadata/disk."""
import importlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from uuid import UUID,uuid4
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from tests.api import test_dag_builder as preview


class DeploymentWorkerTests(unittest.TestCase):
    setUp=preview.ETLPreviewIntegrationTests.setUp
    target=preview.ETLPreviewIntegrationTests.target
    wait=preview.ETLPreviewIntegrationTests.wait
    response=preview.ETLPreviewIntegrationTests.response
    scenario=preview.ETLPreviewIntegrationTests.scenario

    def work(self,count=1):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinitionRevision
        from aat_metadata.models.operations import Operation,DAGDeployment
        results=[self.scenario() for _ in range(count)]
        self.worker.kill();self.worker.wait(timeout=10)
        with transaction() as session:
            operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256='a'*64,
                state='RUNNING',lease_owner='fixture-worker',lease_until=datetime.now(timezone.utc)+timedelta(seconds=120),
                progress_json={'support_objects_acknowledged':True})
            session.add(operation);session.flush();ids=[]
            for uploaded,result,_,_,_ in results:
                self.assertEqual(result['state'],'SUCCEEDED')
                revision=session.scalar(select(ETLDefinitionRevision).where(ETLDefinitionRevision.upload_id==UUID(uploaded['id'])))
                deployment=DAGDeployment(operation_id=operation.id,etl_revision_id=revision.id,state='READY_TO_DEPLOY',revision_sha256=revision.config_sha256)
                session.add(deployment);session.flush();ids.append(deployment.id)
            return {'id':operation.id,'progress_json':operation.progress_json},ids

    def test_multiple_dags_share_operation_but_keep_individual_deployment_identity(self):
        _,identities=self.work(2)
        self.assertEqual(len(set(identities)),2)

    def test_write_uncertainty_is_not_replayed_and_gate_remains_blocked(self):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import DAGDeployment,AdmissionState
        operation,identities=self.work();module=importlib.import_module('aat_api.workers.deployments')
        from aat_api.airflow_client.client import AirflowError
        from aat_api.airflow_client.deployment import DeploymentClient
        def absent(*args,**kwargs):raise AirflowError(404)
        airflow=DeploymentClient(SimpleNamespace(request=absent))
        with tempfile.TemporaryDirectory() as root,patch.dict('os.environ',{'AAT_DAGS_ROOT':root}),\
                patch.object(module,'airflow',return_value=airflow),\
                patch.object(module.storage,'write',side_effect=OSError('injected disk acknowledgement loss')) as writer:
            state,_=module.execute(operation,'fixture-worker')
            self.assertEqual(state,'NEEDS_RECONCILIATION');self.assertEqual(writer.call_count,1)
            # The same dispatched row is evidence to reconcile, never permission to publish again.
            state,_=module.execute(operation,'fixture-worker')
            self.assertEqual(state,'NEEDS_RECONCILIATION');self.assertEqual(writer.call_count,1)
        with transaction() as session:
            deployment=session.get(DAGDeployment,identities[0])
            self.assertTrue(deployment.reconcile_required)
            self.assertEqual(deployment.state,'DEPLOYMENT_PENDING')
            gate=session.scalar(select(AdmissionState).where(AdmissionState.dag_id==deployment.dag_id))
            self.assertEqual(gate.gate_state,'BLOCKED')

    def test_response_loss_reconciles_same_file_without_republication(self):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import DAGDeployment,Operation
        from aat_api.airflow_client.client import AirflowError
        from aat_api.airflow_client.deployment import DeploymentClient
        operation,identities=self.work();module=importlib.import_module('aat_api.workers.deployments')
        def absent(*args,**kwargs):raise AirflowError(404)
        client=DeploymentClient(SimpleNamespace(request=absent))
        actual_write=module.storage.write
        def response_lost(*args,**kwargs):
            actual_write(*args,**kwargs)
            raise OSError('injected response loss after durable rename')
        with tempfile.TemporaryDirectory() as root,patch.dict('os.environ',{'AAT_DAGS_ROOT':root}),\
                patch.object(module,'airflow',return_value=client),\
                patch.object(module.storage,'write',side_effect=response_lost):
            self.assertEqual(module.execute(operation,'fixture-worker')[0],'NEEDS_RECONCILIATION')
            with transaction() as session:
                original=session.get(Operation,operation['id']);original.state='NEEDS_RECONCILIATION'
                recovery=Operation(kind='DAG_RECONCILE',idempotency_key=str(uuid4()),request_sha256='b'*64,
                    state='RUNNING',lease_owner='fixture-worker',lease_until=datetime.now(timezone.utc)+timedelta(seconds=120),
                    progress_json={'deployment_id':str(identities[0])})
                session.add(recovery);session.flush();recover={'id':recovery.id,'progress_json':recovery.progress_json}
            evidence={'version_id':str(uuid4()),'version_number':1,'parsed_at':datetime.now(timezone.utc).isoformat()}
            with patch.object(module.registration,'wait',return_value=evidence),\
                    patch.object(module.storage,'write',side_effect=AssertionError('reconcile must not write')):
                self.assertEqual(module.reconcile(recover,'fixture-worker'),('SUCCEEDED',None))
            self.assertEqual(len(list(Path(root).glob('*.py'))),1)
        with transaction() as session:
            self.assertEqual(session.get(DAGDeployment,identities[0]).state,'DEPLOYED')
            self.assertEqual(session.get(Operation,operation['id']).state,'SUCCEEDED')

    def test_expired_worker_cannot_dispatch_file_after_closing_gate(self):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation
        from aat_api.airflow_client.client import AirflowError
        from aat_api.airflow_client.deployment import DeploymentClient
        from aat_api.errors import APIError
        operation,_=self.work();module=importlib.import_module('aat_api.workers.deployments')
        def absent(*args,**kwargs):raise AirflowError(404)
        client=DeploymentClient(SimpleNamespace(request=absent))
        original_ready=module.admission.assert_ready
        def expire(*args,**kwargs):
            original_ready(*args,**kwargs)
            with transaction() as session:
                session.get(Operation,operation['id']).lease_until=datetime.now(timezone.utc)-timedelta(seconds=1)
        with patch.object(module,'airflow',return_value=client),\
                patch.object(module.admission,'assert_ready',side_effect=expire),\
                patch.object(module.storage,'write') as writer:
            with self.assertRaises(APIError):module.execute(operation,'fixture-worker')
            writer.assert_not_called()

    def test_public_multi_dag_request_is_atomic_and_replays_same_results(self):
        from aat_api.services.table_preview import target_engine
        from aat_api.services.etl_preview import preview
        from sqlalchemy import text
        def edit(book,connection,source,target,revision):
            second='deploy_second_'+uuid4().hex
            with target_engine(revision) as engine,engine.begin() as cursor:
                cursor.execute(text(f'CREATE TABLE {second} (id INTEGER PRIMARY KEY,note VARCHAR(40))'))
            values=[cell.value for cell in book['ETL_Definitions'][2]]
            values[0]='deploy_second_'+uuid4().hex;values[9]=second
            book['ETL_Definitions'].append(values)
        uploaded,result,_,_,_=self.scenario(edit=edit)
        self.assertEqual(result['state'],'SUCCEEDED')
        self.worker.kill();self.worker.wait(timeout=10)
        current=preview(UUID(uploaded['id']))
        body={'upload_id':uploaded['id'],'dag_ids':[row['config']['dag_id'] for row in current['items']],
              'confirmation_token':current['confirmation_token'],'support_objects_acknowledged':True}
        headers={'Idempotency-Key':str(uuid4())}
        response=self.client.post('/api/v1/dag-deployments',json=body,headers=headers)
        operation=self.response(response,'post','/dag-deployments',202)
        self.assertEqual(len(operation['result_links']),2);self.assertEqual(operation['progress']['total'],2)
        replay=self.client.post('/api/v1/dag-deployments',json=body,headers=headers)
        self.assertEqual(replay.json()['id'],operation['id'])
        for link in operation['result_links']:
            detail=self.response(self.client.get(link),'get','/dag-deployments/{id}',200)
            self.assertEqual(detail['state'],'READY_TO_DEPLOY');self.assertFalse(detail['reconcile_required'])
        changed={**body,'dag_ids':body['dag_ids'][:1]}
        self.assertEqual(self.client.post('/api/v1/dag-deployments',json=changed,headers=headers).status_code,409)

    def test_interruption_before_publication_reconciles_without_any_file_write(self):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation,DAGDeployment
        from aat_api.workers import deployments as worker
        operation,identities=self.work()
        with transaction() as session:session.get(Operation,operation['id']).state='NEEDS_RECONCILIATION'
        path='/api/v1/dag-deployments/'+str(identities[0])+'/reconcile';headers={'Idempotency-Key':str(uuid4())}
        command=self.response(self.client.post(path,headers=headers),'post','/dag-deployments/{id}/reconcile',202)
        self.assertEqual(self.client.post(path,headers=headers).json()['id'],command['id'])
        self.assertEqual(self.client.post(path,headers={'Idempotency-Key':str(uuid4())}).status_code,409)
        with transaction() as session:
            recovery=session.get(Operation,UUID(command['id']));recovery.state='RUNNING'
            recovery.lease_owner='fixture-worker';recovery.lease_until=datetime.now(timezone.utc)+timedelta(seconds=120)
            recover={'id':recovery.id,'progress_json':recovery.progress_json}
        with patch.object(worker,'airflow',side_effect=AssertionError('No file was dispatched')),\
                patch.object(worker.storage,'write',side_effect=AssertionError('Reconcile must not publish')):
            self.assertEqual(worker.reconcile(recover,'fixture-worker'),('SUCCEEDED',None))
        with transaction() as session:
            self.assertEqual(session.get(DAGDeployment,identities[0]).state,'DEPLOYMENT_FAILED')
            self.assertEqual(session.get(Operation,operation['id']).state,'FAILED')
