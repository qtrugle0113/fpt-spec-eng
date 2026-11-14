"""Digest/platform và dependency tương thích của image thật; không thay security scan."""

import json
import os
from pathlib import Path
import subprocess
import unittest

from tests.tools.record_image_baseline import validate_lock

ROOT = Path(__file__).resolve().parents[2]
PODMAN = os.environ.get('PODMAN_BIN', 'podman')


class ImageCompatibilityTests(unittest.TestCase):
    def test_source_pins_match_image_lock(self):
        validate_lock(json.loads((ROOT / 'docker/images.lock').read_text(encoding='utf-8')), ROOT)

    def run_image(self, *args, code=None):
        result = subprocess.run([PODMAN, *args], input=code, text=True, encoding='utf-8',capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_pulled_base_digests_match_lock_and_platform(self):
        lock = json.loads((ROOT / 'docker/images.lock').read_text(encoding='utf-8'))
        validate_lock(lock, ROOT)
        for entry in lock['images']:
            data = json.loads(self.run_image('image','inspect',entry['repo_digest']))[0]
            self.assertEqual((data['Os'],data['Architecture']),('linux','amd64'))
            self.assertIn(entry['repo_digest'], data['RepoDigests'])
            self.assertEqual(data['Id'].removeprefix('sha256:'), entry['image_id'].removeprefix('sha256:'))

    def test_backend_and_airflow_dependencies_and_sdk(self):
        for image in ('localhost/aat-backend:0.1.0','localhost/aat-airflow:0.1.0'):
            self.run_image('run','--rm','--entrypoint','python',image,'-m','pip','check')
        self.run_image('run','--rm','--entrypoint','python','localhost/aat-airflow:0.1.0','-c',
                       "import airflow,airflow.sdk,aat_metadata,aat_etl; assert airflow.__version__=='3.3.2'")

    def test_airflow_approved_overrides_and_upstream_provenance(self):
        code = """
import hashlib, importlib.metadata, json, runpy
from pathlib import Path
root=Path('/opt/aat')
policy=json.loads((root/'constraints-policy.json').read_text())
upstream=(root/'constraints-3.12.txt').read_bytes()
assert hashlib.sha256(upstream).hexdigest()=='821effd0f491975682f2774fca3427d7bc2f59ca6de68dcb413ad2c8f890e58c'
derive=runpy.run_path(str(root/'build_constraints.py'))['derive_constraints']
effective=(root/'constraints-effective-3.12.txt').read_bytes()
assert effective==derive(upstream,policy)
provenance=json.loads((root/'constraints-provenance.json').read_text())
assert provenance['effective_sha256']==hashlib.sha256(effective).hexdigest()
for package,version in [('certifi','2026.10.18'),('urllib3','2.8.0'),('dnspython','2.9.2'),('pip','26.3'),('apache-airflow','3.3.2')]:
 assert importlib.metadata.version(package)==version,(package,importlib.metadata.version(package))
print(json.dumps(provenance))
"""
        self.run_image('run','--rm','--entrypoint','python','localhost/aat-airflow:0.1.0','-c',code)

    def test_playwright_client_and_real_browser(self):
        code = """const {chromium}=require('playwright');
(async()=>{if(require('@playwright/test/package.json').version!=='1.65.0')throw Error('Client mismatch');
const browser=await chromium.launch({headless:true});
if(browser.version()!=='158.0.8127.18')throw Error('Browser mismatch');await browser.close();})().catch(()=>process.exit(1));
"""
        self.run_image('run','--rm','-i','localhost/aat-e2e:0.1.0','node','-',code=code)
