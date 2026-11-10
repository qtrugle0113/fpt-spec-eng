"""T079: real session-native lock ownership, contention and connection loss."""
import importlib
import unittest
from uuid import uuid4
from sqlalchemy import text,create_engine
from tests.etl import test_snapshot_staging as fixtures


class TargetSessionTests(unittest.TestCase):
    setUp=fixtures.SnapshotTests.setUp
    engine=fixtures.SnapshotTests.engine

    def run_case(self,kind,kill=False):
        try:module=importlib.import_module('aat_etl.loaders.session')
        except ModuleNotFoundError:raise AssertionError('T079 native session implementation missing') from None
        engine=self.engine(kind);schema='public' if kind=='postgres' else 'etl_test';table='lock_'+uuid4().hex
        alias=create_engine(engine.url.set(host='postgres') if kind=='postgres' else engine.url,hide_parameters=True)
        self.addCleanup(alias.dispose)
        with engine.begin() as c:c.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY)'))
        with module.TargetSession(engine,schema=schema,table=table,timeout=.2) as first:
            first.require_owned()
            with self.assertRaises(module.TargetBusy):
                with module.TargetSession(alias,schema=schema,table=table,timeout=.05):pass
            if kill:
                with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
                    if kind=='postgres':c.execute(text('SELECT pg_terminate_backend(:pid)'),{'pid':first.session_id})
                    else:c.execute(text('KILL CONNECTION '+str(first.session_id)))
                with self.assertRaises(module.SessionLost):first.require_owned()
        with module.TargetSession(engine,schema=schema,table=table,timeout=.2) as second:
            second.require_owned()
            self.assertEqual(second.physical_identity,first.physical_identity)
            if kill:self.assertNotEqual(second.session_id,first.session_id)

    def test_postgres_same_target_contention_and_release(self):self.run_case('postgres')
    def test_mysql_same_target_contention_and_release(self):self.run_case('mysql')
    def test_postgres_session_kill_requires_new_lock_not_reconnect(self):self.run_case('postgres',True)
    def test_mysql_session_kill_requires_new_lock_not_reconnect(self):self.run_case('mysql',True)
