"""T091: native-owner proof, retention and protected-state gates before deletion."""
from datetime import datetime,timedelta,timezone
import importlib
from pathlib import Path
import tempfile
import unittest
import os
from uuid import uuid4
from sqlalchemy import create_engine,text
from tests.integration import test_authorization_repository as fixtures


class StagingCleanupTests(unittest.TestCase):
    def blocked_startup(self,slow=False):
        from tests.unit import test_mapping as configs
        from aat_api.workers.recovery import recover_pending
        import time
        helper=fixtures.AuthorizationRepositoryTests();helper.setUpClass();helper.setUp()
        original=helper.insert
        def insert(c,table,**values):
            if table=='etl_definition_revisions':values['config_json']=configs.configuration()
            original(c,table,**values)
        helper.insert=insert
        with helper.connect() as c:
            case=helper.case(c);intent=helper.repo(c).reserve_once(**helper.request(case));binding=helper.binding(c,case,intent)
            c.execute('UPDATE execution_bindings SET commit_uncertain=true WHERE id=%s',(binding['binding_id'],))
        def unavailable(_):
            if slow:time.sleep(.25)
            raise OSError('Synthetic target offline')
        start=time.monotonic()
        with tempfile.TemporaryDirectory() as root:
            marker=Path(root)/'protected';marker.write_bytes(b'fixture')
            result=recover_pending(helper.connect,resolve_target=unavailable,root=root,budget_seconds=.05 if slow else 120)
            self.assertTrue(marker.exists())
        current=next(r for r in result if r['binding_id']==str(binding['binding_id']))
        self.assertEqual(current['state'],'NEEDS_RECONCILIATION')
        self.assertEqual(current['reason'],'STARTUP_RECOVERY_BUDGET_EXHAUSTED' if slow else 'TARGET_OWNER_OR_EVIDENCE_UNVERIFIED')
        self.assertLess(time.monotonic()-start,.2 if slow else 120)
        with helper.connect() as c:self.assertTrue(c.execute('SELECT commit_uncertain FROM execution_bindings WHERE id=%s',(binding['binding_id'],)).fetchone()[0])

    def test_startup_records_blocked_reason_without_reclaiming_unknown_owner(self):self.blocked_startup()
    def test_slow_target_cannot_extend_the_startup_recovery_deadline(self):self.blocked_startup(slow=True)

    def run_case(self,protected=False,recent=False,scheduled=False):
        try:module=importlib.import_module('aat_etl.staging.cleanup')
        except ModuleNotFoundError:raise AssertionError('T091 cleanup implementation missing') from None
        from aat_etl.loaders.session import TargetSession
        from aat_etl.staging.manager import hashed
        helper=fixtures.AuthorizationRepositoryTests();helper.setUpClass();helper.setUp()
        engine=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(engine.dispose)
        name='gc_target_'+uuid4().hex
        with engine.begin() as c:c.execute(text(f'CREATE TABLE {name} (id INTEGER PRIMARY KEY)'))
        with TargetSession(engine,schema='public',table=name) as old:
            old_id=old.session_id;identity=old.physical_identity;old.connection.invalidate()
        if scheduled:
            from tests.unit import test_mapping as configs
            original_insert=helper.insert
            def with_config(c,table,**values):
                if table=='etl_definition_revisions':
                    config=configs.configuration();config['target'].update(schema='public',table=name,physical_target_id=identity)
                    values['config_json']=config
                original_insert(c,table,**values)
            helper.insert=with_config
        with helper.connect() as c:
            case=helper.case(c);intent=helper.repo(c).reserve_once(**helper.request(case))
            original=helper.insert
            def insert(c,table,**values):
                if table=='dataset_manifests':values['path_key']='/'.join((hashed(case['dag']),hashed(str(intent['run_uuid'])),str(values['id'])))
                original(c,table,**values)
            helper.insert=insert
            binding=helper.binding(c,case,intent)
            dataset=c.execute('SELECT dataset_id FROM execution_bindings WHERE id=%s',(binding['binding_id'],)).fetchone()[0]
            stamp=datetime.now(timezone.utc)-timedelta(days=1 if recent else 8)
            c.execute("UPDATE execution_bindings SET state='SUCCEEDED',last_reconciled_at=%s,updated_at=%s,commit_uncertain=%s WHERE id=%s",(stamp,stamp,protected,binding['binding_id']))
            c.execute('INSERT INTO runtime_leases(id,binding_id,owner_process_id,target_identity,target_lock_identity,recovery_state) VALUES (%s,%s,%s,%s,%s,%s)',
                (uuid4(),binding['binding_id'],'fixture',identity,str(old_id),'NEEDS_RECONCILIATION' if protected else 'COMMIT_VERIFIED'))
        with tempfile.TemporaryDirectory() as root:
            run_path=Path(root)/hashed(case['dag'])/hashed(str(intent['run_uuid']))
            (run_path/str(dataset)).mkdir(parents=True);artifact=run_path/str(dataset)/'owned.part';artifact.write_bytes(b'fixture')
            if scheduled:
                from contextlib import contextmanager
                from aat_api.workers.recovery import collect_terminal_staging
                @contextmanager
                def resolver(_):yield engine
                results=collect_terminal_staging(helper.connect,root=root,resolve_target=resolver)
                current=next((r for r in results if r['binding_id']==str(binding['binding_id'])),None)
                if protected:
                    self.assertTrue(current is None or not current['collected'])
                else:
                    self.assertIsNotNone(current)
                    self.assertEqual(current['collected'],not recent)
            else:
                with TargetSession(engine,schema='public',table=name) as session:
                    result=module.collect_dataset(engine,root=root,dataset_id=dataset,target_session=session,old_session_id=old_id)
                self.assertEqual(result.collected,not (protected or recent))
            self.assertEqual(artifact.exists(),protected or recent)

    def test_terminal_reconciled_dataset_expires_after_retention(self):self.run_case()
    def test_uncertain_dataset_is_never_deleted_to_free_capacity(self):self.run_case(protected=True)
    def test_terminal_dataset_keeps_full_retention(self):self.run_case(recent=True)
    def test_backend_maintenance_applies_native_cleanup_and_persisted_retention(self):self.run_case(scheduled=True)
