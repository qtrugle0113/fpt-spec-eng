"""T074: actual schema drift and physical aliases, without target mutation."""
import importlib
import os
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url,URL


class SchemaPreflightTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        try:self.schema=importlib.import_module('aat_etl.readers.schema')
        except ModuleNotFoundError as error:
            if error.name.startswith('aat_etl'):raise AssertionError('T074 schema preflight implementation missing') from None
            raise
        self.pg=make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg')

    def fixture(self,kind):
        url=self.pg if kind=='postgres' else URL.create('mysql+pymysql',username='aat_test',password=self.pg.password,host='mysql',database='etl_test')
        engine=create_engine(url,hide_parameters=True);alias=create_engine(url,hide_parameters=True)
        self.addCleanup(engine.dispose);self.addCleanup(alias.dispose)
        schema='public' if kind=='postgres' else 'etl_test';name='schema_'+uuid4().hex
        with engine.begin() as connection:
            connection.execute(text(f'CREATE TABLE {name} (id INTEGER NOT NULL PRIMARY KEY, amount DECIMAL(30,6), note VARCHAR(40))'))
            connection.execute(text(f"INSERT INTO {name} VALUES (1,1,'retained')"))
        return engine,alias,schema,name

    def alias(self,kind):
        engine,alias,schema,name=self.fixture(kind)
        left=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        right=self.schema.inspect_table(alias,schema=schema,table=name,used_columns=['id','amount'])
        self.assertEqual(left.physical_identity,right.physical_identity)
        self.assertEqual(left.fingerprint,right.fingerprint)
        with self.assertRaises(ValueError):self.schema.preflight(left,right,expected_source_hash=left.fingerprint,
            expected_target_hash=right.fingerprint,expected_source_identity=left.physical_identity,expected_target_identity=right.physical_identity)
        with engine.connect() as c:self.assertEqual(c.scalar(text(f'SELECT COUNT(*) FROM {name}')),1)

    def test_postgres_connection_aliases_cannot_read_and_write_same_table(self):self.alias('postgres')
    def test_mysql_connection_aliases_cannot_read_and_write_same_table(self):self.alias('mysql')

    def drift(self,kind):
        engine,alias,schema,name=self.fixture(kind)
        before=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        with engine.begin() as c:c.execute(text(f'ALTER TABLE {name} ADD unrelated VARCHAR(10)'))
        extra=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        self.assertEqual(before.fingerprint,extra.fingerprint)
        with engine.begin() as c:
            if kind=='postgres':c.execute(text(f'ALTER TABLE {name} ALTER COLUMN amount TYPE DECIMAL(31,6)'))
            else:c.execute(text(f'ALTER TABLE {name} MODIFY amount DECIMAL(31,6)'))
        after=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        self.assertNotEqual(before.fingerprint,after.fingerprint)
        with self.assertRaises(ValueError):after.require_fingerprint(before.fingerprint)

    def test_postgres_used_type_drift_changes_hash_unmapped_column_does_not(self):self.drift('postgres')
    def test_mysql_used_type_drift_changes_hash_unmapped_column_does_not(self):self.drift('mysql')

    def keys(self,kind):
        engine,alias,schema,name=self.fixture(kind)
        before=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        with engine.begin() as c:c.execute(text(f'ALTER TABLE {name} ADD UNIQUE (amount)'))
        after=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        self.assertNotEqual(before.fingerprint,after.fingerprint)
        with self.assertRaises(ValueError):self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['missing'])

    def test_postgres_key_drift_and_missing_used_column_fail(self):self.keys('postgres')
    def test_mysql_key_drift_and_missing_used_column_fail(self):self.keys('mysql')

    def identity_and_nullability(self,kind):
        engine,alias,schema,name=self.fixture(kind)
        _,_,_,target_name=self.fixture(kind)
        source=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        target=self.schema.inspect_table(engine,schema=schema,table=target_name,used_columns=['id','amount'])
        pins=dict(expected_source_hash=source.fingerprint,expected_target_hash=target.fingerprint,
            expected_source_identity=source.physical_identity,expected_target_identity=target.physical_identity)
        self.assertEqual(self.schema.preflight(source,target,**pins),(source,target))
        pins['expected_source_identity']='0'*64
        with self.assertRaises(ValueError):self.schema.preflight(source,target,**pins)
        with engine.begin() as c:
            c.execute(text(f'ALTER TABLE {name} ALTER COLUMN amount SET NOT NULL' if kind=='postgres' else f'ALTER TABLE {name} MODIFY amount DECIMAL(30,6) NOT NULL'))
        changed=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['id','amount'])
        with self.assertRaises(ValueError):changed.require_fingerprint(source.fingerprint)

    def test_postgres_identity_pin_and_nullability_drift(self):self.identity_and_nullability('postgres')
    def test_mysql_identity_pin_and_nullability_drift(self):self.identity_and_nullability('mysql')

    def collation(self,kind):
        engine,alias,schema,name=self.fixture(kind)
        before=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['note'])
        with engine.begin() as c:
            c.execute(text(f'ALTER TABLE {name} ALTER COLUMN note TYPE VARCHAR(40) COLLATE "C"' if kind=='postgres' else f'ALTER TABLE {name} MODIFY note VARCHAR(40) COLLATE utf8mb4_bin'))
        after=self.schema.inspect_table(engine,schema=schema,table=name,used_columns=['note'])
        self.assertNotEqual(before.fingerprint,after.fingerprint)

    def test_postgres_used_collation_drift_changes_fingerprint(self):self.collation('postgres')
    def test_mysql_used_collation_drift_changes_fingerprint(self):self.collation('mysql')
