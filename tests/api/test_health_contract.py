"""T018 real ASGI app responses validated by canonical T015 harness."""

import unittest
from fastapi.testclient import TestClient
import yaml

from tests.api.test_openapi_contract import CONTRACT, ContractHarness


class HealthContractTests(unittest.TestCase):
    def setUp(self):
        from aat_api.main import app
        self.client = TestClient(app)
        self.app = app
        self.harness = ContractHarness(yaml.safe_load(CONTRACT.read_text(encoding='utf-8')))

    def test_liveness_is_canonical_without_claiming_foundation_ready(self):
        response = self.client.get('/api/v1/health/live')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ALIVE'})
        self.harness.assert_response('get', '/health/live', response.status_code, response.json())

    def test_readiness_fails_closed_with_safe_error_until_t034(self):
        response = self.client.get('/api/v1/health/ready')
        self.assertEqual(response.status_code, 503)
        self.harness.assert_response('get', '/health/ready', response.status_code, response.json())
        self.assertEqual(response.json()['error']['code'], 'FOUNDATION_NOT_READY')
        self.assertNotIn('READY', response.json().get('status', ''))
        self.assertNotEqual(response.json()['error']['request_id'],
                            self.client.get('/api/v1/health/ready').json()['error']['request_id'])

    def test_health_route_operation_ids_and_response_schemas_match_contract(self):
        actual = self.app.openapi()
        selected = {('get', '/health/live'), ('get', '/health/ready')}
        for method, path in selected:
            expected = self.harness.operation(method, path)
            observed = actual['paths']['/api/v1' + path][method]
            self.assertEqual(observed['operationId'], expected['operationId'])
            self.assertNotIn('422', observed['responses'])
        # Verify declared response shape with actual payloads, not all future endpoints.
        actual_harness = ContractHarness(actual)
        live = self.client.get('/api/v1/health/live')
        ready = self.client.get('/api/v1/health/ready')
        actual_harness.assert_response('get', '/api/v1/health/live', 200, live.json())
        actual_harness.assert_response('get', '/api/v1/health/ready', 503, ready.json())


if __name__ == '__main__':
    unittest.main()
