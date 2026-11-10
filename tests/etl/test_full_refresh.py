"""T083/T089: replacement needs real ONCE admission and one target commit."""
from datetime import datetime,timezone
import importlib
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import text
from tests.etl import test_target_ledger as targets
from tests.integration import test_authorization_repository as fixtures


class FullRefreshTests(unittest.TestCase):
    setUp=targets.TargetLedgerTests.setUp
    engine=targets.TargetLedgerTests.engine
    isolated=targets.TargetLedgerTests.isolated

    def run_case(self,kind,mode='normal',file_type=None):
        try:module=importlib.import_module('aat_etl.loaders.full_refresh')
        except ModuleNotFoundError:raise AssertionError('T089 full refresh writer missing') from None
        from aat_etl.loaders.session import TargetSession
        from aat_etl.loaders.ledger import ensure_support
        from aat_etl.loaders.replacement_admission import AdmissionAdapter
        from aat_etl.readers.schema import inspect_table
        from aat_etl.staging.manager import StagingWriter
        from aat_etl.contracts.writer import PreparedDataset
        helper=fixtures.AuthorizationRepositoryTests();helper.setUpClass();helper.setUp()
        engine,schema=self.isolated(kind)
        with engine.begin() as c:c.execute(text('INSERT INTO output_rows VALUES (42)'))
        if mode=='inbound_fk':
            with engine.begin() as c:
                c.execute(text('CREATE TABLE inbound_child (id INTEGER REFERENCES output_rows(id))' if kind=='postgres' else 'CREATE TABLE inbound_child (id INTEGER, FOREIGN KEY(id) REFERENCES output_rows(id)) ENGINE=InnoDB'))
                c.execute(text('INSERT INTO inbound_child VALUES (42)'))
        if mode=='trigger':
            with engine.begin() as c:
                if kind=='postgres':
                    c.execute(text('CREATE FUNCTION fixture_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$'))
                    c.execute(text('CREATE TRIGGER fixture_effect BEFORE INSERT ON output_rows FOR EACH ROW EXECUTE FUNCTION fixture_trigger()'))
                else:c.execute(text('CREATE TRIGGER fixture_effect BEFORE INSERT ON output_rows FOR EACH ROW SET NEW.id=NEW.id'))
        target=inspect_table(engine,schema=schema,table='output_rows',used_columns=['id'])
        with engine.connect() as c:ledger=ensure_support(c,schema=schema,consent=True);c.commit()
        original=helper.insert
        def insert(c,table,**values):
            if table=='replacement_authorizations':values['physical_target_id']=target.physical_identity
            original(c,table,**values)
        helper.insert=insert
        with helper.connect() as c:
            case=helper.case(c,allow_empty=mode=='empty_allowed')
            intent=helper.repo(c).reserve_once(**helper.request(case,physical_target_id=target.physical_identity))
        values=[] if mode.startswith('empty') else [1,2,3]
        if mode=='rollback':values=[1,1]
        dataset_id=uuid4();binding_id=uuid4()
        with tempfile.TemporaryDirectory() as root:
            quota=None
            if file_type:
                import hashlib,os
                from pathlib import Path
                from sqlalchemy import create_engine
                from tests.unit import test_mapping as configs
                from aat_etl.contracts.config import ETLConfig
                from aat_etl.readers.file_source import FileReference,FilePins,inspect_file_inputs,prepare_file
                from aat_etl.staging.quota import QuotaManager
                metadata=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True);self.addCleanup(metadata.dispose)
                staging=Path(root)/'staging';staging.mkdir();quota=QuotaManager(metadata,staging)
                payload=b'id\n1\n2\n3\n';source=Path(root)/uuid4().hex;source.write_bytes(payload);file_id=uuid4()
                reference=FileReference(file_id,1,hashlib.sha256(payload).hexdigest(),len(payload),source,
                    dict(encoding='utf-8',delimiter=',' if file_type=='CSV' else '|',header_present=True,quote_character='"',escape_character=None,null_representation='\\N'))
                raw=configs.configuration();raw.update(dag_id=case['dag'],load_strategy='FULL_REFRESH',mappings=[dict(source_column='id',target_column='id',transformation='TYPE_CONVERSION',enabled=True)])
                raw['source']=dict(type=file_type,file_id=str(file_id),parser_revision=1,file_sha256=reference.sha256)
                raw['target'].update(schema=schema,table='output_rows',physical_target_id=target.physical_identity)
                config=ETLConfig.model_validate(raw);left,right=inspect_file_inputs(config,reference,engine)
                dataset=prepare_file(config,reference,engine,root=staging,quota=quota,run_uuid=intent['run_uuid'],dataset_id=dataset_id,binding_sha256=case['digest'],pins=FilePins(left.fingerprint,right.physical_identity,right.fingerprint))
                manifest=dataset.manifest
                manifest_sha=dataset.manifest_sha256;total_bytes=manifest.stat().st_size
            else:
                with StagingWriter(root,dag_id=case['dag'],run_id=str(intent['run_uuid']),dataset_id=dataset_id,binding_sha256=case['digest'],
                    source_schema_hash='b'*64,target_schema_hash=target.fingerprint,mapping_hash='c'*64,columns=list(target.columns),source_snapshot_time=datetime.now(timezone.utc)) as writer:
                    for value in values:writer.append([value])
                    manifest=writer.complete(validated_rows=len(values))
                manifest_sha=writer.manifest_sha256;total_bytes=writer.bytes
                dataset=PreparedDataset(manifest,manifest_sha,case['digest'],intent['run_uuid'],target.physical_identity,'b'*64,target.fingerprint,'c'*64,len(values),len(values))
            if mode=='corrupt':
                part=next(manifest.parent.rglob('*.jsonl'));part.chmod(0o600);part.write_bytes(b'corrupt\n')
            with helper.connect() as c:
                helper.insert(c,'execution_bindings',id=binding_id,dag_id=case['dag'],airflow_run_id=intent['airflow_run_id'],task_id='transfer',airflow_dag_version_id=str(uuid4()),
                    etl_revision_id=case['etl_revision'],source_revision_id=case['revision'],target_revision_id=case['revision'],authorization_id=case['authorization'],
                    run_intent_id=intent['id'],airflow_run_type='manual',runtime_build='full-refresh-fixture',binding_hash=case['digest'],state='BOUND',commit_uncertain=False)
                helper.insert(c,'dataset_manifests',id=dataset_id,execution_binding_id=binding_id,generation=1,snapshot_started_at=datetime.now(timezone.utc),schema_hash=target.fingerprint,
                    mapping_hash='c'*64,path_key='refresh/'+uuid4().hex,manifest_sha256=manifest_sha,extracted_rows=len(values),validated_rows=len(values),total_bytes=total_bytes,state='COMPLETE')
                c.execute('UPDATE execution_bindings SET dataset_id=%s WHERE id=%s',(dataset_id,binding_id))
                if mode=='revoked':helper.repo(c).revoke(case['authorization'])
            adapter=AdmissionAdapter(helper.connect,authorization_id=case['authorization'],run_intent_id=intent['id'],binding_id=binding_id,scope_sha256=case['digest'])
            if mode=='admitted_revoked':
                admit=adapter.admit
                def revoke_after_admission(*args,**kwargs):
                    result=admit(*args,**kwargs)
                    with helper.connect() as c:helper.repo(c).revoke(case['authorization'])
                    return result
                adapter.admit=revoke_after_admission
            if file_type:
                from aat_etl.engine import execute_file
                from sqlalchemy import event
                cancel=[False]
                def after_insert(connection,cursor,statement,parameters,context,executemany):
                    if statement.startswith('INSERT INTO') and 'output_rows' in statement:cancel[0]=True
                if mode=='cancel':event.listen(engine,'after_cursor_execute',after_insert)
                try:
                    call=lambda:execute_file(config,reference,engine,root=staging,quota=quota,run_uuid=intent['run_uuid'],dataset_id=dataset_id,
                        binding_sha256=case['digest'],pins=FilePins(left.fingerprint,right.physical_identity,right.fingerprint),
                        admission=adapter,prepared=dataset,cancelled=lambda:cancel[0])
                    if mode=='cancel':
                        with self.assertRaises(ValueError):call()
                        with helper.connect() as c:self.assertEqual(c.execute('SELECT state FROM replacement_authorizations WHERE id=%s',(case['authorization'],)).fetchone()[0],'CLOSED')
                    else:self.assertEqual(call().loaded_rows,3)
                finally:
                    if mode=='cancel':event.remove(engine,'after_cursor_execute',after_insert)
            with TargetSession(engine,schema=schema,table='output_rows') as session:
                if mode=='commit_lost':
                    from aat_etl.loaders.batches import CommitUncertain
                    driver=session.connection.connection.driver_connection;commit=driver.commit
                    def lost():
                        commit()
                        if kind=='postgres':
                            import psycopg
                            raise psycopg.OperationalError('Synthetic replacement COMMIT response lost')
                        import pymysql
                        raise pymysql.OperationalError(2013,'Synthetic replacement COMMIT response lost')
                    with patch.object(driver,'commit',side_effect=lost),self.assertRaises(CommitUncertain):
                        module.execute(dataset,session,ledger,adapter,owner_process_id='fixture',batch_rows=1)
                elif mode in ('rollback','revoked','empty_denied','inbound_fk','trigger','corrupt','cancel'):
                    with self.assertRaises(ValueError):module.execute(dataset,session,ledger,adapter,owner_process_id='fixture',batch_rows=1)
                else:self.assertEqual(module.execute(dataset,session,ledger,adapter,owner_process_id='fixture',batch_rows=1),len(values))
            if mode in ('normal','commit_lost'):
                # A verified final marker is sufficient for reconciliation even
                # after ONCE has been consumed; retry cannot replace again.
                with TargetSession(engine,schema=schema,table='output_rows') as session:
                    self.assertEqual(module.execute(dataset,session,ledger,adapter,owner_process_id='retry',batch_rows=1),3)
            with engine.connect() as c:
                actual=list(c.scalars(text('SELECT id FROM output_rows ORDER BY id')))
                self.assertEqual(actual,[42] if mode in ('rollback','revoked','empty_denied','inbound_fk','trigger','corrupt','cancel') else sorted(values))
            if mode in ('inbound_fk','trigger','corrupt'):
                with helper.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM replacement_admissions WHERE binding_id=%s',(binding_id,)).fetchone()[0],0)
            if quota is not None:
                with metadata.connect() as c:owned=list(c.execute(text('SELECT id FROM staging_reservations WHERE run_uuid=:run'),{'run':intent['run_uuid']}).scalars())
                import shutil
                shutil.rmtree(staging)
                for identity in owned:quota.release_after_cleanup(identity,writer_stopped=True,artifacts_removed=True,reconciled=True)

    def test_postgres_replacement_and_consumed_once_retry(self):self.run_case('postgres')
    def test_mysql_replacement_and_consumed_once_retry(self):self.run_case('mysql')
    def test_midinsert_failure_rolls_back_whole_replacement(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,'rollback')
    def test_revoked_before_admission_preserves_old_data(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,'revoked')
    def test_empty_dataset_requires_separate_allow_empty_acknowledgment(self):
        for kind in ('postgres','mysql'):
            for mode in ('empty_denied','empty_allowed'):
                with self.subTest(kind=kind,mode=mode):self.run_case(kind,mode)

    def test_inbound_foreign_keys_and_triggers_block_before_admission(self):
        for kind in ('postgres','mysql'):
            for mode in ('inbound_fk','trigger'):
                with self.subTest(kind=kind,mode=mode):self.run_case(kind,mode)

    def test_revoke_after_admission_does_not_promise_cancellation(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,'admitted_revoked')

    def test_lost_replacement_commit_response_reconciles_without_second_delete(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,'commit_lost')

    def test_corrupt_complete_dataset_preserves_target_and_never_admits(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,'corrupt')

    def test_csv_txt_replacement_prepares_whole_mapped_dataset(self):
        for kind in ('postgres','mysql'):
            for file_type in ('CSV','TXT'):
                with self.subTest(kind=kind,file_type=file_type):self.run_case(kind,file_type=file_type)

    def test_confirmed_cancellation_rolls_back_and_closes_once(self):
        for kind in ('postgres','mysql'):
            with self.subTest(kind=kind):self.run_case(kind,mode='cancel',file_type='CSV')
