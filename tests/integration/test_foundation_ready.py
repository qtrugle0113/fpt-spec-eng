"""Real DB/head/key/worker/Airflow probes; no mocked readiness responses."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import psycopg
import asyncio
import httpx


class FoundationReadinessTests(unittest.TestCase):
    def http(self,path):
        from aat_api.main import app
        async def request():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                return await client.get(path)
        return asyncio.run(request())
    def setUp(self):
        try:self.service=importlib.import_module('aat_api.services.health')
        except ModuleNotFoundError as exc:
            if exc.name!='aat_api.services.health':raise
            raise AssertionError('T034 foundation health missing') from None

    def worker(self):
        self.log=open(os.devnull,'wb');self.addCleanup(self.log.close)
        process=subprocess.Popen([sys.executable,'-m','aat_api.workers.main'],stdout=self.log,stderr=self.log)
        self.addCleanup(lambda: (process.kill(),process.wait(timeout=10)) if process.poll() is None else None)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            self.assertIsNone(process.poll(),'Real worker exited')
            with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
                if c.execute("SELECT count(*) FROM worker_heartbeats WHERE split_part(owner_process_id,'-',1)=%s AND heartbeat_at>now()-interval '10 seconds'",(str(process.pid),)).fetchone()[0]:return process
            time.sleep(.2)
        self.fail('Worker DB heartbeat missing')

    def test_readiness_uses_real_airflow_and_fails_when_its_endpoint_unavailable(self):
        self.worker();result=self.service.probe()
        self.assertTrue(result['ready'],result['dependencies'])
        healthy=self.http('/api/v1/health/ready');self.assertEqual(healthy.status_code,200)
        from aat_api.services.operations import Operations
        from uuid import uuid4
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            operation=Operations(c).enqueue('FOUNDATION_READ',str(uuid4()),'e'*64)
        observed=self.http('/api/v1/operations/'+str(operation['id']));self.assertEqual(observed.status_code,200)
        evidence=[{'method':'get','path':'/health/ready','status':healthy.status_code,'body':healthy.json()},
                  {'method':'get','path':'/operations/{id}','status':observed.status_code,'body':observed.json()}]
        previous=os.environ['AAT_AIRFLOW_HEALTH_URL']
        try:
            os.environ['AAT_AIRFLOW_HEALTH_URL']='http://127.0.0.1:1/unavailable'
            self.assertFalse(self.service.probe()['ready'])
            unhealthy=self.http('/api/v1/health/ready');self.assertEqual(unhealthy.status_code,503)
            evidence.append({'method':'get','path':'/health/ready','status':unhealthy.status_code,'body':unhealthy.json()})
            Path('/tmp/aat-foundation-http.json').write_text(json.dumps(evidence))
        finally:os.environ['AAT_AIRFLOW_HEALTH_URL']=previous

    def test_missing_original_key_and_stale_worker_fail_readiness(self):
        process=self.worker();process.kill();process.wait(timeout=10)
        with psycopg.connect(os.environ['AAT_FOUNDATION_TEST_DSN']) as c:
            c.execute("UPDATE worker_heartbeats SET heartbeat_at=now()-interval '1 minute'")
        self.assertFalse(self.service.probe()['ready'])
        root=Path(os.environ['AAT_APP_KEYRING']);key=root/(json.loads((root/'current.json').read_text())['key_id']+'.key')
        moved=key.with_suffix('.held');key.rename(moved)
        try:self.assertFalse(self.service.probe()['ready'])
        finally:moved.rename(key)
