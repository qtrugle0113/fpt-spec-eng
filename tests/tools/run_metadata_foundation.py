"""Host-side T016 disposable DB driver; no engine socket in any container.

Uses explicit image references, isolated internal network and tmpfs; no published ports
or existing volumes/secrets. Writes the real pytest exit status to evidence.
App-init/worker integration in T030/T033 must consume the explicit test DSN;
this driver never redirects existing services or injects credentials into logs.
"""

import subprocess, secrets, time, json, sys, argparse
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--authorization', action='store_true', help='Run only T017 authorization tests, retaining T016 evidence')
parser.add_argument('--connections-orm', action='store_true', help='Run T019 real ORM DDL checks, not migrations')
parser.add_argument('--definitions-orm', action='store_true', help='Run T020 real ORM plus affected T019 checks')
parser.add_argument('--file-parsers-orm', action='store_true', help='Run T021 real ORM plus T019/T020 regression')
parser.add_argument('--model-task', choices=['t022', 't023', 't024', 't025', 't026', 't027'])
parser.add_argument('--repositories',action='store_true')
parser.add_argument('--owner-init',action='store_true',help='Verify migrations under the non-superuser owner on a fresh fixture')
parser.add_argument('--unittest-module',action='append',help='Run a source test module with unittest using the same isolated DB fixture')
parser.add_argument('--task-label',help='Evidence label required with --unittest-module')
parser.add_argument('--api-foundation',action='store_true')
parser.add_argument('--operations',action='store_true')
parser.add_argument('--readiness',action='store_true')
parser.add_argument('--foundation',action='store_true')
parser.add_argument('--foundation-core',action='store_true',help='Run database/API foundation only; excludes Airflow readiness acceptance')
parser.add_argument('--phase', choices=['red', 'green'], default='green')
parser.add_argument('--postgres-image', default='87507379f5ed1bca39a781c2f03da05f368e9f92b69c670e9a87cdf32cc9cf03')
parser.add_argument('--mysql-image', help='Optional MySQL image for real Connections acceptance')
parser.add_argument('--runner-image', default='89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4')
parser.add_argument('--workbook-deps-image',help='Copy pinned workbook libraries from a reviewed backend image for a source-only test runner')
parser.add_argument('--evidence-dir', help='Workspace-relative directory for a fresh run; preserves historical evidence')
parser.add_argument('--airflow-network', default='aat-phase1-t014-local-20261109_aat_internal')
parser.add_argument('--airflow-health-url', default='http://aat-phase1-t014-local-20261109-airflow-apiserver-1:8080/api/v2/monitor/health')
args = parser.parse_args()
if sum((args.authorization, args.connections_orm, args.definitions_orm, args.file_parsers_orm, bool(args.model_task), args.repositories,args.owner_init,bool(args.unittest_module),args.api_foundation,args.operations,args.readiness,args.foundation,args.foundation_core)) > 1:
    parser.error('Choose one task selector')
if args.unittest_module and (not args.task_label or not re.fullmatch('[a-z0-9-]+',args.task_label)):
    parser.error('A simple lowercase task label is required with unittest modules')
task = 't021' if args.file_parsers_orm else 't020' if args.definitions_orm else 't019' if args.connections_orm else 't017' if args.authorization else 't016'
if args.model_task:
    task = args.model_task
if args.repositories:task='t028-t030'
if args.owner_init:task='t030-owner'
if args.unittest_module:task=args.task_label
if args.api_foundation:task='t032'
if args.operations:task='t033'
if args.readiness:task='t034'
if args.foundation:task='phase2-foundation'
if args.foundation_core:task='phase2-foundation-core'
pg = 'aat-' + task + '-pg-' + secrets.token_hex(4)
runner = 'aat-' + task + '-runner-' + secrets.token_hex(4)
network = 'aat-' + task + '-net-' + secrets.token_hex(4)
mysql = 'aat-' + task + '-mysql-' + secrets.token_hex(4)
test_paths = (['/tmp/tests/unit/test_authorization_states.py', '/tmp/tests/integration/test_authorization_repository.py']
              if args.authorization else ['/tmp/tests/integration/test_metadata_foundation.py'])
log_path = ('docs/testing/t014-round2-logs/local-t017-authorization-red.log' if args.authorization
            else 'docs/testing/t014-round2-logs/local-t016-foundation-red.log')
if args.authorization:log_path='docs/testing/t014-round2-logs/local-t017-authorization-'+args.phase+'.log'
if args.connections_orm:
    test_paths = ['/tmp/tests/integration/test_connection_models.py']
    log_path = 'docs/testing/t014-round2-logs/local-t019-orm-' + args.phase + '.log'
if args.definitions_orm:
    test_paths = ['/tmp/tests/integration/test_connection_models.py', '/tmp/tests/integration/test_definition_models.py']
    log_path = 'docs/testing/t014-round2-logs/local-t020-orm-' + args.phase + '.log'
if args.file_parsers_orm:
    test_paths = ['/tmp/tests/integration/test_connection_models.py', '/tmp/tests/integration/test_definition_models.py',
                  '/tmp/tests/integration/test_file_parser_models.py']
    log_path = 'docs/testing/t014-round2-logs/local-t021-orm-' + args.phase + '.log'
if args.model_task:
    test_paths = ['/tmp/tests/integration/test_' + task + '_models.py']
    log_path = 'docs/testing/t014-round2-logs/local-' + task + '-orm-' + args.phase + '.log'
if args.repositories:
    test_paths=['/tmp/tests/integration/test_phase2_repositories.py']
    log_path='docs/testing/t014-round2-logs/local-t028-t030-'+args.phase+'.log'
if args.owner_init:
    test_paths=['/tmp/tests/integration/test_owner_initialization.py']
    log_path='docs/testing/t014-round2-logs/local-t030-owner-'+args.phase+'.log'
if args.api_foundation or args.operations:
    test_paths=['/tmp/tests/integration/test_phase2_'+('api' if args.api_foundation else 'operations')+'.py']
    log_path='docs/testing/t014-round2-logs/local-'+task+'-'+args.phase+'.log'
    if args.api_foundation:test_paths.append('/tmp/tests/unit/test_bootstrap_secrets.py')
if args.readiness:
    test_paths=['/tmp/tests/integration/test_foundation_ready.py']
    log_path='docs/testing/t014-round2-logs/local-t034-'+args.phase+'.log'
if args.foundation or args.foundation_core:
    test_paths=['/tmp/tests/integration/test_metadata_foundation.py','/tmp/tests/unit/test_authorization_states.py',
                '/tmp/tests/integration/test_authorization_repository.py','/tmp/tests/integration/test_phase2_repositories.py',
                '/tmp/tests/integration/test_phase2_operations.py','/tmp/tests/integration/test_phase2_api.py',
                '/tmp/tests/integration/test_foundation_ready.py']
    if args.foundation_core:
        test_paths.remove('/tmp/tests/integration/test_foundation_ready.py')
    log_path='docs/testing/t014-round2-logs/local-'+task+'-'+args.phase+'.log'
if args.unittest_module:
    test_paths=args.unittest_module
    log_path='docs/testing/t014-round2-logs/local-'+task+'-'+args.phase+'.log'
ROOT = Path(__file__).resolve().parents[2]
evidence_dir = ROOT / 'docs/testing'
if args.evidence_dir:
    evidence_dir = (ROOT / args.evidence_dir).resolve()
    if not evidence_dir.is_relative_to(ROOT):
        parser.error('Evidence directory must stay in workspace')
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = str((evidence_dir / (task + '-' + args.phase + '.log')).relative_to(ROOT))
password = secrets.token_urlsafe(32)
created = []
network_created = False

def run(*args):
    p = subprocess.run(['podman', *args], text=True, encoding='utf-8', capture_output=True)
    if p.returncode:
        raise RuntimeError((p.stdout + p.stderr).replace(password, '[REDACTED]'))
    return p.stdout.strip()

try:
    run('network', 'create', '--internal', network)
    network_created = True
    run('run', '-d', '--name', pg, '--network', network, '--network-alias', 'postgres', '--memory', '256m',
        '--pids-limit', '256', '--tmpfs', '/var/lib/postgresql/data:rw,size=256m',
        '-e', 'POSTGRES_PASSWORD=' + password, '-e', 'POSTGRES_DB=app_metadata',
        args.postgres_image)
    created.append(pg)
    for _ in range(60):
        p = subprocess.run(['podman', 'exec', pg, 'pg_isready', '-U', 'postgres', '-d', 'app_metadata'], capture_output=True)
        if p.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Disposable PostgreSQL unavailable')
    sql = """CREATE DATABASE airflow_metadata;
    CREATE ROLE aat_app_owner LOGIN; CREATE ROLE aat_app_runtime LOGIN; CREATE ROLE aat_airflow LOGIN;
    REVOKE ALL ON DATABASE app_metadata FROM PUBLIC; REVOKE ALL ON DATABASE airflow_metadata FROM PUBLIC;
    GRANT CONNECT ON DATABASE app_metadata TO aat_app_owner,aat_app_runtime;
    GRANT CONNECT ON DATABASE airflow_metadata TO aat_airflow;"""
    sql += ' CREATE ROLE aat_etl LOGIN;'
    p = subprocess.run(['podman', 'exec', '-i', pg, 'psql', '-U', 'postgres', '-d', 'app_metadata', '-v', 'ON_ERROR_STOP=1'], input=sql, text=True, capture_output=True)
    assert p.returncode == 0, 'Fixture role isolation setup failed'
    if args.mysql_image:
        run('run','-d','--name',mysql,'--network',network,'--network-alias','mysql','--memory','1g',
            '--tmpfs','/var/lib/mysql:rw,size=768m','-e','MYSQL_ROOT_PASSWORD='+password,
            '-e','MYSQL_ROOT_HOST=%','-e','MYSQL_DATABASE=etl_test','-e','MYSQL_USER=aat_test','-e','MYSQL_PASSWORD='+password,args.mysql_image)
        created.append(mysql)
        for _ in range(90):
            ready=subprocess.run(['podman','exec',mysql,'mysql','--protocol=tcp','-h127.0.0.1',
                                  '-uaat_test','--password='+password,'-Detl_test','-Nse','SELECT 1'],capture_output=True)
            if ready.returncode==0:break
            time.sleep(1)
        else:raise RuntimeError('Disposable MySQL unavailable')
    run('create', '--name', runner, '--network', network, '--memory', '512m', '--workdir', '/tmp',
        '-e', 'PYTHONPATH=/tmp/backend/src:/tmp/etl_engine/src:/tmp/packages:/tmp/test-deps:/tmp',
        '-e', 'AAT_FOUNDATION_DISPOSABLE=1',
        '-e', 'AAT_APP_KEYRING=/tmp/aat-test-keyring',
        '-e', 'AAT_UPLOADS_ROOT=/tmp/aat-test-uploads',
        '-e', 'AAT_ASSETS_ROOT=/tmp',
        '-e', 'AAT_FOUNDATION_INITIALIZE=' + ('1' if args.authorization or args.operations or args.readiness or args.unittest_module else '0'),
        '-e', 'AAT_FOUNDATION_TEST_RUNNER=' + ('unittest' if args.unittest_module else 'pytest'),
        '-e', 'AAT_DB_ALLOWED_HOSTS=postgres,mysql,' + pg,
        '-e', 'AAT_AIRFLOW_HEALTH_URL=' + args.airflow_health_url,
        '-e', f'AAT_FOUNDATION_TEST_DSN=postgresql://postgres:{password}@{pg}/app_metadata',
        '--entrypoint', 'python', args.runner_image,
        '/tmp/prepare_keyring.py', *([*test_paths,'-v'] if args.unittest_module else ['-p','no:cacheprovider',*test_paths,'-v','--tb=short']))
    created.append(runner)
    if args.readiness or args.foundation:
        # Connect only the disposable runner to the approved Airflow network for
        # read-only /monitor/health; existing containers/networks are unchanged.
        run('network','connect',args.airflow_network,runner)
    for source in ['tests', 'docker', 'backend', 'etl_engine', 'packages', 'samples', 'specs','templates']:
        run('cp', str(ROOT / source), runner + ':/tmp/' + source)
    workbook_dependencies=None
    if args.workbook_deps_image:
        helper='aat-workbook-libs-'+secrets.token_hex(4)
        query="import sysconfig,pathlib,json,importlib.metadata as m; p=pathlib.Path(sysconfig.get_paths()['purelib']); names=['openpyxl','et_xmlfile','defusedxml']; print(json.dumps({'root':str(p),'entries':names+[v.name for v in p.iterdir() if any(v.name.startswith(n+'-') and v.name.endswith('.dist-info') for n in names)],'versions':{n:m.version(n) for n in names}}))"
        run('create','--name',helper,'--network=none','--entrypoint','python',args.workbook_deps_image,'-c',query)
        created.append(helper)
        info=json.loads(run('start','-a',helper))
        if info['versions']!={'openpyxl':'3.1.5','et_xmlfile':'2.0.0','defusedxml':'0.7.1'}:
            raise RuntimeError('Workbook dependency versions differ from backend lock')
        dependencies=ROOT/'.tools'/('test-deps-'+secrets.token_hex(4));dependencies.mkdir(parents=True)
        for entry in info['entries']:
            if Path(entry).name!=entry:raise RuntimeError('Unexpected library entry')
            run('cp',helper+':'+info['root']+'/'+entry,str(dependencies))
        run('cp',str(dependencies),runner+':/tmp/test-deps')
        workbook_dependencies={'source_image_id':run('inspect',helper,'--format','{{.Image}}'),'versions':info['versions']}
    # Private synthetic keyring belongs only to this disposable runner. Product
    # initialization never regenerates missing persistent keys.
    run('cp', str(ROOT / 'tests/tools/prepare_foundation_keyring.py'), runner + ':/tmp/prepare_keyring.py')
    p = subprocess.run(['podman', 'start', '-a', runner], text=True, encoding='utf-8', capture_output=True)
    output = (p.stdout + p.stderr).replace(password, '[REDACTED]')
    if args.readiness or args.foundation:
        subprocess.run(['podman','cp',runner+':/tmp/aat-foundation-http.json',str(evidence_dir/'phase2-http-evidence.json')],capture_output=True)
    (ROOT / log_path).write_bytes(output.encode())
    exit_code = int(run('inspect', runner, '--format', '{{.State.ExitCode}}'))
    print(output[-6500:])
    result = {'postgres_image_id': run('inspect', pg, '--format', '{{.Image}}'),
              'mysql_image_id': run('inspect',mysql,'--format','{{.Image}}') if args.mysql_image else None,
              'runner_image_id': run('inspect', runner, '--format', '{{.Image}}'),
              'workbook_test_dependencies':workbook_dependencies,
              'fixture': 'Disposable PostgreSQL17.11,tmpfs256MiB,no published ports,no existing volumes/secrets mounted',
              'task': task.upper(), 'test_paths': test_paths,
              'test_exit_code': exit_code, 'log': log_path,
              'existing_services_modified': False}
    (evidence_dir / (task + '-fixture-results.json')).write_bytes((json.dumps(result, indent=2) + '\n').encode())
finally:
    for name in reversed(created):
        subprocess.run(['podman', 'rm', '-f', name], capture_output=True)

    if network_created:
        subprocess.run(['podman', 'network', 'rm', network], capture_output=True)

sys.exit(exit_code)
