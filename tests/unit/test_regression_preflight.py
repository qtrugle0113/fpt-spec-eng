"""Kiểm trạng thái preflight; không thay bằng chứng DB/Airflow integration."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


class RegressionPreflightTests(unittest.TestCase):
    def run_preflight(self, group, available):
        with tempfile.TemporaryDirectory(prefix='preflight-') as folder:
            directory = Path(folder)
            script = directory / 'tests/tools/run_regression.py'
            script.parent.mkdir(parents=True)
            script.write_bytes((ROOT / 'tests/tools/run_regression.py').read_bytes())
            manifest = directory / 'images.json'
            images = {name: str(index) * 64 for index, name in enumerate(
                ('tests', 'backend', 'postgres', 'mysql', 'airflow', 'frontend', 'e2e', 'workbook_deps'), 1)}
            manifest.write_text(json.dumps(images), encoding='utf-8')
            inspected = []

            def inspect(command, **kwargs):
                self.assertEqual(command[:3], ['podman', 'image', 'inspect'])
                identity = command[3]
                name = next(name for name, value in images.items() if value == identity)
                inspected.append(name)
                if name in available:
                    return subprocess.CompletedProcess(command, 0, identity + '\n', '')
                return subprocess.CompletedProcess(command, 125, '', 'Image not found')

            arguments = ['run_regression.py', '--group', group, '--preflight-only',
                '--images', str(manifest),
                '--evidence-dir', str(directory)]
            with patch.object(sys, 'argv', arguments), patch('subprocess.run', side_effect=inspect):
                with self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(script), run_name='__main__')
            result = json.loads((directory / 'regression-results.json').read_text(encoding='utf-8'))
            return stopped.exception.code, result, inspected

    def test_missing_images_records_every_blocker_without_starting_fixture(self):
        code, result, inspected = self.run_preflight('all', set())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(len(inspected), 8)
        self.assertTrue(all(row['status'] == 'BLOCKED' for row in result['preflight']))
        self.assertEqual(result['selectors'], [])

    def test_integration_does_not_require_unrelated_browser_or_airflow_images(self):
        expected = {'tests', 'backend', 'postgres', 'mysql'}
        code, result, inspected = self.run_preflight('integration', expected)
        self.assertEqual(code, 0)
        self.assertEqual(set(inspected), expected)
        self.assertEqual(result['status'], 'PREFLIGHT_PASS')
        self.assertFalse(result['tests_executed'])
        self.assertEqual(result['selectors'], [])

    def test_unit_api_requires_sdk_environment_as_well_as_backend(self):
        code, result, _ = self.run_preflight('unit-api', {'tests', 'backend', 'postgres', 'mysql'})
        self.assertEqual(code, 2)
        self.assertEqual([row['name'] for row in result['preflight'] if row['status'] != 'PASS'], ['airflow'])
