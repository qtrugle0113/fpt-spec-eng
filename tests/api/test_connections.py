"""T035: real ASGI/metadata responses checked against the canonical contract."""
import os
from pathlib import Path
import unittest
from urllib.parse import urlparse,unquote
from uuid import UUID,uuid4

from fastapi.testclient import TestClient
import yaml
from tests.api.test_openapi_contract import ContractHarness,CONTRACT


class ConnectionAPITests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':
            raise RuntimeError('Disposable database required')
        from aat_api.main import app
        self.client=TestClient(app,raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.harness=ContractHarness(yaml.safe_load(CONTRACT.read_text(encoding='utf-8')))
        self.prefix='api_'+uuid4().hex
        self.secret=unquote(urlparse(os.environ['AAT_FOUNDATION_TEST_DSN']).password)

    def payload(self,**changes):
        value=dict(code=self.prefix,name='Connection test',database_type='POSTGRESQL',host='postgres',
                   port=5432,database_name='app_metadata',schema_name='public',username='postgres',password=self.secret)
        value.update(changes)
        return value

    def request(self,method,path,expected,*,identity=None,payload=None,headers=None,validate_request=True):
        headers=headers or {}
        if validate_request:
            self.harness.assert_request(method,path,payload=payload,headers=headers)
        target=path.replace('{id}',str(identity)) if identity else path
        response=self.client.request(method,'/api/v1'+target,json=payload,headers=headers)
        self.assertEqual(response.status_code,expected,'Unexpected connection HTTP status')
        body=None if expected==204 else response.json()
        try:self.harness.assert_response(method,path,expected,body,headers=response.headers)
        except AssertionError:raise AssertionError('Connection response violates canonical OpenAPI') from None
        self.assertTrue(self.secret not in response.text,'Response exposed a credential')
        self.assertTrue('"ciphertext"' not in response.text and '"password"' not in response.text,
                        'Response exposed a private credential field')
        return response

    def create(self,**changes):
        response=self.request('post','/connections',201,payload=self.payload(**changes))
        self.assertTrue(response.headers.get('etag'),'Created connection needs ETag')
        return response

    def test_create_detail_and_filtered_pagination(self):
        created=self.create();identity=created.json()['id']
        detail=self.request('get','/connections/{id}',200,identity=identity)
        self.assertTrue(detail.json()['has_password'])
        self.assertEqual(detail.json()['test_status'],'UNTESTED')
        page=self.client.get('/api/v1/connections',params={'search':self.prefix,'database_type':'POSTGRESQL','status':'UNTESTED','limit':1})
        self.assertEqual(page.status_code,200)
        self.harness.assert_response('get','/connections',200,page.json())
        self.assertEqual([x['id'] for x in page.json()['items']],[identity])
        self.assertEqual(page.json()['total'],1)

    def test_duplicate_trimmed_case_insensitive_code_conflicts(self):
        self.create()
        self.request('post','/connections',409,payload=self.payload(code=' '+self.prefix.upper()+' '))

    def test_patch_blank_password_preserves_secret_and_rejects_stale_etag(self):
        created=self.create();identity=created.json()['id'];etag=created.headers['etag']
        updated=self.request('patch','/connections/{id}',200,identity=identity,
                             payload={'name':'Updated name','password':''},headers={'If-Match':etag})
        self.assertGreater(updated.json()['revision'],created.json()['revision'])
        self.request('patch','/connections/{id}',412,identity=identity,
                     payload={'name':'Lost update'},headers={'If-Match':etag})
        tested=self.request('post','/connections/{id}/test',200,identity=identity)
        self.assertEqual(tested.json()['status'],'SUCCESS','Blank password did not preserve actual credential')

    def test_delete_requires_current_etag_and_hides_deleted_connection(self):
        created=self.create();identity=created.json()['id']
        self.request('delete','/connections/{id}',412,identity=identity,headers={'If-Match':'"999999"'})
        self.request('delete','/connections/{id}',204,identity=identity,headers={'If-Match':created.headers['etag']})
        self.request('get','/connections/{id}',404,identity=identity)

    def test_connection_test_reports_real_success_and_safe_auth_failure(self):
        created=self.create()
        response=self.request('post','/connections/{id}/test',200,identity=created.json()['id'])
        self.assertEqual(response.json()['status'],'SUCCESS')
        self.assertLessEqual(response.json()['latency_ms'],30000)
        failed=self.create(code=self.prefix+'_bad',username='missing_'+uuid4().hex)
        response=self.request('post','/connections/{id}/test',200,identity=failed.json()['id'])
        self.assertEqual(response.json()['status'],'FAILED')
        self.assertIsNotNone(response.json()['error'])

    def test_invalid_fields_hosts_and_missing_if_match_fail_safely(self):
        for changes in [{'port':0},{'port':65536},{'host':'postgresql://user:secret@postgres'},
                        {'host':'../../secrets'},{'host':'169.254.169.254'},{'name':' '},{'unknown':'x'}]:
            with self.subTest(fields=tuple(changes)):
                self.request('post','/connections',422,payload=self.payload(**changes),validate_request=False)
        created=self.create()
        self.request('patch','/connections/{id}',422,identity=created.json()['id'],payload={'name':'No match'},
                     validate_request=False)
        for query in [{'limit':201},{'offset':-1}]:
            response=self.client.get('/api/v1/connections',params=query)
            self.assertEqual(response.status_code,422)
            self.harness.assert_response('get','/connections',422,response.json())

    def test_real_definition_dependency_is_listed_and_blocks_delete_and_code_change(self):
        created=self.create();identity=created.json()['id']
        self.request('post','/connections/{id}/test',200,identity=identity)
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        from aat_metadata.repositories.base import create_app_engine
        from aat_metadata.models.connections import Connection
        from aat_metadata.models.definitions import UploadedFile,DefinitionUpload,TableDefinition
        engine=create_app_engine();self.addCleanup(engine.dispose)
        with Session(engine) as session,session.begin():
            connection=session.get(Connection,UUID(identity))
            file=UploadedFile(original_name='fixture.xlsx',sha256='a'*64,bytes=10,extension='.xlsx')
            session.add(file);session.flush()
            upload=DefinitionUpload(kind='TABLE',uploaded_file_id=file.id,template_version='1.0',
                                    workbook_sha256=file.sha256,status='VALIDATED')
            session.add(upload);session.flush()
            table=TableDefinition(upload_id=upload.id,target_connection_revision_id=connection.current_revision_id,
                                  target_schema='public',table_name='fixture_'+uuid4().hex,definition_hash='b'*64)
            session.add(table)
        detail=self.request('get','/connections/{id}',200,identity=identity)
        self.assertTrue(detail.json()['dependencies'],'Actual table dependency missing from detail')
        self.request('delete','/connections/{id}',409,identity=identity,headers={'If-Match':detail.headers['etag']})
        self.request('patch','/connections/{id}',409,identity=identity,payload={'code':self.prefix+'_renamed'},
                     headers={'If-Match':detail.headers['etag']})

    def dag_fixture(self,identity,active=False):
        from datetime import datetime,timezone
        from sqlalchemy.orm import Session
        from aat_metadata.repositories.base import create_app_engine
        from aat_metadata.models.connections import Connection
        from aat_metadata.models.definitions import UploadedFile,DefinitionUpload
        from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
        from aat_metadata.models.authorizations import DataReplacementAuthorization
        from aat_metadata.models.operations import Operation
        from aat_metadata.models.replacement_runs import RunIntent
        from aat_metadata.models.runtime import ExecutionBinding
        engine=create_app_engine();self.addCleanup(engine.dispose)
        with Session(engine) as session,session.begin():
            connection=session.get(Connection,UUID(identity));old=connection.current_revision_id
            file=UploadedFile(original_name='fixture.xlsx',sha256='c'*64,bytes=10,extension='.xlsx')
            session.add(file);session.flush()
            upload=DefinitionUpload(kind='ETL',uploaded_file_id=file.id,template_version='1.0',workbook_sha256=file.sha256,status='VALIDATED')
            dag=ETLDefinition(dag_id='test_'+uuid4().hex)
            session.add_all([upload,dag]);session.flush()
            revision=ETLDefinitionRevision(definition_id=dag.id,revision=1,upload_id=upload.id,status='VALIDATED',
                config_json={'source':{'connection_revision_id':str(old)},'load_strategy':'FULL_REFRESH'})
            session.add(revision);session.flush();dag.current_revision_id=revision.id
            authorization=DataReplacementAuthorization(dag_id=dag.dag_id,etl_revision_id=revision.id,
                physical_target_id='a'*64,scope='ONCE',scope_sha256='b'*64,acknowledged_at=datetime.now(timezone.utc))
            session.add(authorization);session.flush()
            binding_id=None
            if active:
                operation=Operation(kind='DAG_TRIGGER',idempotency_key=str(uuid4()),request_sha256='a'*64)
                session.add(operation);session.flush()
                intent=RunIntent(operation_id=operation.id,run_uuid=uuid4(),dag_id=dag.dag_id,
                    airflow_run_id='manual__'+uuid4().hex,run_type='manual',etl_revision_id=revision.id,
                    authorization_id=authorization.id,request_sha256='a'*64)
                session.add(intent);session.flush()
                binding=ExecutionBinding(dag_id=dag.dag_id,airflow_run_id=intent.airflow_run_id,task_id='transfer',
                    airflow_dag_version_id=str(uuid4()),etl_revision_id=revision.id,source_revision_id=old,
                    target_revision_id=old,authorization_id=authorization.id,run_intent_id=intent.id,
                    airflow_run_type='manual',runtime_build='test-fixture',binding_hash='a'*64)
                session.add(binding);session.flush();binding_id=binding.id
            return dict(revision_id=revision.id,authorization_id=authorization.id,dag_id=dag.dag_id,
                        connection_revision_id=old,binding_id=binding_id)

    def test_location_change_invalidates_scope_but_keeps_historical_config(self):
        created=self.create();identity=created.json()['id'];fixture=self.dag_fixture(identity)
        updated=self.request('patch','/connections/{id}',200,identity=identity,payload={'schema_name':'pg_catalog'},
                             headers={'If-Match':created.headers['etag']})
        self.assertTrue(updated.json()['needs_revalidation'])
        import psycopg
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            self.assertEqual(c.execute('SELECT state FROM replacement_authorizations WHERE id=%s',(fixture['authorization_id'],)).fetchone()[0],'INVALIDATED')
            self.assertEqual(c.execute('SELECT gate_state FROM dag_admission WHERE dag_id=%s',(fixture['dag_id'],)).fetchone()[0],'BLOCKED')
            config=c.execute('SELECT config_json FROM etl_definition_revisions WHERE id=%s',(fixture['revision_id'],)).fetchone()[0]
            self.assertEqual(config['source']['connection_revision_id'],str(fixture['connection_revision_id']))

    def test_active_binding_blocks_location_change_and_keeps_credential_reference(self):
        created=self.create();identity=created.json()['id'];fixture=self.dag_fixture(identity,active=True)
        self.request('patch','/connections/{id}',409,identity=identity,payload={'schema_name':'pg_catalog'},
                     headers={'If-Match':created.headers['etag']})
        self.request('patch','/connections/{id}',200,identity=identity,payload={'password':'rotated-synthetic-password'},
                     headers={'If-Match':created.headers['etag']})
        import psycopg
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            old=c.execute('SELECT source_revision_id FROM execution_bindings WHERE id=%s',(fixture['binding_id'],)).fetchone()[0]
            self.assertEqual(old,fixture['connection_revision_id'])

    def test_mysql_connection_round_trip_through_http_and_real_database(self):
        created=self.create(database_type='MYSQL',host='mysql',port=3306,database_name='etl_test',
                            schema_name=None,username='aat_test')
        identity=created.json()['id']
        tested=self.request('post','/connections/{id}/test',200,identity=identity)
        self.assertEqual(tested.json()['status'],'SUCCESS')
        detail=self.request('get','/connections/{id}',200,identity=identity)
        self.assertEqual(detail.json()['test_status'],'SUCCESS')
        self.assertFalse(detail.json()['needs_revalidation'])

    def test_secret_is_encrypted_at_rest_and_public_projection_is_safe(self):
        created=self.create()
        import psycopg
        from aat_metadata.secrets.codec import SecretCodec
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            key_id,ciphertext=c.execute('''SELECT s.key_id,s.ciphertext FROM connections c
                JOIN connection_revisions r ON r.id=c.current_revision_id
                JOIN connection_secrets s ON s.id=r.secret_id WHERE c.id=%s''',(created.json()['id'],)).fetchone()
        self.assertTrue(self.secret not in ciphertext,'Plaintext credential persisted')
        self.assertTrue(SecretCodec(Path(os.environ['AAT_APP_KEYRING'])).decrypt(key_id,ciphertext)==self.secret,
                        'Stored credential cannot be decrypted with original key')
