"""T095: SIGKILL bypasses finally; quota and disk evidence remain protected."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text


class StorageFailureTests(unittest.TestCase):
    def test_sigkill_rolls_back_open_target_transaction_without_releasing_quota(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable crash database required')
        from aat_etl.loaders.session import TargetSession,TargetBusy
        from aat_etl.recovery.coordinator import require_old_session_finished
        from aat_etl.staging.quota import QuotaManager
        engine=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(engine.dispose);run=uuid4();table='crash_'+run.hex
        with engine.begin() as c:
            c.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY)'));c.execute(text(f'INSERT INTO {table} VALUES (42)'))
        with tempfile.TemporaryDirectory(prefix='aat-crash-') as root:
            child=subprocess.Popen([sys.executable,'-m','tests.etl.storage_crash_worker',root,table,str(run)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                ready=Path(root)/'ready.json';deadline=time.monotonic()+15
                while not ready.exists() and time.monotonic()<deadline:
                    if child.poll() is not None:self.fail('Crash helper exited before the controlled kill point')
                    time.sleep(.05)
                self.assertTrue(ready.exists());proof=json.loads(ready.read_text())
                with self.assertRaises(TargetBusy):
                    with TargetSession(engine,schema='public',table=table,timeout=.05):pass
                child.kill();child.wait(timeout=5);self.assertEqual(child.returncode,-9)
                with TargetSession(engine,schema='public',table=table,timeout=2) as current:
                    require_old_session_finished(current,proof['session_id'])
                    self.assertEqual(list(current.connection.scalars(text(f'SELECT id FROM {table}'))),[42])
                self.assertFalse(Path(proof['manifest']).exists());self.assertTrue(list(Path(root).rglob('*.part')))
                quota=QuotaManager(engine,root);self.assertEqual(quota.usage(run)['run_reserved_bytes'],4096)
                with engine.connect() as c:owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':run}).scalars())
                import shutil
                for path in Path(root).iterdir():
                    if path.is_dir():shutil.rmtree(path)
                    else:path.unlink()
                for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)
            finally:
                if child.poll() is None:child.kill();child.wait()
