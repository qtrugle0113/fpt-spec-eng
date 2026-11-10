"""Rerun browser acceptance on an explicitly retained disposable demo stack."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config',required=True)
parser.add_argument('--evidence-dir',required=True)
parser.add_argument('--refresh-source',action='store_true')
parser.add_argument('--frontend-artifact')
parser.add_argument('--project',choices=['desktop','mobile'])
parser.add_argument('--grep')
parser.add_argument('--suite',choices=['dag_builder','monitoring'],default='dag_builder')
args=parser.parse_args()
config_path=(ROOT/args.config).resolve();evidence=(ROOT/args.evidence_dir).resolve()
if not config_path.is_relative_to(ROOT/'.tools') or not evidence.is_relative_to(ROOT):parser.error('Paths must remain in workspace')
config=json.loads(config_path.read_text(encoding='utf-8'));project=config['name']
if not project.startswith('aat-dag_builder-e2e-'):parser.error('Only owned DAG browser fixtures are supported')
evidence.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,PODMAN_COMPOSE_PROVIDER=str(ROOT/'.tools/docker-compose-5.6.0.exe'))
base=['podman','compose','-f',str(config_path),'-p',project,'--profile','test']
runner=project+'-browser';helper=project+'-workbooks'
result={'project':project,'config':args.config,'status':'NOT_RUN','services_retained':True}

def run(command,check=True,timeout=120):
    process=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    if check and process.returncode:raise RuntimeError('Demo command failed: '+command[0]+'; inspect retained evidence')
    return process

try:
    if args.refresh_source:
        loader=project+'-source-refresh'
        try:
            volume=config['volumes']['current_source']['name']
            run(['podman','create','--name',loader,'--network','none','--user','0:0','-v',volume+':/current','--entrypoint','python',config['services']['backend']['image'],'-c',
                 "from pathlib import Path; [p.chmod(0o755 if p.is_dir() else 0o644) for p in Path('/current').rglob('*')]"])
            for folder in ('backend','packages','etl_engine','docker','airflow','samples','templates','specs'):
                run(['podman','cp',str(ROOT/folder)+'/.',loader+':/current/'+folder])
            if args.frontend_artifact:
                artifact=(ROOT/args.frontend_artifact).resolve()
                if not artifact.is_relative_to(ROOT) or not (artifact/'index.html').exists():raise RuntimeError('Built workspace frontend required')
                run(['podman','cp',str(artifact)+'/.',loader+':/current/frontend-dist'])
            run(['podman','start','-a',loader])
            config['services']['backend'].setdefault('environment',{})['AAT_AIRFLOW_PUBLIC_URL']='http://localhost:18080'
            config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
            process=run([*base,'up','-d','--no-build','--no-deps','--force-recreate','--wait','--wait-timeout','120',
                         'backend','backend-worker','airflow-scheduler','airflow-dag-processor','frontend'],check=False,timeout=180)
            (evidence/'source-refresh.log').write_text(process.stdout+process.stderr,encoding='utf-8')
            if process.returncode:raise RuntimeError('Refreshed demo did not become ready')
        finally:run(['podman','rm','-f',loader],check=False)
    run(['podman','create','--name',helper,'--network','none','--entrypoint','python',config['services']['backend']['image'],'/tmp/make_dag_fixtures.py'])
    run(['podman','cp',str(ROOT/'templates'),helper+':/tmp/aat-dag-template'])
    run(['podman','cp',str(ROOT/'tests/tools/make_dag_fixtures.py'),helper+':/tmp/make_dag_fixtures.py'])
    run(['podman','start','-a',helper])
    fixtures=ROOT/'.tools'/(project+'-dag-fixtures');fixtures.mkdir(exist_ok=True)
    run(['podman','cp',helper+':/tmp/aat-dag-fixtures/.',str(fixtures)])
    run([*base,'run','-d','--no-deps','--name',runner,'e2e-tests','sleep','infinity'])
    run(['podman','cp',str(fixtures),runner+':/tests/dag-fixtures'])
    for name in (args.suite+'.spec.ts','bootstrap.spec.ts','playwright.config.ts'):
        run(['podman','cp',str(ROOT/'tests/e2e'/name),runner+':/tests/'+name])
    if args.suite=='monitoring':
        worker=run([*base,'ps','-q','backend-worker']).stdout.strip()
        run(['podman','cp',str(ROOT/'tests/tools/seed_monitoring_fixture.py'),worker+':/tmp/seed_monitoring_fixture.py'])
        run(['podman','exec','-e','AAT_E2E_PROJECT='+project,worker,'python','/tmp/seed_monitoring_fixture.py'])
    selectors=[]
    if args.project:selectors+=['--project',args.project]
    if args.grep:selectors+=['--grep',args.grep]
    process=run(['podman','exec',runner,'node','node_modules/@playwright/test/cli.js','test',args.suite+'.spec.ts','bootstrap.spec.ts','--timeout=120000','--reporter=line',*selectors],check=False,timeout=600)
    (evidence/'browser.log').write_text(process.stdout+process.stderr,encoding='utf-8')
    result['browser_exit_code']=process.returncode
    print((process.stdout+process.stderr)[-5000:],flush=True)
    run(['podman','cp',runner+':/tmp/aat-e2e-artifacts/.',str(evidence)],check=False)
    run(['podman','cp',runner+':/tests/test-results',str(evidence)],check=False)
    if process.returncode==0:
        backend=run([*base,'ps','-q','backend']).stdout.strip()
        for source,target in [('tests/tools/verify_dag_browser_runs.py','/tmp/verify_dag_browser_runs.py'),('tests/unit/test_health_migration_heads.py','/tmp/test_health_migration_heads.py')]:
            run(['podman','cp',str(ROOT/source),backend+':'+target])
        actual=run(['podman','exec',backend,'python','/tmp/verify_dag_browser_runs.py'],check=False,timeout=210)
        (evidence/'actual-results.log').write_text(actual.stdout+actual.stderr,encoding='utf-8')
        result['actual_exit_code']=actual.returncode;print(actual.stdout,flush=True)
    result['status']='PASS' if result.get('browser_exit_code')==0 and result.get('actual_exit_code')==0 else 'FAIL'
finally:
    for name in (runner,helper):run(['podman','rm','-f',name],check=False)
    (evidence/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if result['status']!='PASS':raise SystemExit(1)
