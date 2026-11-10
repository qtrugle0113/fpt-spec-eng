"""Validate live foundation HTTP responses without a machine-local capture file."""
import os
import unittest
from uuid import uuid4
import yaml
from tests.api.test_openapi_contract import ContractHarness,CONTRACT


class FoundationHTTPContractTests(unittest.TestCase):
    def test_live_foundation_http_responses_match_canonical_contract(self):
        from fastapi.testclient import TestClient
        from aat_api.main import app
        harness=ContractHarness(yaml.safe_load(CONTRACT.read_text(encoding='utf-8')))
        with TestClient(app,raise_server_exceptions=False) as client:
            for path,contract in [('/health/live','/health/live'),('/health/ready','/health/ready'),
                                  ('/operations/'+str(uuid4()),'/operations/{id}')]:
                response=client.get('/api/v1'+path)
                if path=='/health/live':self.assertEqual(response.status_code,200)
                elif path=='/health/ready':self.assertIn(response.status_code,(200,503))
                elif os.environ.get('AAT_FOUNDATION_DISPOSABLE')=='1':self.assertEqual(response.status_code,404)
                else:self.assertIn(response.status_code,(404,503))
                harness.assert_response('get',contract,response.status_code,
                    response.json(),headers=response.headers)
