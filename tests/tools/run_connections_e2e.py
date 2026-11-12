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
parser.add_argument('--suite',choices=['connections','tables','files','dag_builder','monitoring','phase7','full_workflow','language'],default='connections')
parser.add_argument('--source-overlay',action='store_true',help='Run current source read-only on existing dependency images; not packaged-image acceptance')
parser.add_argument('--frontend-artifact',help='Workspace-relative dist from the pinned offline frontend build')
parser.add_argument('--keep-running',action='store_true',help='Keep this new local demo and its volumes after tests; publish loopback 13000/18000/18080')
parser.add_argument('--prepare-only',action='store_true',help='Validate the isolated Compose configuration without starting services')
parser.add_argument('--missing-source-check',action='store_true',help='Check unavailable-source API guards after the full workflow in this owned installed-image fixture')
parser.add_argument('--extra-spec',action='append',default=[],help='Additional current test source in this owned suite fixture')
args=parser.parse_args()
import re
if any(not re.fullmatch(r'[A-Za-z0-9_]+\.spec\.ts',name) or not (ROOT/'tests/e2e'/name).is_file() for name in args.extra_spec):
    parser.error('Extra specs must be existing tests/e2e/*.spec.ts files')
evidence=(ROOT/args.evidence_dir).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
project='aat-'+args.suite+'-e2e-'+secrets.token_hex(4)
runner=project+'-browser'
env=dict(os.environ,PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'),COMPOSE_PARALLEL_LIMIT='2')
config_path=ROOT/'.tools'/('compose-'+project+'.json')
base=['podman','compose','-f',str(config_path),'-p',project,'--profile','test']
private_values=[]
result={'project':project,'status':'NOT_RUN','published_ports':False,'existing_services_modified':False,
        'execution_mode':'INSTALLED_IMAGE_PACKAGES','packaged_image_acceptance':True}
resources_started=False
source_volume=None
source_loader=None


def redact(value:str) -> str:
    for secret in private_values:
        if secret:value=value.replace(secret,'[REDACTED]')
    return value


def execute(command,*,check=True,input=None,timeout=300):
    try:
        process=subprocess.run(command,cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True,input=input,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        def decoded(value):return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''
        result['status']='TIMEOUT'
        (evidence/'last-command-timeout.log').write_text(redact(decoded(error.stdout)+decoded(error.stderr)),encoding='utf-8')
        raise RuntimeError('Isolated E2E command exceeded its deadline') from None
    if check and process.returncode:
        raise RuntimeError('Isolated E2E command failed; inspect fixture evidence')
    return process


try:
    resolved=execute(['podman','compose','-f',str(ROOT/'docker-compose.yml'),'--profile','test','config','--format','json'])
    config=json.loads(resolved.stdout)
    config['name']=project
    config['services'].pop('backend-tests',None)
    for name in list(config['services']):
        if name.startswith('regression-'):config['services'].pop(name)
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
    if args.source_overlay:
        # Copy before starting any service, so scheduler imports cannot retain
        # old installed modules. No change to dependency images or user volumes.
        source_volume=project+'_current_source';source_loader=project+'-source-loader'
        execute(['podman','volume','create',source_volume])
        execute(['podman','create','--name',source_loader,'--network','none','--user','0:0',
                 '-v',source_volume+':/current','--entrypoint','python',images['backend'],'-c',
                 "from pathlib import Path; [p.chmod(0o755 if p.is_dir() else 0o644) for p in Path('/current').rglob('*')]"])
        for folder in ('backend','packages','etl_engine','docker','airflow','samples','templates','specs'):
            execute(['podman','cp',str(ROOT/folder),source_loader+':/current/'+folder])
        if args.frontend_artifact:
            artifact=(ROOT/args.frontend_artifact).resolve()
            if not artifact.is_relative_to(ROOT) or not (artifact/'index.html').is_file():raise RuntimeError('A built workspace frontend artifact is required')
            execute(['podman','cp',str(artifact),source_loader+':/current/frontend-dist'])
        execute(['podman','start','-a',source_loader])
        print('SOURCE_OVERLAY_SNAPSHOT_READY '+project,flush=True)
        config['volumes']['current_source']={'name':source_volume}
        for name,service in config['services'].items():
            if name.startswith('airflow-') or name in ('backend','backend-worker','secrets-init','db-init','app-init'):
                service.setdefault('volumes',[]).append({'type':'volume','source':'current_source','target':'/current','read_only':True,'volume':{'nocopy':True}})
                service.setdefault('environment',{}).update(PYTHONPATH='/current/backend/src:/current/packages:/current/etl_engine/src:/current',AAT_ASSETS_ROOT='/current')
                if name in ('secrets-init','db-init','app-init'):service['working_dir']='/current'
            if name=='frontend' and args.frontend_artifact:
                service.setdefault('volumes',[]).append({'type':'volume','source':'current_source','target':'/usr/share/nginx/html','read_only':True,'volume':{'nocopy':True,'subpath':'frontend-dist'}})
        result['execution_mode']='CURRENT_SOURCE_ON_EXISTING_DEPENDENCY_IMAGES'
        result['packaged_image_acceptance']=False
    if args.suite=='full_workflow':
        config['services']['backend']['environment']['AAT_AIRFLOW_PUBLIC_URL']='http://airflow-apiserver:8080'
        config['services']['airflow-apiserver']['environment']['AIRFLOW__API__BASE_URL']='http://airflow-apiserver:8080'
    if args.keep_running:
        for service,host,container in [('frontend',13000,80),('backend',18000,8000),('airflow-apiserver',18080,8080)]:
            config['services'][service]['ports']=[{'host_ip':'127.0.0.1','published':str(host),'target':container,'protocol':'tcp'}]
        config['services']['backend']['environment']['AAT_ALLOWED_ORIGINS']='http://frontend,http://localhost:13000,http://127.0.0.1:13000'
        config['services']['backend']['environment']['AAT_AIRFLOW_PUBLIC_URL']='http://localhost:18080'
        config['services']['airflow-apiserver']['environment']['AIRFLOW__API__BASE_URL']='http://localhost:18080'
        result.update(published_ports=True,local_url='http://localhost:13000',compose_config=str(config_path.relative_to(ROOT)))
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    execute([*base,'config','--quiet'])
    if args.prepare_only:
        result['status']='PREPARED_NOT_RUN'
        print(args.suite.upper()+'_E2E_CONFIG_PASS '+project)
        raise SystemExit(0)
    table_fixtures=None
    if args.suite=='tables':
        helper=project+'-table-workbooks'
        try:
            execute(['podman','create','--name',helper,'--network','none','--entrypoint','python',images['backend'],'/tmp/make_table_fixtures.py'])
            execute(['podman','cp',str(ROOT/'samples/definitions'),helper+':/tmp/aat-table-fixture-source'])
            execute(['podman','cp',str(ROOT/'tests/tools/make_table_fixtures.py'),helper+':/tmp/make_table_fixtures.py'])
            execute(['podman','start','-a',helper])
            table_fixtures=ROOT/'.tools'/(project+'-table-fixtures');table_fixtures.mkdir(exist_ok=True)
            execute(['podman','cp',helper+':/tmp/aat-table-fixtures/.',str(table_fixtures)])
            result['table_fixture_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in table_fixtures.glob('*.xlsx')}
        finally:execute(['podman','rm','-f',helper],check=False)
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
    if args.suite in ('connections','full_workflow'):
        backend=execute([*base,'ps','-q','backend']).stdout.strip()
        extracted=execute(['podman','exec',backend,'python','-c',
            "import json,pathlib; print(json.dumps({name:(pathlib.Path('/secrets/backend')/name).read_text() for name in ('pg_etl','mysql_etl')}))"])
        credentials=json.loads(extracted.stdout);private_values.extend(credentials.values())
        install="const fs=require('node:fs'); fs.mkdirSync('/run/aat-e2e',{mode:0o700}); for(const [k,v] of Object.entries(JSON.parse(fs.readFileSync(0,'utf8')))) fs.writeFileSync('/run/aat-e2e/'+k,v,{mode:0o400});"
        execute(['podman','exec','-i',runner,'node','-e',install],input=json.dumps(credentials))
    if args.suite=='full_workflow':
        helper=project+'-workbook-libraries'
        libraries=ROOT/'.tools'/(project+'-workbook-libraries');libraries.mkdir(exist_ok=True)
        try:
            query="import sysconfig,json,importlib.metadata as m;print(json.dumps({'root':sysconfig.get_paths()['purelib'],'versions':{n:m.version(n) for n in ('openpyxl','et_xmlfile','defusedxml')}}))"
            execute(['podman','create','--name',helper,'--network','none','--entrypoint','python',images['backend'],'-c',query])
            dependencies=json.loads(execute(['podman','start','-a',helper]).stdout)
            if dependencies['versions']!={'openpyxl':'3.1.5','et_xmlfile':'2.0.0','defusedxml':'0.7.1'}:raise RuntimeError('Workbook fixture dependency drift')
            for package in dependencies['versions']:
                execute(['podman','cp',helper+':'+dependencies['root']+'/'+package,str(libraries/package)])
            execute(['podman','cp',str(libraries),runner+':/tests/workbook-libs'])
            result['workbook_fixture_libraries']={'source_image_id':images['backend'],**dependencies,
                'sha256':{str(p.relative_to(libraries)):hashlib.sha256(p.read_bytes()).hexdigest() for p in libraries.rglob('*') if p.is_file()}}
        finally:execute(['podman','rm','-f',helper],check=False)
        execute(['podman','cp',str(ROOT/'tests/tools/make_full_workflow.py'),runner+':/tests/make_full_workflow.py'])
        execute(['podman','cp',str(ROOT/'samples/data/customers.csv'),runner+':/tests/full-customers.csv'])
    # Test-only edits do not rebuild or mutate the approved application images.
    result['test_source_sha256']={}
    suite_sources=['dashboard.spec.ts','settings.spec.ts','accessibility.spec.ts'] if args.suite=='phase7' else [args.suite+'.spec.ts']
    suite_sources=list(dict.fromkeys([*suite_sources,*args.extra_spec]))
    sources=[*suite_sources,'bootstrap.spec.ts','playwright.config.ts']
    if args.suite=='phase7':sources.append('settings-persistence.spec.ts')
    if args.suite=='phase7':sources.append('dashboard-unavailable.spec.ts')
    if args.suite=='files':sources.append('files-persistence.spec.ts')
    for filename in sources:
        source=ROOT/'tests/e2e'/filename
        execute(['podman','cp',str(source),runner+':/tests/'+filename])
        result['test_source_sha256'][filename]=hashlib.sha256(source.read_bytes()).hexdigest()
    if args.suite=='tables':
        execute(['podman','cp',str(table_fixtures),runner+':/tests/table-fixtures'])
    if args.suite in ('dag_builder','monitoring'):
        helper=project+'-workbooks'
        try:
            execute(['podman','create','--name',helper,'--network','none','--entrypoint','python',images['backend'],'/tmp/make_dag_fixtures.py'])
            execute(['podman','cp',str(ROOT/'templates'),helper+':/tmp/aat-dag-template'])
            execute(['podman','cp',str(ROOT/'tests/tools/make_dag_fixtures.py'),helper+':/tmp/make_dag_fixtures.py'])
            execute(['podman','start','-a',helper])
            fixtures=ROOT/'.tools'/(project+'-dag-fixtures');fixtures.mkdir(exist_ok=True)
            execute(['podman','cp',helper+':/tmp/aat-dag-fixtures/.',str(fixtures)])
            execute(['podman','cp',str(fixtures),runner+':/tests/dag-fixtures'])
        finally:execute(['podman','rm','-f',helper],check=False)
    if args.suite=='monitoring':
        worker=execute([*base,'ps','-q','backend-worker']).stdout.strip()
        execute(['podman','cp',str(ROOT/'tests/tools/seed_monitoring_fixture.py'),worker+':/tmp/seed_monitoring_fixture.py'])
        execute(['podman','exec','-e','AAT_E2E_PROJECT='+project,worker,'python','/tmp/seed_monitoring_fixture.py'])
    tested=execute(['podman','exec',runner,'node','node_modules/@playwright/test/cli.js','test',*suite_sources,'bootstrap.spec.ts','--timeout=120000','--reporter=line'],check=False,timeout=1800 if args.suite=='full_workflow' else 300)
    (evidence/(args.suite+'-e2e.log')).write_text(redact(tested.stdout+tested.stderr),encoding='utf-8')
    if tested.returncode:execute(['podman','cp',runner+':/tests/test-results',str(evidence)],check=False)
    result['exit_code']=tested.returncode
    result['status']='PASS' if tested.returncode==0 else 'FAIL'
    if args.suite=='full_workflow' and tested.returncode==0:
        references=evidence/'full-workflows.json'
        execute(['podman','cp',runner+':/tmp/aat-e2e-artifacts/full-workflows.json',str(references)])
        execute(['podman','cp',str(references),backend+':/tmp/full-workflows.json'])
        execute(['podman','cp',str(ROOT/'tests/tools/verify_full_workflow.py'),backend+':/tmp/verify_full_workflow.py'])
        verified=execute(['podman','exec',backend,'python','/tmp/verify_full_workflow.py'],check=False,timeout=60)
        if verified.returncode==0 and args.missing_source_check:
            result['missing_source_verifier_sha256']=hashlib.sha256((ROOT/'tests/tools/verify_missing_source.py').read_bytes()).hexdigest()
            execute(['podman','cp',str(ROOT/'tests/tools/verify_missing_source.py'),backend+':/tmp/verify_missing_source.py'])
            guarded=execute(['podman','exec',backend,'python','/tmp/verify_missing_source.py'],check=False,timeout=120)
            (evidence/'missing-source-verification.log').write_text(redact(guarded.stdout+guarded.stderr),encoding='utf-8')
            result['missing_source_exit_code']=guarded.returncode
            verified=guarded if guarded.returncode else execute(['podman','exec',backend,'python','/tmp/verify_full_workflow.py'],check=False,timeout=60)
        (evidence/'full-workflow-verification.log').write_text(redact(verified.stdout+verified.stderr),encoding='utf-8')
        result.update(actual_execution_exit_code=verified.returncode,exit_code=verified.returncode,
            status='PASS' if verified.returncode==0 else 'FAIL')
    if args.suite=='phase7' and tested.returncode==0:
        recreated=execute([*base,'up','-d','--no-build','--no-deps','--force-recreate','--wait','--wait-timeout','180','backend-worker','backend'],check=False,timeout=240)
        (evidence/'settings-recreation.log').write_text(redact(recreated.stdout+recreated.stderr),encoding='utf-8')
        result['recreation_exit_code']=recreated.returncode
        if recreated.returncode==0:
            refreshed=execute([*base,'up','-d','--no-build','--no-deps','--force-recreate','--wait','--wait-timeout','120','frontend'],check=False,timeout=180)
            (evidence/'settings-proxy-recreation.log').write_text(redact(refreshed.stdout+refreshed.stderr),encoding='utf-8')
            result['proxy_refresh_exit_code']=refreshed.returncode
            if refreshed.returncode==0:
                persistent=execute(['podman','exec',runner,'node','node_modules/@playwright/test/cli.js','test','settings-persistence.spec.ts','--reporter=line'],check=False,timeout=180)
                (evidence/'settings-persistence.log').write_text(redact(persistent.stdout+persistent.stderr),encoding='utf-8')
                result['persistence_exit_code']=persistent.returncode;result['exit_code']=persistent.returncode
            else:result['exit_code']=refreshed.returncode
        else:result['exit_code']=recreated.returncode
        result['status']='PASS' if result['exit_code']==0 else 'FAIL'
        if result['exit_code']==0:
            # Only the newly owned fixture API is stopped; the user's demo and
            # all pre-existing services remain untouched.
            stopped=execute([*base,'stop','airflow-apiserver'],check=False,timeout=90)
            result['airflow_stop_exit_code']=stopped.returncode
            if stopped.returncode==0:
                down=execute(['podman','exec',runner,'node','node_modules/@playwright/test/cli.js','test','dashboard-unavailable.spec.ts','--reporter=line'],check=False,timeout=180)
                (evidence/'dashboard-unavailable.log').write_text(redact(down.stdout+down.stderr),encoding='utf-8')
                result['outage_exit_code']=down.returncode;result['exit_code']=down.returncode
            else:result['exit_code']=stopped.returncode
            result['status']='PASS' if result['exit_code']==0 else 'FAIL'
    if args.suite=='dag_builder' and tested.returncode==0:
        backend=execute([*base,'ps','-q','backend']).stdout.strip()
        execute(['podman','cp',str(ROOT/'tests/tools/verify_dag_browser_runs.py'),backend+':/tmp/verify_dag_browser_runs.py'])
        actual=execute(['podman','exec',backend,'python','/tmp/verify_dag_browser_runs.py'],check=False,timeout=210)
        (evidence/'dag-browser-actual-results.log').write_text(redact(actual.stdout+actual.stderr),encoding='utf-8')
        result['actual_execution_exit_code']=actual.returncode
        result['exit_code']=actual.returncode
        result['status']='PASS' if actual.returncode==0 else 'FAIL'
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
    if source_loader:execute(['podman','rm','-f',source_loader],check=False)
    if resources_started:execute(['podman','rm','-f',runner],check=False)
    if resources_started and config_path.exists() and not args.keep_running:
        cleaned=execute([*base,'down','--volumes'],check=False)
        result['cleanup_exit_code']=cleaned.returncode
        if cleaned.returncode:
            result.update(status='CLEANUP_FAILED',test_exit_code=result.get('exit_code'),exit_code=cleaned.returncode)
    if args.keep_running:result['services_retained']=resources_started
    (evidence/(args.suite+'-e2e-results.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if result.get('exit_code',1):raise SystemExit(result.get('exit_code',1))
