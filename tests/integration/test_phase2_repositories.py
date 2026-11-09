"""Repository/migration/init expectations on isolated PostgreSQL, no substitutes."""
import importlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4


class RepositoryFoundationTests(unittest.TestCase):
    def test_real_alembic_entry_and_revision_repository_exist(self):
        root=Path(__file__).resolve().parents[2]
        self.assertTrue((root/'backend/alembic/versions/0001_metadata.py').is_file(),'T029 migration missing')
        self.assertTrue((root/'docker/bootstrap/app_init.py').is_file(),'T030 initializer missing')
        for name in ['aat_metadata.repositories.base','aat_metadata.repositories.revisions']:
            module=importlib.import_module(name)
            self.assertTrue(module)

    def test_concurrent_init_then_setting_optimistic_update_and_fk_restrict(self):
        from concurrent.futures import ThreadPoolExecutor
        import psycopg
        root=Path(__file__).resolve().parents[2]
        entry=root/'docker/bootstrap/app_init.py'
        self.assertTrue(entry.exists(),'T030 initializer missing')
        def initialize(_):return subprocess.run([sys.executable,str(entry)],capture_output=True,timeout=120)
        with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(initialize,range(2)))
        self.assertTrue(all(r.returncode==0 for r in outcomes),'Initializer failed; use private diagnostics')
        repo=importlib.import_module('aat_metadata.repositories.revisions')
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            first=c.execute("SELECT revision FROM application_settings WHERE key='default_batch_size'").fetchone()[0]
            repo.update_setting(c,'default_batch_size',first,2000)
            with self.assertRaises(repo.StaleRevision),c.transaction():repo.update_setting(c,'default_batch_size',first,3000)
            self.assertEqual(c.execute("SELECT value_json FROM application_settings WHERE key='default_batch_size'").fetchone()[0],2000)
            self.assertTrue(c.execute('SELECT count(*) FROM alembic_version').fetchone()[0]==1)

    def test_actual_migration_matches_registered_models_and_is_idempotent(self):
        root=Path(__file__).resolve().parents[2]
        initialized=subprocess.run([sys.executable,str(root/'docker/bootstrap/app_init.py')],capture_output=True,timeout=120)
        self.assertEqual(initialized.returncode,0,'Migration initializer failed; use private diagnostics')
        from sqlalchemy import CheckConstraint,UniqueConstraint,create_engine,inspect
        from aat_metadata.models.registry import Base
        engine=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(engine.dispose)
        inspector=inspect(engine)
        for table in Base.metadata.tables.values():
            with self.subTest(table=table.name):
                columns={x['name']:x for x in inspector.get_columns(table.name)}
                self.assertEqual(set(columns),set(table.columns.keys()))
                for column in table.columns:
                    self.assertEqual(columns[column.name]['nullable'],column.nullable)
                    self.assertEqual(columns[column.name]['type'].compile(dialect=engine.dialect),
                                     column.type.compile(dialect=engine.dialect))
                self.assertEqual(inspector.get_pk_constraint(table.name)['constrained_columns'],
                                 [column.name for column in table.primary_key.columns])
                self.assertEqual({c.name for c in table.constraints if isinstance(c,CheckConstraint)},
                                 {c['name'] for c in inspector.get_check_constraints(table.name)})
                self.assertEqual({tuple(column.name for column in c.columns) for c in table.constraints if isinstance(c,UniqueConstraint)},
                                 {tuple(c['column_names']) for c in inspector.get_unique_constraints(table.name)})
                reflected=inspector.get_foreign_keys(table.name)
                self.assertEqual(len(reflected),len(table.foreign_key_constraints))
                self.assertTrue(all(fk['options'].get('ondelete')=='RESTRICT' for fk in reflected))
                self.assertTrue({i.name for i in table.indexes}<={i['name'] for i in inspector.get_indexes(table.name)})
                import re
                from sqlalchemy import text
                # A listener attached to a revision table may create a parent
                # trigger (Connection code dependency guard). Check its actual
                # target table as declared in production DDL.
                for ddl in table.dispatch.after_create:
                    for trigger,target in re.findall(r'CREATE TRIGGER (\w+).*?\bON\s+(?:public\.)?(\w+)',ddl.statement,re.S):
                        with engine.connect() as c:
                            actual=set(c.scalars(text('SELECT trigger_name FROM information_schema.triggers WHERE event_object_table=:name'),{'name':target}))
                        self.assertIn(trigger,actual,'Frozen migration misses production guard: '+target)

    def test_seed_preserves_operator_settings_and_existing_sample_identities(self):
        import psycopg
        root=Path(__file__).resolve().parents[2]
        def initialize():
            return subprocess.run([sys.executable,str(root/'docker/bootstrap/app_init.py')],capture_output=True,timeout=120)
        self.assertEqual(initialize().returncode,0,'Initial seed failed')
        queries=[
            'SELECT id,code,name,current_revision_id FROM connections ORDER BY id',
            'SELECT key,value_json,revision FROM application_settings ORDER BY key',
            'SELECT id,sha256,bytes,safe_storage_key FROM uploaded_files ORDER BY id',
            'SELECT id,file_id,revision FROM file_parser_revisions ORDER BY id',
        ]
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            c.execute("UPDATE application_settings SET value_json='3456'::jsonb WHERE key='default_batch_size'")
            c.execute("UPDATE connections SET name='Operator name' WHERE normalized_code='pg_etl'")
            before=[c.execute(query).fetchall() for query in queries]
        self.assertEqual(initialize().returncode,0,'Repeat seed failed')
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            after=[c.execute(query).fetchall() for query in queries]
        self.assertTrue(before==after,'Repeat seed changed existing operator metadata or sample identities')

    def test_missing_original_key_fails_without_regeneration_or_metadata_changes(self):
        import json
        import psycopg
        root=Path(__file__).resolve().parents[2]
        def initialize():
            return subprocess.run([sys.executable,str(root/'docker/bootstrap/app_init.py')],capture_output=True,timeout=120)
        self.assertEqual(initialize().returncode,0,'Initial seed failed')
        keyroot=Path(os.environ['AAT_APP_KEYRING'])
        current=(keyroot/'current.json').read_bytes()
        key=keyroot/(json.loads(current)['key_id']+'.key')
        original=key.read_bytes()
        held=key.with_suffix('.held')
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            before=c.execute('SELECT id,key_id,ciphertext FROM connection_secrets ORDER BY id').fetchall()
        key.rename(held)
        try:
            result=initialize()
            self.assertNotEqual(result.returncode,0,'Initializer accepted missing persistent key')
            self.assertFalse(key.exists(),'Initializer regenerated missing key')
            self.assertEqual((keyroot/'current.json').read_bytes(),current)
            with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
                after=c.execute('SELECT id,key_id,ciphertext FROM connection_secrets ORDER BY id').fetchall()
            self.assertTrue(before==after,'Failed init changed secret metadata')
        finally:
            held.rename(key)
        self.assertTrue(key.read_bytes()==original,'Original key changed')
