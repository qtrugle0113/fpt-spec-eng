"""Wiring/resource gates trên đúng Podman/Compose; không đánh giá readiness sản phẩm."""

import json
import os
from pathlib import Path
import subprocess
import unittest
import uuid

PODMAN = os.environ.get('PODMAN_BIN', 'podman')
ROOT = Path(__file__).resolve().parents[2]


def run(*args, check=True):
    result = subprocess.run([PODMAN, *args], text=True, capture_output=True)
    if check and result.returncode:
        raise AssertionError(result.stderr)
    return result


class ComposeDependencyTests(unittest.TestCase):
    def test_failed_init_blocks_consumer(self):
        project = 'aat-failed-init-' + uuid.uuid4().hex[:8]
        args = ('compose', '-f', str(ROOT / 'tests/fixtures/compose-dependency-failure.yml'), '-p', project)
        try:
            result = run(*args, 'up', '-d', check=False)
            self.assertNotEqual(result.returncode, 0)
            init_ids = run('ps', '-aq', '--filter', f'label=com.docker.compose.project={project}',
                           '--filter', 'label=com.docker.compose.service=failing-init').stdout.split()
            self.assertEqual(len(init_ids), 1)
            self.assertEqual(json.loads(run('inspect', init_ids[0]).stdout)[0]['State']['ExitCode'], 23)
            ids = run('ps', '-aq', '--filter', f'label=com.docker.compose.project={project}',
                      '--filter', 'label=com.docker.compose.service=consumer').stdout.split()
            for container in ids:
                state = json.loads(run('inspect', container).stdout)[0]['State']
                self.assertFalse(state['Running'])
                self.assertNotIn('CONSUMER_MUST_NOT_START', run('logs', container).stdout)
        finally:
            run(*args, 'down', '--remove-orphans', check=False)


class ComposeStackWiringTests(unittest.TestCase):
    def test_real_stack_health_limits_mounts_ports_and_order(self):
        project = os.environ['AAT_COMPOSE_PROJECT']
        ids = run('ps', '-aq', '--filter', f'label=com.docker.compose.project={project}').stdout.split()
        self.assertTrue(ids)
        containers = json.loads(run('inspect', *ids).stdout)
        services = {c['Config']['Labels']['com.docker.compose.service']: c for c in containers}
        for service in ('secrets-init', 'db-init', 'app-init', 'airflow-init'):
            self.assertEqual(services[service]['State']['Status'], 'exited', service)
            self.assertEqual(services[service]['State']['ExitCode'], 0, service)
        for service in ('postgres','mysql','backend-worker','backend','frontend','airflow-apiserver','airflow-scheduler','airflow-dag-processor'):
            self.assertEqual(services[service]['State']['Health']['Status'], 'healthy', service)
        for service, limit in (('postgres',1073741824), ('mysql',1073741824), ('airflow-scheduler',2147483648)):
            container = services[service]
            self.assertEqual(container['HostConfig']['Memory'], limit)
            self.assertEqual(int(run('exec', container['Id'], 'cat', '/sys/fs/cgroup/memory.max').stdout), limit)
        for service in ('backend','backend-worker','airflow-scheduler','airflow-dag-processor'):
            uid = run('exec', services[service]['Id'], 'id', '-u').stdout.strip()
            self.assertEqual(uid, '50000')
        for service in ('airflow-scheduler','airflow-dag-processor','airflow-apiserver'):
            mounts = {m['Destination']: m for m in services[service]['Mounts']}
            self.assertFalse(mounts['/opt/airflow/dags']['RW'])
            self.assertFalse(mounts['/secrets/airflow']['RW'])
            self.assertNotIn('/secrets/bootstrap_secrets', mounts)
            self.assertNotEqual(run('exec', services[service]['Id'], 'touch',
                                    '/opt/airflow/dags/phase1-ro-probe', check=False).returncode, 0)
        for service in ('postgres','mysql'):
            self.assertFalse(services[service]['HostConfig'].get('PortBindings'))
            mounts = {m['Destination']: m for m in services[service]['Mounts']}
            self.assertTrue(mounts['/secrets']['Name'].endswith(f'_{service}_secrets'))
            self.assertFalse(mounts['/secrets']['RW'])
        for service in ('backend', 'backend-worker'):
            self.assertNotEqual(run('exec', services[service]['Id'], 'test', '-f',
                                    '/secrets/backend/app_owner', check=False).returncode, 0)
            self.assertEqual(run('exec', services[service]['Id'], 'stat', '-c', '%a:%u:%g',
                                 '/secrets/backend').stdout.strip(), '700:50000:50000')
        for service in ('frontend','backend','airflow-apiserver'):
            for bindings in services[service]['HostConfig']['PortBindings'].values():
                self.assertTrue(all(b['HostIp']=='127.0.0.1' for b in bindings))
        for prerequisite, consumer in (('secrets-init','postgres'),('db-init','app-init'),
                                       ('app-init','airflow-init'),('airflow-init','airflow-scheduler')):
            self.assertLess(services[prerequisite]['State']['FinishedAt'], services[consumer]['State']['StartedAt'])
