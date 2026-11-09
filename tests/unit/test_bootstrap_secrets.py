"""Bảo vệ key/bootstrap secrets trước khi triển khai bộ sinh secret."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BootstrapSecretTests(unittest.TestCase):
    def test_owner_domain_is_separate_from_backend_and_runtime(self):
        spec=importlib.util.spec_from_file_location('bootstrap_secrets',ROOT/'docker/bootstrap/secrets.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);module.initialize(root)
            self.assertEqual((root/'app_owner_secrets/app_owner').read_bytes(),(root/'bootstrap_secrets/app_owner').read_bytes())
            self.assertFalse((root/'backend_secrets/app_owner').exists())
            self.assertFalse((root/'runtime_secrets/app_owner').exists())

    def test_idempotence_decryption_and_missing_key_fail_closed(self):
        from aat_metadata.secrets.codec import SecretCodec
        spec = importlib.util.spec_from_file_location("bootstrap_secrets", ROOT / "docker/bootstrap/secrets.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module.initialize(root)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            module.initialize(root)
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})
            codec = SecretCodec(root / 'app_keyring')
            key_id, ciphertext = codec.encrypt('private-value')
            self.assertNotIn('private-value', ciphertext)
            self.assertEqual(codec.decrypt(key_id, ciphertext), 'private-value')
            with self.assertRaises(ValueError):
                codec.decrypt('unknown-key', ciphertext)
            (root / 'app_keyring' / (key_id + '.key')).unlink()
            with self.assertRaises(RuntimeError):
                module.initialize(root)
