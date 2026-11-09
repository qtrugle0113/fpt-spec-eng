"""T047: durable workbook validation/preview/create/history against actual targets."""
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,unquote
from uuid import UUID,uuid4
from fastapi.testclient import TestClient
from openpyxl import load_workbook
import yaml
from tests.api.test_openapi_contract import CONTRACT,ContractHarness
from tests.unit.test_table_workbook import workbook


class TableAPITests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        from aat_api.main import app
        self.app=app;self.client=TestClient(app,raise_server_exceptions=False);self.addCleanup(self.client.close)
        self.harness=ContractHarness(yaml.safe_load(CONTRACT.read_text(encoding='utf-8')))
        self.password=unquote(urlparse(os.environ['AAT_FOUNDATION_TEST_DSN']).password)
        self.log=tempfile.TemporaryFile(mode='w+b');self.addCleanup(self.log.close)
        worker=subprocess.Popen([sys.executable,'-m','aat_api.workers.main'],stdout=self.log,stderr=self.log)
        self.worker=worker
        self.addCleanup(lambda:(worker.kill(),worker.wait(timeout=10)) if worker.poll() is None else None)

    def response(self,response,method,path,status):
        self.assertEqual(response.status_code,status,'Unexpected Table API status')
        body=response.json()
        self.harness.assert_response(method,path,status,body,headers=response.headers)
        self.assertTrue(self.password not in response.text,'Response leaked credential')
        return body

    def target(self,database_type='POSTGRESQL'):
        code='table_'+uuid4().hex
        payload=dict(code=code,name='Table target',database_type=database_type,
            host='mysql' if database_type=='MYSQL' else 'postgres',port=3306 if database_type=='MYSQL' else 5432,
            database_name='etl_test' if database_type=='MYSQL' else 'app_metadata',schema_name=None if database_type=='MYSQL' else 'public',
            username='aat_test' if database_type=='MYSQL' else 'postgres',password=self.password)
        response=self.client.post('/api/v1/connections',json=payload);self.assertEqual(response.status_code,201)
        connection=response.json()
        tested=self.client.post('/api/v1/connections/'+connection['id']+'/test');self.assertEqual(tested.json()['status'],'SUCCESS')
        return connection

    def stop_worker(self):
        if self.worker.poll() is None:self.worker.kill();self.worker.wait(timeout=10)

    def upload(self,target,invalid=False):
        book=workbook();table='table_'+uuid4().hex
        schema='etl_test' if target['database_type']=='MYSQL' else 'public'
        for sheet in ('Tables','Columns'):
            for row in book[sheet].iter_rows(min_row=2):
                row[0].value=target['code'];row[1].value=schema;row[2].value=table
        if invalid:book['Instructions']['B1']='unsupported'
        output=io.BytesIO();book.save(output);book.close();data=output.getvalue()
        uploaded=self.client.post('/api/v1/definition-uploads',data={'kind':'TABLE'},
            files={'file':('../../definition.xlsx',data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
        result=self.response(uploaded,'post','/definition-uploads',201)
        self.assertEqual(result['sha256'],hashlib.sha256(data).hexdigest())
        return result,table

    def wait(self,identity):
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            if self.worker.poll() is not None:
                self.log.seek(0);log=self.log.read().decode(errors='replace')
                frames=re.findall(r'File "([^"]+)", line ([0-9]+), in ([A-Za-z_][A-Za-z0-9_]*)',log)
                codes=re.findall(r'exception_type=([A-Za-z_][A-Za-z0-9_]*)',log)
                self.fail('Worker exited: '+str(self.worker.returncode)+'; frames='+str(frames)+'; exception classes='+str(codes))
            response=self.client.get('/api/v1/operations/'+identity)
            operation=self.response(response,'get','/operations/{id}',200)
            if operation['state'] not in ('QUEUED','RUNNING'):return operation
            time.sleep(.1)
        self.log.seek(0);log=self.log.read().decode(errors='replace')
        self.fail('Durable table operation did not finish within fixture deadline; exception classes='+str(re.findall(r'exception_type=([A-Za-z_][A-Za-z0-9_]*)',log)))

    def validate(self,upload,target):
        payload={'target_connection_id':target['id'],'expected_sha256':upload['sha256']}
        headers={'Idempotency-Key':str(uuid4())}
        self.harness.assert_request('post','/definition-uploads/{id}/validate',payload=payload,headers=headers)
        response=self.client.post('/api/v1/definition-uploads/'+upload['id']+'/validate',json=payload,headers=headers)
        operation=self.response(response,'post','/definition-uploads/{id}/validate',202)
        return self.wait(operation['id'])

    def test_template_binary_checksum_and_schema(self):
        response=self.client.get('/api/v1/templates/table-definition')
        self.assertEqual(response.status_code,200)
        self.assertIn('attachment',response.headers['content-disposition'])
        self.assertEqual(response.headers['etag'],'"'+hashlib.sha256(response.content).hexdigest()+'"')
        book=load_workbook(io.BytesIO(response.content),read_only=True)
        try:self.assertEqual(book['Instructions']['B1'].value,'1.0');self.assertEqual(book.sheetnames,['Instructions','Tables','Columns'])
        finally:book.close()

    def workflow(self,database_type):
        target=self.target(database_type);upload,table=self.upload(target)
        self.assertEqual(self.validate(upload,target)['state'],'SUCCEEDED')
        preview=self.response(self.client.get('/api/v1/definition-uploads/'+upload['id']+'/table-preview'),'get','/definition-uploads/{id}/table-preview',200)
        self.assertEqual(preview['items'][0]['primary_key'],['id'])
        self.assertFalse(preview['items'][0]['existing_table'])
        self.assertTrue(preview['items'][0]['columns'][1]['has_default'])
        key=str(uuid4());payload={'upload_id':upload['id'],'confirmation_token':preview['confirmation_token']}
        headers={'Idempotency-Key':key}
        self.harness.assert_request('post','/table-creation-jobs',payload=payload,headers=headers)
        first=self.response(self.client.post('/api/v1/table-creation-jobs',json=payload,headers=headers),'post','/table-creation-jobs',202)
        replay=self.response(self.client.post('/api/v1/table-creation-jobs',json=payload,headers=headers),'post','/table-creation-jobs',202)
        self.assertEqual(first['id'],replay['id']);self.assertEqual(self.wait(first['id'])['state'],'SUCCEEDED')
        with TestClient(self.app,raise_server_exceptions=False) as fresh:
            history=self.response(fresh.get('/api/v1/table-creation-jobs',params={'upload_id':upload['id']}),'get','/table-creation-jobs',200)
            self.assertEqual(history['total'],1)
            job=self.response(fresh.get('/api/v1/table-creation-jobs/'+history['items'][0]['id']),'get','/table-creation-jobs/{id}',200)
            self.assertEqual(job['results'][0]['state'],'CREATED')
            detail=self.response(fresh.get('/api/v1/table-definitions/'+preview['items'][0]['id']),'get','/table-definitions/{id}',200)
            self.assertEqual(detail['verification_status'],'VERIFIED');self.assertEqual(detail['primary_key'],['id'])
            self.assertIsNotNone(detail['actual_columns'])

    def test_postgres_create_and_persistent_history(self):self.workflow('POSTGRESQL')
    def test_mysql_create_and_persistent_history(self):self.workflow('MYSQL')

    def test_invalid_workbook_has_safe_locations_and_no_preview(self):
        target=self.target();upload,_=self.upload(target,invalid=True)
        self.assertEqual(self.validate(upload,target)['state'],'FAILED')
        issues=self.response(self.client.get('/api/v1/definition-uploads/'+upload['id']+'/issues'),'get','/definition-uploads/{id}/issues',200)
        self.assertGreater(issues['total'],0)
        self.response(self.client.get('/api/v1/definition-uploads/'+upload['id']+'/table-preview'),'get','/definition-uploads/{id}/table-preview',409)
        history=self.response(self.client.get('/api/v1/definition-uploads',params={'kind':'TABLE','status':'INVALID'}),'get','/definition-uploads',200)
        self.assertTrue(any(item['id']==upload['id'] for item in history['items']))

    def test_stale_confirmation_rejects_changed_connection_without_creating_job(self):
        target=self.target();upload,_=self.upload(target)
        self.assertEqual(self.validate(upload,target)['state'],'SUCCEEDED')
        preview=self.response(self.client.get('/api/v1/definition-uploads/'+upload['id']+'/ddl-preview'),'get','/definition-uploads/{id}/ddl-preview',200)
        current=self.client.get('/api/v1/connections/'+target['id'])
        changed=self.client.patch('/api/v1/connections/'+target['id'],json={'schema_name':'pg_catalog'},headers={'If-Match':current.headers['etag']})
        self.assertEqual(changed.status_code,200)
        self.response(self.client.post('/api/v1/table-creation-jobs',json={'upload_id':upload['id'],'confirmation_token':preview['confirmation_token']},
                                      headers={'Idempotency-Key':str(uuid4())}),'post','/table-creation-jobs',409)
        self.assertEqual(self.client.post('/api/v1/connections/'+target['id']+'/test').json()['status'],'SUCCESS')
        revalidate=self.client.post('/api/v1/definition-uploads/'+upload['id']+'/validate',json={'target_connection_id':target['id']},headers={'Idempotency-Key':str(uuid4())})
        self.assertEqual(revalidate.status_code,409)
        self.assertEqual(revalidate.json()['error']['code'],'REUPLOAD_REQUIRED')

    def test_history_filter_pagination_and_request_boundaries(self):
        target=self.target();first,_=self.upload(target);second,_=self.upload(target)
        listing=self.response(self.client.get('/api/v1/definition-uploads',params={'kind':'TABLE','limit':1}),'get','/definition-uploads',200)
        self.assertGreaterEqual(listing['total'],2);self.assertEqual(listing['next_offset'],1)
        next_page=self.response(self.client.get('/api/v1/definition-uploads',params={'kind':'TABLE','limit':1,'offset':1}),'get','/definition-uploads',200)
        self.assertNotEqual(listing['items'][0]['id'],next_page['items'][0]['id'])
        future=self.response(self.client.get('/api/v1/definition-uploads',params={'from':'2099-01-01T00:00:00Z'}),'get','/definition-uploads',200)
        self.assertEqual(future,dict(items=[],total=0,next_offset=None))
        for params in ({'limit':201},{'offset':-1},{'from':'not-a-date'},{'from':'2027-01-01T00:00:00Z','to':'2026-01-01T00:00:00Z'}):
            self.assertEqual(self.client.get('/api/v1/definition-uploads',params=params).status_code,422)
        changed=self.client.post('/api/v1/definition-uploads/'+first['id']+'/validate',json={'target_connection_id':target['id'],'expected_sha256':'0'*64},headers={'Idempotency-Key':str(uuid4())})
        self.assertEqual(changed.status_code,409)
        self.assertEqual(self.client.get('/api/v1/definition-uploads/'+first['id']).json()['status'],'UPLOADED')

    def test_unknown_mysql_ddl_is_durable_and_idempotent_replay_does_not_execute(self):
        from aat_api.ddl import mysql
        from aat_api.ddl.common import DDLOutcomeUnknown
        from aat_api.workers.main import connect
        from aat_api.services.operations import Operations
        from aat_api.workers.tables import execute
        from aat_api.services.table_preview import target_engine
        from sqlalchemy import inspect
        target=self.target('MYSQL');upload,table=self.upload(target)
        self.assertEqual(self.validate(upload,target)['state'],'SUCCEEDED')
        preview=self.client.get('/api/v1/definition-uploads/'+upload['id']+'/table-preview').json()
        self.stop_worker()
        headers={'Idempotency-Key':str(uuid4())};payload={'upload_id':upload['id'],'confirmation_token':preview['confirmation_token']}
        operation=self.client.post('/api/v1/table-creation-jobs',json=payload,headers=headers).json()
        owner='synthetic-ddl-response-loss'
        with connect() as connection:claimed=Operations(connection).claim(owner,ttl=300,kinds=['TABLE_CREATE'])
        self.assertEqual(str(claimed['id']),operation['id'])
        real_create=mysql.create
        def response_lost(engine,definition):
            self.assertEqual(real_create(engine,definition),'CREATED')
            raise DDLOutcomeUnknown('Synthetic transport interruption after real DDL')
        with patch.object(mysql,'create',side_effect=response_lost) as create:
            state,code=execute(claimed,owner)
            self.assertEqual(state,'NEEDS_RECONCILIATION');self.assertEqual(create.call_count,1)
            with connect() as connection:Operations(connection).finish(claimed['id'],owner,state=state,error_code=code)
            replay=self.client.post('/api/v1/table-creation-jobs',json=payload,headers=headers)
            self.assertEqual(replay.status_code,202);self.assertEqual(replay.json()['id'],operation['id'])
            self.assertEqual(replay.json()['state'],'NEEDS_RECONCILIATION');self.assertEqual(create.call_count,1)
        history=self.client.get('/api/v1/table-creation-jobs',params={'upload_id':upload['id']}).json()
        self.assertEqual(history['items'][0]['results'][0]['state'],'UNKNOWN')
        new_preview=self.client.get('/api/v1/definition-uploads/'+upload['id']+'/table-preview').json()
        new_attempt=self.client.post('/api/v1/table-creation-jobs',json=dict(upload_id=upload['id'],confirmation_token=new_preview['confirmation_token']),headers={'Idempotency-Key':str(uuid4())})
        self.assertEqual(new_attempt.status_code,409)
        self.assertEqual(new_attempt.json()['error']['code'],'TABLE_RECONCILIATION_REQUIRED')
        self.assertEqual(self.client.get('/api/v1/table-creation-jobs',params={'upload_id':upload['id']}).json()['total'],1)
        revision=UUID(preview['items'][0]['target_connection_revision_id'])
        with target_engine(revision) as engine:self.assertTrue(inspect(engine).has_table(table,schema='etl_test'))

    def test_mysql_partial_job_preserves_created_table_and_reports_permission_failure(self):
        from sqlalchemy import create_engine,text,inspect
        from sqlalchemy.engine import URL
        root=create_engine(URL.create('mysql+pymysql',username='root',password=self.password,host='mysql',database='etl_test'),hide_parameters=True)
        self.addCleanup(root.dispose)
        username='partial_'+uuid4().hex[:16];first='allowed_'+uuid4().hex;second='denied_'+uuid4().hex
        with root.begin() as connection:
            connection.execute(text("CREATE USER :username@'%' IDENTIFIED BY :password"),dict(username=username,password=self.password))
            connection.execute(text('GRANT CREATE ON `etl_test`.`'+first+'` TO '+"'"+username+"'@'%'") )
        target=self.target('MYSQL')
        current=self.client.get('/api/v1/connections/'+target['id'])
        changed=self.client.patch('/api/v1/connections/'+target['id'],json=dict(username=username,password=self.password),headers={'If-Match':current.headers['etag']})
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.client.post('/api/v1/connections/'+target['id']+'/test').json()['status'],'SUCCESS')
        book=load_workbook(Path(__file__).resolve().parents[2]/'templates/Table Definition.xlsx')
        for name in (first,second):
            book['Tables'].append([target['code'],'etl_test',name,None])
            book['Columns'].append([target['code'],'etl_test',name,'id',1,'Integer',None,None,None,'FALSE','TRUE',None,None])
        output=io.BytesIO();book.save(output);book.close()
        upload=self.client.post('/api/v1/definition-uploads',data={'kind':'TABLE'},files={'file':('partial.xlsx',output.getvalue())}).json()
        self.assertEqual(self.validate(upload,target)['state'],'SUCCEEDED')
        preview=self.client.get('/api/v1/definition-uploads/'+upload['id']+'/table-preview').json()
        operation=self.client.post('/api/v1/table-creation-jobs',json=dict(upload_id=upload['id'],confirmation_token=preview['confirmation_token']),headers={'Idempotency-Key':str(uuid4())}).json()
        self.assertEqual(self.wait(operation['id'])['state'],'PARTIALLY_SUCCEEDED')
        history=self.client.get('/api/v1/table-creation-jobs',params={'upload_id':upload['id']}).json()
        results={result['table_name']:result['state'] for result in history['items'][0]['results']}
        self.assertEqual(results,{first:'CREATED',second:'FAILED'})
        self.assertTrue(inspect(root).has_table(first));self.assertFalse(inspect(root).has_table(second))
        definition=next(item for item in preview['items'] if item['table_name']==first)
        verified=self.client.get('/api/v1/table-definitions/'+definition['id']).json()
        # MySQL permits SHOW CREATE TABLE with this table's CREATE privilege;
        # SELECT permission is not necessary to reflect its real definition.
        self.assertEqual(verified['verification_status'],'VERIFIED')
        self.assertEqual([column['name'] for column in verified['actual_columns']],['id'])
        with root.begin() as connection:connection.exec_driver_sql('ALTER TABLE `etl_test`.`'+first+'` ADD COLUMN `external_column` integer NULL')
        drift=self.response(self.client.get('/api/v1/table-definitions/'+definition['id']),'get','/table-definitions/{id}',200)
        self.assertEqual(drift['verification_status'],'DRIFTED');self.assertEqual(len(drift['columns']),1);self.assertEqual(len(drift['actual_columns']),2)
        # Make only this disposable account unavailable; history stays readable.
        with root.begin() as connection:connection.execute(text("ALTER USER :username@'%' ACCOUNT LOCK"),dict(username=username))
        detail=self.response(self.client.get('/api/v1/table-definitions/'+definition['id']),'get','/table-definitions/{id}',200)
        self.assertEqual(detail['verification_status'],'UNAVAILABLE');self.assertIsNone(detail['actual_columns'])
        self.assertEqual(detail['columns'][0]['name'],'id')

    def test_aliases_cannot_concurrently_admit_creation_for_same_physical_table(self):
        target=self.target();upload,table=self.upload(target)
        self.assertEqual(self.validate(upload,target)['state'],'SUCCEEDED')
        alias=self.target()
        book=workbook()
        for sheet in ('Tables','Columns'):
            for row in book[sheet].iter_rows(min_row=2):
                row[0].value=alias['code'];row[1].value='public';row[2].value=table
        data=io.BytesIO();book.save(data);book.close()
        second=self.client.post('/api/v1/definition-uploads',data={'kind':'TABLE'},files={'file':('alias.xlsx',data.getvalue())}).json()
        self.assertEqual(self.validate(second,alias)['state'],'SUCCEEDED')
        previews=[self.client.get('/api/v1/definition-uploads/'+item['id']+'/table-preview').json() for item in (upload,second)]
        self.assertEqual(previews[0]['items'][0]['physical_target_id'],previews[1]['items'][0]['physical_target_id'])
        self.stop_worker();barrier=Barrier(2)
        def submit(index):
            with TestClient(self.app,raise_server_exceptions=False) as client:
                barrier.wait(timeout=10)
                response=client.post('/api/v1/table-creation-jobs',json=dict(upload_id=previews[index]['upload_id'],confirmation_token=previews[index]['confirmation_token']),headers={'Idempotency-Key':str(uuid4())})
                return response.status_code,response.json()
        with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(submit,(0,1)))
        self.assertEqual(sorted(status for status,_ in results),[202,409])
        self.assertEqual(next(body for status,body in results if status==409)['error']['code'],'TABLE_RECONCILIATION_REQUIRED')

    def test_lost_metadata_commit_ack_keeps_completed_workbook(self):
        import asyncio
        from contextlib import contextmanager
        from sqlalchemy import select
        from aat_metadata.models.definitions import UploadedFile
        from aat_api.services import definition_uploads as service
        from aat_api.errors import APIError
        book=workbook();output=io.BytesIO();book.save(output);book.close();data=output.getvalue()
        class Source:
            filename='acknowledgement.xlsx'
            def __init__(self):self.offset=0
            async def read(self,size):
                chunk=data[self.offset:self.offset+size];self.offset+=len(chunk);return chunk
            async def close(self):pass
        original=service.transaction
        with original() as session:before=set(session.scalars(select(UploadedFile.id)))
        @contextmanager
        def ack_lost():
            with original() as session:yield session
            raise APIError('METADATA_UNAVAILABLE','Synthetic lost acknowledgement after actual commit.',503)
        with patch.object(service,'transaction',ack_lost),self.assertRaises(APIError) as error:
            asyncio.run(service.store(Source(),'TABLE'))
        with original() as session:
            rows=list(session.scalars(select(UploadedFile).where(UploadedFile.id.not_in(before))))
            self.assertEqual(len(rows),1);blob=service.storage()/rows[0].safe_storage_key
            self.assertTrue(blob.exists(),'Committed workbook bytes were deleted after an uncertain acknowledgement')
            self.assertEqual(blob.read_bytes(),data)
        self.assertEqual(error.exception.code,'UPLOAD_PUBLICATION_UNCERTAIN')
