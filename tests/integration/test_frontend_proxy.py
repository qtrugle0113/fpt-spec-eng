"""Nginx thật với upstream fixture cô lập; không nghiệm thu backend sản phẩm."""

import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.request
import uuid

PODMAN = os.environ.get("PODMAN_BIN", "podman")
FIXTURE = """
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
requests = []
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/v1/__requests':
            result = requests
        else:
            requests.append([self.command, self.path])
            result = {'path': self.path}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-AAT-Fixture', 'upstream')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
    do_POST = do_GET
    def log_message(self, *args):
        pass
HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()
"""


def podman(*args: str) -> str:
    return subprocess.check_output([PODMAN, *args], text=True, stderr=subprocess.PIPE).strip()


class FrontendProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        cls.network = f"aat-proxy-test-{suffix}"
        cls.backend = f"aat-proxy-upstream-{suffix}"
        cls.frontend = f"aat-proxy-web-{suffix}"
        cls.addClassCleanup(cls.cleanup)
        podman("network", "create", cls.network)
        podman("run", "-d", "--name", cls.backend, "--network", cls.network,
               "--network-alias", "backend", "docker.io/library/python:3.12.16-slim-bookworm",
               "python", "-u", "-c", FIXTURE)
        podman("run", "-d", "--name", cls.frontend, "--network", cls.network,
               "--publish", "127.0.0.1::80", "localhost/aat-frontend:0.1.0")
        address = podman("port", cls.frontend, "80/tcp").splitlines()[0]
        cls.base = "http://" + address
        for _ in range(40):
            try:
                with urllib.request.urlopen(cls.base + "/", timeout=2) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.25)
        raise RuntimeError("Frontend test container did not become ready")

    @classmethod
    def cleanup(cls) -> None:
        for name in (cls.frontend, cls.backend):
            subprocess.run([PODMAN, "rm", "-f", name], capture_output=True, check=False)
        subprocess.run([PODMAN, "network", "rm", cls.network], capture_output=True, check=False)

    def request(self, path: str, method: str = "GET", token: bool = False) -> tuple[int, bytes, str | None]:
        headers = {"Authorization": "Bearer fixture-only"} if token else {}
        request = urllib.request.Request(self.base + path, method=method, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers.get("X-AAT-Fixture")

    def test_private_prefixes_do_not_reach_upstream(self) -> None:
        before = json.loads(self.request("/api/v1/__requests")[1])
        for path in ("/internal/runtime", "/internal/runtime/bind",
                     "/api/v1/internal/runtime", "/api/v1/internal/runtime/bind"):
            for method in ("GET", "POST"):
                for token in (False, True):
                    with self.subTest(path=path, method=method, token=token):
                        status, body, upstream = self.request(path, method, token)
                        self.assertEqual(status, 404)
                        self.assertIsNone(upstream)
                        self.assertNotIn(b'<div id="root">', body)
        after = json.loads(self.request("/api/v1/__requests")[1])
        self.assertEqual(after, before)

    def test_public_proxy_preserves_path(self) -> None:
        status, body, upstream = self.request("/api/v1/proxy-fixture?test=1")
        self.assertEqual(status, 200)
        self.assertEqual(upstream, "upstream")
        self.assertEqual(json.loads(body)["path"], "/api/v1/proxy-fixture?test=1")

    def test_spa_deep_link(self) -> None:
        status, body, upstream = self.request("/monitoring")
        self.assertEqual(status, 200)
        self.assertIsNone(upstream)
        self.assertIn(b'<div id="root">', body)

    def test_nginx_configuration_is_valid(self) -> None:
        result = subprocess.run([PODMAN, "exec", self.frontend, "nginx", "-t"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
