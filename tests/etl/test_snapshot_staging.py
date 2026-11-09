"""T070: real source snapshots and durable typed staging, never target DML."""
from datetime import date,datetime,timezone
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text,event
from sqlalchemy.engine import URL,make_url


def implementation(name):
    try:return importlib.import_module('aat_etl.'+name)
    except ModuleNotFoundError as error:
        if error.name.startswith('aat_etl'):raise AssertionError('Engine implementation missing: '+name) from None
        raise


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        self.pg_url=make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg')
        self.mysql_url=URL.create('mysql+pymysql',username='aat_test',password=self.pg_url.password,host='mysql',database='etl_test')

    def engine(self,kind):
        engine=create_engine(self.pg_url if kind=='postgres' else self.mysql_url,hide_parameters=True)
        self.addCleanup(engine.dispose);return engine

    def table(self,engine):
        name='snapshot_'+uuid4().hex
        # Generated identifier only; no production tables or arbitrary identifiers.
        with engine.begin() as connection:
            connection.execute(text(f'CREATE TABLE {name} (id INTEGER NOT NULL, amount DECIMAL(30,6), note VARCHAR(80))'))
            connection.execute(text(f'INSERT INTO {name} VALUES (:id,:amount,:note)'),[
                dict(id=i,amount=Decimal('12345678901234567890.123456'),note='value-'+str(i)) for i in range(1,21)])
        return name

    def snapshot(self,kind):
        module=implementation('readers.'+kind);engine=self.engine(kind);table=self.table(engine)
        schema='public' if kind=='postgres' else 'etl_test'
        with module.SnapshotReader(engine,schema=schema,table=table,columns=['id','amount','note'],chunk_rows=1) as reader:
            rows=iter(reader.rows());first=next(rows)
            with engine.begin() as writer:
                writer.execute(text(f"UPDATE {table} SET note='changed'"))
                writer.execute(text(f"INSERT INTO {table} VALUES (21,1,'new')"))
            original=[first,*rows]
        self.assertEqual(len(original),20)
        self.assertEqual(sorted(row['id'] for row in original),list(range(1,21)))
        for row in original:
            self.assertEqual(row['note'],'value-'+str(row['id']))
            self.assertEqual(row['amount'],Decimal('12345678901234567890.123456'))
        with engine.connect() as after:
            self.assertEqual(after.scalar(text(f'SELECT COUNT(*) FROM {table}')),21)

    def test_postgres_snapshot_survives_concurrent_updates_without_primary_key(self):self.snapshot('postgres')
    def test_mysql_snapshot_survives_concurrent_updates_without_primary_key(self):self.snapshot('mysql')

    def disconnect(self,kind,midstream=False):
        module=implementation('readers.'+kind);engine=self.engine(kind);table=self.table(engine)
        with module.SnapshotReader(engine,schema='public' if kind=='postgres' else 'etl_test',table=table,columns=['id','amount','note'],chunk_rows=1) as reader:
            driver=reader.connection.connection.driver_connection
            pid=driver.info.backend_pid if kind=='postgres' else driver.thread_id()
            rows=iter(reader.rows())
            if midstream:self.assertIn('id',next(rows))
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as killer:
                if kind=='postgres':self.assertTrue(killer.scalar(text('SELECT pg_terminate_backend(:pid)'),{'pid':pid}))
                else:killer.execute(text('KILL CONNECTION '+str(int(pid))))
            with self.assertRaises(ValueError):list(rows)
        # A broken source must fail; a reconnect must never append a second snapshot.

    def test_postgres_source_session_loss_fails_without_reconnect(self):self.disconnect('postgres')
    def test_mysql_source_session_loss_fails_without_reconnect(self):self.disconnect('mysql')
    def test_postgres_midstream_session_loss_discards_incomplete_snapshot(self):self.disconnect('postgres',True)
    def test_mysql_midstream_session_loss_discards_incomplete_snapshot(self):self.disconnect('mysql',True)

    def test_mysql_nontransactional_source_is_rejected(self):
        module=implementation('readers.mysql');engine=self.engine('mysql');name='myisam_'+uuid4().hex
        with engine.begin() as connection:connection.execute(text(f'CREATE TABLE {name} (id INTEGER) ENGINE=MyISAM'))
        with self.assertRaises(ValueError):
            with module.SnapshotReader(engine,schema='etl_test',table=name,columns=['id']) as reader:list(reader.rows())

    def guard(self,kind):
        module=implementation('readers.'+kind);engine=self.engine(kind);name='guard_'+uuid4().hex
        with engine.begin() as connection:
            column_type='TEXT' if kind=='postgres' else 'LONGTEXT'
            connection.execute(text(f'CREATE TABLE {name} (note {column_type})'))
            connection.execute(text(f'INSERT INTO {name} VALUES (:note)'),{'note':'x'*(2*1024*1024)})
        transported=[];cursor_types=[]
        def inspect_guard(connection,cursor,statement,parameters,context,executemany):
            if 'CASE WHEN' in statement and name in statement:
                cursor_types.append(type(cursor).__name__)
                transported.append(cursor.fetchone())
                cursor.close()
                raise ValueError('Synthetic inspection stops after the guarded wire row')
        event.listen(engine,'after_cursor_execute',inspect_guard)
        try:
            with module.SnapshotReader(engine,schema='public' if kind=='postgres' else 'etl_test',table=name,columns=['note']) as reader:
                with self.assertRaises(ValueError):list(reader.rows())
        finally:event.remove(engine,'after_cursor_execute',inspect_guard)
        self.assertEqual(len(transported),1);self.assertIsNone(transported[0][0]);self.assertGreater(transported[0][-1],1024*1024)
        self.assertIn('ServerCursor' if kind=='postgres' else 'SSCursor',cursor_types[0])

    def test_postgres_oversized_cell_is_null_on_wire_before_materialization(self):self.guard('postgres')
    def test_mysql_oversized_cell_is_null_on_wire_before_materialization(self):self.guard('mysql')

    def filtered(self,kind):
        module=implementation('readers.'+kind);engine=self.engine(kind);table=self.table(engine)
        schema='public' if kind=='postgres' else 'etl_test'
        predicate={'and':[{'column':'note','operator':'=','value':{'logical_type':'text','value':"' OR 1=1 --"}}]}
        with module.SnapshotReader(engine,schema=schema,table=table,columns=['id'],filter=predicate) as reader:
            self.assertEqual(list(reader.rows()),[])
        predicate['and'][0]['value']['value']='value-7'
        with module.SnapshotReader(engine,schema=schema,table=table,columns=['id'],filter=predicate) as reader:
            self.assertEqual(list(reader.rows()),[{'id':7}])
        with engine.connect() as connection:self.assertEqual(connection.scalar(text(f'SELECT COUNT(*) FROM {table}')),20)

    def test_postgres_filter_is_bound_and_can_use_unprojected_columns(self):self.filtered('postgres')
    def test_mysql_filter_is_bound_and_can_use_unprojected_columns(self):self.filtered('mysql')

    def readonly(self,kind):
        module=implementation('readers.'+kind);engine=self.engine(kind);table=self.table(engine)
        with module.SnapshotReader(engine,schema='public' if kind=='postgres' else 'etl_test',table=table,columns=['id']) as reader:
            if kind=='postgres':
                self.assertEqual(reader.connection.scalar(text("SELECT current_setting('transaction_isolation')")),'repeatable read')
                self.assertEqual(reader.connection.scalar(text("SELECT current_setting('transaction_read_only')")),'on')
            else:
                self.assertEqual(reader.connection.scalar(text('SELECT @@transaction_isolation')),'REPEATABLE-READ')
                self.assertEqual(reader.connection.scalar(text('SELECT @@session.time_zone')),'+00:00')
            with self.assertRaises(Exception):reader.connection.execute(text(f'DELETE FROM {table}'))
        with engine.connect() as connection:self.assertEqual(connection.scalar(text(f'SELECT COUNT(*) FROM {table}')),20)

    def test_postgres_snapshot_session_rejects_writes(self):self.readonly('postgres')
    def test_mysql_snapshot_session_rejects_writes(self):self.readonly('mysql')

    def temporal_unicode(self,kind):
        module=implementation('readers.'+kind);engine=self.engine(kind);name='temporal_'+uuid4().hex
        stamp='TIMESTAMP WITH TIME ZONE' if kind=='postgres' else 'TIMESTAMP(6)'
        with engine.begin() as connection:
            if kind=='mysql':connection.exec_driver_sql("SET SESSION time_zone = '+00:00'")
            connection.execute(text(f'CREATE TABLE {name} (stamp {stamp}, note VARCHAR(80))'))
            connection.execute(text(f'INSERT INTO {name} VALUES (:stamp,:note)'),{
                'stamp':datetime(2026,11,10,12,34,56,123456,tzinfo=timezone.utc) if kind=='postgres' else datetime(2026,11,10,12,34,56,123456),
                'note':'Unicode \U0001f680 \u1ec7'})
        with module.SnapshotReader(engine,schema='public' if kind=='postgres' else 'etl_test',table=name,columns=['stamp','note']) as reader:
            rows=list(reader.rows())
        self.assertEqual(rows[0]['note'],'Unicode \U0001f680 \u1ec7');self.assertEqual(rows[0]['stamp'].microsecond,123456)
        actual=rows[0]['stamp']
        if kind=='mysql':self.assertIsNotNone(actual.tzinfo)
        self.assertEqual(actual,datetime(2026,11,10,12,34,56,123456,tzinfo=timezone.utc))

    def test_postgres_timestamp_and_unicode_are_lossless(self):self.temporal_unicode('postgres')
    def test_mysql_utc_timestamp_and_unicode_are_lossless(self):self.temporal_unicode('mysql')


class TypedStagingTests(unittest.TestCase):
    def setUp(self):
        self.manager=implementation('staging.manager')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.columns=[dict(name=n,logical_type=t,nullable=True,**extra) for n,t,extra in [
            ('id','bigint',{}),('amount','decimal',dict(precision=30,scale=6)),('note','text',{}),
            ('flag','boolean',{}),('day','date',{}),('naive','timestamp',dict(timezone_semantics='naive')),
            ('aware','timestamp',dict(timezone_semantics='aware'))]]
        self.binding='a'*64

    def writer(self):
        return self.manager.StagingWriter(self.root,dag_id='../synthetic/dag',run_id='run/../fixture',
            dataset_id=uuid4(),binding_sha256=self.binding,source_schema_hash='b'*64,target_schema_hash='c'*64,
            mapping_hash='d'*64,columns=self.columns,source_snapshot_time=datetime.now(timezone.utc))

    def values(self):
        return [9223372036854775807,Decimal('12345678901234567890.123456'),'Unicode \U0001f680\n"\\N"',True,
            date(2026,11,10),datetime(2026,11,10,12,34,56,123456),datetime(2026,11,10,12,34,56,123456,tzinfo=timezone.utc)]

    def test_typed_roundtrip_preserves_values_null_and_safe_paths(self):
        original=self.values()
        with self.writer() as writer:
            writer.append(original);writer.append([None]*len(original));manifest=writer.complete()
        path=Path(manifest).resolve();self.assertTrue(path.is_relative_to(self.root.resolve()))
        raw=json.loads(path.read_text());self.assertEqual(raw['format_version'],'aat-jsonl/1');self.assertEqual(raw['state'],'COMPLETE')
        self.assertEqual(raw['extracted_rows'],2)
        reader=self.manager.StagingReader(path,manifest_sha256=writer.manifest_sha256,binding_sha256=self.binding)
        rows=list(reader.rows());self.assertEqual(rows,[original,[None]*len(original)])
        for meta in raw['files']:
            lines=(path.parent/meta['name']).read_text().splitlines()
            self.assertEqual(len(lines),meta['rows'])
            self.assertIsInstance(json.loads(lines[0]),list)

    def test_incomplete_extraction_does_not_publish_complete_manifest(self):
        with self.assertRaises(RuntimeError):
            with self.writer() as writer:
                writer.append(self.values());raise RuntimeError('Synthetic source interruption')
        self.assertEqual(list(self.root.rglob('manifest.json')),[])

    def test_checksum_corruption_and_binding_mismatch_rejected_before_rows(self):
        with self.writer() as writer:writer.append(self.values());manifest=writer.complete()
        with self.assertRaises(ValueError):list(self.manager.StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256='f'*64).rows())
        path=Path(manifest);raw=json.loads(path.read_text());part=path.parent/raw['files'][0]['name']
        part.chmod(0o600)
        part.write_bytes(part.read_bytes()+b'[]\n')
        with self.assertRaises(ValueError):list(self.manager.StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256=self.binding).rows())

    def test_missing_file_and_manifest_schema_drift_are_rejected(self):
        with self.writer() as writer:writer.append(self.values());manifest=writer.complete()
        path=Path(manifest);raw=json.loads(path.read_text());part=path.parent/raw['files'][0]['name'];part.unlink()
        with self.assertRaises(ValueError):list(self.manager.StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256=self.binding).rows())
        path.chmod(0o600)
        raw['columns'][0]['logical_type']='text';path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):list(self.manager.StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256=self.binding,source_schema_hash='0'*64).rows())

    def test_corrupt_last_part_is_rejected_before_first_row_is_yielded(self):
        with self.writer() as writer:
            for _ in range(17):
                values=self.values();values[2]='x'*(1024*1024-1000);writer.append(values)
            manifest=writer.complete()
        raw=json.loads(Path(manifest).read_text());self.assertGreaterEqual(len(raw['files']),2)
        last=Path(manifest).parent/raw['files'][-1]['name'];last.chmod(0o600)
        content=last.read_bytes();last.write_bytes(content.replace(b'x',b'y',1))
        iterator=self.manager.StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256=self.binding).rows()
        with self.assertRaises(ValueError):next(iterator)

    def test_process_exit_before_complete_never_publishes_manifest(self):
        child=os.fork()
        if child==0:
            try:
                with self.writer() as writer:
                    writer.append(self.values());os._exit(71)
            except BaseException:os._exit(72)
        _,status=os.waitpid(child,0);self.assertEqual(os.waitstatus_to_exitcode(status),71)
        self.assertEqual(list(self.root.rglob('manifest.json')),[])
        self.assertTrue(list(self.root.rglob('*.part')))

    def test_decimal_float_and_type_coercion_fail_without_complete_publication(self):
        for index,value in ((0,True),(1,0.1),(1,Decimal('1E+5000000')),(4,'2026-11-10'),(5,datetime.now(timezone.utc))):
            with self.subTest(index=index,value_type=type(value).__name__),self.assertRaises(ValueError):
                with self.writer() as writer:
                    values=self.values();values[index]=value;writer.append(values)
        self.assertEqual(list(self.root.rglob('manifest.json')),[])

    def test_serialized_record_limit_is_enforced_without_publishing_complete(self):
        with self.assertRaises(ValueError):
            with self.writer() as writer:
                values=self.values();values[2]='x'*(1024*1024);writer.append(values)
        self.assertEqual(list(self.root.rglob('manifest.json')),[])

    def test_completed_manifest_cannot_be_rewritten_or_its_schema_relabelled(self):
        with self.writer() as writer:writer.append(self.values());manifest=writer.complete()
        with self.assertRaises(ValueError):writer.append(self.values())
        with self.assertRaises(ValueError):writer.complete()
        path=Path(manifest);raw=json.loads(path.read_text());raw['columns'][1]['logical_type']='text'
        path.chmod(0o600);path.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):self.manager.StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256=self.binding)
