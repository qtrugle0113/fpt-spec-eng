"""T104: reaped-child evidence, owner fences and terminal target projection."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from sqlalchemy import text
from tests.etl import test_runtime_adapter as adapters


class RuntimeLifecycleTests(unittest.TestCase):
    # Do not inherit/rerun the adapter suite; reuse only its fixture methods.
    setUp=adapters.RuntimeAdapterTests.setUp
    target=adapters.RuntimeAdapterTests.target
    wait=adapters.RuntimeAdapterTests.wait
    response=adapters.RuntimeAdapterTests.response
    scenario=adapters.RuntimeAdapterTests.scenario
    prepare=adapters.RuntimeAdapterTests.prepare
    def crash(self,binding,metadata,root,journal,mode=None):
        from aat_etl.resources import run_supervised
        with patch.dict(os.environ,{'AAT_FOUNDATION_TEST_DSN':metadata.url.set(drivername='postgresql').render_as_string(hide_password=False),'AAT_STAGING_ROOT':str(root)}):
            return run_supervised([sys.executable,'-m','tests.etl.runtime_fault_child',str(binding['binding_id']),str(journal),str(os.getpid()),*([mode] if mode else [])])

    def test_reaped_extraction_can_retry_same_once_intent(self):
        from aat_etl.runtime_task import _recover_interrupted_attempt
        binding,_,_,metadata=self.prepare(strategy='FULL_REFRESH')
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);directory=root/'.aat-runtime-journals';directory.mkdir(mode=0o700)
            journal=directory/(str(binding['binding_id'])+'.json')
            proof=self.crash(binding,metadata,root,journal)
            self.assertEqual(proof.exit_code,-9)
            from aat_api.workers.recovery import recover_pending
            import psycopg
            with metadata.connect() as c:before=c.scalar(text('SELECT dataset_id FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']})
            rows=recover_pending(lambda:psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']),root=root)
            current=next(row for row in rows if row['binding_id']==str(binding['binding_id']))
            self.assertEqual(current['reason'],'SOURCE_WRITER_TERMINATION_UNVERIFIED')
            with metadata.connect() as c:self.assertEqual(c.scalar(text('SELECT dataset_id FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}),before)
            self.assertEqual(_recover_interrupted_attempt(str(binding['binding_id']),root,journal,metadata),'RETRY_READY')
            with metadata.connect() as c:
                self.assertIsNone(c.scalar(text('SELECT dataset_id FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}))
                self.assertEqual(c.scalar(text('SELECT state FROM dataset_manifests WHERE execution_binding_id=:id'),{'id':binding['binding_id']}),'EXPIRED')
                self.assertEqual(c.scalar(text('SELECT state FROM replacement_authorizations WHERE id=:id'),{'id':binding['authorization_id']}),'RESERVED')
                self.assertEqual(c.scalar(text("SELECT count(*) FROM staging_reservations WHERE state<>'RELEASED' AND run_uuid=:run"),{'run':binding['run_uuid']}),0)
            self.assertEqual(self.runtime.run_binding(binding['binding_id'],root=root,metadata_engine=metadata).loaded_rows,2)

    def test_terminal_extraction_failure_closes_once_without_freeing_it(self):
        from aat_etl.runtime_lifecycle import finish_attempt
        binding,_,_,metadata=self.prepare(strategy='FULL_REFRESH')
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);journal=root/'private-journal.json';proof=self.crash(binding,metadata,root,journal)
            self.assertEqual(finish_attempt(binding['binding_id'],proof=proof,journal_path=journal,root=root,metadata_engine=metadata,terminal=True),'TERMINAL_VERIFIED')
            with metadata.connect() as c:
                self.assertEqual(c.scalar(text('SELECT state FROM replacement_authorizations WHERE id=:id'),{'id':binding['authorization_id']}),'CLOSED')

    def test_disk_complete_before_metadata_publication_is_never_reextracted(self):
        from aat_etl.runtime_lifecycle import finish_attempt
        binding,_,_,metadata=self.prepare()
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);journal=root/'private-journal.json';proof=self.crash(binding,metadata,root,journal,'publication')
            self.assertEqual(proof.exit_code,-9)
            manifests=list(root.rglob('manifest.json'));self.assertTrue(manifests)
            self.assertEqual(finish_attempt(binding['binding_id'],proof=proof,journal_path=journal,root=root,metadata_engine=metadata,terminal=False),'NEEDS_RECONCILIATION')
            self.assertTrue(all(path.exists() for path in manifests))
            from aat_etl.recovery.coordinator import NeedsReconciliation
            with self.assertRaises(NeedsReconciliation):self.runtime.run_binding(binding['binding_id'],root=root,metadata_engine=metadata)

    def test_owner_change_blocks_incomplete_cleanup(self):
        from aat_etl.runtime_lifecycle import finish_attempt
        binding,_,_,metadata=self.prepare()
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);journal=root/'private-journal.json';proof=self.crash(binding,metadata,root,journal)
            with metadata.begin() as c:c.execute(text("UPDATE runtime_leases SET owner_process_id='new-owner' WHERE binding_id=:id"),{'id':binding['binding_id']})
            self.assertEqual(finish_attempt(binding['binding_id'],proof=proof,journal_path=journal,root=root,metadata_engine=metadata,terminal=False),'NEEDS_RECONCILIATION')
            with metadata.connect() as c:
                self.assertEqual(c.scalar(text('SELECT state FROM dataset_manifests WHERE execution_binding_id=:id'),{'id':binding['binding_id']}),'INCOMPLETE')
                self.assertGreater(c.scalar(text("SELECT sum(reserved_bytes) FROM staging_reservations WHERE state<>'RELEASED' AND run_uuid=:run"),{'run':binding['run_uuid']}),0)
            # The alternate owner above is synthetic and never started a writer.
            # Restore this fixture's actual reaped owner only after checking the
            # refusal, so its protected 10GiB does not consume another test's quota.
            owner=json.loads(journal.read_text())['owner']
            with metadata.begin() as c:c.execute(text('UPDATE runtime_leases SET owner_process_id=:owner WHERE binding_id=:id'),{'id':binding['binding_id'],'owner':owner})
            self.assertEqual(finish_attempt(binding['binding_id'],proof=proof,journal_path=journal,root=root,metadata_engine=metadata,terminal=False),'RETRY_READY')

    def test_business_failure_keeps_complete_dataset_and_projects_committed_prefix(self):
        from aat_etl.runtime_task import run_bound,RuntimeTaskFailed
        binding,_,_,metadata=self.prepare(file_source=True,bad_tail=True)
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'AAT_FOUNDATION_TEST_DSN':metadata.url.set(drivername='postgresql').render_as_string(hide_password=False),'AAT_STAGING_ROOT':root}):
            with self.assertRaises(RuntimeTaskFailed):run_bound(binding['binding_id'])
            with metadata.connect() as c:
                self.assertEqual(c.execute(text('SELECT state,commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}).one(),('FAILED',False))
                self.assertEqual(c.execute(text('SELECT loaded_rows,failed_rows_nullable FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).one(),(2,None))
                self.assertEqual(c.scalar(text('SELECT state FROM dataset_manifests WHERE execution_binding_id=:id'),{'id':binding['binding_id']}),'COMPLETE')
