"""T091: the real worker keeps heartbeats while maintenance runs separately."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest


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
                time.sleep(2.2)
                second=json.loads(heartbeat.read_text());self.assertGreater(second['timestamp'],first['timestamp'])
                self.assertEqual(child.poll(),None)
            finally:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        self.assertNotIn('worker_maintenance_blocked',Path('/tmp/aat-maintenance-worker.log').read_text())
