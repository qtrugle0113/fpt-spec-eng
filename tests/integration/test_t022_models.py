"""Real T022 metadata; no external Airflow collision acceptance."""
import importlib
import unittest
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration import test_definition_models as definitions


class ETLModelTests(definitions.DefinitionModelTests):
    # Inherited T020 tests intentionally remain regression checks here.
    def setUp(self):
        try:
            self.etl = importlib.import_module('aat_metadata.models.etl')
        except ModuleNotFoundError as exc:
            if exc.name != 'aat_metadata.models.etl': raise
            raise AssertionError('T022 ETL models missing') from None
        super().setUp()

    def etl_revision(self, **changes):
        _, upload = self.upload(kind='ETL')
        parent = self.etl.ETLDefinition(dag_id='t022_' + uuid4().hex)
        self.session.add(parent); self.session.flush()
        values = dict(definition_id=parent.id, revision=1, upload_id=upload.id,
                      config_json={'load_strategy':'APPEND','source':{'connection_revision_id':str(uuid4())}},
                      status='VALIDATED')
        values.update(changes)
        revision = self.etl.ETLDefinitionRevision(**values)
        self.session.add(revision); self.session.flush()
        parent.current_revision_id=revision.id; self.session.flush()
        return parent, revision

    def mapping(self, revision, **changes):
        values=dict(etl_revision_id=revision.id, ordinal=1, source_column='id', target_column='id',
                    transformation='DIRECT', enabled=True)
        values.update(changes); row=self.etl.ColumnMapping(**values)
        self.session.add(row); self.session.flush(); return row

    def test_dag_unique_and_current_revision_belongs_to_parent(self):
        parent, revision=self.etl_revision(); other, rev2=self.etl_revision()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.add(self.etl.ETLDefinition(dag_id=parent.dag_id)); self.session.flush()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            parent.current_revision_id=rev2.id; self.session.flush()

    def test_revision_hash_generated_and_wrong_hash_rejected(self):
        _, rev=self.etl_revision()
        expected=self.session.scalar(text("SELECT encode(sha256(convert_to(config_json::text,'UTF8')),'hex') FROM etl_definition_revisions WHERE id=:id"),{'id':rev.id})
        self.assertEqual(rev.config_sha256,expected)
        with self.assertRaises(IntegrityError),self.session.begin_nested(): self.etl_revision(config_sha256='f'*64)

    def test_revision_snapshot_and_mapping_immutable(self):
        _, rev=self.etl_revision(); mapping=self.mapping(rev)
        for statement,params in [ ('UPDATE etl_definition_revisions SET config_json=\'{}\' WHERE id=:id',{'id':rev.id}),
                                  ("UPDATE column_mappings SET target_column='changed' WHERE id=:id",{'id':mapping.id}) ]:
            with self.assertRaises(IntegrityError),self.session.begin_nested():self.session.execute(text(statement),params)

    def test_config_refuses_nested_credentials(self):
        for config in [{'source':{'password':'secret'}},{'token':'x'},{'target':{'dsn':'postgresql://user:pass@db'}}]:
            with self.subTest(config=config),self.assertRaises(IntegrityError),self.session.begin_nested():self.etl_revision(config_json=config)

    def test_enabled_target_unique_disabled_duplicate_allowed(self):
        _, rev=self.etl_revision(); self.mapping(rev)
        with self.assertRaises(IntegrityError),self.session.begin_nested():self.mapping(rev,ordinal=2)
        self.mapping(rev,ordinal=2,enabled=False)

    def test_mapping_transformation_source_literal_and_ordinal_constraints(self):
        _, rev=self.etl_revision()
        for changes in [dict(transformation='PYTHON'),dict(source_column=None),dict(ordinal=0),dict(target_column=''),
                        dict(transformation='CONSTANT',source_column=None),dict(transformation='NULL_HANDLING')]:
            with self.subTest(changes=changes),self.assertRaises(IntegrityError),self.session.begin_nested(): self.mapping(rev,**changes)
        self.mapping(rev,transformation='CONSTANT',source_column=None,default_literal={'logical_type':'integer','value':0})

    def test_restrict_retains_revision_mapping_and_upload(self):
        parent,rev=self.etl_revision();self.mapping(rev)
        for table,row_id in [('etl_definitions',parent.id),('etl_definition_revisions',rev.id),('definition_uploads',rev.upload_id)]:
            with self.assertRaises(IntegrityError),self.session.begin_nested():self.session.execute(text('DELETE FROM '+table+' WHERE id=:id'),{'id':row_id})
