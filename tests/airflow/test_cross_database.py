"""T142: four real SDK routes with composite keys and lossless typed mappings."""
from datetime import date,datetime
from decimal import Decimal
from sqlalchemy import inspect,text
from tests.airflow.test_execution import WorkflowFixture as _WorkflowFixture


class CrossDatabaseTests(_WorkflowFixture):
    def typed_route(self,source_kind,target_kind):
        from aat_api.services.connections.service import transaction
        from aat_api.services.etl_preview import connection_revision
        from aat_api.services.table_preview import target_engine

        def edit(book,connection,source,target,revision):
            sheet=book['ETL_Definitions']
            with transaction() as session:source_revision=connection_revision(session,sheet['D2'].value).id
            source_table=sheet['F2'].value
            self.assertNotEqual(source_table,target)
            for identity,table,is_source in ((source_revision,source_table,True),(revision,target,False)):
                self.assertRegex(table,r'^(preview_source|cross_source|preview_target)_[a-f0-9]{32}$')
                with target_engine(identity) as engine,engine.begin() as cursor:
                    quoted=engine.dialect.identifier_preparer.quote_identifier(table)
                    dialect=engine.dialect.name
                    stamp='TIMESTAMP WITHOUT TIME ZONE' if dialect=='postgresql' else 'DATETIME(6)'
                    final_name='occurred_at' if is_source else 'loaded_at'
                    cursor.execute(text(f'ALTER TABLE {quoted} ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 7'))
                    cursor.execute(text(f'ALTER TABLE {quoted} ADD COLUMN amount DECIMAL(18,4) NULL'))
                    cursor.execute(text(f'ALTER TABLE {quoted} ADD COLUMN event_date DATE NULL'))
                    cursor.execute(text(f'ALTER TABLE {quoted} ADD COLUMN {final_name} {stamp} NULL'))
                    if dialect=='postgresql':
                        key=inspect(cursor).get_pk_constraint(table)['name']
                        cursor.execute(text(f'ALTER TABLE {quoted} DROP CONSTRAINT '+engine.dialect.identifier_preparer.quote_identifier(key)))
                    else:cursor.execute(text(f'ALTER TABLE {quoted} DROP PRIMARY KEY'))
                    cursor.execute(text(f'ALTER TABLE {quoted} ADD PRIMARY KEY(id,tenant_id)'))
                    if is_source:
                        for values in [dict(id=1,tenant=7,amount=Decimal('12345.6789'),day=date(2026,1,1),stamp=datetime(2026,1,1,12,30,0,123456)),
                                       dict(id=2,tenant=9,amount=Decimal('-12.3400'),day=None,stamp=datetime(2026,1,3))]:
                            cursor.execute(text(f'UPDATE {quoted} SET tenant_id=:tenant,amount=:amount,event_date=:day,occurred_at=:stamp WHERE id=:id'),values)
            sheet['P2']='id,tenant_id';sheet['V2']=sheet['A2'].value
            for source_name,target_name in [('id','id'),('note','note'),('tenant_id','tenant_id'),('amount','amount'),('event_date','event_date'),('occurred_at','loaded_at')]:
                book['Column_Mappings'].append([sheet['A2'].value,source_name,target_name,'Direct Mapping',None,'TRUE'])

        result=self.workflow(source_kind=source_kind,target_kind=target_kind,strategy='UPSERT',workbook_edit=edit)
        with target_engine(result['target_revision']) as engine,engine.connect() as connection:
            table=engine.dialect.identifier_preparer.quote_identifier(result['target'])
            self.assertEqual(inspect(connection).get_pk_constraint(result['target'])['constrained_columns'],['id','tenant_id'])
            values=[tuple(row) for row in connection.execute(text(f'SELECT id,note,tenant_id,amount,event_date,loaded_at FROM {table} ORDER BY id'))]
        self.assertEqual(values,[(1,'first',7,Decimal('12345.6789'),date(2026,1,1),datetime(2026,1,1,12,30,0,123456)),
                                 (2,None,9,Decimal('-12.3400'),None,datetime(2026,1,3))])
        print('CROSS_DATABASE_TYPED_VERIFIED '+source_kind+'->'+target_kind+' composite_pk=true explicit_mapping=true decimal_temporal_null_exact=true',flush=True)

    def test_pg_to_pg(self):self.typed_route('POSTGRESQL','POSTGRESQL')
    def test_pg_to_mysql(self):self.typed_route('POSTGRESQL','MYSQL')
    def test_mysql_to_pg(self):self.typed_route('MYSQL','POSTGRESQL')
    def test_mysql_to_mysql(self):self.typed_route('MYSQL','MYSQL')
