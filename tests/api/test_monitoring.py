"""T121: fail-closed monitoring contracts before the read service exists."""
from unittest.mock import patch
import unittest
from tests.api import test_dag_builder as builder


class MonitoringContractTests(unittest.TestCase):
    # Reuse setup only; inherited DAG Builder tests remain independently covered.
    setUp=builder.DAGBuilderContractTests.setUp
    def test_airflow_outage_is_not_an_empty_inventory(self):
        from aat_api.airflow_client.client import AirflowError
        with patch('aat_api.services.monitoring.airflow',side_effect=AirflowError(503,retryable=True)):
            response=self.client.get('/api/v1/dags')
        self.assertEqual(response.status_code,503)
        self.harness.assert_response('get','/dags','default',response.json(),headers=response.headers)
        self.assertNotIn('items',response.json())

    def test_invalid_monitoring_filters_and_paging_are_rejected(self):
        for query in ('limit=201','offset=-1','ownership=unknown','paused=unknown'):
            with self.subTest(query=query):
                response=self.client.get('/api/v1/dags?'+query)
                self.assertEqual(response.status_code,422)
                self.harness.assert_response('get','/dags','default',response.json(),headers=response.headers)

    def test_log_projection_redacts_actual_encrypted_credentials_and_caps_bytes(self):
        from types import SimpleNamespace
        from aat_api.services.connections.service import transaction,codec
        from aat_metadata.models.connections import ConnectionSecret
        secret='synthetic-sensitive-log-credential'
        with transaction() as session:session.add(ConnectionSecret.from_plaintext(codec(),secret))
        payload={'content':[{'event':'credential='+secret+' postgresql://operator:password@private/db Bearer secret-token'},'界'*(1024**2)],
                 'continuation_token':'next-page'}
        with patch('aat_api.services.monitoring.airflow',return_value=SimpleNamespace(logs=lambda *args,**kwargs:payload)):
            response=self.client.get('/api/v1/dags/safe/runs/manual/tasks/execute_etl/logs?attempt=1&map_index=-1')
        self.assertEqual(response.status_code,200)
        self.harness.assert_response('get','/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs',200,response.json(),headers=response.headers)
        result=response.json();self.assertTrue(result['truncated']);self.assertTrue(result['available'])
        self.assertEqual(result['continuation_token'],'next-page')
        content=''.join(result['content'])
        self.assertNotIn(secret,content);self.assertNotIn('secret-token',content)
        self.assertNotIn('postgresql://operator:password',content)
        self.assertLessEqual(len(content.encode()),1024**2)
        self.assertLessEqual(len(response.content),1024**2)
