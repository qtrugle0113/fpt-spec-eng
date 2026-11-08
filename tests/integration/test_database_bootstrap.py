"""Fixture Podman cô lập cho DB init; không dùng làm bằng chứng full Compose gate."""

from pathlib import Path
import os
import subprocess
import time
import unittest
import uuid

PODMAN = os.environ.get('PODMAN_BIN', 'podman')
ROOT = Path(__file__).resolve().parents[2]


class DatabaseBootstrapTests(unittest.TestCase):
    def test_real_init_preserves_edits_and_limits_roles(self):
        prefix = 'aat-db-test-' + uuid.uuid4().hex[:8]
        containers, volumes = [], []
        def run(*args):
            result = subprocess.run([PODMAN, *map(str, args)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode:
                raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout)
            return result.stdout.strip()
        network = prefix
        try:
            run('network', 'create', network)
            mounts = []
            for domain in ('bootstrap_secrets', 'backend_secrets', 'runtime_secrets', 'airflow_secrets', 'app_keyring', 'postgres_secrets', 'mysql_secrets'):
                volume = prefix + '-' + domain
                volumes.append(volume)
                run('volume', 'create', volume)
                mounts.extend(['-v', f'{volume}:/secrets/{domain}'])
            init = prefix + '-secrets'
            containers.append(init)
            run('create', '--name', init, '--user', '0:0', *mounts, 'localhost/aat-backend:0.1.0', 'python', '/tmp/secrets.py')
            run('cp', ROOT / 'docker/bootstrap/secrets.py', f'{init}:/tmp/secrets.py')
            try:
                run('start', '-a', init)
            except subprocess.CalledProcessError as exc:
                self.fail(exc.output)
            self.assertEqual(run('inspect', '--format', '{{.State.ExitCode}}', init), '0')
            for service, image, envs in (
                ('postgres', 'localhost/aat-postgres:17.11', ['POSTGRES_PASSWORD_FILE=/secrets/postgres_admin']),
                ('mysql', 'localhost/aat-mysql:8.4.13', ['MYSQL_ROOT_PASSWORD_FILE=/secrets/mysql_admin', 'MYSQL_ROOT_HOST=%']),
            ):
                name = prefix + '-' + service
                containers.append(name)
                envargs = [item for env in envs for item in ('-e', env)]
                run('run', '-d', '--name', name, '--network', network, '--network-alias', service,
                    '-v', f'{volumes[5 if service == "postgres" else 6]}:/secrets:ro', '--memory', '1g', *envargs, image)
            probe = prefix + '-probe'
            containers.append(probe)
            run('create', '--name', probe, '--network', network, '--user', '0:0',
                '-v', f'{volumes[0]}:/secrets/bootstrap_secrets:ro', 'localhost/aat-backend:0.1.0', 'sleep', 'infinity')
            run('cp', str(ROOT / 'docker') + '/.', f'{probe}:/opt/aat/docker')
            run('start', probe)
            # Poll query thật, không coi container running là DB ready.
            for _ in range(120):
                try:
                    run('exec', probe, 'python', '/opt/aat/docker/bootstrap/db_ready.py')
                    break
                except subprocess.CalledProcessError:
                    time.sleep(1)
            else:
                self.fail('Database queries did not become ready')
            output = run('exec', probe, 'python', '/opt/aat/docker/bootstrap/check_databases.py')
            self.assertIn('DB_INIT_IDEMPOTENCE_GRANTS_ENGINE_PASS', output)
            if os.environ.get('AAT_TEST_AIRFLOW') == '1':
                run('cp', ROOT / 'docker/bootstrap/check_airflow.py', f'{probe}:/opt/aat/docker/bootstrap/check_airflow.py')
                # Chỉ backend domain; admin credential không mount vào Airflow.
                auth_probe = prefix + '-auth-probe'
                containers.append(auth_probe)
                run('create', '--name', auth_probe, '--network', network,
                    '-v', f'{volumes[1]}:/secrets/backend_secrets:ro',
                    'localhost/aat-backend:0.1.0', 'sleep', 'infinity')
                run('cp', ROOT / 'docker/bootstrap/check_airflow.py', f'{auth_probe}:/tmp/check_airflow.py')
                run('start', auth_probe)
                airflow_mount = f'{volumes[3]}:/secrets/airflow:ro'
                for attempt in range(2):
                    name = prefix + f'-airflow-init-{attempt}'
                    containers.append(name)
                    run('run', '--name', name, '--network', network, '-v', airflow_mount,
                        'localhost/aat-airflow:0.1.0', 'aat-initialize')
                    self.assertEqual(run('inspect', '--format', '{{.State.ExitCode}}', name), '0')
                for service, command in (('airflow-apiserver', 'api-server'), ('airflow-scheduler', 'scheduler'),
                                         ('airflow-dag-processor', 'dag-processor')):
                    name = prefix + '-' + service
                    containers.append(name)
                    run('run', '-d', '--name', name, '--network', network, '--network-alias', service,
                        '-v', airflow_mount, '--memory', '2g' if command == 'scheduler' else '1g',
                        'localhost/aat-airflow:0.1.0', command)
                self.assertIn('AIRFLOW_AUTH_API_UI_PASS', run('exec', auth_probe, 'python', '/tmp/check_airflow.py'))
        finally:
            for container in reversed(containers):
                subprocess.run([PODMAN, 'rm', '-f', container], capture_output=True)
            subprocess.run([PODMAN, 'network', 'rm', network], capture_output=True)
            for volume in volumes:
                subprocess.run([PODMAN, 'volume', 'rm', volume], capture_output=True)
