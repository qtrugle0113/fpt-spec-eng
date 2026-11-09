"""T023-T026 real dependency graph, not replacement target execution."""
import importlib
import unittest
from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration import test_t022_models as etl_tests
from tests.integration import test_connection_models as connections


class AuthorizationModelTests(unittest.TestCase):
    setUpClass=classmethod(connections.ConnectionModelTests.setUpClass.__func__)
    tearDown=connections.ConnectionModelTests.tearDown
    connection_row=connections.ConnectionModelTests.connection_row
    revision=connections.ConnectionModelTests.revision
    upload=etl_tests.ETLModelTests.upload
    etl_revision=etl_tests.ETLModelTests.etl_revision

    def setUp(self):
        self.etl=importlib.import_module('aat_metadata.models.etl')
        self.defs=importlib.import_module('aat_metadata.models.definitions')
        for name in ['authorizations','operations','runtime','replacement_runs']:
            try: setattr(self,name,importlib.import_module('aat_metadata.models.'+name))
            except ModuleNotFoundError as exc:
                if exc.name!='aat_metadata.models.'+name: raise
                raise AssertionError('Phase2 actual model missing: '+name) from None
        connections.ConnectionModelTests.setUp(self)

    def authorization(self,**changes):
        parent,rev=self.etl_revision()
        values=dict(dag_id=parent.dag_id,etl_revision_id=rev.id,physical_target_id='a'*64,
            scope='ONCE',scope_sha256='b'*64,acknowledged_at=datetime.now(timezone.utc))
        values.update(changes);row=self.authorizations.DataReplacementAuthorization(**values)
        self.session.add(row);self.session.flush();return row

    def test_authorization_defaults_acknowledgment_and_scope_checks(self):
        row=self.authorization();self.assertFalse(row.allow_empty);self.assertEqual(row.revision,1)
        for changes in [dict(scope='ANY'),dict(state='EXPIRED'),dict(allow_empty=True),
                        dict(scope='SCHEDULED'),dict(scope_sha256='bad')]:
            with self.subTest(changes=changes),self.assertRaises(IntegrityError),self.session.begin_nested():self.authorization(**changes)

    def test_authorization_scope_snapshot_immutable_but_revoke_allowed(self):
        row=self.authorization()
        for column,value in [('allow_empty',True),('scope','SCHEDULED'),('scope_sha256','c'*64)]:
            with self.subTest(column=column),self.assertRaises(IntegrityError),self.session.begin_nested():
                self.session.execute(text('UPDATE replacement_authorizations SET '+column+'=:v WHERE id=:id'),{'v':value,'id':row.id})
        row.state='REVOKED';row.revoked_at=datetime.now(timezone.utc);self.session.flush()

    def test_reservation_pointer_restrict_fk_and_cannot_be_released(self):
        row=self.authorization()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            row.reserved_intent_id=uuid4();self.session.flush();self.session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))

    def test_authorization_dag_must_own_etl_revision(self):
        parent,_=self.etl_revision()
        with self.assertRaises(IntegrityError),self.session.begin_nested():self.authorization(dag_id=parent.dag_id)

