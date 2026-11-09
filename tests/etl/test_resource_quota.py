"""T076: atomic real-metadata reservations and the actual 512 MiB RSS limit."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url


def implementation(name):
    try:return importlib.import_module('aat_etl.'+name)
    except ModuleNotFoundError as error:
        if error.name.startswith('aat_etl'):raise AssertionError('T076 implementation missing: '+name) from None
        raise


class QuotaTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        self.quota=implementation('staging.quota')
        self.engine=create_engine(make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg'),hide_parameters=True)
        self.addCleanup(self.engine.dispose)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.manager=self.quota.QuotaManager(self.engine,Path(self.temp.name))
        # Each method owns every allocation and explicitly proves its fixture has
        # no writer/artifact before releasing. Never delete reservation evidence.
        self.owned=[];self.addCleanup(self.release_owned)

    def release_owned(self):
        for identity in self.owned:self.manager.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)

    def reserve(self,run,size):
        identity=self.manager.reserve(run,uuid4(),size);self.owned.append(identity);return identity

    def test_per_run_10gib_boundary_is_atomic_under_concurrency(self):
        run=uuid4();self.reserve(run,9*1024**3)
        def attempt(_):
            try:return self.reserve(run,1024**3)
            except self.quota.QuotaExceeded:return None
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(attempt,range(2)))
        self.assertEqual(sum(v is not None for v in outcomes),1)
        self.assertEqual(self.manager.usage(run)['run_reserved_bytes'],10*1024**3)

    def test_global_20gib_counts_protected_and_active_allocations(self):
        first=self.reserve(uuid4(),10*1024**3);self.manager.protect(first)
        self.reserve(uuid4(),10*1024**3)
        with self.assertRaises(self.quota.QuotaExceeded):self.reserve(uuid4(),1)
        self.assertEqual(self.manager.usage(uuid4())['global_reserved_bytes'],20*1024**3)
        with self.assertRaises(ValueError):self.manager.release_after_cleanup(first,writer_stopped=False,artifacts_removed=True,reconciled=True)
        with self.assertRaises(ValueError):self.manager.release_after_cleanup(first,writer_stopped=True,artifacts_removed=False,reconciled=True)

    def test_idempotent_reservation_and_release_preserve_evidence(self):
        run=uuid4();attempt=uuid4();identity=self.manager.reserve(run,attempt,1234);self.owned.append(identity)
        self.assertEqual(self.manager.reserve(run,attempt,1234),identity)
        with self.assertRaises(ValueError):self.manager.reserve(run,attempt,1235)
        self.manager.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)
        with self.engine.connect() as c:self.assertEqual(c.scalar(text('SELECT state FROM staging_reservations WHERE id=:id'),{'id':identity}),'RELEASED')
        self.assertEqual(self.manager.usage(run)['run_reserved_bytes'],0)
        with self.assertRaises(ValueError):self.manager.reserve(run,attempt,1234)


class RSSSupervisionTests(unittest.TestCase):
    def test_actual_512mib_process_is_stopped_before_container_oom(self):
        resources=implementation('resources')
        command=[sys.executable,'-c',"import time; blocks=[]\nfor i in range(700):\n blocks.append(bytearray(1024*1024)); time.sleep(.003)\ntime.sleep(30)"]
        result=resources.run_supervised(command)
        self.assertEqual(result.reason,'MEMORY_BUDGET_EXCEEDED')
        self.assertGreater(result.peak_rss_bytes,450*1024**2)
        self.assertLess(result.peak_rss_bytes,700*1024**2)
        self.assertEqual(result.memory_budget_bytes,512*1024**2)
        self.assertNotEqual(result.exit_code,0)
        self.assertFalse(Path('/proc') .joinpath(str(result.pid)).exists())

    def test_normal_child_completes_without_false_memory_failure(self):
        resources=implementation('resources');result=resources.run_supervised([sys.executable,'-c','pass'])
        self.assertEqual(result.exit_code,0);self.assertEqual(result.reason,'COMPLETED')
