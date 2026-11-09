"""Host-owned isolated Compose fixture; never up/migrate an existing project."""
from pathlib import Path
import json
import os
import secrets
import subprocess
import sys
import time
import argparse

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence-dir')
args=parser.parse_args()
evidence=(ROOT/args.evidence_dir).resolve() if args.evidence_dir else ROOT/'docs/testing'
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
log_path=evidence/'compose-foundation.log' if args.evidence_dir else ROOT/'docs/testing/t014-round2-logs/phase2-compose-foundation.log'
project='aat-phase2-foundation-'+secrets.token_hex(4)
env=dict(os.environ,PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'))
base=['podman','compose','-f',str(ROOT/'docker-compose.foundation.yml'),'-p',project,'--profile','foundation']
def compose(*args):return subprocess.run([*base,*args],env=env,text=True,encoding='utf-8',capture_output=True)
result={}
code=1
try:
    started=compose('up','-d','--wait','foundation-postgres')
    if started.returncode:raise RuntimeError('Isolated profile startup failed; '+started.stderr[-2000:])
    prepared=compose('create','foundation-tests')
    if prepared.returncode:raise RuntimeError('Isolated profile test container creation failed')
    name=project+'-foundation-tests-1'
    # Keep the approved installed application wheel; copy only current test code.
    copied=subprocess.run(['podman','cp',(ROOT/'tests').as_posix()+'/.',name+':/opt/aat/tests'],capture_output=True)
    if copied.returncode:raise RuntimeError('Current profile test copy failed')
    started=subprocess.run(['podman','start',name],capture_output=True,text=True,encoding='utf-8')
    if started.returncode:raise RuntimeError('Isolated profile test startup failed')
    print('FOUNDATION_PROFILE_STARTED '+project,flush=True)
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        data=json.loads(subprocess.check_output(['podman','inspect',name],text=True))[0]
        if data['State']['Status']=='exited':break
        time.sleep(2)
    else:raise RuntimeError('Isolated foundation profile deadline exceeded')
    log=subprocess.check_output(['podman','logs',name],text=True,encoding='utf-8',stderr=subprocess.STDOUT)
    log_path.write_bytes(log.encode())
    code=data['State']['ExitCode']
    subprocess.run(['podman','cp',name+':/tmp/aat-foundation-http.json',str(evidence/'phase2-profile-http-evidence.json')],capture_output=True)
    result={'project':project,'provider':'Docker Compose5.6.0','test_image_id':data['Image'],'exit_code':code,
            'application_code':'installed wheel','tests':'current source copy',
            'log':str(log_path.relative_to(ROOT)),'postgres_tmpfs':True,'existing_services_modified':False}
    print(log[-1200:])
finally:
    cleanup=compose('down','--volumes')
    result['cleanup_exit_code']=cleanup.returncode
    (evidence/'phase2-profile-results.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
if code:sys.exit(code)
