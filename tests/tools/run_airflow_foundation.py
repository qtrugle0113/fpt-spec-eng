"""Own a disposable real Airflow fixture for foundation acceptance; no published ports."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--airflow-image', required=True)
parser.add_argument('--postgres-image', required=True)
parser.add_argument('--runner-image', required=True)
parser.add_argument('--evidence-dir', required=True)
parser.add_argument('--compose-profile', action='store_true')
parser.add_argument('--profile-only', action='store_true', help='Focused rerun of Compose profile after selectors have passed')
parser.add_argument('--contract-tests',action='store_true',help='Run T097 contracts on the isolated real API instead of repeating foundation suites')
parser.add_argument('--contract-module',action='append',help='Focused unittest module for contract mode')
parser.add_argument('--fixture-dags',action='store_true',help='Parse 205 paused SDK-only DAGs in new disposable container filesystems')
parser.add_argument('--runtime-bind-tests',action='store_true',help='Run metadata/API binding tests against a real running SDK task in isolated fixtures')
parser.add_argument('--runtime-execution-tests',action='store_true',help='Execute current runtime source through SDK, private backend bind and isolated target DB')
parser.add_argument('--workbook-deps-image',help='Reviewed source of pinned workbook libraries for the nested backend fixture')
parser.add_argument('--mysql-image',help='Optional reviewed MySQL fixture for cross-database SDK execution')
parser.add_argument('--runtime-execution-module',action='append',help='Focused unittest module/class for real runtime execution')
parser.add_argument('--runtime-label',default='t104-real-sdk',help='Evidence label for the real execution selector')
parser.add_argument('--packaged-runtime',action='store_true',help='Execute the installed metadata/engine wheels in Airflow, without source overlays')
args = parser.parse_args()
if args.profile_only and not args.compose_profile:
    parser.error('--profile-only requires --compose-profile')
evidence = (ROOT/args.evidence_dir).resolve()
if not evidence.is_relative_to(ROOT):
    parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True, exist_ok=True)
prefix = 'aat-foundation-airflow-'+secrets.token_hex(4)
network = prefix+'-net'
pg = prefix+'-pg'
api = prefix+'-api'
password = secrets.token_urlsafe(32)
auth_password = secrets.token_urlsafe(32)
created = []
network_created = False
owned_volumes=[]
result = {'published_ports': False, 'existing_services_modified': False,
          'fixture_network': network, 'status': 'NOT_RUN'}
result['airflow_runtime_mode']='INSTALLED_IMAGE_WHEELS' if args.packaged_runtime else 'SOURCE_OVERLAY'


def run(*command, check=True, timeout=180):
    try:
        process = subprocess.run(['podman', *command], capture_output=True, text=True,
                                 encoding='utf-8', timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Podman fixture command timed out: '+command[0]) from None
    if check and process.returncode:
        # Never include command/env/DSN or raw service logs in public diagnostics.
        raise RuntimeError('Podman fixture command failed: '+command[0])
    return process


try:
    # Record actual image identities before creating resources.
    result['images'] = {name: run('image', 'inspect', reference, '--format', '{{.Id}}').stdout.strip()
                        for name, reference in [('airflow', args.airflow_image),
                                                ('postgres', args.postgres_image),
                                                ('runner', args.runner_image)]}
    run('network', 'create', '--internal', network)
    network_created = True
    created.append(pg)
    run('run', '-d', '--name', pg, '--network', network, '--memory', '384m',
        '--tmpfs', '/var/lib/postgresql/data:rw,size=384m',
        '-e', 'POSTGRES_PASSWORD='+password, '-e', 'POSTGRES_DB=airflow_metadata', args.postgres_image)
    deadline = time.monotonic()+60
    while run('exec', pg, 'pg_isready', '-U', 'postgres', '-d', 'airflow_metadata', check=False).returncode:
        if time.monotonic()>deadline:
            raise RuntimeError('Airflow fixture PostgreSQL unavailable')
        time.sleep(1)
    sql = "CREATE ROLE aat_airflow LOGIN PASSWORD '"+password+"'; ALTER DATABASE airflow_metadata OWNER TO aat_airflow; REVOKE ALL ON DATABASE airflow_metadata FROM PUBLIC;"
    configured = subprocess.run(['podman', 'exec', '-i', pg, 'psql', '-U', 'postgres',
                                 '-d', 'airflow_metadata', '-v', 'ON_ERROR_STOP=1'],
                                input=sql, capture_output=True, text=True, timeout=30)
    if configured.returncode:
        raise RuntimeError('Airflow fixture role initialization failed')
    environment = {
        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN': 'postgresql+psycopg://aat_airflow:'+password+'@'+pg+'/airflow_metadata',
        'AIRFLOW__CORE__FERNET_KEY': base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        'AIRFLOW__API_AUTH__JWT_SECRET': secrets.token_urlsafe(48),
        'AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE': '/tmp/aat-fixture-auth.json',
        'AAT_FIXTURE_AUTH_PASSWORD': auth_password,
    }
    if args.fixture_dags or args.runtime_bind_tests or args.runtime_execution_tests:
        environment['AIRFLOW__CORE__DAGS_FOLDER']='/tmp/aat-contract-dags'
        environment['AIRFLOW__CORE__EXECUTION_API_SERVER_URL']='http://'+api+':8080/execution/'
    if args.fixture_dags:
        environment['AAT_FIXTURE_DAG_COUNT']='205'
    if args.runtime_execution_tests:
        environment['PYTHONPATH']='/tmp' if args.packaged_runtime else '/tmp/etl_engine/src:/tmp/packages:/tmp'
        environment['AIRFLOW__DAG_PROCESSOR__REFRESH_INTERVAL']='5'
        for suffix in ('dags','private','staging','logs'):
            name=prefix+'-'+suffix
            run('volume','create',name);owned_volumes.append(name)
    options = []
    for key, value in environment.items():
        options += ['-e', key+'='+value]
    launch = "import json,os,sys; p='/tmp/aat-fixture-auth.json'; secret=os.environ.pop('AAT_FIXTURE_AUTH_PASSWORD'); f=open(p,'w'); json.dump({'aat_service':secret,'operator':secret},f); f.close(); os.chmod(p,0o600); os.execvp('airflow',['airflow',*sys.argv[1:]])"
    init = prefix+'-init'
    created.append(init)
    run('run', '--rm', '--name', init, '--network', network, '--memory', '1g',
        *options, '--entrypoint', 'python', args.airflow_image, '-c', launch, 'db', 'migrate')
    for suffix, command, memory in [('api', 'api-server', '1g'), ('scheduler', 'scheduler', '2g'),
                                     ('processor', 'dag-processor', '1g')]:
        name = prefix+'-'+suffix
        created.append(name)
        mounts=[]
        runtime_options=[]
        if args.runtime_execution_tests:
            mounts=['--volume',owned_volumes[0]+':/tmp/aat-contract-dags:ro,U','--volume',owned_volumes[3]+':/opt/airflow/logs:U']
            if suffix=='scheduler':
                mounts+=['--volume',owned_volumes[1]+':/tmp/aat-runtime-private:ro,U','--volume',owned_volumes[2]+':/tmp/aat-runtime-staging:U']
                runtime_environment={
                    'AAT_RUNTIME_SECRETS':'/tmp/aat-runtime-private/runtime-secrets',
                    'AAT_APP_KEYRING':'/tmp/aat-runtime-private/keyring',
                    'AAT_RUNTIME_TOKEN_FILE':'/tmp/aat-runtime-private/runtime_token',
                    'AAT_RUNTIME_BIND_URL':'http://backend:8000/internal/runtime/bind',
                    'AAT_UPLOADS_ROOT':'/tmp/aat-runtime-private/uploads',
                    'AAT_STAGING_ROOT':'/tmp/aat-runtime-staging','AAT_DB_ALLOWED_HOSTS':'postgres,mysql'}
                for key,value in runtime_environment.items():runtime_options+=['-e',key+'='+value]
        run('create', '--name', name, '--network', network, '--memory', memory,
            *mounts,*options,*runtime_options, '--entrypoint', 'python', args.airflow_image, '-c', launch, command)
        if args.runtime_execution_tests:
            for source in (('tests',) if args.packaged_runtime else ('tests','etl_engine','packages')):run('cp',str(ROOT/source),name+':/tmp/'+source)
        # The scheduler imports shared packages during startup and its task
        # children inherit sys.modules. Populate PYTHONPATH before starting it;
        # changing sys.path later cannot replace already imported image code.
        run('start',name)
        if args.runtime_execution_tests and args.packaged_runtime:
            origins="import aat_etl,aat_metadata,json; from pathlib import Path; d={p.__name__:p.__file__ for p in (aat_etl,aat_metadata)}; assert all(not Path(v).is_relative_to('/tmp') for v in d.values()); Path('/tmp/aat-installed-origins.json').write_text(json.dumps(d))"
            run('exec',name,'python','-c',origins)
            run('cp',name+':/tmp/aat-installed-origins.json',str(evidence/(suffix+'-installed-origins.json')))
        if args.runtime_execution_tests:
            snapshot="from pathlib import Path; import hashlib,json; roots=[Path('/tmp/etl_engine'),Path('/tmp/packages'),Path('/tmp/tests')]; d={p.relative_to('/tmp').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for r in roots for p in r.rglob('*.py') if not any(x in p.parts for x in ('build','__pycache__'))}; Path('/tmp/aat-airflow-fixture-sources.json').write_text(json.dumps(d,sort_keys=True,indent=2))"
            run('exec',name,'python','-c',snapshot)
            run('cp',name+':/tmp/aat-airflow-fixture-sources.json',str(evidence/(suffix+'-source-sha256.json')))
        if args.fixture_dags or args.runtime_bind_tests:
            if args.fixture_dags:
                source="from datetime import datetime,timezone\nfrom airflow.sdk import DAG,task\ndef check(): return 'contract-fixture'\nfor index in range(205):\n    with DAG('aat_contract_%03d'%index,schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),catchup=False,is_paused_upon_creation=True,tags=['aat-contract-fixture']):\n        task(task_id='execute_etl')(check)()\n"
            else:
                sys.path.insert(0,str(ROOT))
                from tests.airflow.binding_fixture import configuration,DAG_ID
                config_json=json.dumps(configuration())
                sql="SELECT encode(sha256(convert_to($aat$"+config_json+"$aat$::jsonb::text,'UTF8')),'hex')"
                config_hash=run('exec',pg,'psql','-U','postgres','-d','airflow_metadata','-Atc',sql).stdout.strip()
                if len(config_hash)!=64:raise RuntimeError('Fixture config hash could not be computed')
                source="from datetime import datetime,timezone\nfrom airflow.sdk import DAG,task\ndef check():\n    import time\n    time.sleep(45)\n    return 'binding-fixture-only'\nwith DAG("+repr(DAG_ID)+",schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),catchup=False,is_paused_upon_creation=True,tags=['aat','aat_revision:"+config_hash+"']):\n    task(task_id='execute_etl')(check)()\n"
            run('exec',name,'python','-c',"from pathlib import Path; import sys; p=Path('/tmp/aat-contract-dags'); p.mkdir(exist_ok=True); (p/'contract_fixture.py').write_text(sys.argv[1])",source)
    health = "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/v2/monitor/health',timeout=3)); print('READY' if all(d.get(k,{}).get('status')=='healthy' for k in ('metadatabase','scheduler','dag_processor')) else 'WAIT')"
    deadline = time.monotonic()+180
    while True:
        checked = run('exec', api, 'python', '-c', health, check=False, timeout=15)
        if checked.returncode == 0 and checked.stdout.strip() == 'READY':
            break
        if time.monotonic()>deadline:
            raise RuntimeError('Real Airflow foundation readiness deadline exceeded')
        time.sleep(2)
    result['airflow_dependencies'] = 'HEALTHY'
    print('AIRFLOW_FOUNDATION_READY '+network, flush=True)
    if args.runtime_bind_tests or args.runtime_execution_tests:
        if not args.workbook_deps_image:raise RuntimeError('A reviewed workbook dependency image is required')
        env=dict(os.environ,AAT_TEST_AIRFLOW_ORIGIN='http://'+api+':8080',AAT_TEST_AIRFLOW_PASSWORD=auth_password)
        command=[sys.executable,'-X','utf8',str(ROOT/'tests/tools/run_metadata_foundation.py'),
            '--postgres-image',args.postgres_image,'--runner-image',args.runner_image,'--workbook-deps-image',args.workbook_deps_image,
            '--runtime-contract-network',network,
            '--task-label',(args.runtime_label if args.runtime_execution_tests else 't103-real-ti-bind'),'--evidence-dir',str(evidence.relative_to(ROOT))]
        modules=(args.runtime_execution_module or ['tests.airflow.test_runtime_execution.RealRuntimeExecutionTests']) if args.runtime_execution_tests else ['tests.airflow.test_runtime_binding']
        for module in modules:command+=['--unittest-module',module]
        if args.mysql_image:command+=['--mysql-image',args.mysql_image]
        if args.runtime_execution_tests:
            command+=['--runtime-fixture-scheduler',prefix+'-scheduler','--runtime-fixture-dags',owned_volumes[0],
                      '--runtime-fixture-private',owned_volumes[1],'--runtime-fixture-staging',owned_volumes[2],
                      '--runner-memory','1g','--disk-databases']
        checked=subprocess.run(command,cwd=ROOT,env=env)
        result['runtime_binding_exit_code']=checked.returncode
        if checked.returncode:raise RuntimeError('Real task binding contract failed; inspect nested fixture evidence')
    if args.fixture_dags:
        inventory="import os,httpx; c=httpx.Client(base_url='http://127.0.0.1:8080',timeout=10,trust_env=False); r=c.post('/auth/token',json={'username':'aat_service','password':os.environ['AAT_FIXTURE_AUTH_PASSWORD']}); c.headers['Authorization']='Bearer '+r.json()['access_token']; r=c.get('/api/v2/dags',params={'dag_id_prefix_pattern':'aat_contract_','limit':1}); print(r.json().get('total_entries',0))"
        deadline=time.monotonic()+120
        while True:
            checked=run('exec',api,'python','-c',inventory,check=False,timeout=20)
            if checked.returncode==0 and checked.stdout.strip()=='205':break
            if time.monotonic()>=deadline:raise RuntimeError('Fixture DAG parse/registration deadline exceeded')
            time.sleep(2)
        result['fixture_dags_registered']=205
    if args.contract_tests:
        for source in ('tests','backend'):
            run('cp',str(ROOT/source),api+':/tmp/'+source)
        modules=args.contract_module or ['tests.airflow.test_api_contract','tests.airflow.test_registration']
        checked=run('exec','-e','PYTHONPATH=/tmp/backend/src:/tmp',api,'python','-m','unittest',
            *modules,'-v',check=False,timeout=120)
        output=(checked.stdout+checked.stderr).replace(password,'[REDACTED]').replace(auth_password,'[REDACTED]')
        (evidence/'t097-airflow-contract.log').write_text(output,encoding='utf-8')
        for artifact in ('aat-airflow-openapi.json','aat-airflow-openapi-sha256.json'):
            run('cp',api+':/tmp/'+artifact,str(evidence/artifact),check=False)
        result['contract_exit_code']=checked.returncode
        print(output[-5000:],flush=True)
        if checked.returncode:raise RuntimeError('T097 contracts are not yet passing; inspect the retained log')
    common = ['--postgres-image', args.postgres_image, '--runner-image', args.runner_image,
              '--airflow-network', network, '--airflow-health-url',
              'http://'+api+':8080/api/v2/monitor/health', '--evidence-dir', args.evidence_dir]
    for selector in ([] if args.profile_only or args.contract_tests or args.runtime_bind_tests or args.runtime_execution_tests else ['--readiness', '--foundation']):
        completed = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'tests/tools/run_metadata_foundation.py'),
                                    selector, *common], cwd=ROOT)
        if completed.returncode:
            raise RuntimeError('Foundation selector failed: '+selector)
    if args.compose_profile:
        env = dict(os.environ, AAT_FOUNDATION_TEST_IMAGE=args.runner_image,
                   AAT_FOUNDATION_POSTGRES_IMAGE=args.postgres_image,
                   AAT_FOUNDATION_AIRFLOW_NETWORK=network,
                   AAT_FOUNDATION_AIRFLOW_HEALTH_URL='http://'+api+':8080/api/v2/monitor/health')
        completed = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'tests/tools/run_foundation_profile.py'),
                                    '--evidence-dir', args.evidence_dir], cwd=ROOT, env=env)
        if completed.returncode:
            raise RuntimeError('Compose foundation profile failed')
    result['status'] = 'PASS'
finally:
    cleanup = [run('rm', '-f', name, check=False).returncode for name in reversed(created) if name != prefix+'-init']
    if network_created:
        cleanup.append(run('network', 'rm', network, check=False).returncode)
    for volume in owned_volumes:cleanup.append(run('volume','rm',volume,check=False).returncode)
    result['cleanup_exit_codes'] = cleanup
    (evidence/'airflow-fixture-results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
