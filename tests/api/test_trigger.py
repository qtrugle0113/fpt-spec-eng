"""T112: persist one intent and exclusive ONCE reservation before Airflow POST."""
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import select,func
from tests.api import test_authorizations as grants


class TriggerTests(unittest.TestCase):
    setUp=grants.AuthorizationCreateTests.setUp
    target=grants.AuthorizationCreateTests.target
    wait=grants.AuthorizationCreateTests.wait
    response=grants.AuthorizationCreateTests.response
    scenario=grants.AuthorizationCreateTests.scenario
    request=grants.AuthorizationCreateTests.request

    def ready(self,scheduled=False):
        from aat_api.services.connections.service import transaction
        from aat_api.services import replacement_authorizations as service
        from aat_metadata.models.operations import Operation,DAGDeployment,AdmissionState
        from aat_metadata.models.etl import ETLDefinitionRevision
        identity,value=self.request(scheduled=scheduled,scope='SCHEDULED' if scheduled else 'ONCE')
        self.worker.kill();self.worker.wait(timeout=10)
        authority=service.grant(identity,value,uuid4())
        with transaction() as session:
            revision=session.get(ETLDefinitionRevision,value.revision_id)
            operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256=revision.config_sha256,state='SUCCEEDED')
            session.add(operation);session.flush()
            deployed=DAGDeployment(operation_id=operation.id,etl_revision_id=revision.id,state='DEPLOYED',revision_sha256=revision.config_sha256,
                generated_file_key=str(uuid4())+'.py',file_sha256='a'*64,airflow_version_id=uuid4(),airflow_version_number=1)
            session.add(deployed);session.flush()
            session.add(AdmissionState(dag_id=revision.config_json['dag_id'],gate_state='OPEN',etl_revision_id=revision.id,deployment_id=deployed.id))
            dag=revision.config_json['dag_id']
        return dag,value,authority

    def test_once_is_reserved_and_identity_is_stable_before_dispatch(self):
        from aat_api.services import dag_control as service
        from aat_api.schemas.dag_control import TriggerRequest
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.replacement_runs import RunIntent
        from aat_metadata.models.authorizations import DataReplacementAuthorization
        dag,value,authority=self.ready();key=uuid4()
        body=TriggerRequest(expected_revision=value.revision_id,confirmation_token=value.confirmation_token,authorization_id=authority['id'])
        operation=service.trigger(dag,body,key)
        with patch.object(service,'preview',side_effect=AssertionError('Replay must retain intent')):
            self.assertEqual(service.trigger(dag,body,key),operation)
        with transaction() as session:
            intent=session.scalar(select(RunIntent).where(RunIntent.operation_id==operation))
            self.assertEqual(intent.airflow_run_id,'manual__aat_'+str(operation))
            self.assertEqual(intent.state,'RESERVED')
            stored=session.get(DataReplacementAuthorization,authority['id'])
            self.assertEqual(stored.state,'RESERVED');self.assertEqual(stored.reserved_intent_id,intent.id)

    def test_two_requests_cannot_transfer_one_once(self):
        from aat_api.services import dag_control as service
        from aat_api.schemas.dag_control import TriggerRequest
        from aat_api.errors import APIError
        dag,value,authority=self.ready()
        body=TriggerRequest(expected_revision=value.revision_id,confirmation_token=value.confirmation_token,authorization_id=authority['id'])
        def request(_):
            try:service.trigger(dag,body,uuid4());return 'accepted'
            except APIError:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(request,range(2))),['accepted','rejected'])

    def test_scheduled_is_not_manual_authority(self):
        from aat_api.services import dag_control as service
        from aat_api.schemas.dag_control import TriggerRequest
        from aat_api.errors import APIError
        dag,value,authority=self.ready(scheduled=True)
        body=TriggerRequest(expected_revision=value.revision_id,confirmation_token=value.confirmation_token,authorization_id=authority['id'])
        with self.assertRaises(APIError):service.trigger(dag,body,uuid4())

    def claimed(self):
        from datetime import datetime,timedelta,timezone
        from aat_api.services import dag_control as service
        from aat_api.schemas.dag_control import TriggerRequest
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation
        dag,value,authority=self.ready()
        body=TriggerRequest(expected_revision=value.revision_id,confirmation_token=value.confirmation_token,authorization_id=authority['id'])
        identity=service.trigger(dag,body,uuid4())
        with transaction() as session:
            operation=session.get(Operation,identity);operation.state='RUNNING'
            operation.lease_owner='trigger-fixture';operation.lease_until=datetime.now(timezone.utc)+timedelta(seconds=120)
            return {'id':identity,'progress_json':operation.progress_json},authority,dag

    def live_fact(self,dag,details=False):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import DAGDeployment
        with transaction() as session:
            deployed=session.scalar(select(DAGDeployment).where(DAGDeployment.dag_id==dag,DAGDeployment.state=='DEPLOYED'))
            if details:return {'latest_dag_version':{'id':str(deployed.airflow_version_id),'version_number':1}}
            return {'dag_id':dag,'fileloc':'/opt/airflow/dags/'+deployed.generated_file_key,
                'tags':[{'name':'aat'},{'name':'aat_revision:'+deployed.revision_sha256}]}

    def test_lost_post_response_is_read_back_without_another_post(self):
        from types import SimpleNamespace
        from aat_api.workers import dag_control as worker
        from aat_api.airflow_client.client import AirflowError
        from aat_api.airflow_client.deployment import DeploymentClient
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.replacement_runs import RunIntent
        operation,authority,dag=self.claimed();posts=[]
        def request(method,path,*,json=None,params=None):
            if method=='GET' and path.endswith('/details'):return self.live_fact(dag,True)
            if method=='GET' and path=='/dags/'+dag:return self.live_fact(dag)
            if method=='POST':
                with transaction() as session:
                    intent=session.scalar(select(RunIntent).where(RunIntent.operation_id==operation['id']))
                    self.assertEqual(intent.state,'SUBMITTING')
                    self.assertEqual(intent.authorization_id,authority['id'])
                posts.append(json['dag_run_id']);raise AirflowError(503)
            return {'dag_id':dag,'dag_run_id':posts[0],'run_type':'manual','dag_versions':[],'state':'queued'}
        client=DeploymentClient(SimpleNamespace(request=request))
        with patch.object(worker,'airflow',return_value=client):
            self.assertEqual(worker.execute(operation,'trigger-fixture'),('SUCCEEDED',None))
            self.assertEqual(worker.execute(operation,'trigger-fixture'),('SUCCEEDED',None))
        self.assertEqual(posts,['manual__aat_'+str(operation['id'])])

    def test_revoke_before_dispatch_closes_once_without_airflow_submission(self):
        from aat_api.workers import dag_control as worker
        from aat_api.services import replacement_authorizations as service
        operation,authority,_=self.claimed()
        current=service.detail(authority['id']);service.revoke(authority['id'],current['revision'],uuid4())
        with patch.object(worker,'airflow',side_effect=AssertionError('Revoked trigger must not contact Airflow')):
            self.assertEqual(worker.execute(operation,'trigger-fixture')[0],'FAILED')
        self.assertEqual(service.detail(authority['id'])['state'],'CLOSED')

    def test_uncertain_trigger_is_observed_by_maintenance_without_reposting(self):
        from types import SimpleNamespace
        from aat_api.workers import dag_control as worker
        from aat_api.airflow_client.client import AirflowError
        from aat_api.airflow_client.deployment import DeploymentClient
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation
        from aat_metadata.models.replacement_runs import RunIntent
        operation,_,dag=self.claimed();posts=[];available=[False]
        run_id='manual__aat_'+str(operation['id'])
        def request(method,path,*,json=None,params=None,deadline=None):
            if method=='GET' and path.endswith('/details'):return self.live_fact(dag,True)
            if method=='GET' and path=='/dags/'+dag:return self.live_fact(dag)
            if method=='POST':posts.append(json['dag_run_id']);raise AirflowError(503)
            if not available[0]:raise AirflowError(503)
            return {'dag_id':dag,'dag_run_id':run_id,'run_type':'manual','dag_versions':[],'state':'queued'}
        client=DeploymentClient(SimpleNamespace(request=request))
        with patch.object(worker,'airflow',return_value=client):
            self.assertEqual(worker.execute(operation,'trigger-fixture')[0],'NEEDS_RECONCILIATION')
            with transaction() as session:session.get(Operation,operation['id']).state='NEEDS_RECONCILIATION'
            available[0]=True;worker.reconcile_pending()
        with transaction() as session:
            self.assertEqual(session.get(Operation,operation['id']).state,'SUCCEEDED')
            intent=session.scalar(select(RunIntent).where(RunIntent.operation_id==operation['id']))
            self.assertEqual(intent.state,'CREATED');self.assertEqual(intent.airflow_run_id,run_id)
        self.assertEqual(posts,[run_id])

    def test_activation_requires_scheduled_scope_and_is_revision_guarded(self):
        from aat_api.services import dag_activation as service,replacement_authorizations as grants
        from aat_api.schemas.dag_control import DagStateRequest
        from aat_api.errors import APIError
        dag,value,scheduled=self.ready(scheduled=True)
        once=grants.grant(self._definition(value.revision_id),value.model_copy(update={'scope':'ONCE'}),uuid4())
        body=DagStateRequest(expected_revision=value.revision_id,confirmation_token=value.confirmation_token,
            authorization_id=once['id'],is_paused=False)
        with self.assertRaises(APIError):service.request(dag,body,1,uuid4())
        body=body.model_copy(update={'authorization_id':scheduled['id']});key=uuid4()
        operation=service.request(dag,body,1,key)
        self.assertEqual(service.request(dag,body,1,key),operation)
        with self.assertRaises(APIError) as stale:service.request(dag,body,1,uuid4())
        self.assertEqual(stale.exception.status,412)
        self.assertEqual(grants.detail(scheduled['id'])['state'],'GRANTED')

    def _definition(self,revision_id):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinitionRevision
        with transaction() as session:return session.get(ETLDefinitionRevision,revision_id).definition_id

    def test_activation_response_loss_readback_and_pause_do_not_revoke_authority(self):
        from types import SimpleNamespace
        from datetime import datetime,timedelta,timezone
        from aat_api.services import dag_activation as service,replacement_authorizations as grants
        from aat_api.workers import dag_activation as worker
        from aat_api.schemas.dag_control import DagStateRequest
        from aat_api.airflow_client.client import AirflowError
        from aat_api.airflow_client.deployment import DeploymentClient
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation
        dag,value,authority=self.ready(scheduled=True);paused=[True];patches=[]
        def request(method,path,*,json=None,params=None,deadline=None):
            if method=='PATCH':
                paused[0]=json['is_paused'];patches.append(paused[0]);raise AirflowError(503)
            if path.endswith('/details'):return self.live_fact(dag,True)
            return {**self.live_fact(dag),'is_paused':paused[0]}
        client=DeploymentClient(SimpleNamespace(request=request))
        for generation,desired in ((1,False),(2,True)):
            body=DagStateRequest(expected_revision=value.revision_id,confirmation_token=value.confirmation_token,
                authorization_id=authority['id'],is_paused=desired)
            identity=service.request(dag,body,generation,uuid4())
            with transaction() as session:
                operation=session.get(Operation,identity);operation.state='RUNNING';operation.lease_owner='state-fixture'
                operation.lease_until=datetime.now(timezone.utc)+timedelta(seconds=120)
                work={'id':identity,'progress_json':operation.progress_json}
            with patch.object(worker,'airflow',return_value=client):self.assertEqual(worker.execute(work,'state-fixture'),('SUCCEEDED',None))
            with transaction() as session:session.get(Operation,identity).state='SUCCEEDED'
        self.assertEqual(patches,[False,True]);self.assertTrue(paused[0])
        self.assertEqual(grants.detail(authority['id'])['state'],'GRANTED')
