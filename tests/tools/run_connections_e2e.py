"""Own an isolated production Compose stack and run real Connections browser tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
for name in ('backend','frontend','e2e','airflow','postgres','mysql'):
    parser.add_argument('--'+name+'-image',required=True)
parser.add_argument('--evidence-dir',required=True)
parser.add_argument('--suite',choices=['connections','tables','files'],default='connections')
parser.add_argument('--prepare-only',action='store_true',help='Validate the isolated Compose configuration without starting services')
args=parser.parse_args()
evidence=(ROOT/args.evidence_dir).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
project='aat-'+args.suite+'-e2e-'+secrets.token_hex(4)
runner=project+'-browser'
env=dict(os.environ,PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'),COMPOSE_PARALLEL_LIMIT='2')
config_path=ROOT/'.tools'/('compose-'+project+'.json')
base=['podman','compose','-f',str(config_path),'-p',project,'--profile','test']
private_values=[]
result={'project':project,'status':'NOT_RUN','published_ports':False,'existing_services_modified':False}
resources_started=False


def redact(value:str) -> str:
    for secret in private_values:
        if secret:value=value.replace(secret,'[REDACTED]')
    return value


def execute(command,*,check=True,input=None,timeout=300):
    try:
        process=subprocess.run(command,cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True,input=input,timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Isolated E2E command exceeded its deadline') from None
    if check and process.returncode:
        raise RuntimeError('Isolated E2E command failed; inspect fixture evidence')
    return process


try:
    resolved=execute(['podman','compose','-f',str(ROOT/'docker-compose.yml'),'--profile','test','config','--format','json'])
    config=json.loads(resolved.stdout)
    config['name']=project
    config['services'].pop('backend-tests',None)
    images={}
    for name in ('backend','frontend','e2e','airflow','postgres','mysql'):
        identity=execute(['podman','image','inspect',getattr(args,name+'_image'),'--format','{{.Id}}']).stdout.strip()
        images[name]=identity
    result['images']=images
    for name,service in config['services'].items():
        service.pop('build',None)
        service.pop('ports',None)
        service['restart']='no'
        kind=('airflow' if name.startswith('airflow-') else 'backend' if name in
              ('backend','backend-worker','secrets-init','db-init','app-init','backend-tests') else
              'e2e' if name=='e2e-tests' else name)
        service['image']=images[kind]
    config['services']['backend'].setdefault('environment',{})['AAT_ALLOWED_ORIGINS']='http://frontend'
    config['services']['e2e-tests']['mem_limit']='1g'
    for network in config['networks'].values():network['internal']=True
    # Resolved Compose names must belong only to this fresh project.
    for name,volume in config.get('volumes',{}).items():
        if volume.get('external'):raise RuntimeError('External fixture volume is forbidden')
        volume['name']=project+'_'+name
    for name,network in config.get('networks',{}).items():
        if network.get('external'):raise RuntimeError('External fixture network is forbidden')
        network['name']=project+'_'+name
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    execute([*base,'config','--quiet'])
    if args.prepare_only:
        result['status']='PREPARED_NOT_RUN'
        print(args.suite.upper()+'_E2E_CONFIG_PASS '+project)
        raise SystemExit(0)
    resources_started=True
    started=execute([*base,'up','-d','--no-build','--wait','--wait-timeout','300','frontend','airflow-scheduler','airflow-dag-processor'],check=False,timeout=360)
    if started.returncode:
        result['status']='STARTUP_FAILED'
        states=execute([*base,'ps','-a','--format','json'],check=False).stdout.strip()
        try:result['services']=json.loads(states or '[]')
        except json.JSONDecodeError:result['services']=[json.loads(line) for line in states.splitlines() if line.strip()]
        (evidence/(args.suite+'-startup.log')).write_text(redact(started.stdout+started.stderr),encoding='utf-8')
        # Read only this disposable project's secret volumes to redact diagnostics.
        # Values stay in process memory and are never copied to published evidence.
        secret_volumes=[volume['name'] for name,volume in config.get('volumes',{}).items()
                        if 'secret' in name or 'keyring' in name]
        mounts=[]
        for index,volume in enumerate(secret_volumes):mounts+=['-v',volume+':/run/diag/'+str(index)+':ro']
        read_values="import pathlib,json; values=[]; [(values.append(p.read_text())) for p in pathlib.Path('/run/diag').rglob('*') if p.is_file()]; print(json.dumps(values))"
        private=execute(['podman','run','--rm','--network=none','--user','0:0',*mounts,'--entrypoint','python',images['backend'],'-c',read_values],check=False)
        if private.returncode==0:
            def strings(value):
                if isinstance(value,str):
                    yield value
                    try:decoded=json.loads(value)
                    except (ValueError,TypeError):return
                    if not isinstance(decoded,str):yield from strings(decoded)
                elif isinstance(value,dict):
                    for part in value.values():yield from strings(part)
                elif isinstance(value,list):
                    for part in value:yield from strings(part)
            private_values.extend(strings(json.loads(private.stdout)))
            service_logs=execute([*base,'logs','--no-color'],check=False)
            (evidence/(args.suite+'-startup-services.log')).write_text(redact(service_logs.stdout+service_logs.stderr),encoding='utf-8')
        raise RuntimeError('Isolated Connections stack did not become ready; no data reset performed')
    execute([*base,'run','-d','--no-deps','--name',runner,'e2e-tests','sleep','infinity'])
    if args.suite=='connections':
        backend=execute([*base,'ps','-q','backend']).stdout.strip()
        extracted=execute(['podman','exec',backend,'python','-c',
            "import json,pathlib; print(json.dumps({name:(pathlib.Path('/secrets/backend')/name).read_text() for name in ('pg_etl','mysql_etl')}))"])
        credentials=json.loads(extracted.stdout);private_values.extend(credentials.values())
        install="const fs=require('node:fs'); fs.mkdirSync('/run/aat-e2e',{mode:0o700}); for(const [k,v] of Object.entries(JSON.parse(fs.readFileSync(0,'utf8')))) fs.writeFileSync('/run/aat-e2e/'+k,v,{mode:0o400});"
        execute(['podman','exec','-i',runner,'node','-e',install],input=json.dumps(credentials))
    # Test-only edits do not rebuild or mutate the approved application images.
    result['test_source_sha256']={}
    sources=[args.suite+'.spec.ts','bootstrap.spec.ts','playwright.config.ts']
    if args.suite=='files':sources.append('files-persistence.spec.ts')
    for filename in sources:
        source=ROOT/'tests/e2e'/filename
        execute(['podman','cp',str(source),runner+':/tests/'+filename])
        result['test_source_sha256'][filename]=hashlib.sha256(source.read_bytes()).hexdigest()
    if args.suite=='tables':
        fixtures=ROOT/'.tools/table-e2e-fixtures'
        if not all((fixtures/name).is_file() for name in ('postgres.xlsx','mysql.xlsx','invalid.xlsx','boundary.xlsx')):
            raise RuntimeError('Prepare public table workbook fixtures before running E2E')
        execute(['podman','cp',str(fixtures),runner+':/tests/table-fixtures'])
    tested=execute(['podman','exec',runner,'node','node_modules/@playwright/test/cli.js','test',args.suite+'.spec.ts','bootstrap.spec.ts','--timeout=120000','--reporter=line'],check=False,timeout=300)
    (evidence/(args.suite+'-e2e.log')).write_text(redact(tested.stdout+tested.stderr),encoding='utf-8')
    result['exit_code']=tested.returncode
    result['status']='PASS' if tested.returncode==0 else 'FAIL'
    if args.suite=='files':
        result['main_exit_code']=tested.returncode;result['persistence_status']='NOT_RUN'
        if tested.returncode==0:
            # Recreate rather than merely restart: uploaded bytes must survive
            # loss of each backend container's writable layer. Refresh nginx's
            # startup DNS resolution after backend addresses are recreated.
            recreated=execute([*base,'up','-d','--no-build','--no-deps','--force-recreate','--wait','--wait-timeout','180','backend-worker','backend'],check=False,timeout=240)
            (evidence/'files-recreation.log').write_text(redact(recreated.stdout+recreated.stderr),encoding='utf-8')
            result['recreation_exit_code']=recreated.returncode
            if recreated.returncode==0:
                refreshed=execute([*base,'up','-d','--no-build','--no-deps','--force-recreate','--wait','--wait-timeout','120','frontend'],check=False,timeout=180)
                result['proxy_refresh_exit_code']=refreshed.returncode
                if refreshed.returncode==0:
                    persistent=execute(['podman','exec',runner,'node','node_modules/@playwright/test/cli.js','test','files-persistence.spec.ts','--timeout=120000','--reporter=line'],check=False,timeout=300)
                    (evidence/'files-persistence.log').write_text(redact(persistent.stdout+persistent.stderr),encoding='utf-8')
                    result['persistence_exit_code']=persistent.returncode
                    result['persistence_status']='PASS' if persistent.returncode==0 else 'FAIL'
                    result['exit_code']=persistent.returncode
                    print(redact((persistent.stdout+persistent.stderr)[-2500:]))
                else:result['exit_code']=refreshed.returncode
            else:result['exit_code']=recreated.returncode
            result['status']='PASS' if result['exit_code']==0 else 'FAIL'
    artifacts=ROOT/'.tools'/(args.suite+'-e2e-artifacts');artifacts.mkdir(parents=True,exist_ok=True)
    execute(['podman','cp',runner+':/tmp/aat-e2e-artifacts/.',str(artifacts)],check=False)
    print(redact((tested.stdout+tested.stderr)[-5000:]))
finally:
    if resources_started:execute(['podman','rm','-f',runner],check=False)
    if resources_started and config_path.exists():
        cleaned=execute([*base,'down','--volumes'],check=False)
        result['cleanup_exit_code']=cleaned.returncode
    (evidence/(args.suite+'-e2e-results.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if result.get('exit_code',1):raise SystemExit(result.get('exit_code',1))
