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
