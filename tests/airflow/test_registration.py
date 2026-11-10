"""T097: a file or stale DAG must never count as registered deployment."""
import importlib
import unittest
from uuid import uuid4


class RegistrationEvidenceTests(unittest.TestCase):
    def test_expected_revision_requires_owner_file_and_parse_version_evidence(self):
        module=importlib.import_module('aat_api.deployments.registration')
        version=str(uuid4())
        expected=dict(dag_id='safe_dag',owner_tag='aat',revision_sha256='a'*64,fileloc='/opt/airflow/dags/owned.py',published_at='2026-11-10T00:00:00Z')
        dag=dict(dag_id='safe_dag',tags=[{'name':'aat'},{'name':'aat_revision:'+'a'*64}],fileloc=expected['fileloc'])
        details=dict(last_parsed_time='2026-11-10T00:00:01Z',latest_dag_version={'id':version,'version_number':1})
        self.assertEqual(module.verify_candidate(expected,dag,details,[])['version_id'],version)
        for field,value in (('tags',[]),('fileloc','/opt/airflow/dags/external.py')):
            with self.subTest(field=field),self.assertRaises(ValueError):module.verify_candidate(expected,{**dag,field:value},details,[])
        with self.assertRaises(ValueError):module.verify_candidate(expected,dag,{**details,'last_parsed_time':'2026-11-09T00:00:00Z'},[])
        with self.assertRaises(ValueError):module.verify_candidate(expected,dag,{**details,'latest_dag_version':None},[])
        with self.assertRaises(ValueError):module.verify_candidate(expected,dag,details,[{'filename':expected['fileloc'],'timestamp':'2026-11-10T00:00:02Z'}])
        with self.assertRaises(ValueError):module.verify_candidate(expected,{**dag,'dag_id':'other_dag'},details,[])
        with self.assertRaises(ValueError):module.verify_candidate(expected,dag,{**details,'last_parsed_time':'invalid'},[])
        # Errors from another exact path must not poison this deployment.
        self.assertEqual(module.verify_candidate(expected,dag,details,[{'filename':'/opt/airflow/dags/other.py','timestamp':'2026-11-10T00:00:02Z'}])['version_id'],version)


class RegistrationPollingTests(unittest.TestCase):
    def fixture(self,*,ready_after=None,parse_error=False):
        from types import SimpleNamespace
        from aat_api.airflow_client.deployment import DeploymentClient
        now=[0.];delays=[];deadlines=[];version=str(uuid4())
        expected=dict(dag_id='safe_dag',owner_tag='aat',revision_sha256='a'*64,
            fileloc='/opt/airflow/dags/owned.py',published_at='2026-11-10T00:00:00Z')
        def request(method,path,*,params=None,deadline=None):
            deadlines.append(deadline)
            if path=='/importErrors':
                errors=[{'filename':expected['fileloc'],'timestamp':'2026-11-10T00:00:02Z'}] if parse_error else []
                return {'import_errors':errors,'total_entries':len(errors)}
            if path.endswith('/details'):
                return dict(last_parsed_time='2026-11-10T00:00:01Z',latest_dag_version={'id':version,'version_number':1})
            return dict(dag_id='safe_dag',fileloc=expected['fileloc'],tags=(
                [{'name':'aat'},{'name':'aat_revision:'+'a'*64}] if ready_after is not None and now[0]>=ready_after else []))
        def sleep(delay):delays.append(delay);now[0]+=delay
        return expected,DeploymentClient(SimpleNamespace(request=request)),now,delays,deadlines,sleep,version

    def test_bounded_backoff_and_one_deadline_across_all_http_pages(self):
        module=importlib.import_module('aat_api.deployments.registration')
        expected,client,now,delays,deadlines,sleep,_=self.fixture()
        with self.assertRaises(module.RegistrationTimeout):
            module.wait(expected,client,timeout=7,clock=lambda:now[0],sleep=sleep,jitter=lambda *_:0)
        self.assertEqual(delays,[1,2,4]);self.assertEqual(now[0],7)
        self.assertTrue(deadlines);self.assertEqual(set(deadlines),{7})

    def test_retry_observes_expected_revision_without_requiring_version_increment(self):
        module=importlib.import_module('aat_api.deployments.registration')
        expected,client,now,delays,_,sleep,version=self.fixture(ready_after=3)
        result=module.wait(expected,client,timeout=10,clock=lambda:now[0],sleep=sleep,jitter=lambda *_:0)
        self.assertEqual(result['version_id'],version);self.assertEqual(delays,[1,2])

    def test_current_exact_file_parse_error_is_terminal(self):
        module=importlib.import_module('aat_api.deployments.registration')
        expected,client,now,delays,_,sleep,_=self.fixture(parse_error=True)
        with self.assertRaisesRegex(ValueError,'REGISTRATION_PARSE_ERROR'):
            module.wait(expected,client,timeout=10,clock=lambda:now[0],sleep=sleep,jitter=lambda *_:0)
        self.assertFalse(delays)

    def test_new_tags_wait_for_the_matching_serialized_task_revision(self):
        from types import SimpleNamespace
        from aat_api.airflow_client.deployment import DeploymentClient
        module=importlib.import_module('aat_api.deployments.registration')
        expected,client,now,delays,_,sleep,version=self.fixture(ready_after=0)
        expected['revision_id']=str(uuid4())
        original=client.client.request
        def request(method,path,**kwargs):
            if path.endswith('/tasks/execute_etl'):
                return {'params':{'aat_revision_id':{'value':expected['revision_id'] if now[0]>=3 else 'old'},
                                  'aat_revision_sha256':{'value':expected['revision_sha256']}}}
            return original(method,path,**kwargs)
        result=module.wait(expected,DeploymentClient(SimpleNamespace(request=request)),timeout=10,
            clock=lambda:now[0],sleep=sleep,jitter=lambda *_:0)
        self.assertEqual(result['version_id'],version);self.assertEqual(delays,[1,2])
