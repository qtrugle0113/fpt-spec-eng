"""Tiếp nhận fixture fresh đã lên bằng một lệnh; kiểm restart giữ volumes và secret bytes."""

import json
import os
from pathlib import Path
import subprocess
import time
import unittest

PODMAN = os.environ.get('PODMAN_BIN', 'podman')
ROOT = Path(__file__).resolve().parents[2]


class BootstrapStartupTests(unittest.TestCase):
    def run_command(self, *args, code=None):
        result = subprocess.run([PODMAN, *args], input=code, text=True, encoding='utf-8',
                                capture_output=True, cwd=self.directory)
        if result.returncode:
            self.fail(f'Command failed ({result.returncode}): {result.stderr[-2000:]}')
        return result.stdout.strip()

    def compose(self, *args):
        return self.run_command('compose', '-p', self.project, *args)

    def services(self):
        ids = self.run_command('ps', '-aq', '--filter', f'label=com.docker.compose.project={self.project}').split()
        return {c['Config']['Labels']['com.docker.compose.service']: c
                for c in json.loads(self.run_command('inspect', *ids))}

    def wait_healthy(self):
        for _ in range(120):
            services = self.services()
            for name in ('secrets-init','db-init','app-init','airflow-init'):
                state = services[name]['State']
                if state['Status'] == 'exited':
                    self.assertEqual(state['ExitCode'], 0, name)
            if all(services[name]['State'].get('Health', {}).get('Status') == 'healthy'
                   for name in ('postgres','mysql','airflow-apiserver','airflow-scheduler',
                                'airflow-dag-processor','backend-worker','backend','frontend')):
                return services
            time.sleep(2)
        self.fail('Bootstrap services did not become healthy')

    def python(self, container, code):
        return self.run_command('exec', '-i', container, 'python', '-', code=code)

    def secret_hashes(self, services):
        result = {}
        for service, folders in (('backend', ['/secrets/backend','/secrets/app_keyring']),
                                 ('airflow-scheduler', ['/secrets/airflow','/secrets/runtime'])):
            code = f"""
import hashlib,json
from pathlib import Path
print(json.dumps({{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in {folders!r} for p in Path(folder).iterdir() if p.is_file()}},sort_keys=True))
"""
            result[service] = json.loads(self.python(services[service]['Id'], code))
        return result

    def sample_edit(self, services, write=False):
        code = f"""
import json,psycopg,pymysql
from pathlib import Path
root=Path('/secrets/backend')
with psycopg.connect(host='postgres',dbname='etl_test',user='aat_etl',password=(root/'pg_etl').read_text()) as c:
 if {write!r}: c.execute("UPDATE sample.customers_source SET customer_name='Persistent test edit' WHERE customer_id=1")
 pg=c.execute('SELECT customer_name FROM sample.customers_source WHERE customer_id=1').fetchone()[0]
with pymysql.connect(host='mysql',database='etl_test',user='aat_etl',password=(root/'mysql_etl').read_text(),autocommit=True) as c:
 with c.cursor() as cur:
  if {write!r}: cur.execute("UPDATE customers_source SET customer_name='Persistent test edit' WHERE customer_id=1")
  cur.execute('SELECT customer_name FROM customers_source WHERE customer_id=1'); my=cur.fetchone()[0]
print(json.dumps([pg,my]))
"""
        return json.loads(self.python(services['backend']['Id'], code))

    def artifacts(self, services, write=False):
        results = {}
        for service, folders in (('backend-worker', ['/data/generated_dags','/data/uploads','/data/staging']),
                                 ('airflow-scheduler', ['/opt/airflow/logs'])):
            code = f"""
import hashlib,json
from pathlib import Path
result={{}}
for folder in {folders!r}:
 p=Path(folder)/'phase1-persistence.marker'
 if {write!r}: p.write_bytes(b'bootstrap persistence fixture')
 result[folder]=hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps(result,sort_keys=True))
"""
            results[service] = json.loads(self.python(services[service]['Id'], code))
        return results

    def test_existing_fresh_fixture_and_persistent_restart(self):
        self.project = os.environ['AAT_COMPOSE_PROJECT']
        self.assertTrue(self.project.startswith('aat-phase1-'), 'Only owned test fixtures may be restarted')
        self.directory = Path(os.environ.get('AAT_COMPOSE_DIR', ROOT))
        if os.environ.get('AAT_FRESH_START') == '1':
            self.assertFalse(self.run_command('ps', '-aq', '--filter',
                                             f'label=com.docker.compose.project={self.project}'))
            self.compose('up', '--build', '-d')
        services = self.wait_healthy()
        before = self.secret_hashes(services)
        self.assertEqual(self.sample_edit(services, write=True), ['Persistent test edit'] * 2)
        artifacts = self.artifacts(services, write=True)
        # Không -v: phải giữ đúng volumes cũ, không reset khi init thất bại.
        self.compose('down')
        self.compose('up', '--build', '-d')
        services = self.wait_healthy()
        self.assertEqual(before, self.secret_hashes(services))
        self.assertEqual(self.sample_edit(services), ['Persistent test edit'] * 2)
        self.assertEqual(artifacts, self.artifacts(services))
        self.run_command('exec', services['backend']['Id'], 'python', '/opt/aat/docker/bootstrap/health.py', 'databases')
        self.run_command('exec', services['backend']['Id'], 'python', '/opt/aat/docker/bootstrap/health.py', 'airflow')
