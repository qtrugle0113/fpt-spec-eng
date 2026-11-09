"""Bảo vệ upstream và các override dependency đã được chủ dự án cho phép."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class AirflowConstraintsTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            'aat_build_constraints', ROOT / 'airflow/docker/build_constraints.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.upstream = b'# upstream\ncertifi==2026.7.22\nurllib3==2.7.0\ndnspython==2.8.0\napache-airflow==3.3.2\n'
        self.policy = {
            'upstream_sha256': hashlib.sha256(self.upstream).hexdigest(),
            'overrides': {'certifi': {'from': '2026.7.22', 'to': '2026.10.18'},
                          'urllib3': {'from': '2.7.0', 'to': '2.8.0'},
                          'dnspython': {'from': '2.8.0', 'to': '2.9.0'}},
        }

    def test_only_approved_pins_change_and_upstream_unchanged(self):
        before = bytes(self.upstream)
        effective = self.module.derive_constraints(self.upstream, self.policy)
        self.assertEqual(self.upstream, before)
        self.assertEqual(effective, before.replace(b'certifi==2026.7.22', b'certifi==2026.10.18')
                         .replace(b'urllib3==2.7.0', b'urllib3==2.8.0')
                         .replace(b'dnspython==2.8.0', b'dnspython==2.9.0'))

    def test_changed_upstream_or_extra_override_fail_closed(self):
        with self.assertRaises(ValueError):
            self.module.derive_constraints(self.upstream + b'# changed\n', self.policy)
        policy = copy.deepcopy(self.policy)
        policy['overrides']['apache-airflow'] = {'from': '3.3.2', 'to': '3.4.0'}
        with self.assertRaises(ValueError):
            self.module.derive_constraints(self.upstream, policy)
        policy = copy.deepcopy(self.policy)
        policy['overrides']['urllib3']['from'] = '2.6.0'
        with self.assertRaises(ValueError):
            self.module.derive_constraints(self.upstream, policy)

    def test_committed_override_artifacts_match_policy(self):
        directory = ROOT / 'airflow/docker'
        policy = json.loads((directory / 'constraints-policy.json').read_text(encoding='utf-8'))
        effective = self.module.derive_constraints((directory / 'constraints-3.12.txt').read_bytes(), policy)
        lock = (directory / 'overrides.lock').read_text(encoding='utf-8')
        for name, override in policy['overrides'].items():
            self.assertIn(f"{name}=={override['to']}".encode(), effective)
            self.assertIn(f"{name}=={override['to']} --hash=sha256:{override['artifact_sha256']}", lock)
