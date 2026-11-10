"""T096: replacement authority must remain explicit through public API gates."""
import unittest
from uuid import uuid4
from tests.api import test_dag_builder as builder


class AuthorizationContractTests(unittest.TestCase):
    setUp=builder.DAGBuilderContractTests.setUp

    def test_missing_authority_detail_list_and_revoke_are_safe_errors(self):
        identity=str(uuid4())
        for method,path in (('get','/etl-definitions/{id}/replacement-authorizations'),
                            ('get','/replacement-authorizations/{id}'),
                            ('post','/replacement-authorizations/{id}/revoke')):
            with self.subTest(path=path):
                response=self.client.request(method,'/api/v1'+path.replace('{id}',identity),
                    headers={'If-Match':'"1"','Idempotency-Key':str(uuid4())})
                self.assertEqual(response.status_code,404)
                self.harness.assert_response(method,path,'default',response.json(),headers=response.headers)

    def test_grant_cannot_acknowledge_empty_replacement_implicitly(self):
        path='/etl-definitions/{id}/replacement-authorizations'
        request=dict(revision_id=str(uuid4()),physical_target_id='a'*64,scope='ONCE',allow_empty=True,
                     acknowledged=True,confirmation_token='stale')
        response=self.client.post('/api/v1'+path.replace('{id}',str(uuid4())),json=request,
            headers={'Idempotency-Key':str(uuid4())})
        self.assertEqual(response.status_code,422)
        self.harness.assert_response('post',path,'default',response.json(),headers=response.headers)

    def test_trigger_needs_an_idempotency_key_and_state_needs_if_match(self):
        for method,path,body in (('post','/dags/{dag_id}/trigger',{}),
                                 ('patch','/dags/{dag_id}/state',{'is_paused':False})):
            with self.subTest(path=path):
                response=self.client.request(method,'/api/v1'+path.replace('{dag_id}','missing'),json=body)
                self.assertEqual(response.status_code,422)
                self.harness.assert_response(method,path,'default',response.json(),headers=response.headers)
