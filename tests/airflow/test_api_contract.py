"""T097: capture/verify the real pinned Airflow API, never metadata SQL."""
import hashlib
import json
import os
from pathlib import Path
import unittest
import httpx


class AirflowAPIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=httpx.Client(base_url='http://127.0.0.1:8080',timeout=httpx.Timeout(10,connect=3),trust_env=False)
        cls.addClassCleanup(cls.http.close)
        response=cls.http.post('/auth/token',json={'username':'aat_service','password':os.environ['AAT_FIXTURE_AUTH_PASSWORD']})
        if response.status_code!=201 and response.status_code!=200:raise AssertionError('Fixture token exchange failed: '+str(response.status_code))
        cls.http.headers['Authorization']='Bearer '+response.json()['access_token']
        response=cls.http.get('/openapi.json')
        if response.status_code!=200:raise AssertionError('Airflow schema unavailable: '+str(response.status_code))
        cls.schema=response.json()
        encoded=json.dumps(cls.schema,sort_keys=True,separators=(',',':')).encode()
        Path('/tmp/aat-airflow-openapi.json').write_bytes(encoded)
        import airflow
        Path('/tmp/aat-airflow-openapi-sha256.json').write_text(json.dumps({'airflow_version':airflow.__version__,'api_version':cls.schema['info']['version'],'sha256':hashlib.sha256(encoded).hexdigest()}))

    def test_pinned_schema_uses_version_objects_and_required_nullable_logical_date(self):
        import airflow
        self.assertEqual(airflow.__version__,'3.3.2');self.assertEqual(self.schema['info']['version'],'2')
        schemas=self.schema['components']['schemas']
        self.assertIn('dag_versions',schemas['DAGRunResponse']['properties'])
        self.assertNotIn('dag_version_id',schemas['DAGRunResponse']['properties'])
        self.assertIn('dag_version',schemas['TaskInstanceResponse']['properties'])
        self.assertIn('logical_date',schemas['TriggerDAGRunPostBody']['required'])

    def test_real_health_and_paginated_inventory_are_authenticated_json(self):
        response=self.http.get('/api/v2/monitor/health');self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['metadatabase']['status'],'healthy')
        response=self.http.get('/api/v2/dags',params={'limit':1,'offset':0});self.assertEqual(response.status_code,200)
        self.assertIsInstance(response.json()['dags'],list);self.assertIsInstance(response.json()['total_entries'],int)

    def test_client_distinguishes_missing_resource_without_exposing_auth(self):
        from aat_api.airflow_client.client import AirflowClient,AirflowError
        with AirflowClient('http://127.0.0.1:8080',username='aat_service',password=os.environ['AAT_FIXTURE_AUTH_PASSWORD']) as client:
            with self.assertRaises(AirflowError) as failure:client.request('GET','/dags/missing_contract_fixture')
        self.assertEqual(failure.exception.status,404)
        self.assertNotIn(os.environ['AAT_FIXTURE_AUTH_PASSWORD'],str(failure.exception))

    def test_deployment_client_reads_real_health_inventory_and_import_errors(self):
        from aat_api.airflow_client.client import AirflowClient
        from aat_api.airflow_client.deployment import DeploymentClient
        with AirflowClient('http://127.0.0.1:8080',username='aat_service',password=os.environ['AAT_FIXTURE_AUTH_PASSWORD']) as client:
            deployment=DeploymentClient(client)
            self.assertEqual(deployment.health()['scheduler']['status'],'healthy')
            self.assertIsInstance(deployment.dags(),list)
            self.assertIsInstance(deployment.import_errors(),list)

    def test_real_version_and_pause_readback_and_inventory_beyond_first_page(self):
        if os.environ.get('AAT_FIXTURE_DAG_COUNT')!='205':self.skipTest('Dedicated parsed-DAG fixture not enabled')
        from aat_api.airflow_client.client import AirflowClient
        from aat_api.airflow_client.deployment import DeploymentClient
        with AirflowClient('http://127.0.0.1:8080',username='aat_service',password=os.environ['AAT_FIXTURE_AUTH_PASSWORD']) as client:
            deployment=DeploymentClient(client)
            managed=[dag for dag in deployment.dags() if dag['dag_id'].startswith('aat_contract_')]
            self.assertEqual(len(managed),205)
            details=deployment.details('aat_contract_000');latest=details['latest_dag_version']
            self.assertEqual(deployment.version('aat_contract_000',latest['version_number'])['id'],latest['id'])
            self.assertTrue(deployment.versions('aat_contract_000'))
            self.assertEqual(deployment.runs('aat_contract_000'),[])
            self.assertTrue(deployment.pause('aat_contract_000',True)['is_paused'])
