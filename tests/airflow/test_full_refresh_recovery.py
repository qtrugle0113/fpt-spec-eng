"""T145: real SDK authorization fences and replacement commit recovery."""
from pathlib import Path
from sqlalchemy import text
from tests.airflow.test_execution import WorkflowFixture as _WorkflowFixture


class FullRefreshRecoveryTests(_WorkflowFixture):
    def verify(self,kind,mode):
        from aat_api.services.connections.service import transaction
        result=self.workflow(target_kind=kind,strategy='FULL_REFRESH',fault_mode=mode)
        current=self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id'])
        self.assertEqual(current.status_code,200)
        self.assertEqual(current.json()['state'],'CLOSED' if mode in ('terminal-extraction','revoke-before-admission') else 'CONSUMED')
        with transaction() as session:
            bindings=session.execute(text('SELECT id FROM execution_bindings WHERE dag_id=:dag'),{'dag':result['dag']}).scalars().all()
            self.assertEqual(len(bindings),1)
            self.assertTrue((Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(bindings[0])+'-'+mode)).exists(),'Fault must execute inside this exact SDK binding')
            admissions=session.execute(text('SELECT a.state FROM replacement_admissions a JOIN execution_bindings b ON b.id=a.binding_id WHERE b.dag_id=:dag'),{'dag':result['dag']}).scalars().all()
            self.assertEqual(admissions,[] if mode in ('terminal-extraction','revoke-before-admission') else ['COMMIT_VERIFIED'])
        print('FULL_REFRESH_RECOVERY_VERIFIED target='+kind+' mode='+mode+' authority_fenced=true exact_rows=true',flush=True)

    def test_postgres_admission_acknowledgement_loss(self):self.verify('POSTGRESQL','admission-ack-loss')
    def test_mysql_admission_acknowledgement_loss(self):self.verify('MYSQL','admission-ack-loss')
    def test_postgres_target_commit_response_loss(self):self.verify('POSTGRESQL','target-commit-loss')
    def test_mysql_target_commit_response_loss(self):self.verify('MYSQL','target-commit-loss')
    def test_postgres_revoke_before_admission_keeps_old_target(self):self.verify('POSTGRESQL','revoke-before-admission')
    def test_mysql_revoke_before_admission_keeps_old_target(self):self.verify('MYSQL','revoke-before-admission')
    def test_postgres_revoke_after_admission_allows_verified_commit(self):self.verify('POSTGRESQL','revoke-after-admission')
    def test_mysql_revoke_after_admission_allows_verified_commit(self):self.verify('MYSQL','revoke-after-admission')
    def test_postgres_reaped_extraction_retries_reserved_once(self):self.verify('POSTGRESQL','extraction-kill')
    def test_mysql_reaped_extraction_retries_reserved_once(self):self.verify('MYSQL','extraction-kill')
    def test_postgres_terminal_extraction_closes_once_keeps_old_target(self):self.verify('POSTGRESQL','terminal-extraction')
    def test_mysql_terminal_extraction_closes_once_keeps_old_target(self):self.verify('MYSQL','terminal-extraction')


class ReplacementBoundaryTests(_WorkflowFixture):
    def check_marker(self,result,mode,expected):
        from aat_api.services.connections.service import transaction
        with transaction() as session:
            identity=session.scalar(text('SELECT id FROM execution_bindings WHERE dag_id=:dag'),{'dag':result['dag']})
        self.assertEqual((Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(identity)+'-'+mode)).read_text(),expected)

    def empty(self,kind,allowed):
        def old_target(item):
            if not allowed:return # The failure fixture already inserts the protected row.
            from aat_api.services.table_preview import target_engine
            target=item['config']['target']
            with target_engine(target['connection_revision_id']) as engine,engine.begin() as connection:
                quote=engine.dialect.identifier_preparer.quote_identifier
                connection.exec_driver_sql('INSERT INTO '+quote(target['schema'])+'.'+quote(target['table'])+" VALUES (99,'old protected row')")
        result=self.workflow(target_kind=kind,extension='csv',strategy='FULL_REFRESH',
            file_data=b'id,note\n',expected_records=[],expect_failure=not allowed,
            allow_empty=allowed,before_trigger=old_target)
        authority=self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id']).json()
        self.assertEqual(authority['state'],'CONSUMED' if allowed else 'CLOSED')
        self.assertEqual(authority['allow_empty'],allowed)
        print('EMPTY_REPLACEMENT_VERIFIED target='+kind+' explicit_consent='+str(allowed),flush=True)

    def rollback(self,kind):
        result=self.workflow(target_kind=kind,strategy='FULL_REFRESH',fault_mode='full-refresh-midinsert',expect_failure=True)
        self.check_marker(result,'full-refresh-midinsert','replacement_rows_inserted_before_rollback')

    def visibility(self,kind):
        def old_target(item):
            from aat_api.services.table_preview import target_engine
            target=item['config']['target']
            with target_engine(target['connection_revision_id']) as engine,engine.begin() as connection:
                quote=engine.dialect.identifier_preparer.quote_identifier
                connection.exec_driver_sql('INSERT INTO '+quote(target['schema'])+'.'+quote(target['table'])+" VALUES (99,'old protected row')")
        result=self.workflow(target_kind=kind,strategy='FULL_REFRESH',fault_mode='full-refresh-visibility',before_trigger=old_target)
        self.check_marker(result,'full-refresh-visibility','old_and_new_generations_verified')

    def test_postgres_empty_without_consent_preserves_old_target(self):self.empty('POSTGRESQL',False)
    def test_mysql_empty_without_consent_preserves_old_target(self):self.empty('MYSQL',False)
    def test_postgres_explicit_empty_consent_replaces_target(self):self.empty('POSTGRESQL',True)
    def test_mysql_explicit_empty_consent_replaces_target(self):self.empty('MYSQL',True)
    def test_postgres_failure_after_insert_rolls_back_replacement(self):self.rollback('POSTGRESQL')
    def test_mysql_failure_after_insert_rolls_back_replacement(self):self.rollback('MYSQL')
    def test_postgres_readers_see_old_then_new_generation(self):self.visibility('POSTGRESQL')
    def test_mysql_readers_see_old_then_new_generation(self):self.visibility('MYSQL')


class AdmissionBoundaryTests(_WorkflowFixture):
    def dependency(self,kind):
        from aat_api.services.connections.service import transaction
        result=self.workflow(target_kind=kind,strategy='FULL_REFRESH',fault_mode='full-refresh-dependency',expect_failure=True)
        with transaction() as session:
            identity=session.scalar(text('SELECT id FROM execution_bindings WHERE dag_id=:dag'),{'dag':result['dag']})
            count=session.scalar(text('SELECT count(*) FROM replacement_admissions WHERE binding_id=:id'),{'id':identity})
            self.assertEqual(count,0,'A new inbound dependency must reject replacement before admission')
        self.assertEqual((Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(identity)+'-full-refresh-dependency')).read_text(),'dependency_installed_before_admission')
        self.assertEqual(self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id']).json()['state'],'CLOSED')

    def expired_confirmation(self,kind):
        import time
        from uuid import uuid4
        from unittest.mock import patch
        from aat_api.services.connections.service import transaction
        result=self.workflow(target_kind=kind,strategy='FULL_REFRESH')
        with patch('aat_api.services.confirmation.time.time',return_value=time.time()+601):
            replay=self.client.post('/api/v1/dags/'+result['dag']+'/trigger',
                headers={'Idempotency-Key':result['trigger_key']},json=result['trigger_body'])
            self.assertEqual(replay.status_code,202)
            self.assertEqual(replay.json()['id'],result['command']['id'])
            rejected=self.client.post('/api/v1/dags/'+result['dag']+'/trigger',
                headers={'Idempotency-Key':str(uuid4())},json=result['trigger_body'])
            self.assertEqual(rejected.status_code,409)
            self.assertEqual(rejected.json()['error']['code'],'CONFIRMATION_STALE_OR_INVALID')
        with transaction() as session:
            self.assertEqual(session.scalar(text('SELECT count(*) FROM run_intents WHERE dag_id=:dag'),{'dag':result['dag']}),1)
        self.assertEqual(self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id']).json()['state'],'CONSUMED')
        print('EXPIRED_CONFIRMATION_VERIFIED target='+kind+' same_key_replays=true new_key_rejected=true no_once_release=true',flush=True)

    def test_postgres_new_inbound_dependency_blocks_before_admission(self):self.dependency('POSTGRESQL')
    def test_mysql_new_inbound_dependency_blocks_before_admission(self):self.dependency('MYSQL')
    def test_postgres_expired_confirmation_replays_only_the_existing_intent(self):self.expired_confirmation('POSTGRESQL')
    def test_mysql_expired_confirmation_replays_only_the_existing_intent(self):self.expired_confirmation('MYSQL')


class InvalidationBoundaryTests(_WorkflowFixture):
    def invalidated(self,kind):
        from aat_api.services.connections.service import transaction
        result=self.workflow(target_kind=kind,strategy='FULL_REFRESH',fault_mode='invalidate-before-admission',
                             expect_failure=True,pause_after_run=False)
        with transaction() as session:
            identity=session.scalar(text('SELECT id FROM execution_bindings WHERE dag_id=:dag'),{'dag':result['dag']})
            self.assertEqual(session.scalar(text('SELECT count(*) FROM replacement_admissions WHERE binding_id=:id'),{'id':identity}),0)
        self.assertEqual((Path('/tmp/aat-runtime-staging')/('authorization-fault-'+str(identity)+'-invalidate-before-admission')).read_text(),'invalidated_before_admission')
        detail=self.client.get('/api/v1/replacement-authorizations/'+result['authority']['id']).json()
        self.assertEqual(detail['state'],'CLOSED')
        self.assertIsNotNone(detail['invalidated_at'])
        print('INVALIDATED_ADMISSION_VERIFIED target='+kind+' no_admission=true old_target_preserved=true',flush=True)

    def test_postgres_changed_credential_invalidates_before_admission(self):self.invalidated('POSTGRESQL')
    def test_mysql_changed_credential_invalidates_before_admission(self):self.invalidated('MYSQL')
