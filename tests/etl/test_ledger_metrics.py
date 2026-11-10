"""T082: project independently committed target markers, never invoke writers."""
import importlib
import unittest
from uuid import uuid4
from sqlalchemy import create_engine,text
import os
from tests.etl import test_target_ledger as targets
from tests.integration import test_authorization_repository as authorization


class LedgerMetricTests(unittest.TestCase):
    setUp=targets.TargetLedgerTests.setUp
    engine=targets.TargetLedgerTests.engine
    isolated=targets.TargetLedgerTests.isolated

    def test_real_committed_marker_projection_is_idempotent_and_failure_does_not_replay(self):
        try:
            metrics=importlib.import_module('aat_etl.metrics')
            repository=importlib.import_module('aat_metadata.repositories.metrics')
        except ModuleNotFoundError:raise AssertionError('T082 metric projection implementation missing') from None
        from aat_etl.loaders.ledger import ensure_support,BatchMarker
        from aat_etl.loaders.session import TargetSession
        from aat_etl.readers.schema import inspect_table
        helper=authorization.AuthorizationRepositoryTests()
        helper.setUpClass();helper.setUp()
        with helper.connect() as c:
            case=helper.case(c);intent=helper.repo(c).reserve_once(**helper.request(case));binding=helper.binding(c,case,intent,dataset_rows=2)
        target,schema=self.isolated('postgres')
        with target.connect() as c:ledger=ensure_support(c,schema=schema,consent=True);c.commit()
        identity=inspect_table(target,schema=schema,table='output_rows',used_columns=['id']).physical_identity
        marker=BatchMarker(identity,intent['run_uuid'],'a'*64,0,'b'*64,2,'c'*64,'APPEND')
        with target.begin() as c:
            c.execute(text('INSERT INTO output_rows VALUES (1),(2)'));ledger.record_batch(c,marker)
        app=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
        self.addCleanup(app.dispose)
        with TargetSession(target,schema=schema,table='output_rows') as session:
            snapshot=metrics.snapshot_from_ledger(session,ledger,target_identity=identity,run_uuid=intent['run_uuid'],
                dataset_sha='a'*64,binding_sha='b'*64,extracted_rows=2,validated_rows=2,phase='LOADING')
        self.assertEqual(snapshot.loaded_rows,2);self.assertIsNone(snapshot.failed_rows)
        for _ in range(2):
            with app.begin() as c:repository.project(c,binding['binding_id'],snapshot)
        with app.connect() as c:
            rows=c.execute(text('SELECT loaded_rows,failed_rows_nullable FROM execution_metrics WHERE binding_id=:id'),{'id':binding['binding_id']}).all()
            self.assertEqual(rows,[(2,None)])
        closed=app.connect();closed.close()
        with self.assertRaises(Exception):repository.project(closed,binding['binding_id'],snapshot)
        with target.connect() as c:self.assertEqual(c.scalar(text('SELECT count(*) FROM output_rows')),2)
