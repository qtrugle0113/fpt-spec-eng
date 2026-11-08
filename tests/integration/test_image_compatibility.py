"""Digest/platform và dependency tương thích của image thật; không thay security scan."""

import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
PODMAN = os.environ.get('PODMAN_BIN', 'podman')


class ImageCompatibilityTests(unittest.TestCase):
    def run_image(self, *args, code=None):
        result = subprocess.run([PODMAN, *args], input=code, text=True, encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_pulled_base_digests_match_lock_and_platform(self):
        lock = json.loads((ROOT / 'docker/images.lock').read_text(encoding='utf-8'))
        self.assertEqual(len(lock['images']), 8)  # Go is an additional build-only base
        for entry in lock['images']:
            data = json.loads(self.run_image('image','inspect',entry['ref']))[0]
            self.assertEqual((data['Os'],data['Architecture']),('linux','amd64'))
            self.assertIn(entry['repo_digest'], data['RepoDigests'])

    def test_backend_and_airflow_dependencies_and_sdk(self):
        for image in ('localhost/aat-backend:0.1.0','localhost/aat-airflow:0.1.0'):
            self.run_image('run','--rm','--entrypoint','python',image,'-m','pip','check')
        self.run_image('run','--rm','--entrypoint','python','localhost/aat-airflow:0.1.0','-c',
                       "import airflow,airflow.sdk,aat_metadata,aat_etl; assert airflow.__version__=='3.3.2'")

    def test_playwright_client_and_real_browser(self):
        code = """const {chromium}=require('playwright');
(async()=>{if(require('@playwright/test/package.json').version!=='1.56.1')throw Error('Client mismatch');
const browser=await chromium.launch({headless:true});
if(browser.version()!=='141.0.7390.37')throw Error('Browser mismatch');await browser.close();})().catch(()=>process.exit(1));
"""
        self.run_image('run','--rm','-i','localhost/aat-e2e:0.1.0','node','-',code=code)
