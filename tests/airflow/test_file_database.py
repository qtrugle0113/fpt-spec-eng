"""T143: real file routes, parser fidelity, and protected replacement failures."""
import hashlib
import json
from uuid import UUID,uuid4,uuid5
from sqlalchemy import text
from tests.airflow.test_execution import WorkflowFixture as _WorkflowFixture


class FileDatabaseTests(_WorkflowFixture):
    def file_route(self,extension,target_kind,strategy='APPEND'):
        delimiter=',' if extension=='csv' else '|'
        header='id,note\n' if extension=='csv' else ''
        raw=(header+'1'+delimiter+'"\\N"\n2'+delimiter+'\\N\n3'+delimiter+'"line one\nline two"\n').encode()
        result=self.workflow(target_kind=target_kind,extension=extension,file_data=raw,strategy=strategy,
            parser_options={'header_present':extension=='csv'},expected_records=[(1,'\\N'),(2,None),(3,'line one\nline two')])
        self.assertEqual(result['item']['config']['source']['file_sha256'],hashlib.sha256(raw).hexdigest())
        print('FILE_DATABASE_VERIFIED '+extension+'->'+target_kind+' checksum=true quoted_null=true multiline=true headerless='+str(extension=='txt'),flush=True)

    def test_csv_to_pg(self):self.file_route('csv','POSTGRESQL')
    def test_csv_to_mysql(self):self.file_route('csv','MYSQL')
    def test_txt_to_pg(self):self.file_route('txt','POSTGRESQL')
    def test_txt_to_mysql(self):self.file_route('txt','MYSQL')
    def test_full_refresh_csv_to_pg(self):self.file_route('csv','POSTGRESQL',strategy='FULL_REFRESH')
    def test_full_refresh_txt_to_mysql(self):self.file_route('txt','MYSQL',strategy='FULL_REFRESH')

    def test_invalid_typed_row_cannot_empty_full_refresh_target(self):
        result=self.workflow(extension='csv',strategy='FULL_REFRESH',file_data=b'id,note\ninvalid,first\n2,tail\n',expect_failure=True)
        from aat_api.services.connections.service import transaction
        from aat_etl.staging.quota import GLOBAL_LIMIT,RUN_LIMIT
        with transaction() as session:
            reserved,protected=session.execute(text("SELECT COALESCE(sum(r.reserved_bytes),0),count(*) FILTER (WHERE r.state='PROTECTED') FROM staging_reservations r JOIN run_intents i ON i.run_uuid=r.run_uuid JOIN execution_bindings b ON b.run_intent_id=i.id WHERE b.dag_id=:dag AND b.airflow_run_id=:run AND r.state<>'RELEASED'"),{'dag':result['dag'],'run':result['run_id']}).one()
            binding=session.execute(text('SELECT i.run_uuid,b.dataset_id FROM execution_bindings b JOIN run_intents i ON i.id=b.run_intent_id WHERE b.dag_id=:dag AND b.airflow_run_id=:run'),{'dag':result['dag'],'run':result['run_id']}).one()
        self.assertGreater(protected,0,'Failure evidence must remain protected')
        self.assertLess(reserved,GLOBAL_LIMIT-RUN_LIMIT,'A tiny failed file must leave capacity for another bounded run')
        import os
        from pathlib import Path
        from aat_etl.staging.manager import hashed
        manifest=Path(os.environ['AAT_STAGING_ROOT'])/hashed(result['dag'])/hashed(str(binding.run_uuid))/str(uuid5(binding.dataset_id,'source'))/'manifest.json'
        self.assertEqual(json.loads(manifest.read_text())['state'],'COMPLETE','Protected raw preparation must not be deleted to free quota')
        print('FILE_FAILURE_QUOTA_VERIFIED protected_bytes='+str(reserved)+' protected_artifacts_retained=true',flush=True)

    def test_missing_file_cannot_empty_full_refresh_target(self):
        def remove_owned_file(item):
            from aat_api.services.connections.service import transaction
            from aat_api.services import files
            with transaction() as session:
                row=files.require(session,UUID(item['config']['source']['file_id']))
                self.assertEqual(row.original_name,'sdk-source.csv')
                path=files.source_path(row.safe_storage_key)
            path.unlink()
        self.workflow(extension='csv',strategy='FULL_REFRESH',before_trigger=remove_owned_file,
            expect_failure=True,expect_trigger_error='FILE_SOURCE_UNAVAILABLE')

    def test_invalid_format_is_rejected_before_full_refresh_publication(self):
        from tests.api.test_files import PARSER
        from aat_api.services.table_preview import target_engine
        def edit(book,connection,source,target,revision):
            with target_engine(revision) as engine,engine.begin() as cursor:
                cursor.execute(text(f"INSERT INTO {target} VALUES (99,'old protected row')"))
            response=self.client.post('/api/v1/files',data={'parser_json':json.dumps(PARSER)},
                files={'file':('invalid.csv',b'id,note\n1,ok\n2,extra,column\n','text/csv')})
            file=self.response(response,'post','/files',201)
            operation=self.response(self.client.post('/api/v1/files/'+file['id']+'/validate',
                headers={'Idempotency-Key':str(uuid4())},json={'expected_sha256':file['sha256'],'parser_revision':1}),
                'post','/files/{id}/validate',202)
            self.assertEqual(self.wait(operation['id'])['state'],'FAILED')
            sheet=book['ETL_Definitions'];sheet['C2']='CSV'
            for key in ('D2','E2','F2'):sheet[key]=None
            sheet['G2']=file['id'];sheet['O2']='FULL_REFRESH';sheet['P2']=None
        _,validation,_,target,revision=self.scenario(edit=edit)
        self.assertEqual(validation['state'],'FAILED')
        with target_engine(revision) as engine,engine.connect() as connection:
            self.assertEqual(list(connection.execute(text(f'SELECT id,note FROM {target} ORDER BY id'))),[(99,'old protected row')])
