"""T078: target-typed disk scratch detects global keys before any target DML."""
import importlib
import unittest
from uuid import uuid4
from sqlalchemy import text,event,create_engine
from tests.etl import test_snapshot_staging as fixtures


class DatasetValidationTests(unittest.TestCase):
    setUp = fixtures.SnapshotTests.setUp
    engine = fixtures.SnapshotTests.engine

    def implementation(self):
        try:return importlib.import_module('aat_etl.mapping.validation')
        except ModuleNotFoundError:raise AssertionError('T078 validation implementation missing') from None

    def setup_target(self,kind):
        engine=self.engine(kind);name='validate_'+uuid4().hex
        schema='public' if kind=='postgres' else 'etl_test'
        collation='COLLATE utf8mb4_0900_ai_ci' if kind=='mysql' else ''
        with engine.begin() as c:
            c.execute(text(f'CREATE TABLE {name} (code VARCHAR(64) {collation} NOT NULL, amount DECIMAL(12,2), PRIMARY KEY(code))'))
            c.execute(text(f"INSERT INTO {name} VALUES ('original',12.34)"))
        return engine,schema,name

    def validate(self,kind,values,**options):
        module=self.implementation();engine,schema,table=self.setup_target(kind)
        try:
            with engine.connect() as c:
                return module.validate_rows(c,schema=schema,table=table,columns=['code','amount'],
                    rows=iter(values),conflict_keys=['code'],**options)
        finally:
            with engine.connect() as c:
                self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {table}')),1)
                self.assertEqual(c.scalar(text(f"SELECT code FROM {table}")),'original')

    def test_postgres_distinct_values_validate_on_disk_without_target_writes(self):
        from decimal import Decimal
        result=self.validate('postgres',({'code':str(i),'amount':Decimal('12.34')} for i in range(2201)))
        self.assertEqual(result.validated_rows,2201);self.assertGreater(result.scratch_bytes,0)

    def test_mysql_case_insensitive_duplicate_across_many_batches_is_rejected(self):
        values=[{'code':'Alpha','amount':None}]+[{'code':'v'+str(i),'amount':None} for i in range(2200)]+[{'code':'alpha','amount':None}]
        with self.assertRaises(ValueError):self.validate('mysql',values)

    def test_postgres_duplicate_across_many_batches_is_rejected(self):
        values=[{'code':str(i),'amount':None} for i in range(2201)]+[{'code':'0','amount':None}]
        with self.assertRaises(ValueError):self.validate('postgres',values)

    def test_null_key_is_rejected_on_both_databases(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.validate(kind,[{'code':None,'amount':None}])

    def test_row_and_byte_limits_fail_before_target_writes(self):
        for kind in ('postgres','mysql'):
            for limits in ({'max_rows':1},{'max_bytes':1}):
                with self.subTest(kind=kind,limits=limits),self.assertRaises(ValueError):
                    self.validate(kind,[{'code':'a','amount':None},{'code':'b','amount':None}],**limits)

    def test_nonunique_conflict_key_is_rejected(self):
        module=self.implementation();engine,schema,table=self.setup_target('postgres')
        with engine.connect() as c,self.assertRaises(ValueError):
            module.validate_rows(c,schema=schema,table=table,columns=['code','amount'],rows=[],conflict_keys=['amount'])

    def test_mysql_distinct_keys_and_exact_decimals_validate(self):
        from decimal import Decimal
        result=self.validate('mysql',[{'code':'A','amount':Decimal('12.34')},{'code':'B','amount':None}])
        self.assertEqual(result.validated_rows,2);self.assertGreater(result.scratch_bytes,0)

    def test_mysql_scratch_physical_size_is_below_charged_bound(self):
        module=self.implementation();engine,schema,table=self.setup_target('mysql')
        monitor=create_engine(engine.url.set(username='root'),hide_parameters=True);self.addCleanup(monitor.dispose)
        measured=[]
        def size_probe(connection,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO aat_validate_'):
                owner=connection.connection.driver_connection.thread_id()
                with monitor.connect() as admin:
                    measured.append(int(admin.scalar(text('SELECT COALESCE(SUM(SIZE),0) FROM INFORMATION_SCHEMA.INNODB_SESSION_TEMP_TABLESPACES WHERE ID=:owner'),{'owner':owner})))
        event.listen(engine,'after_cursor_execute',size_probe)
        try:
            with engine.connect() as c:
                result=module.validate_rows(c,schema=schema,table=table,columns=['code','amount'],
                    rows=({'code':str(i),'amount':None} for i in range(3001)),conflict_keys=['code'])
        finally:event.remove(engine,'after_cursor_execute',size_probe)
        self.assertTrue(measured);self.assertGreater(max(measured),0)
        self.assertLessEqual(max(measured),result.scratch_bytes)
        print(f'MySQL scratch: measured={max(measured)}, charged={result.scratch_bytes}, rows={result.validated_rows}')
