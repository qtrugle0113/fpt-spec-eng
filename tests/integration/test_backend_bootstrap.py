"""Kiểm tra wheel và liveness bootstrap trên image thật; không suy ra product ready."""

import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.request
import uuid

PODMAN = os.environ.get("PODMAN_BIN", "podman")


class BackendBootstrapTests(unittest.TestCase):
    def test_image_import_and_liveness_without_product_readiness(self):
        name = "aat-backend-test-" + uuid.uuid4().hex[:10]
        def run(*args):
            return subprocess.check_output([PODMAN, *args], text=True).strip()
        try:
            run("run", "-d", "--name", name, "--publish", "127.0.0.1::8000", "localhost/aat-backend:0.1.0")
            port = run("port", name, "8000/tcp").rsplit(":", 1)[1]
            base = f"http://127.0.0.1:{port}"
            for _ in range(60):
                try:
                    with urllib.request.urlopen(base + "/api/v1/health/live", timeout=2) as response:
                        result = json.load(response)
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.5)
            else:
                self.fail("Liveness bootstrap unavailable")
            self.assertEqual(result, {"status": "live", "stage": "bootstrap"})
            with self.assertRaises(urllib.error.HTTPError) as failure:
                urllib.request.urlopen(base + "/api/v1/health/ready", timeout=2)
            self.assertEqual(failure.exception.code, 404)
            run("exec", name, "python", "-m", "pip", "check")
            run("exec", name, "python", "-c", "import aat_api.main, aat_metadata, aat_etl")
        finally:
            subprocess.run([PODMAN, "rm", "-f", name], capture_output=True)
