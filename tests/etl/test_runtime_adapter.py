"""T104: direct encrypted lookup and metadata publication before real target DML."""
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from uuid import UUID,uuid4
from sqlalchemy import create_engine,select,text,event
from sqlalchemy.engine import make_url,Engine
from tests.api import test_dag_builder as api


class RuntimeAdapterTests(unittest.TestCase):
    setUp=api.ETLPreviewIntegrationTests.setUp
    target=api.ETLPreviewIntegrationTests.target
    wait=api.ETLPreviewIntegrationTests.wait
    response=api.ETLPreviewIntegrationTests.response
    scenario=api.ETLPreviewIntegrationTests.scenario

    def test_incomplete_recovery_candidate_is_quarantined_without_projecting_null_counts(self):
        from unittest.mock import patch
        import psycopg
        from aat_api.workers.recovery import recover_pending
        binding,_,_,metadata=self.prepare()
        self.worker.kill();self.worker.wait(timeout=10)
        with metadata.begin() as c:
            c.execute(text('UPDATE execution_bindings SET commit_uncertain=true WHERE id=:id'),{'id':binding['binding_id']})
            c.execute(text("INSERT INTO runtime_leases(id,binding_id,owner_process_id,target_identity,target_lock_identity,recovery_state) VALUES(:lease,:id,'fixture','fixture','123','NEEDS_RECONCILIATION')"),{'lease':uuid4(),'id':binding['binding_id']})
            before=c.execute(text('SELECT extracted_rows,validated_rows,loaded_rows FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).first()
        with tempfile.TemporaryDirectory() as root,patch('aat_api.workers.recovery.inspect_candidate',return_value=('COMMIT_VERIFIED',2,'INJECTED_INCOMPLETE_EVIDENCE')):
            rows=recover_pending(lambda:psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']),root=root)
        current=next(row for row in rows if row['binding_id']==str(binding['binding_id']))
        self.assertEqual(current['state'],'NEEDS_RECONCILIATION')
        self.assertEqual(current['reason'],'DATASET_EVIDENCE_UNVERIFIED')
        with metadata.connect() as c:
            self.assertTrue(c.scalar(text('SELECT commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}))
            self.assertEqual(c.execute(text('SELECT extracted_rows,validated_rows,loaded_rows FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).first(),before)

    def test_replacement_recovery_without_admission_keeps_old_target_and_uncertainty(self):
        from unittest.mock import patch
        import psycopg
        from aat_api.services.table_preview import target_engine
        from aat_api.workers.recovery import recover_pending
        binding,target,revision,metadata=self.prepare(strategy='FULL_REFRESH')
        self.worker.kill();self.worker.wait(timeout=10)
        with target_engine(revision) as engine,engine.begin() as c:
            c.execute(text(f"INSERT INTO {target} VALUES (99,'preserved')"))
        with tempfile.TemporaryDirectory() as root:
            with patch('aat_etl.loaders.replacement_admission.AdmissionAdapter.admit',side_effect=ValueError('Synthetic admission unavailable')):
                with self.assertRaises(ValueError):self.runtime.run_binding(binding['binding_id'],root=Path(root),metadata_engine=metadata)
            with metadata.begin() as c:
                self.assertEqual(c.scalar(text('SELECT count(*) FROM replacement_admissions WHERE binding_id=:id'),{'id':binding['binding_id']}),0)
                c.execute(text('UPDATE execution_bindings SET commit_uncertain=true WHERE id=:id'),{'id':binding['binding_id']})
                c.execute(text("UPDATE runtime_leases SET recovery_state='NEEDS_RECONCILIATION' WHERE binding_id=:id"),{'id':binding['binding_id']})
                before=c.execute(text('SELECT extracted_rows,validated_rows,loaded_rows FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).first()
            with patch('aat_api.workers.recovery.inspect_candidate',return_value=('COMMIT_VERIFIED',2,'INJECTED_MISSING_ADMISSION')):
                rows=recover_pending(lambda:psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']),root=root)
            current=next(row for row in rows if row['binding_id']==str(binding['binding_id']))
            self.assertEqual(current['state'],'NEEDS_RECONCILIATION')
            self.assertEqual(current['reason'],'ADMISSION_EVIDENCE_UNVERIFIED')
            with metadata.connect() as c:
                self.assertTrue(c.scalar(text('SELECT commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}))
                self.assertEqual(c.execute(text('SELECT extracted_rows,validated_rows,loaded_rows FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).first(),before)
            with target_engine(revision) as engine,engine.connect() as c:
                self.assertEqual(c.execute(text(f'SELECT id,note FROM {target}')).all(),[(99,'preserved')])

    def prepare(self,kind='POSTGRESQL',strategy='APPEND',file_source=False,bad_tail=False):
        self.runtime=importlib.import_module('aat_etl.runtime')
        def edit(book,*_):
            sheet=book['ETL_Definitions'];sheet['O2']=strategy
            if file_source:
                import json
                from tests.api.test_files import PARSER
                payload=b'id,note\n1,first\n2,second\n'+(b'broken,third\n' if bad_tail else b'')
                uploaded=self.response(self.client.post('/api/v1/files',data={'parser_json':json.dumps(PARSER)},files={'file':('source.csv',payload,'text/csv')}),'post','/files',201)
                queued=self.client.post('/api/v1/files/'+uploaded['id']+'/validate',json={'expected_sha256':uploaded['sha256'],'parser_revision':1},headers={'Idempotency-Key':str(uuid4())})
                self.assertEqual(self.wait(queued.json()['id'])['state'],'SUCCEEDED')
                sheet['C2']='CSV';sheet['G2']=uploaded['id'];sheet['Q2']=2
                for cell in ('D2','E2','F2'):sheet[cell]=None
                dag=sheet['A2'].value
                book['Column_Mappings'].append([dag,'id','id','Type Conversion',None,'TRUE'])
                book['Column_Mappings'].append([dag,'note','note','Direct Mapping',None,'TRUE'])
        uploaded,operation,dag,target,revision=self.scenario(database_type=kind,edit=edit)
        self.assertEqual(operation['state'],'SUCCEEDED')
        from aat_api.services.connections.service import transaction
        from aat_api.services.table_preview import target_engine
        from aat_etl.loaders.ledger import ensure_support
        from aat_metadata.models.etl import ETLDefinitionRevision
        from aat_metadata.models.operations import Operation,DAGDeployment,AdmissionState
        from aat_metadata.repositories.bindings import BindingRepository,VerifiedRun
        import psycopg
        from psycopg import sql
        version=uuid4();run='manual__runtime_'+uuid4().hex
        with target_engine(revision) as engine,engine.begin() as c:
            ensure_support(c,schema='public' if kind=='POSTGRESQL' else 'etl_test',consent=True)
        with transaction() as session:
            config=session.scalar(select(ETLDefinitionRevision).where(ETLDefinitionRevision.upload_id==UUID(uploaded['id'])))
            config_id=config.id
            operation=Operation(kind='DAG_DEPLOY',idempotency_key=str(uuid4()),request_sha256='a'*64,state='SUCCEEDED',progress_json={'support_objects_acknowledged':True})
            session.add(operation);session.flush()
            deployment=DAGDeployment(operation_id=operation.id,etl_revision_id=config.id,state='DEPLOYED',revision_sha256=config.config_sha256,
                airflow_version_id=version,airflow_version_number=1,generated_file_key=uuid4().hex+'.py',file_sha256='b'*64)
            session.add(deployment);session.flush()
            session.add(AdmissionState(dag_id=dag,gate_state='OPEN',etl_revision_id=config.id,deployment_id=deployment.id))
            authority=None
            if strategy=='FULL_REFRESH':
                from datetime import datetime,timezone
                from aat_metadata.models.authorizations import DataReplacementAuthorization
                authority=DataReplacementAuthorization(dag_id=dag,etl_revision_id=config.id,physical_target_id=config.config_json['target']['physical_target_id'],
                    scope='ONCE',scope_sha256='c'*64,acknowledged_at=datetime.now(timezone.utc),allow_empty=False)
                session.add(authority);session.flush();authority=authority.id
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            if authority:
                from aat_metadata.repositories.authorizations import AuthorizationRepository
                from aat_metadata.models.etl import ETLDefinitionRevision
                physical=c.execute("SELECT config_json->'target'->>'physical_target_id' FROM etl_definition_revisions WHERE id=%s",(config_id,)).fetchone()[0]
                AuthorizationRepository(c).reserve_once(authorization_id=authority,dag_id=dag,etl_revision_id=config_id,physical_target_id=physical,
                    scope_sha256='c'*64,idempotency_key=uuid4(),request_sha256='d'*64,run_uuid=uuid4(),airflow_run_id=run)
            binding=BindingRepository(c).bind(VerifiedRun(dag,run,'execute_etl',version,'manual',config_id))
            c.execute(sql.SQL('ALTER ROLE aat_etl PASSWORD {}').format(sql.Literal('synthetic-runtime-fixture')))
        url=make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).set(drivername='postgresql+psycopg',username='aat_etl',password='synthetic-runtime-fixture')
        metadata=create_engine(url,hide_parameters=True);self.addCleanup(metadata.dispose)
        return binding,target,revision,metadata

    def test_database_targets_use_runtime_role_and_publish_before_first_insert(self):
        from aat_api.services.table_preview import target_engine
        for kind in ('POSTGRESQL','MYSQL'):
            with self.subTest(kind=kind):
                binding,target,revision,metadata=self.prepare(kind);observed=[];checking=[True]
                def before_write(connection,cursor,statement,parameters,context,executemany):
                    if not checking[0] or not statement.startswith('INSERT INTO') or target not in statement:return
                    native=connection.connection.driver_connection
                    identity=native.info.backend_pid if kind=='POSTGRESQL' else native.thread_id()
                    with metadata.connect() as c:
                        stored=c.execute(text('SELECT d.state,l.target_lock_identity FROM execution_bindings b JOIN dataset_manifests d ON d.id=b.dataset_id JOIN runtime_leases l ON l.binding_id=b.id WHERE b.id=:id'),{'id':binding['binding_id']}).one()
                        self.assertEqual(stored,('COMPLETE',str(identity)))
                    observed.append(True)
                event.listen(Engine,'before_cursor_execute',before_write)
                try:
                    with tempfile.TemporaryDirectory() as root:
                        result=self.runtime.run_binding(binding['binding_id'],root=Path(root),metadata_engine=metadata)
                        self.assertEqual(result.loaded_rows,2);self.assertTrue(observed)
                        with metadata.connect() as c:
                            state=c.execute(text('SELECT state,commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}).one()
                            self.assertEqual(state,('COMMIT_VERIFIED',False))
                            self.assertEqual(c.scalar(text('SELECT loaded_rows FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}),2)
                        checking[0]=False
                        with target_engine(revision) as engine,engine.begin() as c:
                            c.execute(text(f"INSERT INTO {target} VALUES (99,'external-fixture-row')"))
                        checking[0]=True
                        repeated=self.runtime.run_binding(binding['binding_id'],root=Path(root),metadata_engine=metadata)
                        self.assertEqual(repeated.loaded_rows,2)
                        with target_engine(revision) as engine,engine.connect() as c:self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {target}')),3)
                finally:event.remove(Engine,'before_cursor_execute',before_write)

    def test_bind_failure_does_not_start_the_engine_or_send_credentials(self):
        self.runtime=importlib.import_module('aat_etl.runtime')
        import httpx
        from unittest.mock import patch
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(503,json={'error':{'code':'AIRFLOW_IDENTITY_UNAVAILABLE'}})
        with tempfile.TemporaryDirectory() as root:
            token=Path(root)/'runtime_token';token.write_text('d'*64)
            with patch.dict(os.environ,{'AAT_RUNTIME_TOKEN_FILE':str(token)}):
                with self.assertRaises(self.runtime.RuntimeUnavailable):
                    self.runtime.bind_context(dag_id='safe',run_id='manual__fixture',task_id='execute_etl',expected_revision=str(uuid4()),transport=httpx.MockTransport(handler))
        self.assertEqual(len(requests),1)
        self.assertEqual(str(requests[0].url),'http://backend:8000/internal/runtime/bind')
        self.assertNotIn(b'password',requests[0].content)

    def test_full_refresh_consumes_once_using_the_restricted_runtime_metadata_role(self):
        from aat_api.services.table_preview import target_engine
        for kind in ('POSTGRESQL','MYSQL'):
            with self.subTest(kind=kind):
                binding,target,revision,metadata=self.prepare(kind,'FULL_REFRESH')
                with target_engine(revision) as engine,engine.begin() as c:c.execute(text(f"INSERT INTO {target} VALUES (99,'old fixture data')"))
                with tempfile.TemporaryDirectory() as root:
                    result=self.runtime.run_binding(binding['binding_id'],root=Path(root),metadata_engine=metadata)
                    self.assertEqual(result.loaded_rows,2)
                    with metadata.connect() as c:
                        self.assertEqual(c.scalar(text('SELECT state FROM replacement_authorizations WHERE id=:id'),{'id':binding['authorization_id']}),'CONSUMED')
                    with target_engine(revision) as engine,engine.connect() as c:self.assertEqual(list(c.scalars(text(f'SELECT id FROM {target} ORDER BY id'))),[1,2])

    def test_file_final_commit_can_reconcile_after_staging_is_lost(self):
        import shutil
        for kind in ('POSTGRESQL','MYSQL'):
            with self.subTest(kind=kind):
                binding,_,_,metadata=self.prepare(kind,file_source=True)
                with tempfile.TemporaryDirectory() as root:
                    root=Path(root);result=self.runtime.run_binding(binding['binding_id'],root=root,metadata_engine=metadata)
                    self.assertEqual(result.loaded_rows,2)
                    with metadata.connect() as c:
                        raw_validated=c.scalar(text('SELECT validated_rows FROM dataset_manifests WHERE execution_binding_id=:id'),{'id':binding['binding_id']})
                        self.assertEqual(raw_validated,0)
                    shutil.rmtree(root);root.mkdir()
                    repeated=self.runtime.run_binding(binding['binding_id'],root=root,metadata_engine=metadata)
                    self.assertEqual(repeated.loaded_rows,2)

    def test_file_partial_commit_recovery_does_not_map_the_uncommitted_invalid_tail(self):
        from aat_etl.recovery.coordinator import NeedsReconciliation
        from aat_api.workers.recovery import recover_pending
        import psycopg
        for kind in ('POSTGRESQL','MYSQL'):
            with self.subTest(kind=kind):
                binding,target,_,metadata=self.prepare(kind,file_source=True,bad_tail=True);armed=[]
                def commit_loss(connection,cursor,statement,parameters,context,executemany):
                    if armed or not statement.startswith('INSERT INTO') or target not in statement:return
                    armed.append(True);driver=connection.connection.driver_connection;commit=driver.commit
                    def lost():
                        driver.commit=commit;commit()
                        if kind=='POSTGRESQL':raise psycopg.OperationalError('Synthetic committed response loss')
                        import pymysql
                        raise pymysql.OperationalError(2013,'Synthetic committed response loss')
                    driver.commit=lost
                with tempfile.TemporaryDirectory() as root:
                    event.listen(Engine,'after_cursor_execute',commit_loss)
                    try:
                        with self.assertRaises(NeedsReconciliation):self.runtime.run_binding(binding['binding_id'],root=Path(root),metadata_engine=metadata)
                    finally:event.remove(Engine,'after_cursor_execute',commit_loss)
                    def connect():return psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN'])
                    rows=recover_pending(connect,root=root)
                    current=next(row for row in rows if row['binding_id']==str(binding['binding_id']))
                    self.assertEqual(current['state'],'RESUME_VERIFIED_DATASET')
                    self.assertEqual(current['verified_rows'],2)
                    with metadata.connect() as c:
                        self.assertFalse(c.scalar(text('SELECT commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}))
                        self.assertEqual(c.execute(text('SELECT loaded_rows,validated_rows FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).one(),(2,2))

    def test_late_recovery_cannot_clear_a_new_runtime_owner(self):
        from unittest.mock import patch
        import psycopg
        from aat_api.workers.recovery import recover_pending
        binding,_,_,metadata=self.prepare()
        with metadata.begin() as c:
            c.execute(text("UPDATE execution_bindings SET commit_uncertain=true WHERE id=:id"),{'id':binding['binding_id']})
            c.execute(text("INSERT INTO runtime_leases(id,binding_id,owner_process_id,target_identity,target_lock_identity,recovery_state) VALUES(:lease,:id,'prior','fixture','123','WRITING')"),{'lease':uuid4(),'id':binding['binding_id']})
        def changed_owner(*args):
            with metadata.begin() as c:
                c.execute(text("UPDATE runtime_leases SET owner_process_id='new-owner',target_lock_identity='456' WHERE binding_id=:id"),{'id':binding['binding_id']})
            return 'COMMIT_VERIFIED',2,'TARGET_MARKERS_VERIFIED'
        def connect():return psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN'])
        with tempfile.TemporaryDirectory() as root,patch('aat_api.workers.recovery.inspect_candidate',side_effect=changed_owner):
            rows=recover_pending(connect,root=root)
        current=next(row for row in rows if row['binding_id']==str(binding['binding_id']))
        self.assertEqual(current['reason'],'OWNER_FENCE_CHANGED')
        with metadata.connect() as c:
            self.assertTrue(c.scalar(text('SELECT commit_uncertain FROM execution_bindings WHERE id=:id'),{'id':binding['binding_id']}))
            self.assertEqual(c.execute(text('SELECT owner_process_id,recovery_state FROM runtime_leases WHERE binding_id=:id'),{'id':binding['binding_id']}).one(),('new-owner','WRITING'))

    def test_supervised_child_executes_without_returning_dataset_or_credentials(self):
        from unittest.mock import patch
        from aat_etl.runtime_task import run_bound
        from aat_api.services.table_preview import target_engine
        for kind in ('POSTGRESQL','MYSQL'):
            with self.subTest(kind=kind):
                binding,target,revision,metadata=self.prepare(kind)
                # Disposable-only DSN remains confined to the child environment.
                with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{
                    'AAT_FOUNDATION_TEST_DSN':metadata.url.set(drivername='postgresql').render_as_string(hide_password=False),
                    'AAT_STAGING_ROOT':root}):
                    self.assertIsNone(run_bound(binding['binding_id']))
                    self.assertIsNone(run_bound(binding['binding_id']))
                with target_engine(revision) as engine,engine.connect() as c:
                    self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {target}')),2)

    def test_metadata_admission_outage_cannot_use_cached_authority(self):
        from unittest.mock import patch
        from aat_api.services.table_preview import target_engine
        import psycopg
        binding,target,revision,metadata=self.prepare(strategy='FULL_REFRESH')
        with target_engine(revision) as engine,engine.begin() as c:
            c.execute(text(f"INSERT INTO {target} VALUES (99,'preserved')"))
        with tempfile.TemporaryDirectory() as root,patch('aat_etl.runtime._connect',side_effect=psycopg.OperationalError('Synthetic metadata outage')):
            with self.assertRaises((ValueError,psycopg.Error)):
                self.runtime.run_binding(binding['binding_id'],root=Path(root),metadata_engine=metadata)
        with target_engine(revision) as engine,engine.connect() as c:
            self.assertEqual(list(c.scalars(text(f'SELECT id FROM {target}'))),[99])
        with metadata.connect() as c:
            self.assertEqual(c.scalar(text('SELECT state FROM replacement_authorizations WHERE id=:id'),{'id':binding['authorization_id']}),'RESERVED')
            self.assertEqual(c.scalar(text('SELECT count(*) FROM replacement_admissions WHERE binding_id=:id'),{'id':binding['binding_id']}),0)

    def test_unresolved_other_binding_blocks_writes_to_the_same_physical_target(self):
        import psycopg
        from aat_metadata.repositories.bindings import BindingRepository,VerifiedRun
        from aat_etl.recovery.coordinator import NeedsReconciliation
        from aat_api.services.table_preview import target_engine
        binding,target,revision,metadata=self.prepare()
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            facts=c.execute("SELECT b.dag_id,b.etl_revision_id,b.airflow_dag_version_id,r.config_json->'target'->>'physical_target_id' FROM execution_bindings b JOIN etl_definition_revisions r ON r.id=b.etl_revision_id WHERE b.id=%s",(binding['binding_id'],)).fetchone()
            c.execute('UPDATE execution_bindings SET commit_uncertain=true WHERE id=%s',(binding['binding_id'],))
            c.execute("INSERT INTO runtime_leases(id,binding_id,owner_process_id,target_identity,target_lock_identity,recovery_state) VALUES(%s,%s,'prior',%s,'123','WRITING')",(uuid4(),binding['binding_id'],facts[3]))
            second=BindingRepository(c).bind(VerifiedRun(facts[0],'manual__runtime_'+uuid4().hex,'execute_etl',facts[2],'manual',facts[1]))
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(NeedsReconciliation):
                self.runtime.run_binding(second['binding_id'],root=Path(root),metadata_engine=metadata)
        with target_engine(revision) as engine,engine.connect() as c:
            self.assertEqual(c.scalar(text(f'SELECT count(*) FROM {target}')),0)
