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
result = {'published_ports': False, 'existing_services_modified': False,
          'fixture_network': network, 'status': 'NOT_RUN'}


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
        run('run', '-d', '--name', name, '--network', network, '--memory', memory,
            *options, '--entrypoint', 'python', args.airflow_image, '-c', launch, command)
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
    common = ['--postgres-image', args.postgres_image, '--runner-image', args.runner_image,
              '--airflow-network', network, '--airflow-health-url',
              'http://'+api+':8080/api/v2/monitor/health', '--evidence-dir', args.evidence_dir]
    for selector in ([] if args.profile_only else ['--readiness', '--foundation']):
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
    result['cleanup_exit_codes'] = cleanup
    (evidence/'airflow-fixture-results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
