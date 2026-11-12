"""T148: real metadata encryption and public/internal admission boundaries."""
import unittest
from uuid import uuid4
from sqlalchemy import text
from tests.api import test_connections as connection_fixtures


class SecuritySurfaceTests(unittest.TestCase):
    setUp=connection_fixtures.ConnectionAPITests.setUp
    payload=connection_fixtures.ConnectionAPITests.payload
    request=connection_fixtures.ConnectionAPITests.request
    create=connection_fixtures.ConnectionAPITests.create

    def test_credentials_are_encrypted_in_metadata_and_absent_from_public_reads(self):
        from aat_api.services.connections.service import transaction,codec
        identity=self.create().json()['id']
        with transaction() as session:
            row=session.execute(text('SELECT s.key_id,s.ciphertext FROM connection_secrets s JOIN connection_revisions r ON r.secret_id=s.id JOIN connections c ON c.current_revision_id=r.id WHERE c.id=:id'),{'id':identity}).one()
            self.assertTrue(self.secret not in str(row.ciphertext),'Metadata must not store the plaintext credential')
            self.assertTrue(codec().decrypt(row.key_id,row.ciphertext)==self.secret,'Ciphertext must remain recoverable with the separate keyring')
        for path in ('/connections/'+identity,'/connections?search='+self.prefix,'/settings'):
            response=self.client.get('/api/v1'+path)
            self.assertEqual(response.status_code,200)
            self.assertTrue(self.secret not in response.text,'Public read exposed a credential')
            self.assertNotIn('"ciphertext"',response.text)
            self.assertNotIn('"password"',response.text)
            self.assertNotIn('postgresql://',response.text)

    def test_foreign_origin_and_unsafe_hosts_have_no_metadata_side_effect(self):
        from aat_api.services.connections.service import transaction
        def count():
            with transaction() as session:return session.scalar(text('SELECT count(*) FROM connections WHERE normalized_code LIKE :prefix'),{'prefix':self.prefix+'%'})
        baseline=count()
        foreign=self.client.post('/api/v1/connections',headers={'Origin':'https://untrusted.invalid'},json=self.payload())
        self.assertEqual(foreign.status_code,403)
        for host in ('http://169.254.169.254/latest/meta-data/','../../secrets','postgres; SELECT 1'):
            response=self.client.post('/api/v1/connections',json=self.payload(host=host))
            self.assertEqual(response.status_code,422)
            self.assertTrue(self.secret not in response.text,'Validation error exposed a credential')
            self.assertNotIn('Traceback',response.text)
        self.assertEqual(count(),baseline,'Rejected requests must not create connection metadata')

    def test_private_bind_requires_authentication_and_public_alias_is_absent(self):
        from aat_api.services.connections.service import transaction
        def count():
            with transaction() as session:return session.scalar(text('SELECT count(*) FROM execution_bindings'))
        baseline=count()
        payload={'dag_id':'security_'+uuid4().hex,'run_id':'manual__security','task_id':'execute_etl','expected_revision':str(uuid4())}
        response=self.client.post('/internal/runtime/bind',json=payload)
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.client.post('/api/v1/internal/runtime/bind',json=payload).status_code,404)
        self.assertEqual(count(),baseline,'Unauthorized bind must not persist an execution identity')
