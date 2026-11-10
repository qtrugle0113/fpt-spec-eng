"""T096: DAG Builder public contracts before implementation (real app/database)."""
import hashlib
import io
import os
from pathlib import Path
import unittest
from uuid import UUID,uuid4
from fastapi.testclient import TestClient
import yaml
from sqlalchemy import text
from tests.api.test_openapi_contract import CONTRACT,ContractHarness


class DAGBuilderContractTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable database required')
        from aat_api.main import app
        self.client=TestClient(app,raise_server_exceptions=False);self.addCleanup(self.client.close)
        self.contract=yaml.safe_load(CONTRACT.read_text(encoding='utf-8'))
        self.harness=ContractHarness(self.contract)

    def test_download_preserves_canonical_etl_workbook_bytes_and_etag(self):
        data=(Path(os.environ['AAT_ASSETS_ROOT'])/'templates/ETL Definition.xlsx').read_bytes()
        response=self.client.get('/api/v1/templates/etl-definition')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.content,data)
        self.assertEqual(response.headers['etag'],'"'+hashlib.sha256(data).hexdigest()+'"')
        self.assertIn('attachment',response.headers['content-disposition'])

    def test_etl_upload_is_durable_and_roundtrips_the_workbook_hash(self):
        data=(Path(os.environ['AAT_ASSETS_ROOT'])/'templates/ETL Definition.xlsx').read_bytes()
        response=self.client.post('/api/v1/definition-uploads',data={'kind':'ETL'},
            files={'file':('../../etl.xlsx',data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
        self.assertEqual(response.status_code,201)
        self.harness.assert_response('post','/definition-uploads',201,response.json(),headers=response.headers)
        uploaded=response.json();self.assertEqual(uploaded['sha256'],hashlib.sha256(data).hexdigest())
        self.assertEqual(uploaded['kind'],'ETL');self.assertEqual(uploaded['status'],'UPLOADED')
        detail=self.client.get('/api/v1/definition-uploads/'+uploaded['id'])
        self.assertEqual(detail.status_code,200);self.assertEqual(detail.json(),uploaded)
        self.assertEqual(response.headers['location'],'/api/v1/definition-uploads/'+uploaded['id'])

    def test_sample_references_exist_in_the_actual_seeded_registry(self):
        from aat_api.validation.etl_definitions import validate
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.connections import Connection
        from aat_metadata.models.definitions import UploadedFile
        from sqlalchemy import select,func
        result=validate(Path(os.environ['AAT_ASSETS_ROOT'])/'samples/definitions/ETL Definition.sample.xlsx')
        self.assertFalse(result.issues)
        with transaction() as session:
            for definition in result.definitions:
                values=definition.values
                for key in ('source_connection_code','target_connection_code'):
                    if values.get(key):self.assertIsNotNone(session.scalar(select(Connection.id).where(func.lower(Connection.code)==values[key].lower())))
                if values.get('source_file_id'):self.assertIsNotNone(session.get(UploadedFile,UUID(values['source_file_id'])))

    def test_missing_preview_and_deployment_return_safe_contract_errors(self):
        identity=str(uuid4())
        for path in ('/definition-uploads/{id}/etl-preview','/dag-deployments/{id}'):
            with self.subTest(path=path):
                response=self.client.get('/api/v1'+path.replace('{id}',identity))
                self.assertEqual(response.status_code,404)
                self.harness.assert_response('get',path,'default',response.json(),headers=response.headers)

    def test_deployment_requires_valid_confirmation_and_idempotency_before_work(self):
        response=self.client.post('/api/v1/dag-deployments',json={'upload_id':str(uuid4()),'dag_ids':['safe_dag'],
            'confirmation_token':'stale','support_objects_acknowledged':False})
        self.assertEqual(response.status_code,422)
        self.harness.assert_response('post','/dag-deployments','default',response.json(),headers=response.headers)


class ETLPreviewIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests.api import test_tables
        test_tables.TableAPITests.setUp(self)

    from tests.api import test_tables as _tables
    target=_tables.TableAPITests.target
    wait=_tables.TableAPITests.wait
    response=_tables.TableAPITests.response

    def scenario(self,invalid=False,edit=None,database_type='POSTGRESQL'):
        from tests.unit.test_etl_workbook import workbook
        from aat_api.services.table_preview import target_engine
        connection=self.target(database_type);source='preview_source_'+uuid4().hex;target='preview_target_'+uuid4().hex
        # Resolve the immutable connection revision through metadata; public DTO
        # revision numbers are not revision UUIDs.
        from aat_api.services.connections.service import transaction,active
        with transaction() as session:_,current=active(session,UUID(connection['id']));revision=current.id
        with target_engine(revision) as engine,engine.begin() as c:
            c.execute(text(f'CREATE TABLE {source} (id INTEGER PRIMARY KEY,note VARCHAR(40))'))
            c.execute(text(f"INSERT INTO {source} VALUES (1,'first'),(2,NULL)"))
            c.execute(text(f'CREATE TABLE {target} (id INTEGER PRIMARY KEY,note VARCHAR(40))'))
        book=workbook();sheet=book['ETL_Definitions'];dag='preview_'+uuid4().hex
        target_schema='public' if database_type=='POSTGRESQL' else 'etl_test'
        for cell,value in {'A2':dag,'D2':connection['code'],'E2':target_schema,'F2':source,'H2':connection['code'],'I2':target_schema,'J2':target}.items():sheet[cell]=value
        if invalid:sheet['R2']=11
        if edit:edit(book,connection,source,target,revision)
        output=io.BytesIO();book.save(output);book.close();data=output.getvalue()
        response=self.client.post('/api/v1/definition-uploads',data={'kind':'ETL'},files={'file':('etl.xlsx',data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
        uploaded=self.response(response,'post','/definition-uploads',201)
        validated=self.client.post('/api/v1/definition-uploads/'+uploaded['id']+'/validate',json={'expected_sha256':uploaded['sha256']},headers={'Idempotency-Key':str(uuid4())})
        operation=self.response(validated,'post','/definition-uploads/{id}/validate',202)
        finished=self.wait(operation['id'])
        return uploaded,finished,dag,target,revision

    def test_validated_workbook_produces_typed_persisted_preview_without_target_writes(self):
        uploaded,operation,dag,target,revision=self.scenario()
        self.assertEqual(operation['state'],'SUCCEEDED')
        response=self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/etl-preview')
        preview=self.response(response,'get','/definition-uploads/{id}/etl-preview',200)
        self.assertEqual(len(preview['items']),1);item=preview['items'][0]
        from aat_etl.contracts.config import ETLConfig
        config=ETLConfig.model_validate(item['config'])
        self.assertEqual(config.dag_id,dag);self.assertTrue(config.is_paused)
        self.assertEqual(config.target.connection_revision_id,revision)
        self.assertEqual(config.target.table,target);self.assertIn('support_ddl',item)
        self.assertTrue(preview['confirmation_token']);self.assertTrue(preview['dependency_fingerprint'])
        from aat_api.services.table_preview import target_engine
        with target_engine(revision) as engine,engine.connect() as c:self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {target}')),0)

    def test_invalid_workbook_does_not_create_partial_etl_definitions(self):
        uploaded,operation,dag,_,_=self.scenario(invalid=True)
        self.assertEqual(operation['state'],'FAILED')
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinition
        from sqlalchemy import select
        with transaction() as session:self.assertIsNone(session.scalar(select(ETLDefinition.id).where(ETLDefinition.dag_id==dag)))
        response=self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/issues')
        issues=self.response(response,'get','/definition-uploads/{id}/issues',200)
        self.assertTrue(issues['items']);self.assertEqual(issues['items'][0]['row'],2)

    def test_schema_drift_invalidates_preview_before_confirmation(self):
        uploaded,operation,_,target,revision=self.scenario()
        self.assertEqual(operation['state'],'SUCCEEDED')
        from aat_api.services.table_preview import target_engine
        with target_engine(revision) as engine,engine.begin() as c:c.execute(text(f'ALTER TABLE {target} ALTER COLUMN note TYPE VARCHAR(20)'))
        response=self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/etl-preview')
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()['error']['code'],'DEPENDENCY_CHANGED')

    def test_same_physical_table_and_nonunique_upsert_keys_are_rejected(self):
        for mode in ('alias','key'):
            def edit(book,connection,source,target,revision):
                sheet=book['ETL_Definitions']
                if mode=='alias':sheet['F2']=target
                else:sheet['O2']='UPSERT';sheet['P2']='note'
            with self.subTest(mode=mode):
                uploaded,operation,_,_,_=self.scenario(edit=edit)
                self.assertEqual(operation['state'],'FAILED')
                self.assertEqual(self.client.get('/api/v1/definition-uploads/'+uploaded['id']).json()['status'],'INVALID')

    def test_full_refresh_with_inbound_fk_is_rejected_on_both_targets(self):
        from aat_api.services.table_preview import target_engine
        for kind in ('POSTGRESQL','MYSQL'):
            def edit(book,connection,source,target,revision):
                book['ETL_Definitions']['O2']='FULL_REFRESH'
                with target_engine(revision) as engine,engine.begin() as c:
                    c.execute(text(f'CREATE TABLE child_{uuid4().hex} (id INTEGER REFERENCES {target}(id))') if kind=='POSTGRESQL' else text(f'CREATE TABLE child_{uuid4().hex} (id INTEGER,FOREIGN KEY(id) REFERENCES {target}(id))'))
            with self.subTest(kind=kind):
                _,operation,_,_,_=self.scenario(edit=edit,database_type=kind)
                self.assertEqual(operation['state'],'FAILED')

    def test_one_invalid_dependency_prevents_publication_of_every_dag(self):
        def edit(book,connection,source,target,revision):
            row=[cell.value for cell in book['ETL_Definitions'][2]]
            row[0]+='_other';row[9]='missing_'+uuid4().hex;book['ETL_Definitions'].append(row)
        uploaded,operation,dag,_,_=self.scenario(edit=edit)
        self.assertEqual(operation['state'],'FAILED')
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.etl import ETLDefinition
        from sqlalchemy import select
        with transaction() as session:self.assertFalse(session.scalars(select(ETLDefinition.id).where(ETLDefinition.dag_id.in_([dag,dag+'_other']))).all())

    def test_csv_and_txt_preview_pin_validated_parser_and_typed_mappings(self):
        import json
        from tests.api.test_files import PARSER
        for kind in ('POSTGRESQL','MYSQL'):
            for extension in ('csv','txt'):
                def edit(book,connection,source,target,revision):
                    response=self.client.post('/api/v1/files',data={'parser_json':json.dumps(PARSER)},
                        files={'file':('source.'+extension,b'id,note\n1,hello\n2,world\n','text/plain')})
                    file=self.response(response,'post','/files',201)
                    operation=self.client.post('/api/v1/files/'+file['id']+'/validate',json={'expected_sha256':file['sha256'],'parser_revision':1},headers={'Idempotency-Key':str(uuid4())})
                    self.assertEqual(self.wait(operation.json()['id'])['state'],'SUCCEEDED')
                    sheet=book['ETL_Definitions'];sheet['C2']=None
                    for cell in ('D2','E2','F2'):sheet[cell]=None
                    sheet['G2']=file['id']
                    dag=sheet['A2'].value
                    book['Column_Mappings'].append([dag,'id','id','Type Conversion',None,'TRUE'])
                    book['Column_Mappings'].append([dag,'note','note','Direct Mapping',None,'TRUE'])
                with self.subTest(database=kind,extension=extension):
                    uploaded,operation,_,_,_=self.scenario(edit=edit,database_type=kind)
                    if operation['state']!='SUCCEEDED':
                        from aat_api.services.connections.service import transaction
                        from aat_api.services.definition_uploads import require,storage,UploadedFile
                        from aat_api.validation.etl_definitions import validate
                        from aat_api.services.etl_preview import compile_definition
                        import traceback
                        with transaction() as session:
                            stored=require(session,UUID(uploaded['id']));file=session.get(UploadedFile,stored.uploaded_file_id);path=storage()/file.safe_storage_key
                        try:compile_definition(validate(path).definitions[0])
                        except Exception as error:
                            self.fail(type(error).__name__+' frames='+str([(Path(frame.filename).name,frame.lineno,frame.name) for frame in traceback.extract_tb(error.__traceback__)]))
                    self.assertEqual(operation['state'],'SUCCEEDED')
                    preview=self.response(self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/etl-preview'),'get','/definition-uploads/{id}/etl-preview',200)
                    config=preview['items'][0]['config'];self.assertEqual(config['source']['type'],extension.upper())
                    self.assertEqual(config['source']['parser_revision'],1)
                    self.assertEqual(config['mappings'][0]['transformation'],'TYPE_CONVERSION')

    def test_duplicate_revision_fails_without_leaving_validation_stuck(self):
        uploaded,operation,_,_,_=self.scenario()
        self.assertEqual(operation['state'],'SUCCEEDED')
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.definitions import DefinitionUpload,UploadedFile
        from aat_api.services.definition_uploads import storage
        with transaction() as session:
            upload=session.get(DefinitionUpload,UUID(uploaded['id']));file=session.get(UploadedFile,upload.uploaded_file_id)
            data=(storage()/file.safe_storage_key).read_bytes()
        response=self.client.post('/api/v1/definition-uploads',data={'kind':'ETL'},files={'file':('same.xlsx',data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
        duplicate=response.json()
        queued=self.client.post('/api/v1/definition-uploads/'+duplicate['id']+'/validate',json={},headers={'Idempotency-Key':str(uuid4())})
        self.assertEqual(self.wait(queued.json()['id'])['state'],'FAILED')
        self.assertEqual(self.client.get('/api/v1/definition-uploads/'+duplicate['id']).json()['status'],'INVALID')
        issues=self.client.get('/api/v1/definition-uploads/'+duplicate['id']+'/issues').json()
        self.assertEqual(issues['items'][0]['code'],'ETL_REVISION_EXISTS')

    def test_readonly_target_and_unreadable_source_fail_before_publication(self):
        from aat_api.services.table_preview import target_engine
        from psycopg import sql
        for mode in ('target','source'):
            def edit(book,connection,source,target,revision):
                role='readonly_'+uuid4().hex
                with target_engine(revision) as engine,engine.begin() as c:
                    with c.connection.driver_connection.cursor() as cursor:
                        cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(self.password)))
                        cursor.execute(sql.SQL('GRANT CONNECT ON DATABASE app_metadata TO {}').format(sql.Identifier(role)))
                        cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
                        cursor.execute(sql.SQL('GRANT SELECT ON {} TO {}').format(sql.Identifier(target),sql.Identifier(role)))
                response=self.client.post('/api/v1/connections',json=dict(code=role,name='Read only fixture',database_type='POSTGRESQL',
                    host='postgres',port=5432,database_name='app_metadata',schema_name='public',username=role,password=self.password))
                restricted=self.response(response,'post','/connections',201)
                self.assertEqual(self.client.post('/api/v1/connections/'+restricted['id']+'/test').json()['status'],'SUCCESS')
                book['ETL_Definitions']['H2' if mode=='target' else 'D2']=role
            with self.subTest(mode=mode):
                uploaded,operation,_,_,_=self.scenario(edit=edit)
                self.assertEqual(operation['state'],'FAILED')
                issues=self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/issues').json()['items']
                self.assertEqual(issues[0]['code'],'TARGET_NOT_WRITABLE' if mode=='target' else 'ETL_DEPENDENCY_INVALID')

    def test_preview_columns_keep_real_lengths_primary_key_and_literal_default(self):
        from aat_api.services.table_preview import target_engine
        for kind in ('POSTGRESQL','MYSQL'):
            def edit(book,connection,source,target,revision):
                with target_engine(revision) as engine,engine.begin() as c:
                    c.execute(text(f"ALTER TABLE {target} ALTER COLUMN note SET DEFAULT 'unknown'"))
            with self.subTest(kind=kind):
                uploaded,operation,_,_,_=self.scenario(edit=edit,database_type=kind)
                self.assertEqual(operation['state'],'SUCCEEDED')
                preview=self.response(self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/etl-preview'),'get','/definition-uploads/{id}/etl-preview',200)
                item=preview['items'][0];self.assertEqual(item['primary_key'],['id'])
                columns={column['name']:column for column in item['columns']}
                self.assertEqual(columns['id']['primary_key_ordinal'],1)
                self.assertEqual(columns['note']['length'],40)
                self.assertEqual(columns['note']['default_literal'],{'logical_type':'varchar','value':'unknown'})

    def test_connection_revision_change_during_preview_prevents_confirmation(self):
        uploaded,operation,_,_,_=self.scenario()
        self.assertEqual(operation['state'],'SUCCEEDED')
        from unittest.mock import patch
        from aat_api.services import etl_preview
        from aat_api.services.connections.service import transaction
        from aat_metadata.models.connections import Connection,ConnectionRevision
        original=etl_preview.compile_definition
        def rotate_after_compile(spec):
            compiled=original(spec)
            with transaction() as session:
                old=session.get(ConnectionRevision,compiled.config.target.connection_revision_id)
                parent=session.get(Connection,old.connection_id)
                fields={key:getattr(old,key) for key in ('database_type','host','port','database_name','schema_name','username','secret_id','test_status','tested_at','physical_server_fingerprint')}
                revision=ConnectionRevision(connection_id=parent.id,revision=old.revision+1,**fields)
                session.add(revision);session.flush();parent.current_revision_id=revision.id
            return compiled
        with patch.object(etl_preview,'compile_definition',side_effect=rotate_after_compile):
            response=self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/etl-preview')
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()['error']['code'],'DEPENDENCY_CHANGED')
        self.assertNotIn('confirmation_token',response.json())

    def test_safe_full_refresh_preview_requires_separate_authority_and_empty_acknowledgment(self):
        for kind in ('POSTGRESQL','MYSQL'):
            def edit(book,*_):book['ETL_Definitions']['O2']='FULL_REFRESH'
            with self.subTest(kind=kind):
                uploaded,operation,_,_,_=self.scenario(edit=edit,database_type=kind)
                self.assertEqual(operation['state'],'SUCCEEDED')
                preview=self.response(self.client.get('/api/v1/definition-uploads/'+uploaded['id']+'/etl-preview'),'get','/definition-uploads/{id}/etl-preview',200)
                warnings=' '.join(preview['items'][0]['warnings'])
                self.assertIn('separate scoped replacement authorization',warnings)
                self.assertIn('Empty replacement requires a separate explicit acknowledgment',warnings)
                self.assertNotIn('allow_empty',preview['items'][0]['config'])
