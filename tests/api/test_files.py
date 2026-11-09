"""T061: Files contract, durable validation and immutable parser revisions on real PG."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import UUID,uuid4
from fastapi.testclient import TestClient
import yaml
from tests.api.test_openapi_contract import CONTRACT,ContractHarness

PARSER=dict(encoding='utf-8',delimiter=',',header_present=True,quote_character='"',escape_character=None,null_representation=r'\N')


class FilesAPITests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable metadata database required')
        from aat_api.main import app
        self.app=app;self.client=TestClient(app,raise_server_exceptions=False);self.addCleanup(self.client.close)
        self.harness=ContractHarness(yaml.safe_load(CONTRACT.read_text(encoding='utf-8')))
        self.log=tempfile.TemporaryFile();self.addCleanup(self.log.close)
        self.worker=subprocess.Popen([sys.executable,'-m','aat_api.workers.main'],stdout=self.log,stderr=self.log)
        self.addCleanup(self.stop_worker)

    def stop_worker(self):
        if self.worker.poll() is None:self.worker.kill();self.worker.wait(timeout=10)

    def response(self,response,method,path,status):
        self.assertEqual(response.status_code,status,'Unexpected Files API status')
        value=response.json();self.harness.assert_response(method,path,status,value,headers=response.headers)
        self.assertNotIn('safe_storage_key',response.text);self.assertNotIn('/data/uploads',response.text)
        return value

    def upload(self,data=b'a,b\n1,2\n',name='source.csv',parser=None):
        response=self.client.post('/api/v1/files',data={'parser_json':json.dumps(parser or PARSER)},files={'file':(name,data,'text/csv')})
        value=self.response(response,'post','/files',201)
        self.assertEqual(value['sha256'],hashlib.sha256(data).hexdigest());self.assertEqual(value['size'],len(data))
        self.assertTrue(value['needs_revalidation']);self.assertEqual(value['parser_revision'],1)
        return value,response.headers['etag']

    def wait(self,identity):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            value=self.response(self.client.get('/api/v1/operations/'+identity),'get','/operations/{id}',200)
            if value['state'] not in ('QUEUED','RUNNING'):return value
            if self.worker.poll() is not None:self.fail('Files worker exited before operation completed')
            time.sleep(.1)
        self.fail('Files operation exceeded fixture deadline')

    def validate(self,file,**changes):
        payload=dict(expected_sha256=file['sha256'],parser_revision=file['parser_revision']);payload.update(changes)
        response=self.client.post('/api/v1/files/'+file['id']+'/validate',json=payload,headers={'Idempotency-Key':str(uuid4())})
        value=self.response(response,'post','/files/{id}/validate',202)
        return self.wait(value['id'])

    def test_upload_same_name_distinct_reference_and_persistent_listing(self):
        first,_=self.upload(name='../../same.csv');second,_=self.upload(name='same.csv')
        self.assertNotEqual(first['id'],second['id']);self.assertEqual(first['file_name'],'same.csv')
        with TestClient(self.app,raise_server_exceptions=False) as fresh:
            listing=self.response(fresh.get('/api/v1/files',params={'limit':200}),'get','/files',200)
            self.assertTrue({first['id'],second['id']}<={item['id'] for item in listing['items']})
            detail=self.response(fresh.get('/api/v1/files/'+first['id']),'get','/files/{id}',200)
            self.assertEqual(detail['sha256'],first['sha256'])

    def test_preview_uses_quoted_null_semantics_and_never_marks_file_valid(self):
        file,_=self.upload(b'id,name,note\n1,"\\N",\\N\n2,"",\n3,0,false\n')
        value=self.response(self.client.get('/api/v1/files/'+file['id']+'/preview'),'get','/files/{id}/preview',200)
        self.assertEqual(value['rows'],[['1',r'\N',None],['2','',''],['3','0','false']])
        detail=self.client.get('/api/v1/files/'+file['id']).json();self.assertEqual(detail['validation_status'],'PENDING')
        self.assertTrue(detail['needs_revalidation'])

    def test_candidate_preview_does_not_persist_and_patch_requires_current_etag(self):
        file,etag=self.upload(b'a;b\n1;2\n');candidate={**PARSER,'delimiter':';'}
        preview=self.response(self.client.get('/api/v1/files/'+file['id']+'/preview',params={'parser_json':json.dumps(candidate)}),'get','/files/{id}/preview',200)
        self.assertEqual(preview['rows'],[['1','2']])
        unchanged=self.client.get('/api/v1/files/'+file['id']);self.assertEqual(unchanged.headers['etag'],etag)
        self.assertEqual(unchanged.json()['parser']['delimiter'],',')
        changed=self.client.patch('/api/v1/files/'+file['id']+'/parser',json=candidate,headers={'If-Match':etag})
        value=self.response(changed,'patch','/files/{id}/parser',200)
        self.assertEqual(value['id'],file['id']);self.assertEqual(value['sha256'],file['sha256']);self.assertEqual(value['parser_revision'],2)
        self.response(self.client.patch('/api/v1/files/'+file['id']+'/parser',json=PARSER,headers={'If-Match':etag}),'patch','/files/{id}/parser',412)
        self.assertEqual(self.validate(value)['state'],'SUCCEEDED')
        final=self.client.get('/api/v1/files/'+file['id']).json();self.assertEqual(final['validation_status'],'VALID');self.assertFalse(final['needs_revalidation'])

    def test_full_validation_finds_bad_record_beyond_preview_limit(self):
        file,_=self.upload(b'a,b\n'+b'1,2\n'*101+b'private-bad-row\n')
        preview=self.response(self.client.get('/api/v1/files/'+file['id']+'/preview'),'get','/files/{id}/preview',200)
        self.assertEqual(len(preview['rows']),100);self.assertTrue(preview['limited'])
        operation=self.validate(file);self.assertEqual(operation['state'],'FAILED')
        issue=operation['error']['error']['details'][0]
        self.assertEqual(issue['row'],103);self.assertIn('Record 102',issue['message'])
        self.assertNotIn('private-bad-row',json.dumps(operation))
        detail=self.client.get('/api/v1/files/'+file['id']).json();self.assertEqual(detail['validation_status'],'INVALID')

    def test_boundaries_invalid_parser_and_checksum_rejected(self):
        file,_=self.upload()
        for params in ({'max_rows':101},{'max_rows':-1},{'parser_json':'not-json'}):
            self.assertEqual(self.client.get('/api/v1/files/'+file['id']+'/preview',params=params).status_code,422)
        self.assertEqual(self.client.post('/api/v1/files/'+file['id']+'/validate',json={'expected_sha256':'0'*64},headers={'Idempotency-Key':str(uuid4())}).status_code,409)
        for revision in (True,'1'):
            self.assertEqual(self.client.post('/api/v1/files/'+file['id']+'/validate',json={'parser_revision':revision},headers={'Idempotency-Key':str(uuid4())}).status_code,422)
        self.assertEqual(self.client.post('/api/v1/files',data={'parser_json':json.dumps(PARSER)},files={'file':('unsafe.xlsx',b'not a CSV')}).status_code,422)
        too_large=self.client.post('/api/v1/files',content=b'',headers={'Content-Length':str(257*1024*1024+1)})
        self.response(too_large,'post','/files',413)

    def test_expired_or_missing_source_fails_without_empty_preview(self):
        from datetime import datetime,timezone,timedelta
        from sqlalchemy.orm import Session
        from aat_metadata.repositories.base import create_app_engine
        from aat_metadata.models.definitions import UploadedFile
        file,_=self.upload();engine=create_app_engine();self.addCleanup(engine.dispose)
        with Session(engine) as session,session.begin():session.get(UploadedFile,UUID(file['id'])).expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        response=self.client.get('/api/v1/files/'+file['id']+'/preview')
        self.response(response,'get','/files/{id}/preview',410)
        missing,_=self.upload()
        with Session(engine) as session:key=session.get(UploadedFile,UUID(missing['id'])).safe_storage_key
        root=Path(os.environ['AAT_UPLOADS_ROOT']).resolve();source=(root/key).resolve()
        self.assertTrue(source.is_relative_to(root));source.unlink()
        self.response(self.client.get('/api/v1/files/'+missing['id']+'/preview'),'get','/files/{id}/preview',410)

    def dependency_fixture(self,file,active=False,uncertain=False):
        from datetime import datetime,timezone
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        from aat_metadata.repositories.base import create_app_engine
        from aat_metadata.models.connections import Connection
        from aat_metadata.models.definitions import UploadedFile,DefinitionUpload
        from aat_metadata.models.file_parsers import FileParserRevision
        from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
        from aat_metadata.models.operations import Operation
        from aat_metadata.models.replacement_runs import RunIntent
        from aat_metadata.models.runtime import ExecutionBinding
        from aat_metadata.models.authorizations import DataReplacementAuthorization
        engine=create_app_engine();self.addCleanup(engine.dispose)
        with Session(engine) as session,session.begin():
            target=session.scalar(select(Connection).where(Connection.code=='pg_etl'))
            parser=session.scalar(select(FileParserRevision).where(FileParserRevision.file_id==UUID(file['id']),FileParserRevision.revision==1))
            workbook=UploadedFile(original_name='fixture.xlsx',sha256='c'*64,bytes=10,extension='.xlsx')
            session.add(workbook);session.flush()
            upload=DefinitionUpload(kind='ETL',uploaded_file_id=workbook.id,workbook_sha256=workbook.sha256,template_version='1.0',status='VALIDATED')
            dag=ETLDefinition(dag_id='file_fixture_'+uuid4().hex);session.add_all([upload,dag]);session.flush()
            revision=ETLDefinitionRevision(definition_id=dag.id,revision=1,upload_id=upload.id,status='VALIDATED',
                config_json={'source':{'type':'CSV','file_id':file['id'],'parser_revision':1,'file_sha256':file['sha256']},'load_strategy':'FULL_REFRESH'})
            session.add(revision);session.flush();dag.current_revision_id=revision.id
            authorization=DataReplacementAuthorization(dag_id=dag.dag_id,etl_revision_id=revision.id,physical_target_id='a'*64,
                scope='ONCE',scope_sha256='b'*64,acknowledged_at=datetime.now(timezone.utc))
            session.add(authorization);session.flush()
            binding_id=None
            if active:
                operation=Operation(kind='FILE_FIXTURE_TRIGGER',idempotency_key=str(uuid4()),request_sha256='a'*64)
                session.add(operation);session.flush()
                intent=RunIntent(operation_id=operation.id,run_uuid=uuid4(),dag_id=dag.dag_id,airflow_run_id='manual__'+uuid4().hex,
                    run_type='manual',etl_revision_id=revision.id,authorization_id=authorization.id,request_sha256='a'*64)
                session.add(intent);session.flush()
                binding=ExecutionBinding(dag_id=dag.dag_id,airflow_run_id=intent.airflow_run_id,task_id='transfer',airflow_dag_version_id=str(uuid4()),
                    etl_revision_id=revision.id,target_revision_id=target.current_revision_id,file_parser_revision=parser.id,source_file_sha256=file['sha256'],
                    run_intent_id=intent.id,airflow_run_type='manual',runtime_build='file-test-fixture',binding_hash='b'*64,
                    authorization_id=authorization.id,
                    commit_uncertain=uncertain,last_reconciled_at=datetime.now(timezone.utc) if uncertain else None)
                session.add(binding);session.flush();binding_id=binding.id
            return dict(revision_id=revision.id,parser_id=parser.id,binding_id=binding_id,authorization_id=authorization.id)

    def test_active_and_uncertain_bindings_block_parser_change_without_mutating_snapshot(self):
        import psycopg
        for uncertain in (False,True):
            with self.subTest(uncertain=uncertain):
                file,etag=self.upload();fixture=self.dependency_fixture(file,active=True,uncertain=uncertain)
                self.response(self.client.patch('/api/v1/files/'+file['id']+'/parser',json={**PARSER,'delimiter':';'},headers={'If-Match':etag}),'patch','/files/{id}/parser',409)
                with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as connection:
                    retained=connection.execute('SELECT file_parser_revision,source_file_sha256 FROM execution_bindings WHERE id=%s',(fixture['binding_id'],)).fetchone()
                self.assertEqual(retained,(fixture['parser_id'],file['sha256']))

    def test_parser_change_invalidates_future_definition_without_rewriting_its_config(self):
        import psycopg
        file,etag=self.upload();fixture=self.dependency_fixture(file)
        self.response(self.client.patch('/api/v1/files/'+file['id']+'/parser',json={**PARSER,'delimiter':';'},headers={'If-Match':etag}),'patch','/files/{id}/parser',200)
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as connection:
            state,config=connection.execute('SELECT status,config_json FROM etl_definition_revisions WHERE id=%s',(fixture['revision_id'],)).fetchone()
            authorization=connection.execute('SELECT state FROM replacement_authorizations WHERE id=%s',(fixture['authorization_id'],)).fetchone()[0]
        self.assertEqual(state,'INVALID');self.assertEqual(config['source']['parser_revision'],1)
        self.assertEqual(authorization,'INVALIDATED')

    def test_validation_replay_keeps_snapshot_and_old_parser_cannot_mark_new_parser_valid(self):
        file,_=self.upload();self.stop_worker()
        payload=dict(expected_sha256=file['sha256'],parser_revision=1);headers={'Idempotency-Key':str(uuid4())}
        path='/api/v1/files/'+file['id']+'/validate'
        first=self.response(self.client.post(path,json=payload,headers=headers),'post','/files/{id}/validate',202)
        current=self.client.get('/api/v1/files/'+file['id'])
        changed=self.client.patch('/api/v1/files/'+file['id']+'/parser',json={**PARSER,'delimiter':';'},headers={'If-Match':current.headers['etag']})
        self.assertEqual(changed.status_code,200);self.assertEqual(changed.json()['parser_revision'],2)
        replay=self.response(self.client.post(path,json=payload,headers=headers),'post','/files/{id}/validate',202)
        self.assertEqual(replay['id'],first['id'])
        self.assertEqual(self.client.post(path,json={**payload,'parser_revision':2},headers=headers).status_code,409)
        self.worker=subprocess.Popen([sys.executable,'-m','aat_api.workers.main'],stdout=self.log,stderr=self.log)
        operation=self.wait(first['id']);self.assertEqual(operation['state'],'FAILED')
        self.assertEqual(operation['error']['error']['code'],'FILE_VALIDATION_STALE')
        current=self.client.get('/api/v1/files/'+file['id']).json()
        self.assertEqual(current['parser_revision'],2);self.assertEqual(current['validation_status'],'PENDING')
        self.assertEqual(current['sha256'],file['sha256'])
