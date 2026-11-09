"""Chặn giải mã artifact sai hash và regression mạng trước bản vá Brotli."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[2]


class AirflowOfflinePatchTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            'offline_security_patch', ROOT / 'airflow/docker/install_security_patch.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root / 'libbrotli1.deb'
        self.artifact.write_bytes(b'trusted-deb-test-fixture')
        self.policy = {'package': 'libbrotli1', 'version': '1.0.9-2+deb12u1',
                       'architecture': 'amd64', 'sha256': hashlib.sha256(self.artifact.read_bytes()).hexdigest()}
        self.write_policy()

    def write_policy(self):
        (self.root / 'brotli.lock.json').write_text(json.dumps(self.policy), encoding='utf8')

    def test_tampered_archive_fails_before_package_manager(self):
        self.artifact.write_bytes(self.artifact.read_bytes() + b'tampered')
        with patch.object(self.module.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                self.module.install(self.root)
            run.assert_not_called()

    def test_unapproved_package_version_or_architecture_fails_closed(self):
        for field, value in [('package', 'other'), ('version', '1.0.9-2+b6'), ('architecture', 'arm64')]:
            with self.subTest(field=field):
                original = self.policy[field]
                self.policy[field] = value
                self.write_policy()
                with patch.object(self.module.subprocess, 'run') as run:
                    with self.assertRaises(ValueError):
                        self.module.install(self.root)
                    run.assert_not_called()
                self.policy[field] = original

    def test_verified_archive_installs_and_checks_exact_version(self):
        with patch.object(self.module.subprocess, 'run', return_value=Mock(stdout='1.0.9-2+deb12u1')) as run:
            self.module.install(self.root)
            self.assertEqual(run.call_args_list[0].args[0], ['dpkg', '-i', str(self.artifact)])
            self.assertEqual(run.call_args_list[1].args[0], ['dpkg-query', '-W', '-f=${Version}', 'libbrotli1'])
        self.assertFalse(self.artifact.exists())

    def test_airflow_stage_patches_offline_before_first_network_command(self):
        source = (ROOT / 'airflow/docker/Dockerfile').read_text(encoding='utf8')
        stage = source.split('FROM docker.io/apache/airflow:', 1)[1]
        first_run = next(line for line in stage.splitlines() if line.startswith('RUN '))
        self.assertEqual(first_run, 'RUN --network=none python /opt/aat/security/install_security_patch.py')
        self.assertLess(stage.index('install_security_patch.py\nRUN --network=none'), stage.index('apt-get update'))
        lock = json.loads((ROOT / 'airflow/docker/security/brotli.lock.json').read_text(encoding='utf8'))
        self.assertIn(lock['url'], stage)
        self.assertEqual(lock['sha256'], 'e27b3d655fa6fadd7a56f706687e94573c0af68b7d6df394a32a381a3a6c6d8b')

    def test_wrong_installed_version_is_not_success(self):
        with patch.object(self.module.subprocess, 'run', return_value=Mock(stdout='1.0.9-2+b6')):
            with self.assertRaises(RuntimeError):
                self.module.install(self.root)
