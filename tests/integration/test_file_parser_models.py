"""T021 production ORM on disposable PostgreSQL; not binding/recovery acceptance."""

import hashlib
import importlib
import json
import unittest
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from tests.integration import test_connection_models as connection_tests


class FileParserModelTests(unittest.TestCase):
    setUpClass = classmethod(connection_tests.ConnectionModelTests.setUpClass.__func__)
    tearDown = connection_tests.ConnectionModelTests.tearDown

    def setUp(self):
        self.defs = importlib.import_module('aat_metadata.models.definitions')
        try:
            self.parsers = importlib.import_module('aat_metadata.models.file_parsers')
        except ModuleNotFoundError as exc:
            if exc.name != 'aat_metadata.models.file_parsers':
                raise
            raise AssertionError('T021 FileParserRevision is not implemented') from None
        connection_tests.ConnectionModelTests.setUp(self)

    def file(self, **changes):
        values = dict(original_name='synthetic.csv', sha256='a' * 64, bytes=12, extension='.csv',
                      encoding='utf-8', delimiter=',', header_present=True, quote_char='"',
                      escape_char=None, null_token='\\N')
        values.update(changes)
        row = self.defs.UploadedFile(**values)
        self.session.add(row); self.session.flush()
        return row

    def parser(self, file, number=1, **changes):
        values = dict(file_id=file.id, revision=number, encoding=file.encoding, delimiter=file.delimiter,
                      header_present=file.header_present, quote_char=file.quote_char,
                      escape_char=file.escape_char, null_token=file.null_token)
        values.update(changes)
        row = self.parsers.FileParserRevision(**values)
        self.session.add(row); self.session.flush()
        return row

    def immediate(self):
        self.session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))

    def test_complete_config_hash_and_null_round_trip(self):
        file = self.file(); parser = self.parser(file); self.immediate()
        self.session.refresh(parser)
        array = ['utf-8', ',', True, '"', None, '\\N']
        expected = hashlib.sha256(json.dumps(array, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(parser.config_sha256, expected)
        self.assertIsNone(parser.escape_char)
        self.assertEqual(parser.null_token, '\\N')
        self.assertIsNotNone(parser.created_at.utcoffset())
        self.assertEqual(file.revision, 1)

    def test_hash_distinguishes_null_escape_empty_escape_and_null_marker(self):
        file = self.file(); a = self.parser(file)
        b = self.parser(file, 2, escape_char='', null_token='')
        self.assertNotEqual(a.config_sha256, b.config_sha256)
        self.assertEqual(b.escape_char, '')
        self.assertEqual(b.null_token, '')

    def test_unicode_config_and_supplied_hash_are_verified_by_database(self):
        file = self.file(delimiter='\t', header_present=False, null_token='rỗng')
        array = ['utf-8', '\t', False, '"', None, 'rỗng']
        expected = hashlib.sha256(json.dumps(array, ensure_ascii=False).encode()).hexdigest()
        parser = self.parser(file, config_sha256=expected)
        self.immediate(); self.session.refresh(parser)
        self.assertEqual(parser.config_sha256, expected)
        self.assertFalse(parser.header_present)
        self.assertEqual(parser.delimiter, '\t')

    def test_committed_file_and_parser_history_survive_new_sessions(self):
        # Independent transactions in the disposable DB exercise deferred FK at
        # real COMMIT, rather than only SET CONSTRAINTS inside a rolled-back test.
        with Session(self.engine) as session:
            file = self.defs.UploadedFile(original_name='committed.txt', extension='.txt',
                sha256='b' * 64, bytes=7, encoding='utf-8', delimiter='|',
                header_present=False, quote_char='"', escape_char=None, null_token='')
            session.add(file); session.flush(); file_id = file.id
            session.add(self.parsers.FileParserRevision(file_id=file_id, revision=1,
                encoding='utf-8', delimiter='|', header_present=False, quote_char='"', null_token=''))
            session.commit()
        with Session(self.engine) as session:
            file = session.get(self.defs.UploadedFile, file_id)
            session.add(self.parsers.FileParserRevision(file_id=file_id, revision=2,
                encoding='utf-8', delimiter=';', header_present=False, quote_char='"', null_token=''))
            session.flush(); file.parser_revision = 2; session.commit()
        with Session(self.engine) as session:
            file = session.get(self.defs.UploadedFile, file_id)
            self.assertEqual((file.parser_revision, file.revision, file.sha256), (2, 2, 'b' * 64))
            self.assertEqual(session.scalar(text('SELECT count(*) FROM file_parser_revisions WHERE file_id=:id'),
                                            {'id': file_id}), 2)

    def test_unique_file_revision_but_same_revision_on_other_file(self):
        file = self.file(); self.parser(file)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.parser(file)
        other = self.file(); self.parser(other); self.immediate()

    def test_file_fk_restricts_delete_and_rejects_missing_parent(self):
        file = self.file(); self.parser(file); self.immediate()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(text('DELETE FROM uploaded_files WHERE id=:id'), {'id': file.id})
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.add(self.parsers.FileParserRevision(file_id=uuid4(), revision=1,
                encoding='utf-8', delimiter=',', header_present=True, quote_char='"', null_token='\\N'))
            self.session.flush()

    def test_current_revision_fk_restricts_delete(self):
        file = self.file(); parser = self.parser(file); self.immediate()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(text('DELETE FROM file_parser_revisions WHERE id=:id'), {'id': parser.id})

    def test_csv_requires_initial_history_at_transaction_boundary(self):
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.file(); self.immediate()

    def test_xlsx_does_not_require_delimited_parser(self):
        file = self.file(extension='.xlsx'); self.immediate()
        self.assertIsNone(file.parser_file_id)

    def test_current_pointer_cannot_reference_other_file_or_missing_revision(self):
        file = self.file(); self.parser(file)
        other = self.file(); self.parser(other); self.parser(other, 2)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            file.parser_revision = 2; self.session.flush(); self.immediate()

    def test_initial_snapshot_must_match_file_and_xlsx_cannot_have_parser(self):
        file = self.file()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.parser(file, delimiter=';')
        xlsx = self.file(extension='.xlsx')
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.parser(xlsx)

    def test_parser_boundaries_reject_invalid_config_or_hash(self):
        file = self.file(); self.parser(file)
        for changes in [dict(revision=0), dict(encoding=''), dict(delimiter=''), dict(delimiter=';;'),
                        dict(quote_char=''), dict(quote_char='""'), dict(config_sha256='f' * 64)]:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), self.session.begin_nested():
                number = changes.pop('revision', 2)
                self.parser(file, number, **changes)
        for changes in [dict(encoding=None), dict(delimiter=None), dict(header_present=None),
                        dict(quote_char=None), dict(null_token=None)]:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.parser(file, 2, **changes)

    def test_history_is_immutable_in_orm_and_direct_sql(self):
        file = self.file(); parser = self.parser(file)
        for column, value in [('delimiter', ';'), ('encoding', 'latin-1'), ('header_present', False),
                              ('quote_char', "'"), ('escape_char', '\\'), ('null_token', ''),
                              ('config_sha256', 'f' * 64), ('revision', 2), ('file_id', uuid4()),
                              ('id', uuid4())]:
            with self.subTest(column=column), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('UPDATE file_parser_revisions SET ' + column + '=:v WHERE id=:id'),
                                     {'v': value, 'id': parser.id})
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            parser.delimiter = ';'; self.session.flush()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(text("UPDATE file_parser_revisions SET created_at=created_at+interval '1 second' WHERE id=:id"),
                                 {'id': parser.id})

    def test_edit_appends_snapshot_and_advances_etag_preserving_content(self):
        file = self.file(); old = self.parser(file); old_hash = old.config_sha256
        new = self.parser(file, 2, delimiter=';')
        file.parser_revision = 2; self.session.flush(); self.immediate(); self.session.expire_all()
        self.assertEqual(file.revision, 2)
        self.assertEqual(file.parser_revision, 2)
        self.assertEqual(file.sha256, 'a' * 64)
        self.assertEqual(file.bytes, 12)
        self.assertEqual(file.delimiter, ',')
        self.assertEqual(old.config_sha256, old_hash)
        self.assertEqual(old.delimiter, ',')
        self.assertEqual(new.delimiter, ';')

    def test_pointer_rollback_or_direct_etag_forgery_is_rejected(self):
        file = self.file(); self.parser(file); self.parser(file, 2)
        file.parser_revision = 2; self.session.flush()
        for column, value in [('parser_revision', 1), ('revision', 0), ('revision', 100)]:
            with self.subTest(column=column), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('UPDATE uploaded_files SET ' + column + '=:v WHERE id=:id'),
                                     {'v': value, 'id': file.id})

    def test_direct_sql_update_bumps_etag_and_stale_orm_write_fails(self):
        file = self.file(); self.parser(file)
        self.session.execute(text("UPDATE uploaded_files SET validation_status='VALID' WHERE id=:id"), {'id': file.id})
        # Separate ORM identity map over the same real transaction sees version2.
        with Session(bind=self.connection, join_transaction_mode='create_savepoint') as other:
            row = other.get(self.defs.UploadedFile, file.id)
            self.assertEqual(row.revision, 2)
        with self.assertRaises(StaleDataError), self.session.begin_nested():
            file.validation_status = 'INVALID'; self.session.flush()
