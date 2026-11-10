"""T107: real registry gates with isolated Airflow transport facts."""
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import UUID,uuid4
from sqlalchemy import select
from tests.api import test_dag_builder as preview


class DeploymentAdmissionTests(unittest.TestCase):
    setUp=preview.ETLPreviewIntegrationTests.setUp
    target=preview.ETLPreviewIntegrationTests.target
    wait=preview.ETLPreviewIntegrationTests.wait
    response=preview.ETLPreviewIntegrationTests.response
    scenario=preview.ETLPreviewIntegrationTests.scenario

    def candidate(self):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinitionRevision
        from aat_metadata.models.operations import Operation,DAGDeployment
        uploaded,result,dag,_,_=self.scenario()
        self.assertEqual(result['state'],'SUCCEEDED')
        with transaction() as session:
            revision=session.scalar(select(ETLDefinitionRevision).where(ETLDefinitionRevision.upload_id==UUID(uploaded['id'])))
            operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256=revision.config_sha256)
            session.add(operation);session.flush()
            deployment=DAGDeployment(operation_id=operation.id,etl_revision_id=revision.id,
                state='READY_TO_DEPLOY',revision_sha256=revision.config_sha256)
            session.add(deployment);session.flush()
            return SimpleNamespace(id=deployment.id,dag=dag,revision=revision.id)

    def gate(self,dag):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import AdmissionState
        with transaction() as session:return session.scalar(select(AdmissionState).where(AdmissionState.dag_id==dag))

    def test_new_dag_blocks_bind_gate_before_airflow_lookup(self):
        from aat_api.airflow_client.client import AirflowError
        candidate=self.candidate();airflow=Mock()
        def absent(dag):
            self.assertEqual(self.gate(dag).gate_state,'BLOCKED')
            raise AirflowError(404)
        airflow.dag.side_effect=absent
        module=importlib.import_module('aat_api.deployments.admission')
        result=module.prepare(candidate.id,airflow)
        self.assertTrue(result.is_new);airflow.pause.assert_not_called()
        self.assertEqual(self.gate(candidate.dag).deployment_id,candidate.id)

    def test_external_even_with_forged_aat_tag_is_not_claimed(self):
        candidate=self.candidate();airflow=Mock()
        airflow.dag.return_value={'dag_id':candidate.dag,'tags':[{'name':'aat'}],
                                  'fileloc':'/opt/airflow/dags/external.py','is_paused':False}
        module=importlib.import_module('aat_api.deployments.admission')
        with self.assertRaises(ValueError):module.prepare(candidate.id,airflow)
        airflow.pause.assert_not_called()
        self.assertEqual(self.gate(candidate.dag).gate_state,'BLOCKED')

    def test_failed_airflow_lookup_keeps_gate_blocked(self):
        from aat_api.airflow_client.client import AirflowError
        candidate=self.candidate();airflow=Mock();airflow.dag.side_effect=AirflowError(503)
        module=importlib.import_module('aat_api.deployments.admission')
        with self.assertRaises(AirflowError):module.prepare(candidate.id,airflow)
        self.assertEqual(self.gate(candidate.dag).gate_state,'BLOCKED')

    def owned(self,candidate):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.operations import Operation,DAGDeployment
        version=uuid4();key=str(uuid4())+'.py'
        with transaction() as session:
            current=session.get(DAGDeployment,candidate.id)
            operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256=current.revision_sha256,state='SUCCEEDED')
            session.add(operation);session.flush()
            previous=DAGDeployment(operation_id=operation.id,etl_revision_id=candidate.revision,
                state='DEPLOYED',revision_sha256=current.revision_sha256,generated_file_key=key,
                file_sha256='b'*64,airflow_version_id=version,airflow_version_number=1)
            session.add(previous);session.flush();current.previous_deployment_id=previous.id
            sha=current.revision_sha256
        airflow=Mock()
        dag={'dag_id':candidate.dag,'tags':[{'name':'aat'},{'name':'aat_revision:'+sha}],
             'fileloc':'/opt/airflow/dags/'+key,'is_paused':False}
        airflow.dag.side_effect=lambda _:dict(dag)
        airflow.details.return_value={'latest_dag_version':{'id':str(version),'version_number':1}}
        airflow.pause.side_effect=lambda _,paused:dag.update(is_paused=paused)
        airflow.runs.return_value=[]
        return airflow

    def test_redeploy_pauses_drains_and_preserves_previous_active_state(self):
        candidate=self.candidate();airflow=self.owned(candidate)
        module=importlib.import_module('aat_api.deployments.admission')
        result=module.prepare(candidate.id,airflow)
        self.assertFalse(result.is_new);self.assertFalse(result.previous_paused)
        airflow.pause.assert_called_once_with(candidate.dag,True)
        self.assertEqual(self.gate(candidate.dag).gate_state,'BLOCKED')
        # A run arriving after the first check must block publication too.
        airflow.runs.return_value=[{'state':'queued'}]
        with self.assertRaises(ValueError):module.assert_ready(result,airflow)

    def test_running_or_unknown_runs_keep_redeploy_paused_and_blocked(self):
        candidate=self.candidate();airflow=self.owned(candidate)
        airflow.runs.return_value=[{'state':'running'}]
        module=importlib.import_module('aat_api.deployments.admission')
        with self.assertRaises(ValueError):module.prepare(candidate.id,airflow)
        airflow.pause.assert_called_once_with(candidate.dag,True)
        self.assertEqual(self.gate(candidate.dag).gate_state,'BLOCKED')

    def test_revision_changed_during_lookup_blocks_publication(self):
        from aat_api.airflow_client.client import AirflowError
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinitionRevision
        candidate=self.candidate();airflow=Mock()
        def changed(_):
            with transaction() as session:
                session.get(ETLDefinitionRevision,candidate.revision).status='INVALIDATED'
            raise AirflowError(404)
        airflow.dag.side_effect=changed
        module=importlib.import_module('aat_api.deployments.admission')
        with self.assertRaises(ValueError):module.prepare(candidate.id,airflow)
        self.assertEqual(self.gate(candidate.dag).gate_state,'BLOCKED')

    def test_new_revision_redeploy_keeps_old_current_until_registration(self):
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
        from aat_metadata.models.operations import DAGDeployment
        candidate=self.candidate();airflow=self.owned(candidate)
        with transaction() as session:
            old=session.get(ETLDefinitionRevision,candidate.revision)
            config={**old.config_json,'batch_size':999}
            new=ETLDefinitionRevision(definition_id=old.definition_id,revision=old.revision+1,
                upload_id=old.upload_id,config_json=config,status='VALIDATED')
            session.add(new);session.flush();new_id=new.id
            pending=session.get(DAGDeployment,candidate.id)
            pending.etl_revision_id=new.id;pending.revision_sha256=new.config_sha256
        module=importlib.import_module('aat_api.deployments.admission')
        result=module.prepare(candidate.id,airflow)
        self.assertEqual(result.revision_id,new_id)
        with transaction() as session:
            old=session.get(ETLDefinitionRevision,candidate.revision)
            self.assertEqual(session.get(ETLDefinition,old.definition_id).current_revision_id,candidate.revision)
