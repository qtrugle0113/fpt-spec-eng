"""Execute SDK-dependent unit tests in the approved Airflow image, without a DB."""
import argparse
import json
from pathlib import Path
import re
import secrets
import subprocess

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',required=True)
parser.add_argument('--module',action='append',required=True)
parser.add_argument('--evidence-dir',required=True)
args=parser.parse_args()
if any(not re.fullmatch(r'tests\.unit\.[A-Za-z0-9_]+',name) for name in args.module):parser.error('Only explicit unit modules are allowed')
evidence=(ROOT/args.evidence_dir).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
name='aat-sdk-unit-'+secrets.token_hex(4)
def run(*command):return subprocess.run(['podman',*command],capture_output=True,text=True,encoding='utf-8',check=True)
result={'network':'none','existing_services_modified':False,'execution_mode':'SOURCE_FACTORY_ON_INSTALLED_AIRFLOW_SDK'}
try:
    result['image_id']=run('image','inspect',args.image,'--format','{{.Id}}').stdout.strip()
    run('create','--name',name,'--network','none','--memory','512m','--workdir','/tmp',
        '-e','PYTHONPATH=/tmp/backend/src:/tmp','-e','AAT_ASSETS_ROOT=/tmp','--entrypoint','python',args.image,
        '-m','unittest',*args.module,'-v')
    for folder in ('backend','tests','airflow','specs'):
        run('cp',str(ROOT/folder),name+':/tmp/'+folder)
    checked=subprocess.run(['podman','start','-a',name],capture_output=True,text=True,encoding='utf-8')
    (evidence/'sdk-unit.log').write_text(checked.stdout+checked.stderr,encoding='utf-8')
    result['exit_code']=int(run('inspect',name,'--format','{{.State.ExitCode}}').stdout)
    result['status']='PASS' if result['exit_code']==0 else 'FAIL'
    print((checked.stdout+checked.stderr)[-4000:])
finally:
    result['cleanup_exit_code']=subprocess.run(['podman','rm','-f',name],capture_output=True).returncode
    (evidence/'sdk-unit-results.json').write_text(json.dumps(result,indent=2)+'\n')
if result.get('exit_code',1):raise SystemExit(result.get('exit_code',1))
