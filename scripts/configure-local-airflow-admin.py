"""Đặt/khôi phục admin cho đúng demo local đã ghi nhận; không sửa DB hoặc service secrets."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args, timeout=180):
    result = subprocess.run(['podman', *map(str, args)], cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=timeout)
    if result.returncode: raise RuntimeError('Podman operation failed: ' + str(args[0]) + '; values suppressed')
    return result.stdout.strip()


def document(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def snapshot(base):
    def get(path):
        with urlopen(base + '/api/v1' + path, timeout=40) as response: return json.load(response)
    data = {}
    for key, path, field in [('connections', '/connections?limit=50', 'id'), ('definitions', '/definition-uploads?limit=200', 'id'),
                             ('jobs', '/table-creation-jobs?limit=200', 'id'), ('files', '/files?limit=200', 'id'), ('dags', '/dags?limit=200', 'dag_id')]:
        # Chỉ giữ ID, không xuất nội dung connection/credential.
        page = get(path)
        values = list(page['items'])
        while page.get('next_offset') is not None:
            page = get(path + '&offset=' + str(page['next_offset'])); values.extend(page['items'])
        data[key] = sorted(str(item[field]) for item in values)
    data['runs'] = {}
    from urllib.parse import quote
    for dag in data['dags']:
        page = get('/dags/' + quote(dag, safe='') + '/runs?limit=200')
        values = list(page['items'])
        while page.get('next_offset') is not None:
            page = get('/dags/' + quote(dag, safe='') + '/runs?limit=200&offset=' + str(page['next_offset'])); values.extend(page['items'])
        data['runs'][dag] = sorted(item['run_id'] for item in values)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, default=ROOT / '.tools/local-demo.json')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    record = document(args.record)
    project = record['project']
    if not project.startswith('aat-') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in project):
        raise ValueError('Invalid local project')
    config_path = Path(record['compose_config']).resolve()
    if not config_path.is_relative_to(ROOT / '.tools'): raise ValueError('Local Compose config must stay in workspace .tools')
    public = urlsplit(record['airflow_url'])
    if public.scheme != 'http' or public.hostname not in ('localhost', '127.0.0.1') or not public.port:
        raise ValueError('Only an explicit local loopback Airflow URL is supported')
    container = project + '-airflow-apiserver-1'
    state = json.loads(run('inspect', container))[0]
    labels = state['Config']['Labels']
    if labels.get('com.docker.compose.project', labels.get('io.podman.compose.project')) != project:
        raise ValueError('Container project mismatch')
    bindings = state['HostConfig']['PortBindings'].get('8080/tcp', [])
    if not bindings or any(b['HostIp'] != '127.0.0.1' or int(b['HostPort']) != public.port for b in bindings):
        raise ValueError('Airflow must be published on the recorded loopback port only')
    mounts = {m['Destination']: m for m in state['Mounts']}
    secret_volume = mounts['/secrets/airflow']['Name']
    if not secret_volume.startswith(project + '_') or mounts['/secrets/airflow']['RW']:
        raise ValueError('Unexpected Airflow secret volume')
    config = document(config_path)
    if config['name'] != project: raise ValueError('Compose project mismatch')
    backend_url = 'http://127.0.0.1:' + str(next(b['HostPort'] for b in json.loads(run('inspect', project + '-backend-1'))[0]['HostConfig']['PortBindings']['8000/tcp']))
    probe = "import json,airflow; from airflow.configuration import conf; print(json.dumps(dict(version=airflow.__version__,manager=conf.get('core','auth_manager'),users=conf.get('core','simple_auth_manager_users'),all_admins=conf.getboolean('core','simple_auth_manager_all_admins'))))"
    auth = json.loads(run('exec', container, 'python', '-c', probe).splitlines()[-1])
    if not auth['manager'].endswith('.SimpleAuthManager') or auth['all_admins']:
        raise ValueError('Expected authenticated SimpleAuthManager')
    before = snapshot(backend_url)
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
    folder = ROOT / '.tools/local-admin-migrations' / identity
    folder.mkdir(parents=True, mode=0o700)
    backup_config = folder / 'compose.before.json'
    backup_config.write_bytes(config_path.read_bytes())
    helper = project + '-admin-helper-' + uuid.uuid4().hex[:8]
    receipt = {'project': project, 'airflow_version': auth['version'], 'secret_volume': secret_volume,
               'image_unchanged': state['Image'], 'before': before,
               'volume_ids': {target: mount['Name'] for target, mount in mounts.items() if mount['Type'] == 'volume'},
               'compose_backup': str(backup_config.relative_to(ROOT)), 'status': 'PREPARED'}
    operation = 'restore' if args.restore else 'reset'
    command = ['--password-file', '/secrets/airflow/simple_auth_passwords.json', '--local-demo']
    if args.restore:
        old = document(args.restore)
        if old['project'] != project or old['secret_volume'] != secret_volume: raise ValueError('Restore project mismatch')
        old_config = (ROOT / old['compose_backup']).resolve()
        if not old_config.is_relative_to(ROOT / '.tools/local-admin-migrations'): raise ValueError('Invalid restore config path')
        command += ['--backup', old['secret_backup']]
    try:
        image = config['services']['secrets-init']['image']
        run('create', '--name', helper, '--network=none', '--user=0:0', '--memory=128m', '-v', secret_volume + ':/secrets/airflow', '--entrypoint=python', image, '/tmp/local_admin.py', operation, *command)
        run('cp', ROOT / 'docker/bootstrap/local_airflow_admin.py', helper + ':/tmp/local_admin.py')
        result = json.loads(run('start', '-a', helper).splitlines()[-1])
        receipt['secret_backup'] = result.get('backup')
        receipt['other_accounts_unchanged'] = result.get('other_accounts_unchanged', True)
        if args.restore:
            config_path.write_bytes(old_config.read_bytes())
        else:
            from sys import path
            path.insert(0, str(ROOT))
            from docker.bootstrap.local_airflow_admin import merge_users
            for name, service in config['services'].items():
                if name.startswith('airflow-'):
                    environment = service.setdefault('environment', {})
                    environment['AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS'] = merge_users(environment.get('AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS', auth['users']))
                    environment['AAT_LOCAL_DEMO_AUTH'] = '1'
                if name == 'secrets-init': service.setdefault('environment', {})['AAT_LOCAL_DEMO_AUTH'] = '1'
            temporary = config_path.with_suffix('.admin-update.json')
            temporary.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
            os.replace(temporary, config_path)
        os.environ['PODMAN_COMPOSE_PROVIDER'] = str(ROOT / '.tools/docker-compose-5.6.0.exe')
        run('compose', '-f', config_path, '-p', project, 'config', '--quiet')
        run('compose', '-f', config_path, '-p', project, 'up', '-d', '--no-build', '--no-deps', '--force-recreate', 'airflow-apiserver')
        token_ok = False
        for attempt in range(60):
            try:
                if args.restore:
                    with urlopen(record['airflow_url'] + '/api/v2/monitor/health', timeout=5) as response: token_ok = response.status == 200
                else:
                    request = Request(record['airflow_url'] + '/auth/token', data=json.dumps({'username': 'admin', 'password': 'admin'}).encode(), headers={'Content-Type': 'application/json'})
                    with urlopen(request, timeout=5) as response: token_ok = bool(json.load(response).get('access_token'))
                if token_ok: break
            except Exception: time.sleep(2)
        if not token_ok: raise RuntimeError('Airflow login/readiness failed; use recorded backup to restore')
        after = snapshot(backend_url)
        current = json.loads(run('inspect', container))[0]
        receipt['after'] = after
        receipt['data_ids_unchanged'] = before == after
        receipt['volumes_unchanged'] = receipt['volume_ids'] == {m['Destination']: m['Name'] for m in current['Mounts'] if m['Type'] == 'volume'}
        receipt['image_unchanged'] = state['Image'] == current['Image']
        if not all(receipt[key] for key in ('data_ids_unchanged', 'volumes_unchanged', 'image_unchanged', 'other_accounts_unchanged')):
            raise RuntimeError('Preservation verification failed; inspect receipt and restore backup')
        receipt['status'] = 'RESTORED' if args.restore else 'UPDATED_LOGIN_VERIFIED'
    except Exception:
        receipt['status'] = 'FAILED_BACKUP_RETAINED'
        raise
    finally:
        (folder / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        try: run('rm', helper)
        except RuntimeError: pass
    print(json.dumps({'status': receipt['status'], 'receipt': str((folder / 'receipt.json').relative_to(ROOT)), 'data_ids_unchanged': receipt['data_ids_unchanged'], 'volumes_unchanged': receipt['volumes_unchanged']}))


if __name__ == '__main__':
    try: main()
    except Exception as error: raise SystemExit('Local admin migration failed (' + type(error).__name__ + '): ' + str(error)) from None
