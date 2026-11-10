"""T092/T094: standalone real cross-DB execution, final-marker replay and metrics."""
from decimal import Decimal
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
from tests.etl import test_snapshot_staging as fixtures
from tests.unit import test_mapping as configs


class TransferRouteTests(unittest.TestCase):
    setUp=fixtures.SnapshotTests.setUp
    engine=fixtures.SnapshotTests.engine
    table=fixtures.SnapshotTests.table

    def run_route(self,source_kind,target_kind):
        module=importlib.import_module('aat_etl.engine')
        self.assertTrue(hasattr(module,'execute_database'),'T092 policy dispatch missing')
        from aat_etl.contracts.config import ETLConfig
        from aat_etl.staging.quota import QuotaManager
        source=self.engine(source_kind);target=self.engine(target_kind)
        source_table=self.table(source);target_table='transfer_'+uuid4().hex
        source_schema='public' if source_kind=='postgres' else 'etl_test'
        target_schema='public' if target_kind=='postgres' else 'etl_test'
        with target.begin() as c:c.execute(text(f'CREATE TABLE {target_table} (id BIGINT PRIMARY KEY, amount DECIMAL(30,6), note VARCHAR(80))'))
        raw=configs.configuration();raw['source'].update(schema=source_schema,table=source_table);raw['target'].update(schema=target_schema,table=target_table)
        config=ETLConfig.model_validate(raw);left,right=module.inspect_inputs(config,source,target)
        raw['target']['physical_target_id']=right.physical_identity;config=ETLConfig.model_validate(raw)
        pins=module.PreparationPins(left.physical_identity,left.fingerprint,right.physical_identity,right.fingerprint)
        metadata=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(metadata.dispose);run=uuid4()
        with tempfile.TemporaryDirectory() as root:
            quota=QuotaManager(metadata,root);dataset=uuid4()
            try:
                snapshots=[]
                result=module.execute_database(config,source,target,root=root,quota=quota,run_uuid=run,dataset_id=dataset,
                    binding_sha256='a'*64,pins=pins,support_consent=True,project=snapshots.append)
                self.assertEqual(result.loaded_rows,20);self.assertEqual(result.failed_rows,0)
                with source.begin() as c:c.execute(text(f"UPDATE {source_table} SET note='changed after commit'"))
                retried=module.execute_database(config,source,target,root=root,quota=quota,run_uuid=run,dataset_id=dataset,
                    binding_sha256='a'*64,pins=pins,support_consent=False,project=snapshots.append)
                self.assertEqual(retried.loaded_rows,20);self.assertEqual(len(snapshots),2)
                with target.connect() as c:
                    rows=c.execute(text(f'SELECT id,amount,note FROM {target_table} ORDER BY id')).all()
                    self.assertEqual(len(rows),20)
                    self.assertEqual(rows[0],(1,Decimal('12345678901234567890.123456'),'value-1'))
            finally:
                with metadata.connect() as c:owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':run}).scalars())
                import shutil
                for path in Path(root).iterdir():
                    if path.is_dir():shutil.rmtree(path)
                for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)

    def test_postgres_to_postgres(self):self.run_route('postgres','postgres')
    def test_postgres_to_mysql(self):self.run_route('postgres','mysql')
    def test_mysql_to_postgres(self):self.run_route('mysql','postgres')
    def test_mysql_to_mysql(self):self.run_route('mysql','mysql')
