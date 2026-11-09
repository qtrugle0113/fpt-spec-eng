"""T019 real PostgreSQL/real ORM DDL tests; explicitly not Alembic acceptance."""

import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aat_metadata.secrets.codec import SecretCodec


class ConnectionModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dsn = os.environ.get('AAT_FOUNDATION_TEST_DSN')
        if not dsn or os.environ.get('AAT_FOUNDATION_DISPOSABLE') != '1':
            raise RuntimeError('T019 requires explicit disposable PostgreSQL, never existing volumes')
        cls.engine = create_engine(dsn.replace('postgresql://', 'postgresql+psycopg://', 1), hide_parameters=True)
        cls.addClassCleanup(cls.engine.dispose)
        cls.schema_created = False

    def setUp(self):
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(text('SELECT current_database()')), 'app_metadata')
        try:
            self.models = importlib.import_module('aat_metadata.models.connections')
        except ModuleNotFoundError as exc:
            if exc.name not in {'aat_metadata.models', 'aat_metadata.models.connections'}:
                raise
            raise AssertionError('T019 Connection/Revision/Secret models are not implemented') from None
        if not type(self).schema_created:
            self.models.Base.metadata.create_all(self.engine)
            type(self).schema_created = True
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection)
        self.temp = tempfile.TemporaryDirectory()
        self.keyring = Path(self.temp.name)
        key_id = uuid4().hex
        (self.keyring / (key_id + '.key')).write_bytes(Fernet.generate_key())
        (self.keyring / 'current.json').write_text(json.dumps({'key_id': key_id}))
        self.codec = SecretCodec(self.keyring)

    def tearDown(self):
        if hasattr(self, 'session'):
            self.session.close()
            if self.transaction.is_active:
                self.transaction.rollback()
            self.connection.close()
            self.temp.cleanup()

    def connection_row(self, code=None, **changes):
        values = dict(code=code or 't019_' + uuid4().hex, name='Synthetic connection', database_type='POSTGRESQL')
        values.update(changes)
        row = self.models.Connection(**values)
        self.session.add(row); self.session.flush()
        return row

    def revision(self, parent, number=1, **changes):
        secret = self.models.ConnectionSecret.from_plaintext(self.codec, 'synthetic-password')
        self.session.add(secret); self.session.flush()
        values = dict(connection_id=parent.id, revision=number, host='fixture.invalid', port=5432,
                      database_name='synthetic', schema_name='public', username='synthetic', secret_id=secret.id)
        values.update(changes)
        row = self.models.ConnectionRevision(**values)
        self.session.add(row); self.session.flush()
        return row, secret

    def test_normalized_code_is_trimmed_case_insensitive_unique_in_db(self):
        parent = self.connection_row(code='  Sales_19  ')
        self.session.refresh(parent)
        self.assertEqual(parent.code, 'Sales_19')
        self.assertEqual(parent.normalized_code, 'sales_19')
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.connection_row(code='SALES_19')

    def test_database_type_and_nonempty_required_values_are_db_constraints(self):
        for changes in ({'database_type': 'SQLITE'}, {'code': '  '}, {'name': '  '}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.connection_row(**changes)
        self.assertEqual(self.connection_row(database_type='MYSQL').database_type, 'MYSQL')

    def test_revision_unique_per_connection_and_positive(self):
        parent = self.connection_row(); self.revision(parent)
        for number in (1, 0):
            with self.subTest(number=number), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.revision(parent, number)

    def test_port_boundaries_are_enforced_by_postgresql(self):
        parent = self.connection_row()
        for n, port in enumerate((1, 65535), 1):
            self.assertEqual(self.revision(parent, n, port=port)[0].port, port)
        for port in (0, 65536):
            with self.subTest(port=port), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.revision(parent, 3, port=port)

    def test_secret_and_connection_fk_reject_orphans(self):
        parent = self.connection_row()
        for changes in ({'secret_id': uuid4()}, {'connection_id': uuid4()}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.revision(parent, **changes)

    def test_restrict_delete_preserves_revision_and_secret_history(self):
        parent = self.connection_row(); revision, secret = self.revision(parent)
        for table, identity in [('connections', parent.id), ('connection_secrets', secret.id)]:
            with self.subTest(table=table), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('DELETE FROM ' + table + ' WHERE id=:id'), {'id': identity})

    def test_current_revision_must_belong_to_same_connection(self):
        one = self.connection_row(); two = self.connection_row()
        revision, _ = self.revision(one)
        one.current_revision_id = revision.id; self.session.flush()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            two.current_revision_id = revision.id; self.session.flush()

    def test_direct_sql_cannot_mutate_revision_endpoint_or_credential(self):
        parent = self.connection_row(); revision, _ = self.revision(parent)
        for column, value in [('host', 'changed.invalid'), ('port', 3306), ('database_name', 'changed'),
                              ('schema_name', 'changed'), ('username', 'changed'), ('secret_id', uuid4()), ('revision', 2)]:
            with self.subTest(column=column), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('UPDATE connection_revisions SET ' + column + '=:v WHERE id=:id'), {'v': value, 'id': revision.id})

    def test_orm_revision_update_is_also_blocked_but_test_status_is_mutable(self):
        parent = self.connection_row(); revision, _ = self.revision(parent)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            revision.host = 'changed.invalid'; self.session.flush()
        revision = self.session.get(self.models.ConnectionRevision, revision.id)
        revision.test_status = 'SUCCESS'; self.session.flush()
        self.assertEqual(revision.test_status, 'SUCCESS')

    def test_database_type_is_snapshotted_so_parent_edit_does_not_change_old_revision(self):
        parent = self.connection_row(); old, _ = self.revision(parent)
        self.assertEqual(old.database_type, 'POSTGRESQL')
        parent.database_type = 'MYSQL'; self.session.flush()
        new, _ = self.revision(parent, 2)
        self.session.refresh(old)
        self.assertEqual((old.database_type, new.database_type), ('POSTGRESQL', 'MYSQL'))
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(text('UPDATE connection_revisions SET database_type=:v WHERE id=:id'),
                                 {'v': 'MYSQL', 'id': old.id})

    def test_codec_ciphertext_roundtrip_has_no_plaintext_and_safe_projection(self):
        parent = self.connection_row(); revision, secret = self.revision(parent)
        self.assertNotEqual(secret.ciphertext, 'synthetic-password')
        self.assertEqual(self.codec.decrypt(secret.key_id, secret.ciphertext), 'synthetic-password')
        public = json.dumps([parent.public_dict(), revision.public_dict()], default=str)
        self.assertNotIn('ciphertext', public); self.assertNotIn('password', public)
        self.assertNotIn(secret.ciphertext, public)
        self.assertNotIn(secret.ciphertext, repr(secret))
        with self.assertRaises(TypeError):
            secret.public_dict()

    def test_plaintext_secret_rejected_by_model_and_database(self):
        with self.assertRaises(ValueError):
            self.models.ConnectionSecret(ciphertext='synthetic-password', key_id=uuid4().hex)
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(text('INSERT INTO connection_secrets(id,ciphertext,key_id) VALUES (:id,:cipher,:key)'),
                                    {'id': uuid4(), 'cipher': 'synthetic-password', 'key': uuid4().hex})

    def test_stored_ciphertext_and_key_id_are_immutable(self):
        parent = self.connection_row(); _, secret = self.revision(parent)
        other_key, other_cipher = self.codec.encrypt('different-synthetic-password')
        for column, value in [('ciphertext', other_cipher), ('key_id', uuid4().hex)]:
            with self.subTest(column=column), self.assertRaises(IntegrityError), self.session.begin_nested():
                self.session.execute(text('UPDATE connection_secrets SET ' + column + '=:v WHERE id=:id'), {'v': value, 'id': secret.id})

    def test_secret_not_readable_by_airflow_or_public_default_grants(self):
        parent = self.connection_row(); self.revision(parent)
        self.assertFalse(self.connection.scalar(text("SELECT has_table_privilege('aat_airflow','connection_secrets','SELECT')")))
        self.assertFalse(self.connection.scalar(text("SELECT EXISTS(SELECT 1 FROM information_schema.role_table_grants WHERE table_name='connection_secrets' AND grantee='PUBLIC')")))

    def test_code_can_change_before_business_dependency_and_updated_at_is_aware(self):
        parent = self.connection_row(); self.revision(parent)
        parent.code = 'renamed_' + uuid4().hex; self.session.flush(); self.session.refresh(parent)
        self.assertEqual(parent.normalized_code, parent.code.lower())
        self.assertIsNotNone(parent.created_at.tzinfo)


if __name__ == '__main__':
    unittest.main()
