"""T048: real target DDL, composite keys and existing-table preservation."""
import importlib
import os
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,inspect,select,func,event
from sqlalchemy.engine import make_url,URL


class TableDDLTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        try:
            self.spec=importlib.import_module('aat_api.validation.tables')
            self.pg=importlib.import_module('aat_api.ddl.postgres')
            self.mysql=importlib.import_module('aat_api.ddl.mysql')
        except ModuleNotFoundError as error:
            if error.name.startswith('aat_api.'):raise AssertionError('T051/T053/T054 DDL implementation missing') from None
            raise
        self.password=make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).password

    def definition(self,schema):
        C=self.spec.ColumnSpec
        return self.spec.TableSpec(name='ddl_'+uuid4().hex,target_schema=schema,description='Synthetic fixture',columns=[
            C(name='tenant_id',ordinal=1,logical_type='bigint',nullable=False,primary_key_ordinal=1),
            C(name='id',ordinal=2,logical_type='integer',nullable=False,primary_key_ordinal=2),
            C(name='name',ordinal=3,logical_type='varchar',nullable=True,length=80,has_default=True,
              default_literal={'logical_type':'varchar','value':"O'Reilly"})])

    def check(self,adapter,engine,schema):
        self.addCleanup(engine.dispose)
        definition=self.definition(schema)
        sql=adapter.compile_table(definition)
        self.assertIn('CREATE TABLE',sql)
        self.assertEqual(adapter.create(engine,definition),'CREATED')
        inspector=inspect(engine)
        self.assertEqual(inspector.get_pk_constraint(definition.name,schema=schema)['constrained_columns'],['tenant_id','id'])
        table=adapter.build_table(definition)
        with engine.begin() as connection:
            connection.execute(table.insert().values(tenant_id=1,id=7))
        self.assertEqual(adapter.create(engine,definition),'ALREADY_EXISTS')
        with engine.connect() as connection:
            self.assertEqual(connection.scalar(select(func.count()).select_from(table)),1)
            self.assertEqual(connection.scalar(select(table.c.name)),"O'Reilly")

    def test_postgres_real_ddl_and_existing_data_preserved(self):
        engine=create_engine(make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg'),hide_parameters=True)
        self.check(self.pg,engine,'public')

    def test_mysql_real_ddl_and_existing_data_preserved(self):
        engine=create_engine(URL.create('mysql+pymysql',username='aat_test',password=self.password,host='mysql',database='etl_test'),hide_parameters=True)
        self.check(self.mysql,engine,'etl_test')

    def test_mysql_lost_response_after_real_implicit_commit_is_unknown(self):
        from aat_api.ddl.common import DDLOutcomeUnknown
        engine=create_engine(URL.create('mysql+pymysql',username='aat_test',password=self.password,host='mysql',database='etl_test'),hide_parameters=True)
        self.addCleanup(engine.dispose)
        definition=self.definition('etl_test')
        def lost_response(connection,cursor,statement,parameters,context,executemany):
            if statement.lstrip().upper().startswith('CREATE TABLE'):
                raise ConnectionError('Synthetic response interruption after actual server DDL')
        event.listen(engine,'after_cursor_execute',lost_response)
        with self.assertRaises(DDLOutcomeUnknown):self.mysql.create(engine,definition)
        event.remove(engine,'after_cursor_execute',lost_response)
        self.assertTrue(inspect(engine).has_table(definition.name,schema='etl_test'))

    def all_types(self,adapter,engine,schema):
        from datetime import date,datetime
        from decimal import Decimal
        self.addCleanup(engine.dispose)
        C=self.spec.ColumnSpec
        columns=[]
        values=[('decimal','12345678901234567890.123456'),('boolean',True),('date','2026-11-09'),('timestamp','2026-11-09T12:34:56.123456'),('text',"O'Reilly"),('varchar',None)]
        for index,(logical,value) in enumerate(values,1):
            columns.append(C(name='c'+str(index),ordinal=index,logical_type=logical,nullable=True,
                precision=30 if logical=='decimal' else None,scale=6 if logical=='decimal' else None,
                length=80 if logical=='varchar' else None,has_default=True,default_literal={'logical_type':logical,'value':value}))
        definition=self.spec.TableSpec(name='types_'+uuid4().hex,target_schema=schema,columns=columns)
        self.assertEqual(adapter.create(engine,definition),'CREATED')
        table=adapter.build_table(definition)
        with engine.begin() as connection:
            connection.execute(table.insert().values())
            row=connection.execute(select(table)).one()
        self.assertEqual(tuple(row),(Decimal(values[0][1]),True,date(2026,11,9),datetime(2026,11,9,12,34,56,123456),"O'Reilly",None))

    def test_postgres_all_types_and_lossless_defaults(self):
        self.all_types(self.pg,create_engine(make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg'),hide_parameters=True),'public')

    def test_mysql_all_types_and_lossless_defaults(self):
        self.all_types(self.mysql,create_engine(URL.create('mysql+pymysql',username='aat_test',password=self.password,host='mysql',database='etl_test'),hide_parameters=True),'etl_test')
