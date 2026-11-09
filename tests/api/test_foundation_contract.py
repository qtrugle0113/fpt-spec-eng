"""Validate captured real foundation HTTP responses with the T015 harness."""
import json
from pathlib import Path
import unittest
import yaml
from tests.api.test_openapi_contract import ContractHarness,CONTRACT


class FoundationHTTPContractTests(unittest.TestCase):
    def test_recorded_real_http_responses_match_canonical_contract(self):
        evidence=json.loads((Path(__file__).resolve().parents[1]/'fixtures/phase2-http-evidence.json').read_text())
        self.assertEqual(len(evidence),3)
        harness=ContractHarness(yaml.safe_load(CONTRACT.read_text(encoding='utf-8')))
        for record in evidence:
            with self.subTest(path=record['path'],status=record['status']):
                harness.assert_response(record['method'],record['path'],record['status'],record['body'])
