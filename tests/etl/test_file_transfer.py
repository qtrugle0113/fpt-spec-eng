"""T093/T094: CSV/TXT immutable checksum, quoted NULL, aware instants and late type errors."""
from datetime import datetime,timezone
import hashlib
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
from tests.etl import test_snapshot_staging as fixtures
from tests.unit import test_mapping as configs


class FileTransferTests(unittest.TestCase):
    setUp=fixtures.SnapshotTests.setUp
    engine=fixtures.SnapshotTests.engine

    def run_route(self,kind,file_type,late_error=False,mode=None):
        try:source_module=importlib.import_module('aat_etl.readers.file_source')
        except ModuleNotFoundError:raise AssertionError('T093 file execution source missing') from None
        from aat_etl.engine import execute_file
        from aat_etl.contracts.config import ETLConfig
        from aat_etl.staging.quota import QuotaManager
        engine=self.engine(kind);schema='public' if kind=='postgres' else 'etl_test';table='file_transfer_'+uuid4().hex
        stamp_type='TIMESTAMP WITH TIME ZONE' if kind=='postgres' else 'TIMESTAMP(6)'
        with engine.begin() as c:c.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY, note VARCHAR(80), stamp {stamp_type} NULL)'))
        metadata=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(metadata.dispose);run=uuid4();file_id=uuid4();separator=',' if file_type=='CSV' else '|'
        payload=(f'id{separator}note{separator}stamp\n'
                 f'1{separator}"\\N"{separator}2026-11-10T12:34:56.123456+09:00\n'
                 f'2{separator}\\N{separator}\\N\n'
                 f'{"invalid" if late_error else "1" if mode=="duplicate_keys" else "3"}{separator}"Unicode \U0001f680\nsecond line"{separator}{"invalid" if mode=="upsert_late" else chr(92)+"N"}\n').encode()
        if mode=='malformed':payload+=b'"unterminated'
        if mode=='headerless':payload=payload.split(b'\n',1)[1]
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/uuid4().hex;source.write_bytes(payload);staging=Path(root)/'staging';staging.mkdir()
            parser=dict(encoding='utf-8',delimiter=separator,header_present=mode!='headerless',quote_character='"',escape_character=None,null_representation='\\N')
            reference=source_module.FileReference(file_id,1,hashlib.sha256(payload).hexdigest(),len(payload),source,parser)
            raw=configs.configuration();raw['source']=dict(type=file_type,file_id=str(file_id),parser_revision=1,file_sha256=reference.sha256)
            raw['target'].update(schema=schema,table=table);raw['batch_size']=2
            raw['mappings']=[dict(source_column=n,target_column=n,transformation='TYPE_CONVERSION' if n in ('id','stamp') else 'DIRECT',enabled=True) for n in ('id','note','stamp')]
            if mode=='headerless':
                for index,mapping in enumerate(raw['mappings'],1):mapping['source_column']='column_'+str(index)
            if mode in ('duplicate_keys','upsert_late'):raw['load_strategy']='UPSERT';raw['conflict_keys']=['id']
            config=ETLConfig.model_validate(raw);left,right=source_module.inspect_file_inputs(config,reference,engine)
            raw['target']['physical_target_id']=right.physical_identity;config=ETLConfig.model_validate(raw)
            pins=source_module.FilePins(left.fingerprint,right.physical_identity,right.fingerprint)
            quota=QuotaManager(metadata,staging)
            if mode=='checksum':source.write_bytes(payload[:-1]+b'!')
            try:
                failure=late_error or mode in ('duplicate_keys','malformed','checksum','upsert_late')
                if failure:
                    with self.assertRaises(ValueError):execute_file(config,reference,engine,root=staging,quota=quota,run_uuid=run,dataset_id=uuid4(),binding_sha256='a'*64,pins=pins,support_consent=True)
                else:
                    result=execute_file(config,reference,engine,root=staging,quota=quota,run_uuid=run,dataset_id=uuid4(),binding_sha256='a'*64,pins=pins,support_consent=True)
                    self.assertEqual(result.loaded_rows,3)
                with engine.connect() as c:
                    if kind=='mysql':c.execute(text("SET time_zone='+00:00'"))
                    rows=c.execute(text(f'SELECT id,note,stamp FROM {table} ORDER BY id')).all()
                    if mode in ('duplicate_keys','malformed','checksum'):
                        self.assertEqual(rows,[]);return
                    self.assertEqual(len(rows),2 if late_error or mode=='upsert_late' else 3)
                    self.assertEqual(rows[0][1],'\\N');self.assertIsNone(rows[1][1])
                    expected=datetime(2026,11,10,3,34,56,123456,tzinfo=timezone.utc)
                    self.assertEqual(rows[0][2] if kind=='postgres' else rows[0][2].replace(tzinfo=timezone.utc),expected)
            finally:
                with metadata.connect() as c:owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':run}).scalars())
                import shutil
                for path in staging.iterdir():
                    if path.is_dir():shutil.rmtree(path)
                for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)

    def test_csv_to_postgres(self):self.run_route('postgres','CSV')
    def test_csv_to_mysql(self):self.run_route('mysql','CSV')
    def test_txt_to_postgres(self):self.run_route('postgres','TXT')
    def test_txt_to_mysql(self):self.run_route('mysql','TXT')
    def test_append_late_type_error_preserves_committed_batch(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_route(kind,'CSV',True)

    def test_global_upsert_key_errors_precede_every_target_write(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_route(kind,'CSV',mode='duplicate_keys')

    def test_upsert_late_nonkey_type_error_preserves_prior_batch(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_route(kind,'CSV',mode='upsert_late')

    def test_bad_full_format_or_changed_checksum_never_loads(self):
        for kind in ('postgres','mysql'):
            for mode in ('malformed','checksum'):
                with self.subTest(kind=kind,mode=mode):self.run_route(kind,'CSV',mode=mode)

    def test_headerless_txt_maps_generated_columns(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_route(kind,'TXT',mode='headerless')
