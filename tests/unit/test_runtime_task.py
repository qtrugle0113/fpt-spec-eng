"""Runtime process lifetime and SDK retry classification, without dataset output."""
import json
import io
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
from contextlib import redirect_stderr


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
            with self.subTest(reason=reason,code=code),tempfile.TemporaryDirectory() as root, \
                    patch.dict(os.environ,{'AAT_STAGING_ROOT':root}), \
                    patch('aat_etl.runtime_task.run_supervised',return_value=SupervisionResult(1,code,reason,0)):
                with self.assertRaises(error):run_bound(uuid4())

    def test_interrupted_attempt_is_reconciled_only_after_child_exit(self):
        from aat_etl.runtime_task import _recover_interrupted_attempt,RuntimeUnavailable
        identity=str(uuid4());pid=12345
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root)/'.aat-runtime-journals'
            directory.mkdir()
            journal=directory/(identity+'.json')
            journal.write_text(json.dumps({
                'binding_id':identity,'owner':str(pid)+':'+('a'*32),'pid':pid,
                'attempts':[],'terminal':False}))
            with patch('aat_etl.runtime_task._runtime_child_active',return_value=True), \
                    patch('aat_etl.runtime_lifecycle.finish_attempt') as finish:
                with self.assertRaises(RuntimeUnavailable):
                    _recover_interrupted_attempt(identity,Path(root),journal)
                finish.assert_not_called()
                self.assertTrue(journal.exists())
            with patch('aat_etl.runtime_task._runtime_child_active',return_value=False), \
                    patch('aat_etl.runtime_lifecycle.finish_attempt',return_value='RETRY_READY') as finish:
                self.assertEqual(_recover_interrupted_attempt(identity,Path(root),journal),'RETRY_READY')
                self.assertFalse(journal.exists())
                self.assertEqual(finish.call_args.kwargs['proof'].pid,pid)
                self.assertEqual(finish.call_args.kwargs['proof'].exit_code,-9)

    def test_terminal_child_outcome_is_preserved_in_interrupted_journal(self):
        from aat_etl.runtime_task import _recover_interrupted_attempt
        identity=str(uuid4());pid=12345
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root)/'.aat-runtime-journals'
            directory.mkdir()
            journal=directory/(identity+'.json')
            journal.write_text(json.dumps({
                'binding_id':identity,'owner':str(pid)+':'+('a'*32),'pid':pid,
                'attempts':[],'exit_code':21,'terminal':False}))
            with patch('aat_etl.runtime_task._runtime_child_active',return_value=False), \
                    patch('aat_etl.runtime_lifecycle.finish_attempt',return_value='TERMINAL_VERIFIED') as finish:
                self.assertEqual(_recover_interrupted_attempt(identity,Path(root),journal),'TERMINAL_VERIFIED')
                self.assertTrue(finish.call_args.kwargs['terminal'])
                self.assertFalse(journal.exists())

    def test_runtime_child_records_only_its_exit_classification(self):
        if sys.platform!='linux':self.skipTest('Atomic journal fsync requires Linux')
        from aat_etl.runtime_journal import AttemptJournal,record_exit
        identity=uuid4()
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root)/'.aat-runtime-journals'
            directory.mkdir(mode=0o700)
            journal=directory/(str(identity)+'.json')
            AttemptJournal(journal,identity,str(os.getpid())+':'+('c'*32),terminal=True)
            self.assertTrue(record_exit(journal,identity,20))
            self.assertEqual(json.loads(journal.read_text())['exit_code'],20)
            self.assertTrue(json.loads(journal.read_text())['terminal'])

    def test_child_validation_log_contains_location_but_not_exception_text(self):
        from aat_etl.runtime_child import main
        def fail(*args,**kwargs):
            raise ValueError('synthetic-secret-must-not-be-logged')
        output=io.StringIO()
        with patch('sys.argv',['runtime_child',str(uuid4()),'123']), \
                patch('aat_etl.runtime_child.parent_guard'), \
                patch('aat_etl.runtime.run_binding',side_effect=fail), \
                redirect_stderr(output):
            self.assertEqual(main(),21)
        self.assertIn('AAT_ETL_CHILD_FAILURE test_runtime_task.py:',output.getvalue())
        self.assertNotIn('synthetic-secret-must-not-be-logged',output.getvalue())

    def test_attempt_journal_does_not_overwrite_unreconciled_evidence(self):
        from aat_etl.runtime_journal import AttemptJournal
        with tempfile.TemporaryDirectory() as root:
            journal=Path(root)/'attempt.json'
            journal.write_text('{}')
            with self.assertRaisesRegex(ValueError,'unreconciled'):
                AttemptJournal(journal,uuid4(),str(os.getpid())+':'+('b'*32))

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
