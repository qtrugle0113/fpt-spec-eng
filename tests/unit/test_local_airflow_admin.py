"""Kiểm account local có opt-in, không reset ngầm và backup/restore."""
from pathlib import Path
import json
import tempfile
import unittest
from docker.bootstrap.local_airflow_admin import configure, restore, merge_users


class LocalAirflowAdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'passwords.json'
        self.original = {'aat_service': 'service-private', 'operator': 'operator-private', 'other': 'other-private'}
        self.path.write_text(json.dumps(self.original))

    def test_requires_explicit_local_opt_in(self):
        with self.assertRaises(ValueError): configure(self.path, local_demo=False)
        self.assertEqual(json.loads(self.path.read_text()), self.original)

    def test_create_preserves_others_and_custom_password(self):
        configure(self.path, local_demo=True)
        value = json.loads(self.path.read_text())
        self.assertEqual(value, {**self.original, 'admin': 'admin'})
        value['admin'] = 'custom-private'
        self.path.chmod(0o600); self.path.write_text(json.dumps(value))
        configure(self.path, local_demo=True)
        self.assertEqual(json.loads(self.path.read_text())['admin'], 'custom-private')

    def test_explicit_reset_and_exact_restore(self):
        before = self.path.read_bytes()
        result = configure(self.path, local_demo=True, reset=True)
        self.assertTrue(result['other_accounts_unchanged'])
        self.assertEqual(json.loads(self.path.read_text())['admin'], 'admin')
        self.assertNotIn('service-private', json.dumps(result))
        restore(self.path, result['backup'], local_demo=True)
        self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_missing_and_invalid_values_fail_closed(self):
        for value in ['bad-json', '[]', '{"aat_service": 1}', '{"aat_service":""}']:
            self.path.chmod(0o600); self.path.write_text(value)
            with self.assertRaises((ValueError, json.JSONDecodeError)): configure(self.path, local_demo=True)
        self.path.unlink()
        with self.assertRaises(FileNotFoundError): configure(self.path, local_demo=True)

    def test_role_merge_preserves_other_users_and_promotes_admin(self):
        self.assertEqual(merge_users('aat_service:admin,operator:admin,admin:viewer,alice:user'), 'aat_service:admin,operator:admin,alice:user,admin:admin')

    def test_restore_cannot_escape_backup_folder(self):
        with self.assertRaises(ValueError): restore(self.path, '../outside', local_demo=True)
