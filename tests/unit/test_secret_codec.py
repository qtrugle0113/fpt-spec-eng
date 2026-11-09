"""T036/T037: explicit key rotation preserves historical decryption and fails closed."""
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from cryptography.fernet import Fernet
from aat_metadata.secrets.codec import SecretCodec


class SecretRotationTests(unittest.TestCase):
    def test_rotation_uses_existing_current_key_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=uuid4().hex;new=uuid4().hex
            (root/(old+'.key')).write_bytes(Fernet.generate_key())
            (root/'current.json').write_text(json.dumps({'key_id':old}))
            previous=SecretCodec(root);key_id,token=previous.encrypt('synthetic-secret')
            (root/(new+'.key')).write_bytes(Fernet.generate_key())
            (root/'current.json').write_text(json.dumps({'key_id':new}))
            current=SecretCodec(root)
            self.assertTrue(callable(getattr(current,'rotate',None)),'T037 rotation missing')
            rotated_id,rotated=current.rotate(key_id,token)
            self.assertEqual(rotated_id,new)
            self.assertEqual(current.decrypt(rotated_id,rotated),'synthetic-secret')
            self.assertEqual(current.decrypt(old,token),'synthetic-secret')
            self.assertEqual(previous.decrypt(old,token),'synthetic-secret')
            self.assertTrue((root/(old+'.key')).exists(),'Rotation deleted a historical key')

    def test_missing_old_key_and_tampered_tokens_do_not_generate_replacements(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=uuid4().hex;new=uuid4().hex
            (root/(old+'.key')).write_bytes(Fernet.generate_key())
            (root/'current.json').write_text(json.dumps({'key_id':old}))
            key_id,token=SecretCodec(root).encrypt('synthetic-secret')
            (root/(new+'.key')).write_bytes(Fernet.generate_key())
            (root/'current.json').write_text(json.dumps({'key_id':new}))
            codec=SecretCodec(root)
            self.assertTrue(callable(getattr(codec,'rotate',None)),'T037 rotation missing')
            with self.assertRaises(ValueError):codec.rotate(key_id,'not-a-token')
            (root/(old+'.key')).unlink()
            before={p.name:p.read_bytes() for p in root.iterdir()}
            with self.assertRaises(ValueError):codec.rotate(key_id,token)
            with self.assertRaises(ValueError):codec.decrypt(key_id,token)
            self.assertTrue(before=={p.name:p.read_bytes() for p in root.iterdir()},'Missing key regenerated or keyring mutated')
