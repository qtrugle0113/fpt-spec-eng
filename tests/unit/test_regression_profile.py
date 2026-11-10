"""Regression runners must never receive application networks or secret volumes."""
from pathlib import Path
import unittest
import yaml


class RegressionIsolationTests(unittest.TestCase):
    def test_test_profile_cannot_reach_production_secret_domains(self):
        root=Path(__file__).resolve().parents[2]
        config=yaml.safe_load((root/'docker-compose.yml').read_text(encoding='utf-8'))
        services=config['services'];runner=services['backend-tests']
        self.assertEqual(runner['networks'],['regression_internal'])
        self.assertTrue(config['networks']['regression_internal']['internal'])
        self.assertEqual(runner['environment']['AAT_FOUNDATION_DISPOSABLE'],'1')
        for name in ('backend-tests','regression-secrets','regression-postgres','regression-mysql'):
            service=services[name]
            self.assertFalse(service.get('ports'))
            for mount in service.get('volumes',[]):
                self.assertIsInstance(mount,str)
                self.assertTrue(mount.split(':')[0].startswith('regression_'))
            self.assertNotIn('aat_internal',service.get('networks',{}))
        self.assertEqual(services['regression-secrets']['network_mode'],'none')
        self.assertNotIn('frontend',runner['depends_on'])
