"""T095: real >1 GiB transfer, disk allocation and supervisor-measured RSS."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text


class DiskStagingStressTests(unittest.TestCase):
    def test_dataset_larger_than_one_gib_and_worker_budget_uses_verified_disk(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable stress database required')
        from aat_etl.resources import run_supervised
        from aat_etl.staging.quota import QuotaManager
        engine=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(engine.dispose);run=uuid4()
        with tempfile.TemporaryDirectory(prefix='aat-disk-stress-') as root:
            result=run_supervised([sys.executable,'-m','tests.stress.disk_worker',root,str(run)])
            self.assertEqual(result.reason,'COMPLETED');self.assertEqual(result.exit_code,0)
            self.assertGreater(result.peak_rss_bytes,0);self.assertLessEqual(result.peak_rss_bytes,512*1024**2)
            evidence=json.loads((Path(root)/'result.json').read_text())
            self.assertGreater(evidence['target_bytes'],1024**3)
            self.assertGreater(evidence['batch_commits'],20)
            self.assertEqual(evidence['target_rows'],evidence['rows']);self.assertEqual(evidence['loaded_rows'],evidence['rows'])
            self.assertEqual(evidence['bad_payload_rows'],0)
            self.assertEqual(evidence['id_sum'],evidence['rows']*(evidence['rows']+1)//2)
            self.assertGreater(evidence['staging']['staging_payload_bytes'],2*1024**3)
            self.assertGreater(evidence['staging']['staging_allocated_bytes'],2*1024**3)
            # Read the target independently from the supervisor child.
            with engine.connect() as c:
                table='stress_target_'+run.hex
                self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {table}')),evidence['rows'])
                owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':run}).scalars())
            print('stress_rss_evidence '+json.dumps(dict(peak_rss_bytes=result.peak_rss_bytes,memory_budget_bytes=result.memory_budget_bytes,
                dataset_bytes=evidence['target_bytes'],batch_commits=evidence['batch_commits'],allocated_bytes=evidence['staging']['staging_allocated_bytes'])),flush=True)
            # All work is complete and the child has been reaped. Only this
            # fixture's directory is removed before quota release.
            import shutil
            for path in Path(root).iterdir():
                if path.is_dir():shutil.rmtree(path)
                else:path.unlink()
            quota=QuotaManager(engine,root)
            for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)
