"""T083/T086-T088: batch commits, retry/rerun and exact chosen conflict keys."""
from datetime import datetime,timezone
from decimal import Decimal
import importlib
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import text
from tests.etl import test_target_ledger as fixtures


class LoadPolicyTests(unittest.TestCase):
    setUp=fixtures.TargetLedgerTests.setUp
    engine=fixtures.TargetLedgerTests.engine
    isolated=fixtures.TargetLedgerTests.isolated

    def run_case(self,kind,strategy,partial=False):
        try:module=importlib.import_module('aat_etl.loaders.batches')
        except ModuleNotFoundError:raise AssertionError('Batch policy writer implementation missing') from None
        from aat_etl.loaders.ledger import ensure_support
        from aat_etl.loaders.session import TargetSession
        from aat_etl.readers.schema import inspect_table
        from aat_etl.staging.manager import StagingWriter
        from aat_etl.contracts.writer import PreparedDataset
        engine,schema=self.isolated(kind)
        name='policy_'+uuid4().hex
        with engine.begin() as c:
            c.execute(text(f'CREATE TABLE {name} (id INTEGER PRIMARY KEY, note VARCHAR(64), retained INTEGER DEFAULT 99, UNIQUE(note))'))
            if strategy=='UPSERT':c.execute(text(f"INSERT INTO {name} VALUES (1,'old',42)"))
        target=inspect_table(engine,schema=schema,table=name,used_columns=['id','note'])
        with engine.connect() as c:ledger=ensure_support(c,schema=schema,consent=True);c.commit()
        run=uuid4()
        with tempfile.TemporaryDirectory() as root:
            with StagingWriter(root,dag_id='policy',run_id=str(run),dataset_id=uuid4(),binding_sha256='a'*64,
                    source_schema_hash='b'*64,target_schema_hash=target.fingerprint,mapping_hash='c'*64,
                    columns=list(target.columns),source_snapshot_time=datetime.now(timezone.utc)) as writer:
                for values in ([(1,'a'),(2,'b'),(1,'duplicate')] if partial else [(1,'a'),(2,'b'),(3,'c')]):writer.append(values)
                manifest=writer.complete(validated_rows=3)
            dataset=PreparedDataset(manifest,writer.manifest_sha256,'a'*64,run,target.physical_identity,'b'*64,target.fingerprint,'c'*64,3,3)
            with TargetSession(engine,schema=schema,table=name) as session:
                if partial:
                    with self.assertRaises(ValueError):module.write_batches(dataset,session,ledger,strategy=strategy,batch_rows=2)
                    session.connection.rollback()
                    self.assertEqual(session.connection.scalar(text(f'SELECT count(*) FROM {name}')),2)
                else:
                    self.assertEqual(module.write_batches(dataset,session,ledger,strategy=strategy,batch_rows=2,conflict_keys=['id'] if strategy=='UPSERT' else []),3)
            if not partial:
                with TargetSession(engine,schema=schema,table=name) as session:
                    self.assertEqual(module.write_batches(dataset,session,ledger,strategy=strategy,batch_rows=2,conflict_keys=['id'] if strategy=='UPSERT' else []),3)
                with engine.connect() as c:
                    self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {name}')),3)
                    if strategy=='UPSERT':self.assertEqual(c.scalar(text(f'SELECT retained FROM {name} WHERE id=1')),42)

    def test_postgres_append_retry_skips_verified_batches(self):self.run_case('postgres','APPEND')
    def test_mysql_append_retry_skips_verified_batches(self):self.run_case('mysql','APPEND')
    def test_postgres_append_unique_failure_preserves_prior_batch(self):self.run_case('postgres','APPEND',True)
    def test_mysql_append_unique_failure_preserves_prior_batch(self):self.run_case('mysql','APPEND',True)
    def test_postgres_upsert_preserves_unmapped_values_and_retry_is_stable(self):self.run_case('postgres','UPSERT')
    def test_mysql_upsert_preserves_unmapped_values_and_retry_is_stable(self):self.run_case('mysql','UPSERT')

    def edge_case(self,kind,case):
        from aat_etl.loaders.batches import write_batches
        from aat_etl.loaders.ledger import ensure_support
        from aat_etl.loaders.session import TargetSession
        from aat_etl.readers.schema import inspect_table
        from aat_etl.staging.manager import StagingWriter
        from aat_etl.contracts.writer import PreparedDataset
        engine,schema=self.isolated(kind);name='edge_'+uuid4().hex
        with engine.begin() as c:
            if case=='rerun':c.execute(text(f'CREATE TABLE {name} (id INTEGER, note VARCHAR(64))'))
            elif case=='keyonly':
                c.execute(text(f"CREATE TABLE {name} (id INTEGER, part INTEGER, note VARCHAR(64) DEFAULT 'kept', PRIMARY KEY(id,part))"))
                c.execute(text(f"INSERT INTO {name} VALUES (1,1,'original')"))
            else:
                c.execute(text(f'CREATE TABLE {name} (id INTEGER PRIMARY KEY, note VARCHAR(64) UNIQUE)'))
                c.execute(text(f"INSERT INTO {name} VALUES (1,'a'),(2,'b')"))
        columns=['id','part'] if case=='keyonly' else ['id','note']
        target=inspect_table(engine,schema=schema,table=name,used_columns=columns)
        with engine.connect() as c:ledger=ensure_support(c,schema=schema,consent=True);c.commit()
        strategy='APPEND' if case=='rerun' else 'UPSERT'
        for _ in range(3 if case in ('rerun','keyonly') else 1):
            run=uuid4();values=[(1,1),(1,2)] if case=='keyonly' else [(1,'b')] if case=='collision' else [(1,'a'),(2,'b')]
            with tempfile.TemporaryDirectory() as root:
                with StagingWriter(root,dag_id='edge',run_id=str(run),dataset_id=uuid4(),binding_sha256='a'*64,
                    source_schema_hash='b'*64,target_schema_hash=target.fingerprint,mapping_hash='c'*64,
                    columns=list(target.columns),source_snapshot_time=datetime.now(timezone.utc)) as writer:
                    for value in values:writer.append(value)
                    manifest=writer.complete(validated_rows=len(values))
                dataset=PreparedDataset(manifest,writer.manifest_sha256,'a'*64,run,target.physical_identity,'b'*64,target.fingerprint,'c'*64,len(values),len(values))
                with TargetSession(engine,schema=schema,table=name) as session:
                    if case=='collision':
                        with self.assertRaises(ValueError):write_batches(dataset,session,ledger,strategy=strategy,conflict_keys=['id'])
                    else:write_batches(dataset,session,ledger,strategy=strategy,conflict_keys=columns if case=='keyonly' else [])
        with engine.connect() as c:
            self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {name}')),6 if case=='rerun' else 2)
            if case=='collision':self.assertEqual(c.scalar(text(f'SELECT note FROM {name} WHERE id=1')),'a')
            if case=='keyonly':self.assertEqual(c.scalar(text(f'SELECT note FROM {name} WHERE id=1 AND part=1')),'original')

    def test_new_append_run_can_duplicate_without_unique_constraint(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.edge_case(kind,'rerun')

    def test_key_only_composite_upsert_is_stable_across_three_runs(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.edge_case(kind,'keyonly')

    def test_secondary_unique_collision_never_updates_wrong_row(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.edge_case(kind,'collision')
