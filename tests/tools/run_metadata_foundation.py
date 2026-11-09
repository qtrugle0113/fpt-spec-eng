"""Host-side T016 disposable DB driver; no engine socket in any container.

Uses approved image IDs, isolated internal network and tmpfs; no published ports
or existing volumes/secrets. Writes the real pytest exit status to evidence.
App-init/worker integration in T030/T033 must consume the explicit test DSN;
this driver never redirects existing services or injects credentials into logs.
"""

import subprocess, secrets, time, json, sys, argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--authorization', action='store_true', help='Run only T017 authorization tests, retaining T016 evidence')
parser.add_argument('--connections-orm', action='store_true', help='Run T019 real ORM DDL checks, not migrations')
parser.add_argument('--definitions-orm', action='store_true', help='Run T020 real ORM plus affected T019 checks')
parser.add_argument('--file-parsers-orm', action='store_true', help='Run T021 real ORM plus T019/T020 regression')
parser.add_argument('--model-task', choices=['t022', 't023', 't024', 't025', 't026', 't027'])
parser.add_argument('--repositories',action='store_true')
parser.add_argument('--api-foundation',action='store_true')
parser.add_argument('--operations',action='store_true')
parser.add_argument('--readiness',action='store_true')
parser.add_argument('--foundation',action='store_true')
parser.add_argument('--phase', choices=['red', 'green'], default='green')
args = parser.parse_args()
if sum((args.authorization, args.connections_orm, args.definitions_orm, args.file_parsers_orm, bool(args.model_task), args.repositories,args.api_foundation,args.operations,args.readiness,args.foundation)) > 1:
    parser.error('Choose one task selector')
task = 't021' if args.file_parsers_orm else 't020' if args.definitions_orm else 't019' if args.connections_orm else 't017' if args.authorization else 't016'
if args.model_task:
    task = args.model_task
if args.repositories:task='t028-t030'
if args.api_foundation:task='t032'
if args.operations:task='t033'
if args.readiness:task='t034'
if args.foundation:task='phase2-foundation'
pg = 'aat-' + task + '-pg-' + secrets.token_hex(4)
runner = 'aat-' + task + '-runner-' + secrets.token_hex(4)
network = 'aat-' + task + '-net-' + secrets.token_hex(4)
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
if args.api_foundation or args.operations:
    test_paths=['/tmp/tests/integration/test_phase2_'+('api' if args.api_foundation else 'operations')+'.py']
    log_path='docs/testing/t014-round2-logs/local-'+task+'-'+args.phase+'.log'
    if args.api_foundation:test_paths.append('/tmp/tests/unit/test_bootstrap_secrets.py')
if args.readiness:
    test_paths=['/tmp/tests/integration/test_foundation_ready.py']
    log_path='docs/testing/t014-round2-logs/local-t034-'+args.phase+'.log'
if args.foundation:
    test_paths=['/tmp/tests/integration/test_metadata_foundation.py','/tmp/tests/unit/test_authorization_states.py',
                '/tmp/tests/integration/test_authorization_repository.py','/tmp/tests/integration/test_phase2_repositories.py',
                '/tmp/tests/integration/test_phase2_operations.py','/tmp/tests/integration/test_phase2_api.py',
                '/tmp/tests/integration/test_foundation_ready.py']
    log_path='docs/testing/t014-round2-logs/local-phase2-foundation-'+args.phase+'.log'
ROOT = Path(__file__).resolve().parents[2]
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
    run('run', '-d', '--name', pg, '--network', network, '--memory', '256m',
        '--pids-limit', '256', '--tmpfs', '/var/lib/postgresql/data:rw,size=256m',
        '-e', 'POSTGRES_PASSWORD=' + password, '-e', 'POSTGRES_DB=app_metadata',
        '87507379f5ed1bca39a781c2f03da05f368e9f92b69c670e9a87cdf32cc9cf03')
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
    run('create', '--name', runner, '--network', network, '--memory', '512m',
        '-e', 'PYTHONPATH=/tmp/backend/src:/tmp/packages:/tmp',
        '-e', 'AAT_FOUNDATION_DISPOSABLE=1',
        '-e', 'AAT_APP_KEYRING=/tmp/aat-test-keyring',
        '-e', 'AAT_UPLOADS_ROOT=/tmp/aat-test-uploads',
        '-e', 'AAT_FOUNDATION_INITIALIZE=' + ('1' if args.authorization or args.operations or args.readiness else '0'),
        '-e', 'AAT_AIRFLOW_HEALTH_URL=http://aat-phase1-t014-local-20261109-airflow-apiserver-1:8080/api/v2/monitor/health',
        '-e', f'AAT_FOUNDATION_TEST_DSN=postgresql://postgres:{password}@{pg}/app_metadata',
        '--entrypoint', 'python', '89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4',
        '/tmp/prepare_keyring.py', '-p', 'no:cacheprovider', *test_paths, '-v', '--tb=short')
    created.append(runner)
    if args.readiness or args.foundation:
        # Connect only the disposable runner to the approved Airflow network for
        # read-only /monitor/health; existing containers/networks are unchanged.
        run('network','connect','aat-phase1-t014-local-20261109_aat_internal',runner)
    for source in ['tests', 'docker', 'backend', 'packages', 'samples', 'specs']:
        run('cp', str(ROOT / source), runner + ':/tmp/' + source)
    # Private synthetic keyring belongs only to this disposable runner. Product
    # initialization never regenerates missing persistent keys.
    run('cp', str(ROOT / 'tests/tools/prepare_foundation_keyring.py'), runner + ':/tmp/prepare_keyring.py')
    p = subprocess.run(['podman', 'start', '-a', runner], text=True, encoding='utf-8', capture_output=True)
    output = (p.stdout + p.stderr).replace(password, '[REDACTED]')
    if args.readiness or args.foundation:
        subprocess.run(['podman','cp',runner+':/tmp/aat-foundation-http.json',str(ROOT/'docs/testing/phase2-http-evidence.json')],capture_output=True)
    (ROOT / log_path).write_bytes(output.encode())
    exit_code = int(run('inspect', runner, '--format', '{{.State.ExitCode}}'))
    print(output[-6500:])
    result = {'postgres_image_id': run('inspect', pg, '--format', '{{.Image}}'),
              'runner_image_id': '89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4',
              'fixture': 'Disposable PostgreSQL17.11,tmpfs256MiB,no published ports,no existing volumes/secrets mounted',
              'task': task.upper(), 'test_paths': test_paths,
              'test_exit_code': exit_code, 'log': log_path,
              'existing_services_modified': False}
    (ROOT / ('docs/testing/' + task + '-fixture-results.json')).write_bytes((json.dumps(result, indent=2) + '\n').encode())
finally:
    for name in reversed(created):
        subprocess.run(['podman', 'rm', '-f', name], capture_output=True)

    if network_created:
        subprocess.run(['podman', 'network', 'rm', network], capture_output=True)

sys.exit(exit_code)
