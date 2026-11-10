"""T077: real DB snapshots and introspected types mapped into durable staging."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import text
from tests.etl import test_snapshot_staging as fixtures


class MappingPipelineTests(unittest.TestCase):
    setUp = fixtures.SnapshotTests.setUp
    engine = fixtures.SnapshotTests.engine
    table = fixtures.SnapshotTests.table
    def pipeline(self, kind):
        from aat_etl.mapping.mapper import map_row
        from aat_etl.readers.schema import inspect_table
        from aat_etl.staging.manager import StagingWriter, StagingReader
        from aat_etl.readers import postgres, mysql
        engine = self.engine(kind)
        source = self.table(engine)
        target = 'mapped_' + uuid4().hex
        schema = 'public' if kind == 'postgres' else 'etl_test'
        with engine.begin() as connection:
            connection.execute(text(f'CREATE TABLE {target} (new_id BIGINT NOT NULL, amount DECIMAL(30,6), label VARCHAR(80), retained INTEGER DEFAULT 99)'))
        source_columns = inspect_table(engine, schema=schema, table=source, used_columns=['id','amount','note']).columns
        target_columns = inspect_table(engine, schema=schema, table=target, used_columns=['new_id','amount','label']).columns
        mappings = [dict(source_column=s, target_column=t, transformation='DIRECT', enabled=True)
                    for s,t in [('id','new_id'),('amount','amount'),('note','label')]]
        adapter = postgres if kind == 'postgres' else mysql
        with tempfile.TemporaryDirectory() as temporary:
            with StagingWriter(temporary, dag_id='mapping', run_id=str(uuid4()), dataset_id=uuid4(),
                    binding_sha256='a'*64, source_schema_hash='b'*64, target_schema_hash='c'*64,
                    mapping_hash='d'*64, columns=list(target_columns), source_snapshot_time=datetime.now(timezone.utc)) as writer:
                with adapter.SnapshotReader(engine,schema=schema,table=source,columns=['id','amount','note']) as reader:
                    for index, row in enumerate(reader.rows(), 1):
                        mapped = map_row(row, source_schema=source_columns, target_schema=target_columns,
                                         mappings=mappings, row_number=index)
                        writer.append([mapped[c['name']] for c in target_columns])
                manifest = writer.complete()
            rows = list(StagingReader(manifest,manifest_sha256=writer.manifest_sha256,binding_sha256='a'*64).rows())
            self.assertEqual(len(rows),20)
            self.assertEqual(sorted(r[0] for r in rows),list(range(1,21)))
            self.assertTrue(all(r[1] == Decimal('12345678901234567890.123456') for r in rows))
            self.assertTrue(Path(manifest).is_file())
        with engine.connect() as connection:
            self.assertEqual(connection.scalar(text(f'SELECT count(*) FROM {target}')),0)

    def test_postgres_mapping_to_disk_uses_real_introspected_types(self):self.pipeline('postgres')
    def test_mysql_mapping_to_disk_uses_real_introspected_types(self):self.pipeline('mysql')

