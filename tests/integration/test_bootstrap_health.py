"""Fault injection trên project test sở hữu: probe phải phản ánh dependency down."""

import json
import os
import subprocess
import time
import unittest
import urllib.request

PODMAN = os.environ.get('PODMAN_BIN', 'podman')


class BootstrapHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project = os.environ['AAT_COMPOSE_PROJECT']
        if not project.startswith('aat-phase1-'):
            raise RuntimeError('Fault injection requires an owned aat-phase1 test project')
        ids = cls.run_podman('ps', '-aq', '--filter', f'label=com.docker.compose.project={project}').stdout.split()
        containers = json.loads(cls.run_podman('inspect', *ids).stdout)
        cls.services = {c['Config']['Labels']['com.docker.compose.service']:c['Id'] for c in containers}

    @staticmethod
    def run_podman(*args, check=True):
        result = subprocess.run([PODMAN, *args], text=True, capture_output=True)
        if check and result.returncode:
            raise AssertionError(result.stderr or result.stdout)
        return result

    def probe(self, mode, check=True):
        return self.run_podman('exec', self.services['backend'], 'python',
                               '/opt/aat/docker/bootstrap/health.py', mode, check=check)

    def wait_probe(self, mode):
        for _ in range(60):
            if self.probe(mode, check=False).returncode == 0:
                return
            time.sleep(2)
        self.fail(f'{mode} probe did not recover')

    def test_mysql_down_fails_query_probe_but_live_remains_live(self):
        self.probe('databases')
        try:
            self.run_podman('stop', '--time', '10', self.services['mysql'])
            self.assertNotEqual(self.probe('mysql', check=False).returncode, 0)
            self.probe('live')
        finally:
            self.run_podman('start', self.services['mysql'])
            self.wait_probe('databases')

    def test_http200_does_not_hide_stale_scheduler(self):
        self.probe('airflow')
        try:
            self.run_podman('stop', '--time', '10', self.services['airflow-scheduler'])
            for _ in range(60):
                with urllib.request.urlopen(os.environ.get('AAT_AIRFLOW_URL', 'http://127.0.0.1:8080') + '/api/v2/monitor/health', timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    payload = json.load(response)
                if payload['scheduler']['status'] != 'healthy':
                    break
                time.sleep(2)
            else:
                self.fail('Stopped scheduler must become unhealthy in JSON')
            self.assertNotEqual(self.probe('airflow', check=False).returncode, 0)
            self.probe('live')
        finally:
            self.run_podman('start', self.services['airflow-scheduler'])
            self.wait_probe('airflow')
