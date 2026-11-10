"""T091/T093: source bootstrap grants enough scratch/inspection, no admin role."""
import importlib
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url,URL
from sqlalchemy.exc import SQLAlchemyError


class MySQLRuntimePermissionsTests(unittest.TestCase):
    def test_actual_source_bootstrap_is_idempotent_and_runtime_can_validate(self):
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable MySQL required')
        from aat_etl.loaders.session import TargetSession
        from aat_etl.loaders.ledger import ensure_support
        from aat_etl.loaders.full_refresh import check_dependencies
        from aat_etl.mapping.validation import validate_rows
        password=make_url(os.environ['AAT_FOUNDATION_TEST_DSN']).password
        runtime_password=secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory() as root:
            (Path(root)/'mysql_admin').write_text(password);(Path(root)/'mysql_etl').write_text(runtime_password)
            bootstrap=importlib.import_module('docker.mysql.initialize')
            with patch.object(bootstrap,'SECRETS',Path(root)):
                bootstrap.initialize();bootstrap.initialize()
        url=URL.create('mysql+pymysql',username='aat_etl',password=runtime_password,host='mysql',database='etl_test',query={'charset':'utf8mb4'})
        engine=create_engine(url,hide_parameters=True);self.addCleanup(engine.dispose)
        with TargetSession(engine,schema='etl_test',table='customers_target') as session:
            ensure_support(session.connection,schema='etl_test',consent=False);session.connection.commit()
            check_dependencies(session)
            result=validate_rows(session.connection,schema='etl_test',table='customers_target',columns=['customer_id','customer_name'],
                rows=[dict(customer_id=987654,customer_name='permission fixture')],conflict_keys=['customer_id'])
            self.assertEqual(result.validated_rows,1)
        with engine.connect() as c:
            self.assertEqual(c.scalar(text('SELECT count(*) FROM customers_source')),3)
            c.rollback()
            with self.assertRaises(SQLAlchemyError):c.execute(text('SELECT count(*) FROM mysql.user'))
