"""T103 metadata policy tests; observed API facts are test inputs, not live evidence."""
import importlib
import unittest
from uuid import uuid4
from tests.integration import test_authorization_repository as fixtures
from tests.unit.test_mapping import configuration


class RuntimeBindingTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixtures.AuthorizationRepositoryTests();self.helper.setUpClass();self.helper.setUp()
        self.module=importlib.import_module('aat_metadata.repositories.bindings')

    def scenario(self,strategy='APPEND',scope='ONCE',file_id=None):
        helper=self.helper;original=helper.insert;version=uuid4();run_id='manual__binding_'+uuid4().hex
        def insert(connection,table,**values):
            if table=='etl_definition_revisions':
                config=configuration();config.update(dag_id=dag[0],load_strategy=strategy)
                config['source']['connection_revision_id']=str(revision[0]);config['target']['connection_revision_id']=str(revision[0])
                config['target']['physical_target_id']='a'*64
                if file_id:config['source']=dict(type='CSV',file_id=str(file_id),parser_revision=1,file_sha256='a'*64)
                if scope=='SCHEDULED':config.update(schedule='0 0 * * *',start_date='2026-01-01T00:00:00Z',timezone='UTC')
                values['config_json']=config
            if table=='etl_definitions':dag.append(values['dag_id'])
            if table=='connection_revisions':revision.append(values['id'])
            if table=='replacement_authorizations':
                values['physical_target_id']='a'*64
                if scope=='SCHEDULED':
                    from aat_metadata.repositories.bindings import schedule_hash
                    config=configuration();config.update(schedule='0 0 * * *',start_date='2026-01-01T00:00:00Z',timezone='UTC')
                    values['schedule_sha256']=schedule_hash(config)
            original(connection,table,**values)
        dag=[];revision=[];helper.insert=insert
        with helper.connect() as c:
            case=helper.case(c,scope=scope)
            operation=uuid4();deployment=uuid4()
            original(c,'operations',id=operation,kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256=case['digest'],state='SUCCEEDED')
            digest=c.execute('SELECT config_sha256 FROM etl_definition_revisions WHERE id=%s',(case['etl_revision'],)).fetchone()[0]
            original(c,'dag_deployments',id=deployment,operation_id=operation,etl_revision_id=case['etl_revision'],state='DEPLOYED',revision_sha256=digest,
                expected_owner_tag='aat',generated_file_key=uuid4().hex+'.py',file_sha256='b'*64,airflow_version_id=version,airflow_version_number=1)
            original(c,'dag_admission',id=uuid4(),dag_id=case['dag'],generation=1,desired_paused=True,gate_state='OPEN',etl_revision_id=case['etl_revision'],deployment_id=deployment)
        facts=self.module.VerifiedRun(case['dag'],run_id,'execute_etl',version,'manual',case['etl_revision'])
        return case,facts

    def test_append_binding_is_idempotent_and_has_no_replacement_authority(self):
        case,facts=self.scenario()
        with self.helper.connect() as c:first=self.module.BindingRepository(c).bind(facts)
        with self.helper.connect() as c:second=self.module.BindingRepository(c).bind(facts)
        self.assertEqual(first['binding_id'],second['binding_id']);self.assertIsNone(first['authorization_id'])
        self.assertTrue(first['run_uuid']);self.assertTrue(first['run_intent_id'])

    def test_blocked_gate_and_old_version_cannot_create_a_binding(self):
        from dataclasses import replace
        case,facts=self.scenario()
        with self.helper.connect() as c:
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(replace(facts,dag_version_id=uuid4()))
            c.execute("UPDATE dag_admission SET gate_state='BLOCKED' WHERE dag_id=%s",(case['dag'],))
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(facts)

    def test_manual_full_refresh_requires_once_intent_and_existing_binding_survives_revoke(self):
        case,facts=self.scenario('FULL_REFRESH')
        with self.helper.connect() as c:
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(facts)
            intent=self.helper.repo(c).reserve_once(**self.helper.request(case,airflow_run_id=facts.run_id,physical_target_id='a'*64))
            first=self.module.BindingRepository(c).bind(facts)
            self.assertEqual(first['run_intent_id'],intent['id'])
            self.helper.repo(c).revoke(case['authorization'])
        with self.helper.connect() as c:
            self.assertEqual(self.module.BindingRepository(c).bind(facts)['binding_id'],first['binding_id'])

    def test_scheduled_authority_is_never_used_for_manual_or_backfill(self):
        from dataclasses import replace
        case,facts=self.scenario('FULL_REFRESH','SCHEDULED')
        with self.helper.connect() as c:
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(facts)
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(replace(facts,run_type='backfill'))
            result=self.module.BindingRepository(c).bind(replace(facts,run_type='scheduled',run_id='scheduled__binding_'+uuid4().hex))
            self.assertEqual(result['authorization_id'],case['authorization'])

    def test_concurrent_first_bind_reuses_one_binding_and_intent(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        _,facts=self.scenario();barrier=Barrier(2)
        def attempt():
            with self.helper.connect() as c:
                barrier.wait(timeout=10);return self.module.BindingRepository(c).bind(facts)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(results[0],results[1])

    def test_revoke_before_first_binding_blocks_replacement(self):
        case,facts=self.scenario('FULL_REFRESH')
        with self.helper.connect() as c:
            self.helper.repo(c).reserve_once(**self.helper.request(case,airflow_run_id=facts.run_id,physical_target_id='a'*64))
            self.helper.repo(c).revoke(case['authorization'])
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(facts)
            self.assertEqual(c.execute('SELECT count(*) FROM execution_bindings WHERE dag_id=%s',(case['dag'],)).fetchone()[0],0)

    def test_file_binding_pins_parser_uuid_and_old_binding_can_reconcile_after_change(self):
        from dataclasses import replace
        identity=uuid4();parser=uuid4()
        with self.helper.connect() as c:
            self.helper.insert(c,'uploaded_files',id=identity,original_name='fixture.csv',safe_storage_key=uuid4().hex,sha256='a'*64,
                bytes=1,extension='.csv',parser_revision=1,validation_status='VALID',encoding='utf-8',delimiter=',',header_present=True,quote_char='"',null_token='\\N')
            self.helper.insert(c,'file_parser_revisions',id=parser,file_id=identity,revision=1,encoding='utf-8',delimiter=',',header_present=True,quote_char='"',null_token='\\N')
        _,facts=self.scenario(file_id=identity)
        with self.helper.connect() as c:
            result=self.module.BindingRepository(c).bind(facts)
            pinned=c.execute('SELECT file_parser_revision,source_file_sha256 FROM execution_bindings WHERE id=%s',(result['binding_id'],)).fetchone()
            self.assertEqual(pinned,(parser,'a'*64))
            self.helper.insert(c,'file_parser_revisions',id=uuid4(),file_id=identity,revision=2,encoding='utf-8',delimiter=';',header_present=True,quote_char='"',null_token='\\N')
            c.execute("UPDATE uploaded_files SET parser_revision=2,validation_status='PENDING' WHERE id=%s",(identity,))
            with self.assertRaises(ValueError):self.module.BindingRepository(c).bind(replace(facts,run_id='manual__new_'+uuid4().hex))
            self.assertEqual(self.module.BindingRepository(c).bind(facts)['binding_id'],result['binding_id'])
