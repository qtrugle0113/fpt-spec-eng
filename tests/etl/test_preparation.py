"""T081: source COMPLETE -> mapped validation -> durable preparation; no load."""
import importlib
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
import os
from tests.etl import test_snapshot_staging as fixtures
from tests.unit import test_mapping as configs


class PreparationTests(unittest.TestCase):
    setUp=fixtures.SnapshotTests.setUp
    engine=fixtures.SnapshotTests.engine
    table=fixtures.SnapshotTests.table

    def run_case(self,kind,duplicate=False):
        try:module=importlib.import_module('aat_etl.engine')
        except ModuleNotFoundError:raise AssertionError('T081 preparation implementation missing') from None
        from aat_etl.contracts.config import ETLConfig
        from aat_etl.staging.quota import QuotaManager
        from aat_etl.staging.manager import StagingReader
        engine=self.engine(kind);source=self.table(engine);target='prepared_'+uuid4().hex
        schema='public' if kind=='postgres' else 'etl_test'
        with engine.begin() as c:
            c.execute(text(f'CREATE TABLE {target} (id INTEGER PRIMARY KEY, amount DECIMAL(30,6), note VARCHAR(80))'))
            if duplicate:c.execute(text(f'INSERT INTO {source} VALUES (1,0,NULL)'))
        raw=configs.configuration();raw['source'].update(schema=schema,table=source)
        raw['target'].update(schema=schema,table=target)
        config=ETLConfig.model_validate(raw)
        source_schema,target_schema=module.inspect_inputs(config,engine,engine)
        raw['target']['physical_target_id']=target_schema.physical_identity
        config=ETLConfig.model_validate(raw)
        pins=module.PreparationPins(source_schema.physical_identity,source_schema.fingerprint,target_schema.physical_identity,target_schema.fingerprint)
        metadata=create_engine(make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg'),hide_parameters=True)
        self.addCleanup(metadata.dispose)
        run=uuid4()
        with tempfile.TemporaryDirectory() as root:
            quota=QuotaManager(metadata,root)
            try:
                if duplicate:
                    raw['load_strategy']='UPSERT';raw['conflict_keys']=['id'];config=ETLConfig.model_validate(raw)
                    with self.assertRaises(ValueError):module.prepare_database(config,engine,engine,root=root,quota=quota,run_uuid=run,dataset_id=uuid4(),binding_sha256='a'*64,pins=pins)
                    self.assertEqual(len(list(Path(root).rglob('manifest.json'))),1)
                else:
                    prepared=module.prepare_database(config,engine,engine,root=root,quota=quota,run_uuid=run,dataset_id=uuid4(),binding_sha256='a'*64,pins=pins)
                    self.assertEqual(prepared.validated_rows,20)
                    reader=StagingReader(prepared.manifest,manifest_sha256=prepared.manifest_sha256,binding_sha256='a'*64)
                    self.assertEqual(reader.manifest['validated_rows'],20)
                    self.assertEqual(len(list(reader.rows())),20)
                    batches=list(prepared.batches(7))
                    self.assertEqual([len(b.rows) for b in batches],[7,7,6])
                    self.assertEqual([b.index for b in batches],[0,1,2])
            finally:
                # Only this test owns these writers/artifacts. Remove files
                # before explicitly releasing quota; never infer from age.
                with metadata.connect() as c:
                    owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':run}).scalars())
                import shutil
                for path in Path(root).iterdir():
                    if path.is_dir():shutil.rmtree(path)
                    else:path.unlink()
                for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)
        with engine.connect() as c:self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {target}')),0)

    def test_postgres_prepares_verified_disk_dataset_without_load(self):self.run_case('postgres')
    def test_mysql_prepares_verified_disk_dataset_without_load(self):self.run_case('mysql')
    def test_postgres_invalid_global_key_leaves_only_source_complete(self):self.run_case('postgres',True)
    def test_mysql_invalid_global_key_leaves_only_source_complete(self):self.run_case('mysql',True)
