import importlib
import unittest
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from tests.integration import test_connection_models as connections


class SettingModelTests(unittest.TestCase):
    setUpClass=classmethod(connections.ConnectionModelTests.setUpClass.__func__)
    tearDown=connections.ConnectionModelTests.tearDown

    def setUp(self):
        try:
            self.settings=importlib.import_module('aat_metadata.models.settings')
            self.schema=importlib.import_module('aat_api.schemas.settings')
        except ModuleNotFoundError as exc:
            if exc.name not in ('aat_metadata.models.settings','aat_api.schemas.settings'):raise
            raise AssertionError('T027 settings models/validators missing') from None
        connections.ConnectionModelTests.setUp(self)

    def test_db_whitelist_ranges_types_and_iana_timezone(self):
        for key,value,typ in [('password','raw','string'),('default_batch_size',0,'integer'),
            ('default_batch_size',10001,'integer'),('dashboard_refresh_interval',4,'integer'),
            ('staging_retention_days',366,'integer'),('default_timezone','Invalid/Zone','string'),
            ('default_batch_size',True,'integer')]:
            with self.subTest(key=key,value=value),self.assertRaises(IntegrityError),self.session.begin_nested():
                self.session.add(self.settings.ApplicationSetting(key=key,value_json=value,value_type=typ));self.session.flush()
        for key,value,typ in [('default_batch_size',1000,'integer'),('default_timezone','UTC','string')]:
            self.session.add(self.settings.ApplicationSetting(key=key,value_json=value,value_type=typ));self.session.flush()

    def test_patch_strict_ranges_and_readonly_fields(self):
        for value in [{'airflow_connectivity_status':'AVAILABLE'},{'application_version':'x'},
                      {'default_batch_size':True},{'default_batch_size':'1000'},
                      {'dashboard_refresh_interval':3601},{'staging_retention_days':0},
                      {'default_timezone':'Invalid/Zone'}]:
            with self.subTest(value=value),self.assertRaises(ValidationError):self.schema.SettingsPatch(**value)
        patch=self.schema.SettingsPatch(default_batch_size=1,dashboard_refresh_interval=3600,
                                        staging_retention_days=365,default_timezone='Asia/Tokyo')
        self.assertEqual(patch.default_batch_size,1)
