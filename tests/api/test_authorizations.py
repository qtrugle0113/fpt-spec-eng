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
                    headers={'If-Match':'"1"','Idempotency-Key':str(uuid4())},**({'json':{'acknowledged':True}} if method=='post' else {}))
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

class AuthorizationCreateTests(unittest.TestCase):
    setUp=builder.ETLPreviewIntegrationTests.setUp
    target=builder.ETLPreviewIntegrationTests.target
    wait=builder.ETLPreviewIntegrationTests.wait
    response=builder.ETLPreviewIntegrationTests.response
    scenario=builder.ETLPreviewIntegrationTests.scenario

    def request(self,scheduled=False,**changes):
        from uuid import UUID
        from aat_api.schemas.authorizations import AuthorizationRequest
        from aat_api.services.etl_preview import preview
        def edit(book,*_):
            sheet=book['ETL_Definitions'];sheet['O2']='FULL_REFRESH'
            if scheduled:sheet['K2']='0 0 * * *';sheet['L2']='2026-11-01T00:00:00Z'
        uploaded,result,_,_,_=self.scenario(edit=edit)
        self.assertEqual(result['state'],'SUCCEEDED')
        current=preview(UUID(uploaded['id']));item=current['items'][0]
        payload=dict(revision_id=item['id'],physical_target_id=item['config']['target']['physical_target_id'],
            scope='ONCE',allow_empty=False,acknowledged=True,confirmation_token=current['confirmation_token'])
        payload.update(changes)
        return UUID(item['definition_id']),AuthorizationRequest.model_validate(payload)

    def test_grant_is_persisted_and_same_request_replays_without_new_confirmation(self):
        from unittest.mock import patch
        from aat_api.services import replacement_authorizations as service
        identity,value=self.request();key=uuid4()
        created=service.grant(identity,value,key)
        self.assertEqual(created['state'],'GRANTED');self.assertFalse(created['allow_empty'])
        self.assertFalse(created['replacement_in_progress'])
        with patch.object(service,'preview',side_effect=AssertionError('Replay must return existing authority')):
            replay=service.grant(identity,value,key)
        self.assertEqual(replay['id'],created['id']);self.assertEqual(replay['scope_sha256'],created['scope_sha256'])

    def test_empty_permission_is_separate_and_scheduled_manual_is_rejected(self):
        from pydantic import ValidationError
        from aat_api.errors import APIError
        from aat_api.services import replacement_authorizations as service
        with self.assertRaises(ValidationError):self.request(allow_empty=True)
        identity,value=self.request(allow_empty=True,allow_empty_acknowledged=True)
        self.assertTrue(service.grant(identity,value,uuid4())['allow_empty'])
        identity,value=self.request(scope='SCHEDULED')
        with self.assertRaises(APIError):service.grant(identity,value,uuid4())

    def test_target_scope_and_idempotency_payload_changes_are_rejected(self):
        from aat_api.errors import APIError
        from aat_api.services import replacement_authorizations as service
        identity,value=self.request();key=uuid4()
        service.grant(identity,value,key)
        with self.assertRaises(APIError):service.grant(identity,value.model_copy(update={'allow_empty':True,'allow_empty_acknowledged':True}),key)
        with self.assertRaises(APIError):service.grant(identity,value.model_copy(update={'physical_target_id':'a'*64}),uuid4())

    def test_http_grant_history_revoke_etag_and_replay(self):
        identity,value=self.request()
        path='/etl-definitions/{id}/replacement-authorizations'
        response=self.client.post('/api/v1'+path.replace('{id}',str(identity)),json=value.model_dump(mode='json'),
            headers={'Idempotency-Key':str(uuid4())})
        authority=self.response(response,'post',path,201)
        etag=response.headers['etag'];self.assertEqual(etag,'"1"')
        listing=self.client.get('/api/v1'+path.replace('{id}',str(identity)))
        page=self.response(listing,'get',path,200);self.assertEqual(page['items'][0]['id'],authority['id'])
        detail=self.client.get('/api/v1/replacement-authorizations/'+authority['id'])
        self.response(detail,'get','/replacement-authorizations/{id}',200)
        key=str(uuid4());headers={'Idempotency-Key':key,'If-Match':etag}
        url='/api/v1/replacement-authorizations/'+authority['id']+'/revoke'
        self.assertEqual(self.client.post(url,headers=headers,json={'acknowledged':False}).status_code,422)
        revoked=self.response(self.client.post(url,headers=headers,json={'acknowledged':True}),'post','/replacement-authorizations/{id}/revoke',200)
        self.assertEqual(revoked['state'],'REVOKED');self.assertGreater(revoked['revision'],1)
        self.assertEqual(self.client.post(url,headers=headers,json={'acknowledged':True}).json()['id'],authority['id'])
        self.assertEqual(self.client.post(url,headers={**headers,'Idempotency-Key':str(uuid4())},json={'acknowledged':True}).status_code,412)

    def test_scheduled_scope_pins_schedule_and_connection_change_invalidates_grant(self):
        from aat_api.services import replacement_authorizations as service
        from aat_api.services.connections import service as connections
        from aat_api.services.connections.service import transaction
        from aat_api.schemas.connections import ConnectionPatch
        from aat_metadata.models.etl import ETLDefinitionRevision
        from aat_metadata.models.connections import ConnectionRevision
        from aat_metadata.models.authorizations import DataReplacementAuthorization
        from aat_metadata.repositories.bindings import schedule_hash
        from uuid import UUID
        identity,value=self.request(scheduled=True,scope='SCHEDULED')
        authority=service.grant(identity,value,uuid4())
        with transaction() as session:
            config=session.get(ETLDefinitionRevision,value.revision_id).config_json
            self.assertEqual(authority['schedule_sha256'],schedule_hash(config))
            target=session.get(ConnectionRevision,UUID(config['target']['connection_revision_id']))
            connection_id,revision=target.connection_id,target.revision
        connections.patch(connection_id,revision,ConnectionPatch(password='synthetic-rotated-value'))
        with transaction() as session:
            self.assertEqual(session.get(DataReplacementAuthorization,authority['id']).state,'INVALIDATED')
