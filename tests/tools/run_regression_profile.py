"""Run the real Compose test profile only on a fresh private regression project."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
for kind in ('tests','backend','postgres','mysql'):parser.add_argument('--'+kind+'-image',required=True)
parser.add_argument('--evidence-dir',required=True)
parser.add_argument('--path',action='append',help='Repository-relative tests/ directory or module path')
parser.add_argument('--ignore',action='append',help='Explicit selectors assigned to a different runner environment')
parser.add_argument('--current-test-sources',action='store_true',help='Refresh only tests in a private read-only volume; application packages stay installed')
parser.add_argument('--show-passed-output',action='store_true',help='Include reviewed test measurements printed by passing selectors')
args=parser.parse_args()
import re
if args.path and any(not re.fullmatch(r'tests(?:/[A-Za-z0-9_.-]+)+',value) for value in args.path):
    parser.error('Test paths must stay under tests/')
if args.ignore and any(not re.fullmatch(r'tests(?:/[A-Za-z0-9_.-]+)+',value) for value in args.ignore):
    parser.error('Ignored paths must stay under tests/')
evidence=(ROOT/args.evidence_dir).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
project='aat-regression-'+secrets.token_hex(4)
config_path=ROOT/'.tools'/('compose-'+project+'.json')
environment=dict(os.environ,PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'),COMPOSE_PARALLEL_LIMIT='2')
base=['podman','compose','-f',str(config_path),'-p',project,'--profile','test']
result={'project':project,'status':'NOT_RUN','published_ports':False,'existing_services_modified':False}
private=[];started=False
test_source_volume=None

def redact(value):
    for secret in private:value=value.replace(secret,'[REDACTED]')
    return value

def run(command,*,check=True,timeout=300):
    checked=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    if check and checked.returncode:raise RuntimeError('Regression profile command failed; inspect owned fixture evidence')
    return checked

try:
    config=json.loads(run(['podman','compose','-f',str(ROOT/'docker-compose.yml'),'--profile','test','config','--format','json']).stdout)
    names=('regression-secrets','regression-postgres','regression-mysql','backend-tests')
    config['services']={name:config['services'][name] for name in names}
    images={kind:run(['podman','image','inspect',getattr(args,kind+'_image'),'--format','{{.Id}}']).stdout.strip() for kind in ('tests','backend','postgres','mysql')}
    for name,service in config['services'].items():
        service.pop('build',None);service.pop('ports',None)
        service['image']=images['tests' if name=='backend-tests' else 'backend' if name=='regression-secrets' else 'postgres' if name=='regression-postgres' else 'mysql']
        service['restart']='no'
    volumes=('regression_credentials','regression_pg_data','regression_mysql_data')
    config['volumes']={name:{'name':project+'_'+name} for name in volumes}
    config['networks']={'regression_internal':{'name':project+'_internal','internal':True}}
    config['name']=project
    if args.current_test_sources:
        import hashlib
        test_source_volume=project+'_test_sources'
        loader=project+'-test-source-loader'
        run(['podman','volume','create','--label','com.docker.compose.project='+project,
             '--label','com.docker.compose.volume=test_sources','--label','com.docker.compose.version=5.6.0',test_source_volume])
        try:
            run(['podman','create','--name',loader,'--network','none','-v',test_source_volume+':/test-source',
                 '--entrypoint','/bin/true',images['tests']])
            run(['podman','cp',str(ROOT/'tests')+'/.',loader+':/test-source'])
        finally:run(['podman','rm','-f',loader],check=False)
        config['volumes']['test_sources']={'name':test_source_volume}
        config['services']['backend-tests']['volumes'].append({'type':'volume','source':'test_sources','target':'/opt/aat/tests','read_only':True})
        result.update(application_source_overlay=False,current_test_sources=True,
            test_source_sha256={p.relative_to(ROOT/'tests').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (ROOT/'tests').rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    result['images']=images;result['compose_config']=str(config_path.relative_to(ROOT))
    started=True
    ready=run([*base,'up','-d','--no-build','--wait','--wait-timeout','180','regression-postgres','regression-mysql'],check=False,timeout=240)
    (evidence/'startup.log').write_text(redact(ready.stdout+ready.stderr),encoding='utf-8')
    result['startup_exit_code']=ready.returncode
    if ready.returncode:raise RuntimeError('Disposable regression databases did not become ready')
    # Capture only this synthetic fixture secret for output redaction. Never
    # mount any production/demo secret domain or expose its value in evidence.
    query="from pathlib import Path; print(Path('/run/regression/password').read_text())"
    password=run(['podman','run','--rm','--network','none','--user','0:0','--entrypoint','python',
                  '-v',project+'_regression_credentials:/run/regression:ro',images['backend'],'-c',query]).stdout.strip()
    if len(password)<32:raise RuntimeError('Invalid synthetic regression credential')
    private.append(password)
    paths=args.path or ['tests/unit','tests/api']
    ignored=[value for path in args.ignore or [] for value in ('--ignore',path)]
    checked=run([*base,'run','--rm','--no-deps','backend-tests','pytest','-p','no:cacheprovider',*paths,*ignored,'-v','--tb=short',
                 *(['-rP'] if args.show_passed_output else [])],check=False,timeout=1800)
    (evidence/'pytest.log').write_text(redact(checked.stdout+checked.stderr),encoding='utf-8')
    result.update(exit_code=checked.returncode,status='PASS' if checked.returncode==0 else 'FAIL',test_paths=paths,selectors_assigned_elsewhere=args.ignore or [])
    print(redact((checked.stdout+checked.stderr)[-6500:]))
finally:
    if started:
        cleanup=run([*base,'down','--volumes'],check=False,timeout=180)
        result['cleanup_exit_code']=cleanup.returncode
        if cleanup.returncode:
            result.update(status='CLEANUP_FAILED',test_exit_code=result.get('exit_code'),exit_code=cleanup.returncode)
    if test_source_volume and not started:
        result['test_source_cleanup_exit_code']=run(['podman','volume','rm',test_source_volume],check=False).returncode
    (evidence/'regression-profile-results.json').write_text(json.dumps(result,indent=2)+'\n')
if result.get('exit_code',1):raise SystemExit(result.get('exit_code',1))
