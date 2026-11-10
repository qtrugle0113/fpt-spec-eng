"""T105: generated Python imports under the actual pinned SDK; cells stay data."""
import importlib
from pathlib import Path
import runpy
import tempfile
import unittest
from uuid import uuid4
from tests.unit.test_mapping import configuration


class DAGFactoryTests(unittest.TestCase):
    def generated(self,config):
        module=importlib.import_module('aat_api.deployments.factory')
        return module.render(config,revision_id=uuid4(),revision_sha256='a'*64)

    def test_generated_wrapper_has_one_non_xcom_task_and_finite_sdk_retries(self):
        config=configuration();config.update(retry_count=2,retry_delay=17)
        source=self.generated(config)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'owned.py';path.write_bytes(source)
            namespace=runpy.run_path(str(path));dag=namespace['dag']
        self.assertEqual(dag.dag_id,config['dag_id']);self.assertEqual(dag.max_active_runs,1)
        self.assertFalse(dag.catchup);self.assertTrue(dag.is_paused_upon_creation)
        self.assertEqual(set(dag.task_dict),{'execute_etl'})
        task=dag.task_dict['execute_etl'];self.assertFalse(task.do_xcom_push)
        self.assertEqual(task.retries,2);self.assertEqual(task.retry_delay.total_seconds(),17)
        self.assertIn('aat',dag.tags);self.assertIn('aat_revision:'+'a'*64,dag.tags)

    def test_untrusted_literal_remains_data_and_extra_credentials_are_rejected(self):
        config=configuration();config['mappings']=[dict(source_column=None,target_column='note',transformation='CONSTANT',enabled=True,
            default_literal={'logical_type':'text','value':"'); raise RuntimeError('cell executed'); #"})]
        source=self.generated(config);compile(source,'wrapper.py','exec')
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'owned.py';path.write_bytes(source);runpy.run_path(str(path))
        config['password']='never-copy-this-secret'
        with self.assertRaises(ValueError):self.generated(config)

    def test_canonical_bytes_are_deterministic_and_invalid_identity_rejected(self):
        module=importlib.import_module('aat_api.deployments.factory');identity=uuid4();config=configuration()
        first=module.render(config,revision_id=identity,revision_sha256='a'*64)
        self.assertEqual(first,module.render(dict(reversed(list(config.items()))),revision_id=identity,revision_sha256='a'*64))
        for revision,sha in [('not-a-uuid','a'*64),(identity,'not-a-hash')]:
            with self.subTest(revision=str(revision)),self.assertRaises(ValueError):module.render(config,revision_id=revision,revision_sha256=sha)
