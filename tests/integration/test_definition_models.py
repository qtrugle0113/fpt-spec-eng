"""T020 actual model DDL on disposable PostgreSQL, plus T019 real dependency."""

import importlib
import unittest
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration import test_connection_models as connection_tests


class DefinitionModelTests(unittest.TestCase):
    setUpClass = classmethod(connection_tests.ConnectionModelTests.setUpClass.__func__)
    tearDown = connection_tests.ConnectionModelTests.tearDown
    connection_row = connection_tests.ConnectionModelTests.connection_row
    revision = connection_tests.ConnectionModelTests.revision

    def setUp(self):
        try:
            self.defs = importlib.import_module('aat_metadata.models.definitions')
        except ModuleNotFoundError as exc:
            if exc.name != 'aat_metadata.models.definitions':
                raise
            raise AssertionError('T020 definition models are not implemented') from None
        connection_tests.ConnectionModelTests.setUp(self)

    def upload(self, **changes):
        file = self.defs.UploadedFile(original_name='../../untrusted.xlsx', sha256='a' * 64,
                                      bytes=10, extension='.xlsx')
        self.session.add(file); self.session.flush()
        values = dict(kind='TABLE', uploaded_file_id=file.id, template_version='1.0',
                      workbook_sha256=file.sha256, status='VALIDATED')
        values.update(changes)
        upload = self.defs.DefinitionUpload(**values)
        self.session.add(upload); self.session.flush()
        return file, upload

    def table(self, upload=None, revision=None, **changes):
        if upload is None:
            _, upload = self.upload()
        if revision is None:
            parent = self.connection_row()
            revision, _ = self.revision(parent, physical_server_fingerprint='b' * 64)
        values = dict(upload_id=upload.id, target_connection_revision_id=revision.id,
                      target_schema='public', table_name='t_' + uuid4().hex, definition_hash='c' * 64)
        values.update(changes)
        row = self.defs.TableDefinition(**values)
        self.session.add(row); self.session.flush()
        return row

    def column(self, table, **changes):
        values = dict(table_definition_id=table.id, name='id', ordinal=1,
                      logical_type='integer', nullable=False, primary_key_ordinal=1)
        values.update(changes)
        row = self.defs.TableColumn(**values)
        self.session.add(row); self.session.flush()
        return row

    def test_storage_key_is_server_generated_and_not_original_filename(self):
        file, _ = self.upload()
        self.assertRegex(file.safe_storage_key, r'^[0-9a-f]{32}$')
        self.assertNotIn('untrusted', file.safe_storage_key)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            bad = self.defs.UploadedFile(original_name='x', safe_storage_key='../../x',
                                        sha256='a' * 64, bytes=1, extension='.xlsx')
            self.session.add(bad); self.session.flush()

    def test_upload_content_identity_and_initial_parser_snapshot_are_immutable(self):
        file, _ = self.upload()
        for column, value in [('sha256', 'd' * 64), ('bytes', 20), ('safe_storage_key', uuid4().hex),
                              ('delimiter', ';')]:
            with self.subTest(column=column), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('UPDATE uploaded_files SET ' + column + '=:v WHERE id=:id'), {'v': value, 'id': file.id})

    def test_checksum_size_and_extension_boundaries(self):
        for values in ({'sha256': 'bad'}, {'bytes': -1}, {'extension': '.exe'}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), self.session.begin_nested():
                data = dict(original_name='x', sha256='a' * 64, bytes=1, extension='.xlsx'); data.update(values)
                self.session.add(self.defs.UploadedFile(**data)); self.session.flush()

    def test_definition_kind_version_and_checksum_bind_to_file(self):
        for changes in ({'kind': 'SQL'}, {'template_version': '2.0'}, {'workbook_sha256': 'd' * 64}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.upload(**changes)

    def test_issue_workbook_null_location_and_cell_one_based(self):
        _, upload = self.upload()
        issue = self.defs.DefinitionIssue(upload_id=upload.id, code='INVALID_WORKBOOK', scope='workbook',
                                          severity='ERROR', message_key='invalid_workbook')
        self.session.add(issue); self.session.flush()
        self.assertIsNone(issue.row); self.assertIsNone(issue.column)
        for scope, row, column in [('workbook', 1, None), ('cell', 0, 1), ('cell', 1, 0)]:
            with self.subTest(scope=scope,row=row,column=column), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.add(self.defs.DefinitionIssue(upload_id=upload.id, code='INVALID_CELL', scope=scope,
                    sheet='Columns', row=row, column=column, severity='ERROR', message_key='invalid_cell'))
                self.session.flush()

    def test_issue_safe_context_rejects_raw_cell_secret(self):
        _, upload = self.upload()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.add(self.defs.DefinitionIssue(upload_id=upload.id, code='INVALID_CELL', scope='workbook',
                severity='ERROR', message_key='invalid_cell', safe_context={'raw_value': 'synthetic-secret'}))
            self.session.flush()

    def test_orphan_upload_issue_table_and_column_fk_rejected(self):
        for kind in ('issue', 'table', 'column'):
            with self.subTest(kind=kind), self.assertRaises(IntegrityError), self.session.begin_nested():
                if kind == 'issue':
                    self.session.add(self.defs.DefinitionIssue(upload_id=uuid4(), code='INVALID', scope='workbook', severity='ERROR', message_key='invalid'))
                elif kind == 'table':
                    self.table(upload_id=uuid4())
                else:
                    self.session.add(self.defs.TableColumn(table_definition_id=uuid4(), name='x', ordinal=1, logical_type='integer', nullable=True))
                self.session.flush()

    def test_table_unique_by_physical_identity_across_credential_revisions(self):
        _, upload = self.upload(); parent = self.connection_row()
        one, _ = self.revision(parent, 1, physical_server_fingerprint='b' * 64)
        two, _ = self.revision(parent, 2, physical_server_fingerprint='b' * 64)
        first = self.table(upload, one, table_name='same_physical')
        self.assertIsNotNone(first.physical_table_identity)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.table(upload, two, table_name='same_physical')

    def test_unknown_physical_server_identity_is_rejected(self):
        parent = self.connection_row(); revision, _ = self.revision(parent)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.table(revision=revision)

    def test_column_names_ordinals_and_primary_key_ordinals_are_unique(self):
        table = self.table(); self.column(table)
        for values in ({'name': 'id', 'ordinal': 2, 'primary_key_ordinal': 2},
                       {'name': 'other', 'ordinal': 1, 'primary_key_ordinal': 2},
                       {'name': 'other', 'ordinal': 2, 'primary_key_ordinal': 1}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.column(table, **values)

    def test_composite_pk_order_matches_column_order_and_key_not_nullable(self):
        table = self.table(); self.column(table)
        self.column(table, name='second', ordinal=3, primary_key_ordinal=2)
        for values in ({'name': 'middle', 'ordinal': 2, 'primary_key_ordinal': 3},
                       {'name': 'nullable_key', 'ordinal': 4, 'primary_key_ordinal': 3, 'nullable': True}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.column(table, **values)

    def test_type_length_precision_scale_boundaries(self):
        table = self.table()
        for values in ({'logical_type': 'varchar', 'length': 0}, {'logical_type': 'varchar', 'length': 65536},
                       {'logical_type': 'decimal', 'precision': 2, 'scale': 3},
                       {'logical_type': 'integer', 'length': 10}, {'logical_type': 'arbitrary_sql'}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.column(table, **values)

    def test_tagged_defaults_preserve_decimal_text_and_explicit_null(self):
        table = self.table()
        value = '12345678901234567890.123456789'
        decimal = self.column(table, logical_type='decimal', precision=38, scale=9, nullable=True,
                              primary_key_ordinal=None, default_literal={'logical_type':'decimal', 'value':value})
        null = self.column(table, name='null_value', ordinal=2, nullable=True, primary_key_ordinal=None,
                           default_literal={'logical_type':'integer', 'value':None})
        absent = self.column(table, name='no_default', ordinal=3, nullable=True, primary_key_ordinal=None)
        self.session.expire_all()
        self.assertEqual(decimal.default_literal['value'], value)
        self.assertEqual(null.default_literal, {'logical_type':'integer', 'value':None})
        self.assertIsNone(absent.default_literal)

    def test_defaults_reject_float_untagged_expression_and_type_mismatch(self):
        table = self.table()
        for literal in (1.25, {'logical_type':'decimal', 'value':1.25},
                        {'logical_type':None, 'value':1},
                        {'logical_type':'integer','value':True}, {'logical_type':'text','value':'x'},
                        {'logical_type':'integer','value':1,'expression':'now()'}):
            with self.subTest(literal=literal), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.column(table, default_literal=literal)

    def test_delete_restrict_keeps_upload_table_column_history(self):
        file, upload = self.upload(); table = self.table(upload=upload); self.column(table)
        for name, identity in [('uploaded_files',file.id), ('definition_uploads',upload.id), ('table_definitions',table.id)]:
            with self.subTest(table=name), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('DELETE FROM '+name+' WHERE id=:id'), {'id':identity})

    def test_t019_real_table_dependency_blocks_code_change_in_orm_and_sql(self):
        parent = self.connection_row(); revision, _ = self.revision(parent, physical_server_fingerprint='b'*64)
        self.table(revision=revision)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(text('UPDATE connections SET code=:code WHERE id=:id'), {'code':'changed','id':parent.id})
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            parent.code = 'changed_again'; self.session.flush()
        other = self.connection_row(); other.code='allowed_'+uuid4().hex; self.session.flush()


if __name__ == '__main__':
    unittest.main()
