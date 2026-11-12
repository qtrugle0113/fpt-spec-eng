"""T091: the real worker keeps heartbeats while maintenance runs separately."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import psycopg


class WorkerMaintenanceTests(unittest.TestCase):
    def test_real_worker_runs_maintenance_without_delaying_heartbeat(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable worker fixture required')
        heartbeat=Path('/tmp/aat-worker-heartbeat.json');heartbeat.unlink(missing_ok=True)
        with open('/tmp/aat-maintenance-worker.log','w') as output:
            child=subprocess.Popen([sys.executable,'-m','aat_api.workers.main'],stdout=output,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    if child.poll() is not None:self.fail('Worker exited; inspect private fixture log')
                    if heartbeat.exists():break
                    time.sleep(.1)
                self.assertTrue(heartbeat.exists())
                first=json.loads(heartbeat.read_text());self.assertEqual(first['pid'],child.pid)
                # Dispatch renews its heartbeat every5seconds; this shared
                # regression fixture can still contain queued operations from
                # the preceding lifecycle tests. Stay well within the20second
                # readiness limit, and verify both durable and file evidence.
                with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as connection:
                    initial=connection.execute('SELECT heartbeat_at FROM worker_heartbeats WHERE owner_process_id=%s',(first['owner'],)).fetchone()[0]
                deadline=time.monotonic()+10
                second=first
                while time.monotonic()<deadline:
                    self.assertIsNone(child.poll(),'Worker exited during heartbeat verification')
                    second=json.loads(heartbeat.read_text())
                    if second['timestamp']>first['timestamp']:break
                    time.sleep(.1)
                self.assertGreater(second['timestamp'],first['timestamp'])
                self.assertEqual(second['pid'],child.pid)
                self.assertEqual(second['owner'],first['owner'])
                with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as connection:
                    current=connection.execute('SELECT heartbeat_at FROM worker_heartbeats WHERE owner_process_id=%s',(first['owner'],)).fetchone()[0]
                self.assertGreater(current,initial)
                self.assertEqual(child.poll(),None)
            finally:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        self.assertNotIn('worker_maintenance_blocked',Path('/tmp/aat-maintenance-worker.log').read_text())
