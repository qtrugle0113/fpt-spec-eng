"""Runtime process lifetime and SDK retry classification, without dataset output."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4
from unittest.mock import patch


class RuntimeTaskTests(unittest.TestCase):
    def test_post_reap_metadata_outage_keeps_reconciliation_pending(self):
        from aat_etl.runtime_lifecycle import finish_attempt
        from aat_etl.resources import SupervisionResult
        with patch('aat_etl.runtime_lifecycle.create_app_engine',side_effect=OSError('Synthetic private config outage')):
            self.assertEqual(finish_attempt(uuid4(),proof=SupervisionResult(123,20,'PROCESS_FAILED',0),journal_path='/missing-private-journal'),'NEEDS_RECONCILIATION')

    def test_business_and_memory_failures_do_not_request_replay(self):
        from aat_etl.runtime_task import run_bound,RuntimeTaskFailed
        from aat_etl.resources import SupervisionResult
        from aat_etl.runtime import RuntimeUnavailable
        for reason,code,error in [('PROCESS_FAILED',21,RuntimeTaskFailed),('MEMORY_BUDGET_EXCEEDED',-9,RuntimeTaskFailed),('PROCESS_FAILED',20,RuntimeUnavailable)]:
            with self.subTest(reason=reason,code=code),patch('aat_etl.runtime_task.run_supervised',return_value=SupervisionResult(1,code,reason,0)):
                with self.assertRaises(error):run_bound(uuid4())

    def test_child_is_killed_when_its_supervisor_dies(self):
        if sys.platform!='linux':self.skipTest('Linux parent-death guarantee')
        with tempfile.TemporaryDirectory() as root:
            record=Path(root)/'child.pid'
            child="from aat_etl.runtime_child import parent_guard; import os,pathlib,sys,time; parent_guard(int(sys.argv[1])); pathlib.Path(sys.argv[2]).write_text(str(os.getpid())); time.sleep(60)"
            parent="import os,subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],str(os.getpid()),sys.argv[2]]); time.sleep(60)"
            process=subprocess.Popen([sys.executable,'-c',parent,child,str(record)])
            child_pid=None
            try:
                deadline=time.monotonic()+10
                while not record.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(record.exists(),'Child guard did not start')
                child_pid=int(record.read_text());process.kill();process.wait(timeout=5)
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    status=Path(f'/proc/{child_pid}/stat')
                    if not status.exists() or status.read_text().split()[2]=='Z':break
                    time.sleep(.02)
                else:self.fail('ETL child survived supervisor death')
            finally:
                if process.poll() is None:process.kill()
                process.wait(timeout=5)
                if child_pid:
                    try:os.kill(child_pid,signal.SIGKILL)
                    except ProcessLookupError:pass
