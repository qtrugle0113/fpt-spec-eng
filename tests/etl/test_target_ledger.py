"""T080: exact support signatures and atomic target DML/markers on both DBs."""
import importlib
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
from tests.etl import test_snapshot_staging as fixtures


class TargetLedgerTests(unittest.TestCase):
    setUp=fixtures.SnapshotTests.setUp
    engine=fixtures.SnapshotTests.engine

    def isolated(self,kind):
        original=self.engine(kind)
        admin=create_engine(original.url.set(username='root') if kind=='mysql' else original.url,hide_parameters=True)
        self.addCleanup(admin.dispose)
        database='ledger_'+uuid4().hex
        with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as c:c.execute(text(f'CREATE DATABASE {database}'))
        engine=create_engine(admin.url.set(database=database),hide_parameters=True)
        def cleanup():
            engine.dispose()
            with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as c:c.execute(text(f'DROP DATABASE {database}'))
        self.addCleanup(cleanup)
        schema='public' if kind=='postgres' else database
        with engine.begin() as c:c.execute(text('CREATE TABLE output_rows (id INTEGER PRIMARY KEY)'))
        return engine,schema

    def ledger(self):
        try:return importlib.import_module('aat_etl.loaders.ledger')
        except ModuleNotFoundError:raise AssertionError('T080 ledger implementation missing') from None

    def run_case(self,kind):
        module=self.ledger();engine,schema=self.isolated(kind)
        with engine.connect() as c:
            with self.assertRaises(ValueError):module.ensure_support(c,schema=schema,consent=False)
            c.rollback()
            ledger=module.ensure_support(c,schema=schema,consent=True);c.commit()
            marker=module.BatchMarker('e'*64,uuid4(),'a'*64,0,'b'*64,1,'c'*64,'APPEND')
            with c.begin():
                c.execute(text('INSERT INTO output_rows VALUES (1)'));ledger.record_batch(c,marker)
            self.assertTrue(ledger.verify_batch(c,marker));c.rollback()
            from dataclasses import replace
            with self.assertRaises(ValueError):ledger.verify_batch(c,replace(marker,payload_sha='d'*64))
            c.rollback()
            with self.assertRaises(RuntimeError):
                with c.begin():
                    c.execute(text('INSERT INTO output_rows VALUES (2)'))
                    ledger.record_batch(c,replace(marker,batch_index=1));raise RuntimeError('Injected rollback')
            self.assertFalse(ledger.verify_batch(c,replace(marker,batch_index=1)));c.rollback()
            self.assertEqual(c.scalar(text('SELECT count(*) FROM output_rows')),1);c.rollback()
            final=module.RunMarker(marker.target_identity,marker.run_uuid,marker.dataset_sha,marker.binding_sha,1,None)
            with c.begin():ledger.record_run(c,final)
            self.assertTrue(ledger.verify_run(c,final));c.rollback()
            signature=ledger.version
            with c.begin():c.execute(signature.update().values(signature='wrong'))
            with self.assertRaises(ValueError):module.ensure_support(c,schema=schema,consent=True)

    def test_postgres_markers_commit_and_rollback_with_target_dml(self):self.run_case('postgres')
    def test_mysql_markers_commit_and_rollback_with_target_dml(self):self.run_case('mysql')

    def test_postgres_existing_support_name_collision_is_not_adopted(self):
        module=self.ledger();engine,schema=self.isolated('postgres')
        with engine.begin() as c:
            c.execute(text('CREATE SCHEMA _aat_control'))
            c.execute(text('CREATE TABLE _aat_control.batch_commits (arbitrary INTEGER)'))
        with engine.connect() as c,self.assertRaises(ValueError):module.ensure_support(c,schema=schema,consent=True)
