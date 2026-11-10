"""T128: unavailable is explicit, and invalid date/timezone scopes fail safely."""
import unittest
from unittest.mock import patch
from tests.api import test_dag_builder as builder


class DashboardContractTests(unittest.TestCase):
    setUp=builder.DAGBuilderContractTests.setUp

    def test_invalid_timezone_date_range_and_scope_are_rejected(self):
        for query in ('timezone=Invalid/Timezone','from=2026-11-10&to=2026-11-01','scope=unknown'):
            with self.subTest(query=query):
                result=self.client.get('/api/v1/dashboard?'+query)
                self.assertEqual(result.status_code,422)
                self.harness.assert_response('get','/dashboard','default',result.json(),headers=result.headers)

    def test_airflow_outage_returns_unavailable_values_not_zero(self):
        from aat_api.airflow_client.client import AirflowError
        from aat_api.services import dashboard
        dashboard.clear_cache()
        with patch.object(dashboard,'airflow',side_effect=AirflowError(503,retryable=True)):
            response=self.client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code,200)
        self.harness.assert_response('get','/dashboard',200,response.json(),headers=response.headers)
        data=response.json();self.assertEqual(data['completeness'],'UNAVAILABLE')
        self.assertIsNone(data['inventory']['total']);self.assertIsNone(data['run_metrics']['total'])
        self.assertIsNone(data['last_successful_run']);self.assertEqual(data['last_successful_run_availability'],'UNAVAILABLE')

    def test_missing_history_page_is_incomplete_and_never_a_partial_total(self):
        from aat_api.services import dashboard
        from types import SimpleNamespace
        from unittest.mock import Mock
        dashboard.clear_cache()
        transport=Mock()
        transport.request.side_effect=[{'total_entries':2,'dag_runs':[{
            'dag_id':'external','dag_run_id':'first','state':'success','run_type':'manual',
            'start_date':'2026-11-11T00:00:00Z','end_date':'2026-11-11T00:01:00Z'}]},
            {'total_entries':2,'dag_runs':[]}]
        fixture=SimpleNamespace(dags=lambda:[],client=transport)
        with patch.object(dashboard,'airflow',return_value=fixture):
            result=self.client.get('/api/v1/dashboard?from=2026-11-11&to=2026-11-11').json()
        self.assertEqual(result['completeness'],'INCOMPLETE')
        self.assertIsNone(result['run_metrics']['total'])
        self.assertIsNone(result['lifetime_metrics']['total'])
        self.assertFalse(result['stale'])

    def test_force_refresh_outage_marks_prior_snapshot_stale(self):
        from aat_api.services import dashboard
        from aat_api.airflow_client.client import AirflowError
        from types import SimpleNamespace
        from unittest.mock import Mock
        dashboard.clear_cache()
        transport=Mock();transport.request.return_value={'total_entries':0,'dag_runs':[]}
        with patch.object(dashboard,'airflow',return_value=SimpleNamespace(dags=lambda:[],client=transport)):
            first=self.client.get('/api/v1/dashboard').json()
        self.assertEqual(first['completeness'],'COMPLETE')
        with patch.object(dashboard,'airflow',side_effect=AirflowError(503,retryable=True)):
            result=self.client.get('/api/v1/dashboard?force_refresh=true').json()
        self.assertTrue(result['stale']);self.assertEqual(result['completeness'],'UNAVAILABLE')
        self.assertEqual(result['fetched_at'],first['fetched_at'])
