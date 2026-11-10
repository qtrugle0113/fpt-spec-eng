"""T101: transport fault controls supplement, never replace real Airflow tests."""
import unittest
import httpx


class AirflowClientTests(unittest.TestCase):
    def client(self,handler):
        from aat_api.airflow_client.client import AirflowClient
        client=AirflowClient('http://airflow-fixture',username='aat_service',password='private-fixture-password',transport=httpx.MockTransport(handler),sleep=lambda _:None)
        self.addCleanup(client.close);return client

    def test_401_refreshes_once_and_never_returns_credentials(self):
        counts={'auth':0,'get':0}
        def handler(request):
            if request.url.path=='/auth/token':counts['auth']+=1;return httpx.Response(201,json={'access_token':'fixture-token-'+str(counts['auth'])})
            counts['get']+=1
            return httpx.Response(401 if counts['get']==1 else 200,json={'ok':True})
        self.assertEqual(self.client(handler).request('GET','/dags'),{'ok':True})
        self.assertEqual(counts,{'auth':2,'get':2})

    def test_get_retries_are_finite_and_post_is_never_replayed(self):
        from aat_api.airflow_client.client import AirflowError
        counts={'GET':0,'POST':0}
        def handler(request):
            if request.url.path=='/auth/token':return httpx.Response(201,json={'access_token':'fixture-token'})
            counts[request.method]+=1;return httpx.Response(503,json={'detail':'private error'})
        client=self.client(handler)
        for method in ('GET','POST'):
            with self.assertRaises(AirflowError) as failure:client.request(method,'/dags',json={} if method=='POST' else None)
            self.assertNotIn('private error',str(failure.exception))
        self.assertEqual(counts,{'GET':3,'POST':1})

    def test_permission_error_is_not_retried_or_relabelled_as_connectivity(self):
        from aat_api.airflow_client.client import AirflowError
        calls=[]
        def handler(request):
            if request.url.path=='/auth/token':return httpx.Response(201,json={'access_token':'fixture-token'})
            calls.append(1);return httpx.Response(403,json={'detail':'forbidden'})
        with self.assertRaises(AirflowError) as failure:self.client(handler).request('GET','/dags')
        self.assertEqual(failure.exception.status,403);self.assertEqual(calls,[1])

    def test_path_segments_are_encoded_and_retry_after_cannot_exceed_deadline(self):
        from aat_api.airflow_client.client import AirflowError,segment
        self.assertEqual(segment('a/b?x#y'),'a%2Fb%3Fx%23y')
        calls=[]
        def handler(request):
            if request.url.path=='/auth/token':return httpx.Response(201,json={'access_token':'fixture-token'})
            calls.append(1);return httpx.Response(429,headers={'Retry-After':'3600'},json={})
        with self.assertRaises(AirflowError):self.client(handler).request('GET','/dags')
        self.assertEqual(calls,[1])
