"""Kiểm log bootstrap không chứa giá trị secret của đúng project test sở hữu."""

import json
import os
import subprocess
import unittest


class BootstrapSecretLogTests(unittest.TestCase):
    def test_secret_values_are_absent_from_service_logs(self):
        podman = os.environ.get('PODMAN_BIN', 'podman')
        project = os.environ['AAT_COMPOSE_PROJECT']
        self.assertTrue(project.startswith('aat-phase1-'))
        def run(*args, code=None):
            return subprocess.run([podman, *args], input=code, text=True, encoding='utf-8',
                                  capture_output=True, check=True).stdout
        ids = run('ps','-aq','--filter',f'label=com.docker.compose.project={project}').split()
        self.assertTrue(ids)
        containers = json.loads(run('inspect', *ids))
        services = {c['Config']['Labels']['com.docker.compose.service']:c['Id'] for c in containers}
        values = set()
        init = next(c for c in containers if c['Config']['Labels']['com.docker.compose.service']=='secrets-init')
        volume = next(m['Name'] for m in init['Mounts'] if m['Destination']=='/secrets/bootstrap_secrets')
        code = "from pathlib import Path; import json; print(json.dumps([p.read_text() for p in Path('/audit').iterdir() if p.is_file()]))"
        values.update(json.loads(run('run','--rm','-i','--entrypoint','python','-v',f'{volume}:/audit:ro',
                                    'localhost/aat-backend:0.1.0','-',code=code)))
        for service, folders in (('backend',['/secrets/backend','/secrets/app_keyring']),
                                 ('airflow-scheduler',['/secrets/airflow','/secrets/runtime'])):
            code = f"from pathlib import Path; import json; print(json.dumps([p.read_text() for folder in {folders!r} for p in Path(folder).iterdir() if p.is_file()]))"
            values.update(json.loads(run('exec','-i',services[service],'python','-',code=code)))
        self.assertTrue(values)
        for service, container in services.items():
            result = subprocess.run([podman,'logs',container], text=True, encoding='utf-8',capture_output=True,check=True)
            logs = result.stdout + result.stderr
            self.assertFalse(any(value and value in logs for value in values),
                             f'Secret value found in {service} logs; values suppressed')
