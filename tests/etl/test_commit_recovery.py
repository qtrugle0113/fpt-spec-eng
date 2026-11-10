"""T083/T090: actual target commit followed by a synthetic lost response."""
from datetime import datetime,timezone
import importlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import text
from tests.etl import test_target_ledger as fixtures


class CommitRecoveryTests(unittest.TestCase):
    setUp=fixtures.TargetLedgerTests.setUp
    engine=fixtures.TargetLedgerTests.engine
    isolated=fixtures.TargetLedgerTests.isolated

    def run_case(self,kind,automatic=False,lost_volume=False):
        try:recovery=importlib.import_module('aat_etl.recovery.coordinator')
        except ModuleNotFoundError:raise AssertionError('T090 commit recovery implementation missing') from None
        from aat_etl.loaders.batches import write_batches,CommitUncertain
        from aat_etl.loaders.session import TargetSession
        from aat_etl.loaders.ledger import ensure_support
        from aat_etl.readers.schema import inspect_table
        from aat_etl.staging.manager import StagingWriter
        from aat_etl.contracts.writer import PreparedDataset
        engine,schema=self.isolated(kind)
        target=inspect_table(engine,schema=schema,table='output_rows',used_columns=['id'])
        with engine.connect() as c:ledger=ensure_support(c,schema=schema,consent=True);c.commit()
        run=uuid4()
        with tempfile.TemporaryDirectory() as root:
            with StagingWriter(root,dag_id='recovery',run_id=str(run),dataset_id=uuid4(),binding_sha256='a'*64,
                source_schema_hash='b'*64,target_schema_hash=target.fingerprint,mapping_hash='c'*64,
                columns=list(target.columns),source_snapshot_time=datetime.now(timezone.utc)) as writer:
                for i in (1,2,3):writer.append([i])
                manifest=writer.complete(validated_rows=3)
            dataset=PreparedDataset(manifest,writer.manifest_sha256,'a'*64,run,target.physical_identity,'b'*64,target.fingerprint,'c'*64,3,3)
            if automatic:
                calls=[];delays=[]
                def attempt(dataset,session,ledger):
                    calls.append(1)
                    if len(calls)>1:return write_batches(dataset,session,ledger,strategy='APPEND',batch_rows=2)
                    driver=session.connection.connection.driver_connection;commit=driver.commit
                    def lost_first():
                        commit()
                        if kind=='postgres':
                            import psycopg
                            raise psycopg.OperationalError('Synthetic first COMMIT response lost')
                        import pymysql
                        raise pymysql.OperationalError(2013,'Synthetic first COMMIT response lost')
                    with patch.object(driver,'commit',side_effect=lost_first):return write_batches(dataset,session,ledger,strategy='APPEND',batch_rows=2)
                loaded=recovery.execute_with_recovery(dataset,
                    session_factory=lambda:TargetSession(engine,schema=schema,table='output_rows'),
                    ledger_factory=lambda c:ensure_support(c,schema=schema,consent=False),writer=attempt,strategy='APPEND',
                    retry_count=1,retry_delay=0,batch_rows=2,sleep=delays.append)
                self.assertEqual(loaded,3);self.assertEqual(len(calls),2);self.assertEqual(delays,[0])
                with engine.connect() as c:self.assertEqual(list(c.scalars(text('SELECT id FROM output_rows ORDER BY id'))),[1,2,3])
                return
            with TargetSession(engine,schema=schema,table='output_rows') as old:
                old_id=old.session_id;driver=old.connection.connection.driver_connection;commit=driver.commit
                def lost():
                    commit()
                    if kind=='postgres':
                        import psycopg
                        raise psycopg.OperationalError('Synthetic response lost after actual target COMMIT')
                    import pymysql
                    raise pymysql.OperationalError(2013,'Synthetic response lost after actual target COMMIT')
                with patch.object(driver,'commit',side_effect=lost),self.assertRaises(CommitUncertain):
                    write_batches(dataset,old,ledger,strategy='APPEND',batch_rows=2)
            with TargetSession(engine,schema=schema,table='output_rows') as current:
                if lost_volume:
                    original=dataset.manifest.parent.parent;backup=Path(root)/'lost-volume-owned'
                    original.rename(backup)
                    with self.assertRaises(recovery.NeedsReconciliation):
                        recovery.reconcile_batches(dataset,current,ledger,old_session_id=old_id,strategy='APPEND',batch_rows=2)
                    current.connection.rollback()
                    self.assertEqual(current.connection.scalar(text('SELECT count(*) FROM output_rows')),2);current.connection.rollback()
                    backup.rename(original)
                decision=recovery.reconcile_batches(dataset,current,ledger,old_session_id=old_id,strategy='APPEND',batch_rows=2)
                self.assertEqual(decision.verified_rows,2)
                self.assertEqual(decision.state,'RESUME_VERIFIED_DATASET')
                write_batches(dataset,current,ledger,strategy='APPEND',batch_rows=2)
            with engine.connect() as c:self.assertEqual(list(c.scalars(text('SELECT id FROM output_rows ORDER BY id'))),[1,2,3])

    def test_postgres_commit_loss_reconciles_marker_before_retry(self):self.run_case('postgres')
    def test_mysql_commit_loss_reconciles_marker_before_retry(self):self.run_case('mysql')

    def test_bounded_retry_preserves_the_same_dataset_on_both_databases(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,True)

    def test_missing_staging_after_partial_commit_blocks_until_original_files_return(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,lost_volume=True)
