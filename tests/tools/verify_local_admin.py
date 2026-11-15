"""Kiểm login/service auth/persistence/restart thật mà không xuất credential."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def execute(*args):
    result = subprocess.run(['podman', *map(str, args)], text=True, encoding='utf-8', capture_output=True, timeout=180)
    if result.returncode: raise RuntimeError('Local auth verification operation failed: ' + str(args[0]) + '; values suppressed')
    return result.stdout.strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--fresh', action='store_true')
    args=parser.parse_args()
    if not args.project.startswith('aat-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.project): raise ValueError('Invalid owned project')
    evidence=(ROOT/args.evidence).resolve()
    if not evidence.is_relative_to(ROOT): raise ValueError('Evidence must stay in workspace')
    evidence.parent.mkdir(parents=True,exist_ok=True)
    api=args.project+'-airflow-apiserver-1'; backend=args.project+'-backend-1'
    state=json.loads(execute('inspect',api))[0]
    if any(b['HostIp']!='127.0.0.1' for b in state['HostConfig']['PortBindings']['8080/tcp']): raise ValueError('Not loopback')
    mounts={m['Destination']:m['Name'] for m in state['Mounts'] if m['Type']=='volume'}
    digest_code="import hashlib;from pathlib import Path;print(hashlib.sha256(Path('/secrets/airflow/simple_auth_passwords.json').read_bytes()).hexdigest())"
    before_digest=execute('exec',api,'python','-c',digest_code)
    execute('cp',ROOT/'scripts/configure-local-airflow-admin.py',backend+':/tmp/aat_admin_snapshot.py')
    snapshot_code="import importlib.util,json;s=importlib.util.spec_from_file_location('snapshot','/tmp/aat_admin_snapshot.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(json.dumps(m.snapshot('http://127.0.0.1:8000')))"
    before=json.loads(execute('exec',backend,'python','-c',snapshot_code))
    probe="""
import base64,json,httpx
from pathlib import Path
origin='http://airflow-apiserver:8080'
def login(user,password):
    response=httpx.post(origin+'/auth/token',json={'username':user,'password':password},timeout=15)
    response.raise_for_status();return response.json()['access_token']
token=login('admin','admin')
claims=json.loads(base64.urlsafe_b64decode(token.split('.')[1]+'==='))
assert claims['sub']=='admin' and claims['role']=='admin'
response=httpx.get(origin+'/api/v2/variables?limit=1',headers={'Authorization':'Bearer '+token},timeout=15);response.raise_for_status()
service=login('aat_service',Path('/secrets/backend/airflow_service_password').read_text().strip())
response=httpx.get(origin+'/api/v2/dags',headers={'Authorization':'Bearer '+service},timeout=15);response.raise_for_status()
assert httpx.get(origin+'/api/v2/variables?limit=1',timeout=15).status_code in (401,403)
assert httpx.post(origin+'/auth/token',json={'username':'admin','password':'invalid-test-password'},timeout=15).status_code==401
print(json.dumps({'admin_login':True,'role':'admin','service_auth':True,'auth_enabled':True}))
"""
    proof=json.loads(execute('exec',backend,'python','-c',probe))
    if args.fresh:
        if not args.project.startswith('aat-definition_admin-e2e-'): raise ValueError('Fresh-only operations require this feature fixture')
        helper=args.project+'-backup-roundtrip'
        image=json.loads(execute('inspect',backend))[0]['Image']
        code="import importlib.util,json;from pathlib import Path;s=importlib.util.spec_from_file_location('local','/tmp/admin.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);p=Path('/secrets/airflow/simple_auth_passwords.json');before=p.read_bytes();r=m.configure(p,local_demo=True,reset=True);m.restore(p,r['backup'],local_demo=True);assert p.read_bytes()==before;print(json.dumps({'backup_restore_roundtrip':True,'other_accounts_unchanged':r['other_accounts_unchanged']}))"
        execute('create','--name',helper,'--network=none','--user=0:0','-v',mounts['/secrets/airflow']+':/secrets/airflow','--entrypoint=python',image,'-c',code)
        try:
            execute('cp',ROOT/'docker/bootstrap/local_airflow_admin.py',helper+':/tmp/admin.py')
            proof.update(json.loads(execute('start','-a',helper)))
        finally: execute('rm',helper)
        execute('start','-a',args.project+'-secrets-init-1')
        proof['real_bootstrap_idempotent']=execute('exec',api,'python','-c',digest_code)==before_digest
        if not proof['real_bootstrap_idempotent']: raise RuntimeError('Bootstrap changed persistent passwords')
    execute('restart',api)
    for attempt in range(60):
        try:
            json.loads(execute('exec',backend,'python','-c',probe)); break
        except RuntimeError:
            if attempt==59: raise
            time.sleep(2)
    after=json.loads(execute('exec',backend,'python','-c',snapshot_code))
    current=json.loads(execute('inspect',api))[0]
    proof.update(project=args.project,status='PASS',restart_login=True,data_ids_unchanged=before==after,
                 volumes_unchanged=mounts=={m['Destination']:m['Name'] for m in current['Mounts'] if m['Type']=='volume'},
                 password_store_unchanged=execute('exec',api,'python','-c',digest_code)==before_digest,
                 image_unchanged=state['Image']==current['Image'],before=before,after=after)
    if not all(proof[k] for k in ('data_ids_unchanged','volumes_unchanged','password_store_unchanged','image_unchanged')): raise RuntimeError('Preservation check failed')
    evidence.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps({key: value for key,value in proof.items() if key not in ('before','after')}))


if __name__=='__main__': main()
