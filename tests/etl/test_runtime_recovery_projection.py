"""T091: restore raw-file mapping and project real target evidence after restart."""
from datetime import datetime,timedelta,timezone
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,event,text
from tests.etl import test_snapshot_staging as targets
from tests.integration import test_authorization_repository as metadata_fixtures
from tests.unit import test_mapping as configs


class RuntimeRecoveryProjectionTests(unittest.TestCase):
    setUp=targets.SnapshotTests.setUp
    engine=targets.SnapshotTests.engine

    def run_case(self,kind,final_loss=False):
        from aat_etl.contracts.config import ETLConfig
        from aat_etl.engine import execute_file
        from aat_etl.readers.file_source import FileReference,FilePins,inspect_file_inputs,FileDataset
        from aat_etl.staging.quota import QuotaManager
        from aat_etl.recovery.coordinator import NeedsReconciliation
        from aat_api.workers.recovery import recover_pending
        helper=metadata_fixtures.AuthorizationRepositoryTests();helper.setUpClass();helper.setUp()
        target=self.engine(kind);schema='public' if kind=='postgres' else 'etl_test';table='restart_'+uuid4().hex
        with target.begin() as c:c.execute(text(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY,note VARCHAR(40))'))
        app=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(app.dispose);run=uuid4();dataset_id=uuid4();binding_id=uuid4();intent_id=uuid4();operation_id=uuid4();file_id=uuid4();parser_id=uuid4()
        payload=b'id,note\n1,a\n2,b\n3,c\n';sha=hashlib.sha256(payload).hexdigest();password=self.pg_url.password
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);source=root/uuid4().hex;source.write_bytes(payload);stage=root/'staging';stage.mkdir()
            parser=dict(encoding='utf-8',delimiter=',',header_present=True,quote_character='"',escape_character=None,null_representation='\\N')
            reference=FileReference(file_id,1,sha,len(payload),source,parser)
            raw=configs.configuration();raw['source']=dict(type='CSV',file_id=str(file_id),parser_revision=1,file_sha256=sha)
            raw['target'].update(schema=schema,table=table);raw['batch_size']=2
            raw['mappings']=[dict(source_column='id',target_column='id',transformation='TYPE_CONVERSION',enabled=True),dict(source_column='note',target_column='note',transformation='DIRECT',enabled=True)]
            left,right=inspect_file_inputs(ETLConfig.model_validate(raw),reference,target);raw['target']['physical_target_id']=right.physical_identity
            original=helper.insert
            def insert(c,table_name,**values):
                if table_name=='connection_secrets':
                    from aat_metadata.secrets.codec import SecretCodec
                    values['key_id'],values['ciphertext']=SecretCodec(Path(os.environ['AAT_APP_KEYRING'])).encrypt(password)
                if table_name=='connections':values['database_type']='POSTGRESQL' if kind=='postgres' else 'MYSQL'
                if table_name=='connection_revisions':
                    values.update(database_type='POSTGRESQL' if kind=='postgres' else 'MYSQL',host='postgres' if kind=='postgres' else 'mysql',port=5432 if kind=='postgres' else 3306,
                        database_name='app_metadata' if kind=='postgres' else 'etl_test',schema_name='public' if kind=='postgres' else None,username='postgres' if kind=='postgres' else 'aat_test',physical_server_fingerprint=right.server_fingerprint)
                    raw['target']['connection_revision_id']=str(values['id'])
                if table_name=='etl_definitions':raw['dag_id']=values['dag_id']
                if table_name=='etl_definition_revisions':values.update(config_json=ETLConfig.model_validate(raw).model_dump(mode='json',by_alias=True,exclude_none=True),schema_fingerprint_source=left.fingerprint,schema_fingerprint_target=right.fingerprint)
                if table_name=='replacement_authorizations':values['physical_target_id']=right.physical_identity
                original(c,table_name,**values)
            helper.insert=insert
            with helper.connect() as c:
                original(c,'uploaded_files',id=file_id,original_name='restart.csv',safe_storage_key=source.name,sha256=sha,bytes=len(payload),extension='.csv',parser_revision=1,validation_status='VALID',
                    expires_at=datetime.now(timezone.utc)+timedelta(days=30),encoding='utf-8',delimiter=',',header_present=True,quote_char='"',escape_char=None,null_token='\\N')
                original(c,'file_parser_revisions',id=parser_id,file_id=file_id,revision=1,encoding='utf-8',delimiter=',',header_present=True,quote_char='"',escape_char=None,null_token='\\N')
                case=helper.case(c)
                original(c,'operations',id=operation_id,kind='DAG_TRIGGER',idempotency_key=str(uuid4()),request_sha256='a'*64,state='QUEUED')
                original(c,'run_intents',id=intent_id,operation_id=operation_id,run_uuid=run,dag_id=case['dag'],airflow_run_id='manual__restart_'+run.hex,run_type='manual',etl_revision_id=case['etl_revision'],authorization_id=None,request_sha256='a'*64,state='RESERVED')
            config=ETLConfig.model_validate(raw);pins=FilePins(left.fingerprint,right.physical_identity,right.fingerprint);quota=QuotaManager(app,stage)
            def published(dataset):
                with helper.connect() as c:
                    original(c,'execution_bindings',id=binding_id,dag_id=case['dag'],airflow_run_id='manual__restart_'+run.hex,task_id='execute_etl',airflow_dag_version_id=str(uuid4()),
                        etl_revision_id=case['etl_revision'],source_revision_id=None,target_revision_id=case['revision'],file_parser_revision=parser_id,source_file_sha256=sha,
                        authorization_id=None,run_intent_id=intent_id,airflow_run_type='manual',runtime_build='recovery-fixture',binding_hash='a'*64,state='BOUND',commit_uncertain=False)
                    original(c,'dataset_manifests',id=dataset_id,execution_binding_id=binding_id,generation=1,snapshot_started_at=datetime.now(timezone.utc),schema_hash=right.fingerprint,mapping_hash=dataset.mapping_hash,
                        path_key=dataset.manifest.parent.relative_to(stage).as_posix(),manifest_sha256=dataset.manifest_sha256,extracted_rows=3,validated_rows=0,total_bytes=dataset.manifest.stat().st_size,state='COMPLETE')
                    c.execute('UPDATE execution_bindings SET dataset_id=%s WHERE id=%s',(dataset_id,binding_id))
            armed=[];old_ids=[]
            def arm_loss(connection,cursor,statement,parameters,context,executemany):
                if armed or not statement.startswith('INSERT INTO'):return
                if (final_loss and 'run_commits' not in statement) or (not final_loss and table not in statement):return
                armed.append(True);driver=connection.connection.driver_connection;commit=driver.commit
                old_id=driver.info.backend_pid if kind=='postgres' else driver.thread_id();old_ids.append(old_id)
                with helper.connect() as c:
                    c.execute('UPDATE execution_bindings SET commit_uncertain=true WHERE id=%s',(binding_id,))
                    original(c,'runtime_leases',id=uuid4(),binding_id=binding_id,owner_process_id='old-fixture',target_identity=right.physical_identity,target_lock_identity=str(old_id),recovery_state='NEEDS_RECONCILIATION')
                def lost():
                    driver.commit=commit;commit()
                    if kind=='postgres':
                        import psycopg
                        raise psycopg.OperationalError('Synthetic committed response loss')
                    import pymysql
                    raise pymysql.OperationalError(2013,'Synthetic committed response loss')
                driver.commit=lost
            event.listen(target,'after_cursor_execute',arm_loss)
            try:
                with self.assertRaises(NeedsReconciliation):execute_file(config,reference,target,root=stage,quota=quota,run_uuid=run,dataset_id=dataset_id,binding_sha256='a'*64,pins=pins,support_consent=True,on_prepared=published)
            finally:event.remove(target,'after_cursor_execute',arm_loss)
            result=recover_pending(helper.connect,root=stage)
            current=next(r for r in result if r['binding_id']==str(binding_id))
            self.assertEqual(current['state'],'COMMIT_VERIFIED' if final_loss else 'RESUME_VERIFIED_DATASET')
            self.assertEqual(current['verified_rows'],3 if final_loss else 2)
            with helper.connect() as c:
                if final_loss:
                    self.assertEqual(c.execute('SELECT loaded_rows,validated_rows FROM execution_metrics WHERE binding_id=%s',(binding_id,)).fetchone(),(3,3))
                stored=c.execute('SELECT path_key,manifest_sha256 FROM dataset_manifests WHERE id=%s',(dataset_id,)).fetchone()
            restored=FileDataset.from_manifest(stage/stored[0]/'manifest.json',manifest_sha256=stored[1],binding_sha256='a'*64,config=config,source_schema_hash=left.fingerprint,target=right,run_uuid=run)
            completed=execute_file(config,reference,target,root=stage,quota=quota,run_uuid=run,dataset_id=dataset_id,binding_sha256='a'*64,pins=pins,prepared=restored,old_session_id=old_ids[0])
            self.assertEqual(completed.loaded_rows,3)
            with target.connect() as c:self.assertEqual(list(c.execute(text(f'SELECT id,note FROM {table} ORDER BY id'))),[(1,'a'),(2,'b'),(3,'c')])
            with app.connect() as c:owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':run}).scalars())
            import shutil
            shutil.rmtree(stage);stage.mkdir()
            for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)

    def test_restart_reconstructs_file_mapping_and_resumes_verified_prefix(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind)

    def test_final_file_marker_projects_counts_even_when_raw_validated_count_is_zero(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,True)
