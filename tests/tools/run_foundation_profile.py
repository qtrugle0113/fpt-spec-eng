"""Host-owned isolated Compose fixture; never up/migrate an existing project."""
from pathlib import Path
import json
import os
import secrets
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
project='aat-phase2-foundation-'+secrets.token_hex(4)
env=dict(os.environ,PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'))
base=['podman','compose','-f',str(ROOT/'docker-compose.foundation.yml'),'-p',project,'--profile','foundation']
def compose(*args):return subprocess.run([*base,*args],env=env,text=True,encoding='utf-8',capture_output=True)
result={}
try:
    started=compose('up','-d','foundation-tests')
    if started.returncode:raise RuntimeError('Isolated profile startup failed; '+started.stderr[-2000:])
    print('FOUNDATION_PROFILE_STARTED '+project,flush=True)
    name=project+'-foundation-tests-1'
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        data=json.loads(subprocess.check_output(['podman','inspect',name],text=True))[0]
        if data['State']['Status']=='exited':break
        time.sleep(2)
    else:raise RuntimeError('Isolated foundation profile deadline exceeded')
    log=subprocess.check_output(['podman','logs',name],text=True,encoding='utf-8',stderr=subprocess.STDOUT)
    (ROOT/'docs/testing/t014-round2-logs/phase2-compose-foundation.log').write_bytes(log.encode())
    code=data['State']['ExitCode']
    subprocess.run(['podman','cp',name+':/tmp/aat-foundation-http.json',str(ROOT/'docs/testing/phase2-profile-http-evidence.json')],capture_output=True)
    result={'project':project,'provider':'Docker Compose5.6.0','test_image_id':data['Image'],'exit_code':code,
            'log':'docs/testing/t014-round2-logs/phase2-compose-foundation.log','postgres_tmpfs':True,'existing_services_modified':False}
    print(log[-1200:])
finally:
    cleanup=compose('down','--volumes')
    result['cleanup_exit_code']=cleanup.returncode
    (ROOT/'docs/testing/phase2-profile-results.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
if code:sys.exit(code)
