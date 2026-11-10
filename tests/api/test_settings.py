"""T133: persistent settings, ranges, readonly fields and optimistic concurrency."""
import unittest
from tests.api import test_dag_builder as builder


class SettingsContractTests(unittest.TestCase):
    setUp=builder.DAGBuilderContractTests.setUp

    def test_concurrent_edits_to_different_fields_share_one_document_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        current=self.client.get('/api/v1/settings');etag=current.headers['etag']
        def update(body):
            return self.client.patch('/api/v1/settings',headers={'If-Match':etag},json=body).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(update,[{'default_batch_size':4321},{'dashboard_refresh_interval':17}]))
        self.assertEqual(sorted(results),[200,412])

    def test_shorter_retention_never_collects_protected_recovery_data(self):
        current=self.client.get('/api/v1/settings')
        changed=self.client.patch('/api/v1/settings',headers={'If-Match':current.headers['etag']},json={'staging_retention_days':1})
        self.assertEqual(changed.status_code,200)
        from tests.etl.test_staging_cleanup import StagingCleanupTests
        helper=StagingCleanupTests()
        try:helper.run_case(protected=True,scheduled=True)
        finally:helper.doCleanups()

    def test_defaults_persist_and_global_revision_changes_for_each_setting(self):
        response=self.client.get('/api/v1/settings');self.assertEqual(response.status_code,200)
        self.harness.assert_response('get','/settings',200,response.json(),headers=response.headers)
        value=response.json();etag=response.headers['etag']
        for key,setting in [('default_batch_size',2000),('dashboard_refresh_interval',15),('default_timezone','Asia/Seoul'),('staging_retention_days',9)]:
            changed=self.client.patch('/api/v1/settings',headers={'If-Match':etag},json={key:setting})
            self.assertEqual(changed.status_code,200);self.harness.assert_response('patch','/settings',200,changed.json(),headers=changed.headers)
            self.assertGreater(changed.json()['revision'],value['revision']);self.assertEqual(changed.json()[key],setting)
            stale=self.client.patch('/api/v1/settings',headers={'If-Match':etag},json={key:setting})
            self.assertEqual(stale.status_code,412)
            value=changed.json();etag=changed.headers['etag']
        self.assertEqual(self.client.get('/api/v1/settings').json()['default_timezone'],'Asia/Seoul')

    def test_invalid_ranges_bool_timezone_and_readonly_mutations_are_rejected(self):
        response=self.client.get('/api/v1/settings');self.assertEqual(response.status_code,200)
        for body in ({'default_batch_size':0},{'default_batch_size':10001},{'default_batch_size':True},
                     {'dashboard_refresh_interval':4},{'dashboard_refresh_interval':3601},{'staging_retention_days':0},
                     {'staging_retention_days':366},{'default_timezone':'Invalid/Timezone'},
                     {'application_version':'hacked'},{'airflow_connectivity_status':'AVAILABLE'},{'default_batch_size':None}):
            with self.subTest(body=body):
                invalid=self.client.patch('/api/v1/settings',headers={'If-Match':response.headers['etag']},json=body)
                self.assertEqual(invalid.status_code,422)
                self.harness.assert_response('patch','/settings','default',invalid.json(),headers=invalid.headers)
        self.assertEqual(self.client.patch('/api/v1/settings',json={'default_batch_size':1000}).status_code,422)


class SettingsNewConfigTests(unittest.TestCase):
    setUp=builder.ETLPreviewIntegrationTests.setUp
    target=builder.ETLPreviewIntegrationTests.target
    wait=builder.ETLPreviewIntegrationTests.wait
    response=builder.ETLPreviewIntegrationTests.response
    scenario=builder.ETLPreviewIntegrationTests.scenario

    def test_new_batch_defaults_do_not_mutate_a_validated_revision(self):
        def change(value):
            current=self.client.get('/api/v1/settings');self.assertEqual(current.status_code,200)
            response=self.client.patch('/api/v1/settings',headers={'If-Match':current.headers['etag']},json={'default_batch_size':value})
            self.assertEqual(response.status_code,200)
        change(2000)
        first,result,_,_,_=self.scenario();self.assertEqual(result['state'],'SUCCEEDED')
        old=self.client.get('/api/v1/definition-uploads/'+first['id']+'/etl-preview').json()['items'][0]
        self.assertEqual(old['config']['batch_size'],2000)
        change(3000)
        after=self.client.get('/api/v1/definition-uploads/'+first['id']+'/etl-preview').json()['items'][0]
        self.assertEqual(after['id'],old['id']);self.assertEqual(after['config']['batch_size'],2000)
        second,result,_,_,_=self.scenario();self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(self.client.get('/api/v1/definition-uploads/'+second['id']+'/etl-preview').json()['items'][0]['config']['batch_size'],3000)
        explicit,result,_,_,_=self.scenario(edit=lambda book,*_:setattr(book['ETL_Definitions']['Q2'],'value',123))
        self.assertEqual(result['state'],'SUCCEEDED')
        preview=self.client.get('/api/v1/definition-uploads/'+explicit['id']+'/etl-preview')
        self.assertEqual(preview.status_code,200)
        self.assertEqual(preview.json()['items'][0]['config']['batch_size'],123)
