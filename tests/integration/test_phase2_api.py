"""Real ASGI error/origin boundary; no dependency responses are mocked."""
import asyncio
import importlib
import unittest
from uuid import UUID
import httpx


class FoundationAPITests(unittest.TestCase):
    def setUp(self):
        try:self.errors=importlib.import_module('aat_api.errors')
        except ModuleNotFoundError as exc:
            if exc.name!='aat_api.errors':raise
            raise AssertionError('T032 error/middleware boundary missing') from None
        from aat_api.main import app
        self.app=app

    def request(self,method,path,**kwargs):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app,raise_app_exceptions=False),base_url='http://test') as c:
                return await c.request(method,path,**kwargs)
        return asyncio.run(run())

    def test_framework_errors_have_safe_envelope_and_request_id(self):
        response=self.request('GET','/api/v1/not-a-route')
        self.assertEqual(response.status_code,404)
        body=response.json()['error'];UUID(body['request_id'])
        self.assertFalse(body['retryable']);self.assertNotIn('detail',response.json())

    def test_validation_location_and_stale_revision_are_safe_contract_errors(self):
        r=self.request('GET','/api/v1/operations/not-a-uuid')
        self.assertEqual(r.status_code,422)
        self.assertEqual(r.json()['error']['details'][0]['column_name'],'path.id')
        self.assertNotIn('not-a-uuid',r.text)
        path='/__foundation_stale_revision'
        if not any(getattr(route,'path',None)==path for route in self.app.routes):
            @self.app.get(path,include_in_schema=False)
            def stale():
                from aat_metadata.repositories.revisions import StaleRevision
                raise StaleRevision('private metadata details')
        r=self.request('GET',path);self.assertEqual(r.status_code,412)
        self.assertNotIn('private metadata details',r.text)

    def test_cross_origin_mutation_blocked_and_liveness_stays_available(self):
        for headers in [{'Origin':'https://evil.example'},{'Sec-Fetch-Site':'cross-site'}]:
            r=self.request('POST','/api/v1/operations',headers=headers)
            self.assertEqual(r.status_code,403);self.assertEqual(r.json()['error']['code'],'ORIGIN_REJECTED')
        self.assertEqual(self.request('GET','/api/v1/health/live').status_code,200)

    def test_unclassified_exception_suppresses_secret_dsn_path_and_traceback(self):
        path='/__foundation_test_exception'
        if not any(getattr(r,'path',None)==path for r in self.app.routes):
            @self.app.get(path,include_in_schema=False)
            def explode():raise RuntimeError('postgresql://user:password@db /secrets/private Traceback secret')
        r=self.request('GET',path);self.assertEqual(r.status_code,500)
        self.assertEqual(r.json()['error']['code'],'INTERNAL_ERROR')
        for marker in ['postgresql://','password','/secrets','Traceback']:self.assertNotIn(marker,r.text)
