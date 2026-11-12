"""T149: actual loopback HTTP timings against real PostgreSQL and uploaded bytes."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import unittest
import httpx
from tests.api import test_connections as connection_fixtures
from tests.api.test_files import PARSER


class ResponseLimitTests(unittest.TestCase):
    setUp=connection_fixtures.ConnectionAPITests.setUp
    payload=connection_fixtures.ConnectionAPITests.payload
    request=connection_fixtures.ConnectionAPITests.request
    create=connection_fixtures.ConnectionAPITests.create

    def test_list_detail_preview_and_connection_probe_meet_published_budgets(self):
        identities=[self.create(code=self.prefix+'_'+str(index)).json()['id'] for index in range(20)]
        data=('id,name\n'+''.join(str(i)+',sample_'+('x'*80)+'\n' for i in range(1000))).encode()
        uploaded=self.client.post('/api/v1/files',data={'parser_json':json.dumps(PARSER)},
            files={'file':('performance.csv',data,'text/csv')})
        self.assertEqual(uploaded.status_code,201)
        file=uploaded.json()
        server=subprocess.Popen([sys.executable,'-m','uvicorn','aat_api.main:app','--host','127.0.0.1','--port','8999','--no-access-log'],
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def close():
            if server.poll() is None:server.terminate();server.wait(timeout=10)
        self.addCleanup(close)
        client=httpx.Client(base_url='http://127.0.0.1:8999',trust_env=False,timeout=35)
        self.addCleanup(client.close)
        deadline=time.monotonic()+20
        while True:
            try:
                if client.get('/api/v1/health/live').status_code==200:break
            except httpx.HTTPError:pass
            if server.poll() is not None or time.monotonic()>deadline:self.fail('Private HTTP fixture did not become available')
            time.sleep(.1)
        observations={}
        paths={'list':'/api/v1/connections?limit=20&search='+self.prefix,
               'detail':'/api/v1/connections/'+identities[0],
               'preview100':'/api/v1/files/'+file['id']+'/preview'}
        for label,path in paths.items():
            samples=[]
            for _ in range(20):
                began=time.perf_counter();response=client.get(path);samples.append(time.perf_counter()-began)
                self.assertEqual(response.status_code,200)
                if label=='list':self.assertEqual(len(response.json()['items']),20)
                if label=='preview100':self.assertEqual(len(response.json()['rows']),100)
            p95=sorted(samples)[math.ceil(.95*len(samples))-1]
            self.assertLessEqual(p95,3,label+' p95 exceeded the published three-second budget')
            observations[label]={'samples_ms':[round(value*1000,3) for value in samples],
                                 'p95_ms':round(p95*1000,3),'max_ms':round(max(samples)*1000,3)}
        began=time.perf_counter();probe=client.post('/api/v1/connections/'+identities[0]+'/test')
        elapsed=time.perf_counter()-began
        self.assertEqual(probe.status_code,200)
        self.assertEqual(probe.json()['status'],'SUCCESS')
        self.assertLessEqual(elapsed,30)
        memory=[line for line in Path('/proc/'+str(server.pid)+'/status').read_text().splitlines() if line.startswith('VmRSS:')]
        print('RESPONSE_LIMITS_VERIFIED '+json.dumps({'transport':'real loopback HTTP','connection_records':20,
            'source_rows':1000,'preview_rows':100,'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),
            'observations':observations,'connection_probe_ms':round(elapsed*1000,3),'server_rss':memory}),flush=True)
