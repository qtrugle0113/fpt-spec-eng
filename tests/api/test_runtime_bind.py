"""T103: canonical bearer gate is independent of metadata/Airflow availability."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from uuid import uuid4


class RuntimeBearerTests(unittest.TestCase):
    def test_only_canonical_route_accepts_a_runtime_bearer(self):
        from aat_api.main import app
        with tempfile.TemporaryDirectory() as root:
            token=Path(root)/'runtime_token';token.write_text('a'*64)
            payload=dict(dag_id='missing',run_id='missing',task_id='execute_etl',expected_revision=str(uuid4()))
            with patch.dict(os.environ,{'AAT_RUNTIME_TOKEN_FILE':str(token)}),TestClient(app,raise_server_exceptions=False) as client:
                response=client.post('/internal/runtime/bind',json=payload)
                self.assertEqual(response.status_code,401)
                response=client.post('/internal/runtime/bind',json=payload,headers={'Authorization':'Bearer '+'b'*64})
                self.assertEqual(response.status_code,403)
                response=client.post('/api/v1/internal/runtime/bind',json=payload,headers={'Authorization':'Bearer '+'a'*64})
                self.assertEqual(response.status_code,404)
                self.assertEqual(response.json()['error']['code'],'HTTP_404')
                response=client.post('/internal/runtime/bind',json=payload,headers={'Authorization':'Bearer '+'a'*64})
                self.assertEqual(response.status_code,404)
                self.assertEqual(response.json()['error']['code'],'ETL_REVISION_NOT_FOUND')
                self.assertNotIn('a'*64,response.text)
