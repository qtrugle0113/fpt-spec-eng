"""Source-backed Uvicorn HTTP/probe regression; no image or DB acceptance implied."""

import json
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


class HealthSourceTests(unittest.TestCase):
    def test_http_liveness_probe_and_readiness_fail_closed(self):
        with tempfile.TemporaryFile() as private_log:
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'aat_api.main:app',
                                        '--host', '127.0.0.1', '--port', '8000'],
                                       stdout=private_log, stderr=private_log)
            try:
                for _ in range(100):
                    self.assertIsNone(process.poll(), 'Source-backed Uvicorn exited')
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=1) as r:
                            payload = json.load(r)
                        break
                    except (OSError, urllib.error.URLError):
                        time.sleep(0.1)
                else:
                    self.fail('Source-backed liveness unavailable')
                self.assertEqual(payload, {'status': 'ALIVE'})
                from docker.bootstrap.health import live
                live()  # Actual urllib probe against actual Uvicorn; no monkeypatch.
                with self.assertRaises(urllib.error.HTTPError) as failure:
                    urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=2)
                self.assertEqual(failure.exception.code, 503)
                self.assertEqual(json.load(failure.exception)['error']['code'], 'FOUNDATION_NOT_READY')
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
