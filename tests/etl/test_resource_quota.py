"""T076: atomic real-metadata reservations and the actual 512 MiB RSS limit."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
import errno
import shutil
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
        # Remove only this method's TemporaryDirectory, after every writer has
        # exited; no persistent staging or external paths are involved.
        self.temp.cleanup()
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

    def writer(self,run,size=4096):
        staging=implementation('staging.manager')
        return staging.StagingWriter(self.temp.name,dag_id='quota-test',run_id=str(run),dataset_id=uuid4(),
            binding_sha256='a'*64,source_schema_hash='b'*64,target_schema_hash='c'*64,mapping_hash='d'*64,
            columns=[dict(name='note',logical_type='text',nullable=False)],source_snapshot_time=datetime.now(timezone.utc),
            quota=self.manager,run_uuid=run,reservation_bytes=size)

    def test_writer_accounts_manifest_and_retains_protected_bytes(self):
        run=uuid4()
        with self.writer(run) as writer:
            writer.append(['Unicode \U0001f680']);manifest=writer.complete()
        self.owned.append(writer.reservation_id)
        actual=sum(p.stat().st_size for p in Path(manifest).parent.rglob('*') if p.is_file())
        self.assertEqual(self.manager.usage(run)['run_reserved_bytes'],actual)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(text('SELECT state FROM staging_reservations WHERE id=:id'),{'id':writer.reservation_id}),'PROTECTED')

    def test_failed_write_keeps_reservation_and_never_publishes_manifest(self):
        run=uuid4()
        with self.assertRaises(OSError):
            with self.writer(run) as writer:
                writer.append(['first'])
                with patch('aat_etl.staging.manager.os.fsync',side_effect=OSError(errno.ENOSPC,'Synthetic disk full')):
                    writer.complete()
        self.owned.append(writer.reservation_id)
        self.assertFalse((writer.path/'manifest.json').exists())
        self.assertEqual(self.manager.usage(run)['run_reserved_bytes'],4096)

    def test_reservation_overflow_cannot_publish_even_if_caller_catches_error(self):
        run=uuid4()
        with self.writer(run,size=64) as writer:
            with self.assertRaises(ValueError):writer.append(['x'*100])
            with self.assertRaises(ValueError):writer.complete()
        self.owned.append(writer.reservation_id)
        self.assertFalse((writer.path/'manifest.json').exists())

    def test_free_disk_reserve_rejects_without_allocating_metadata(self):
        run=uuid4();before=self.manager.usage(run)
        disk=shutil.disk_usage(self.temp.name)
        with patch('aat_etl.staging.quota.shutil.disk_usage',return_value=type(disk)(disk.total,disk.used,1024**3)):
            with self.assertRaises(self.quota.QuotaExceeded):self.reserve(run,1)
        self.assertEqual(self.manager.usage(run),before)


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
        print(f'RSS evidence: peak={result.peak_rss_bytes}, budget={result.memory_budget_bytes}, reason={result.reason}, exit={result.exit_code}')

    def test_normal_child_completes_without_false_memory_failure(self):
        resources=implementation('resources');result=resources.run_supervised([sys.executable,'-c','pass'])
        self.assertEqual(result.exit_code,0);self.assertEqual(result.reason,'COMPLETED')
