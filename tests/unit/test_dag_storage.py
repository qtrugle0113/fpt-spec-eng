"""T106: atomic replacement, crash boundaries and confined generated files."""
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4


class DAGStorageTests(unittest.TestCase):
    def storage(self):return importlib.import_module('aat_api.deployments.storage')

    def test_write_returns_exact_file_hash_and_only_internal_uuid_key(self):
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            storage=self.storage();identity=uuid4();source=b'dag = None\n'
            artifact=storage.write(source,file_id=identity,root=Path(root))
            self.assertEqual(artifact.key,str(identity)+'.py')
            self.assertEqual((Path(root)/artifact.key).read_bytes(),source)
            self.assertEqual(artifact.sha256,hashlib.sha256(source).hexdigest())
            self.assertEqual(list(Path(root).iterdir()),[Path(root)/artifact.key])
            for invalid in ('../outside','/tmp/outside',str(identity)+'.py'):
                with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                    storage.write(source,file_id=invalid,root=Path(root))

    def test_interrupted_before_rename_keeps_previous_bytes_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as root:
            storage=self.storage();identity=uuid4();root=Path(root)
            artifact=storage.write(b'old',file_id=identity,root=root)
            with patch.object(storage.os,'replace',side_effect=OSError('injected rename failure')):
                with self.assertRaises(OSError):storage.write(b'new',file_id=identity,root=root)
            self.assertEqual((root/artifact.key).read_bytes(),b'old')
            self.assertEqual(len(list(root.iterdir())),1)

    def test_failure_after_rename_leaves_complete_file_for_reconciliation(self):
        with tempfile.TemporaryDirectory() as root:
            storage=self.storage();identity=uuid4();root=Path(root)
            original=storage.os.fsync;calls=[]
            def fail_directory(fd):
                calls.append(fd)
                if len(calls)==2:raise OSError('injected directory fsync failure')
                return original(fd)
            with patch.object(storage.os,'fsync',side_effect=fail_directory):
                with self.assertRaises(OSError):storage.write(b'complete-new',file_id=identity,root=root)
            self.assertEqual((root/(str(identity)+'.py')).read_bytes(),b'complete-new')
            self.assertEqual(len(list(root.iterdir())),1)

    def test_symlink_root_or_destination_is_rejected_without_touching_outside(self):
        with tempfile.TemporaryDirectory() as workspace:
            base=Path(workspace);outside=base/'outside';outside.mkdir();linked=base/'linked'
            linked.symlink_to(outside,target_is_directory=True)
            storage=self.storage();identity=uuid4()
            with self.assertRaises((OSError,ValueError)):storage.write(b'new',file_id=identity,root=linked)
            root=base/'dags';root.mkdir();victim=outside/'victim';victim.write_bytes(b'protected')
            (root/(str(identity)+'.py')).symlink_to(victim)
            with self.assertRaises((OSError,ValueError)):storage.write(b'new',file_id=identity,root=root)
            self.assertEqual(victim.read_bytes(),b'protected')
