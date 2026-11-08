"""Khởi tạo secret một lần; không log giá trị hoặc tự thay secret đã mất."""

import json
import os
from pathlib import Path
import uuid

from cryptography.fernet import Fernet


def initialize(root: Path) -> None:
    domains = ('bootstrap_secrets', 'backend_secrets', 'airflow_secrets', 'runtime_secrets', 'app_keyring', 'postgres_secrets', 'mysql_secrets')
    for domain in domains:
        (root / domain).mkdir(parents=True, exist_ok=True, mode=0o700)
    state = root / 'bootstrap_secrets' / 'initialized.json'
    if state.exists():
        expected = json.loads(state.read_text())
        if any(not (root / filename).is_file() for filename in expected):
            raise RuntimeError('Persistent secret missing; restore original secret volumes, do not regenerate')
        key_id = json.loads((root / 'app_keyring/current.json').read_text())['key_id']
        key = (root / 'app_keyring' / f'{key_id}.key').read_bytes()
        if Fernet(key).decrypt((root / 'bootstrap_secrets/key_probe').read_bytes()) != b'bootstrap':
            raise RuntimeError('Persistent encryption key verification failed')
        return

    def write(domain: str, filename: str, value: str) -> str:
        path = root / domain / filename
        if not path.exists():
            with path.open('x', encoding='utf-8') as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            path.chmod(0o400)
        return path.read_text()

    pg_admin = write('bootstrap_secrets', 'postgres_admin', os.urandom(32).hex())
    mysql_admin = write('bootstrap_secrets', 'mysql_admin', os.urandom(32).hex())
    write('postgres_secrets', 'postgres_admin', pg_admin)
    write('mysql_secrets', 'mysql_admin', mysql_admin)
    # Giữ domain riêng; không mount admin credential vào backend/Airflow.
    for filename in ('app_owner', 'app_runtime', 'pg_etl', 'mysql_etl'):
        value = write('bootstrap_secrets', filename, os.urandom(32).hex())
        if filename != 'app_owner':
            write('backend_secrets', filename, value)
        if filename == 'app_runtime':
            write('runtime_secrets', filename, value)
    airflow_db = write('bootstrap_secrets', 'airflow_db', os.urandom(32).hex())
    write('airflow_secrets', 'airflow_db', airflow_db)
    for filename in ('jwt_secret', 'fernet_key', 'service_password', 'operator_password'):
        value = Fernet.generate_key().decode() if filename == 'fernet_key' else os.urandom(32).hex()
        write('airflow_secrets', filename, value)
    write('backend_secrets', 'airflow_service_password', (root / 'airflow_secrets/service_password').read_text())
    write('airflow_secrets', 'simple_auth_passwords.json', json.dumps({
        'aat_service': (root / 'airflow_secrets/service_password').read_text(),
        'operator': (root / 'airflow_secrets/operator_password').read_text(),
    }))
    token = write('runtime_secrets', 'runtime_token', os.urandom(32).hex())
    write('backend_secrets', 'runtime_token', token)
    current = root / 'app_keyring/current.json'
    key_id = json.loads(current.read_text())['key_id'] if current.exists() else uuid.uuid4().hex
    write('app_keyring', f'{key_id}.key', Fernet.generate_key().decode())
    write('app_keyring', 'current.json', json.dumps({'key_id': key_id}))
    # Probe ciphertext độc lập với DB; product schema/key-loss guard ở T030/T034.
    write('bootstrap_secrets', 'key_probe', Fernet((root / f'app_keyring/{key_id}.key').read_bytes()).encrypt(b'bootstrap').decode())
    files = sorted(str(p.relative_to(root)) for domain in domains for p in (root / domain).iterdir() if p.is_file())
    write('bootstrap_secrets', 'initialized.json', json.dumps(files))


if __name__ == '__main__':
    try:
        root = Path(os.environ.get('AAT_SECRET_ROOT', '/secrets'))
        initialize(root)
        for domain in root.iterdir():
            if domain.is_dir():
                os.chown(domain, 50000, 50000)
                domain.chmod(0o700)
                for path in domain.iterdir():
                    os.chown(path, 50000, 50000)
                    path.chmod(0o400)
        print('Bootstrap secrets initialized; values suppressed')
    except Exception as exc:
        raise SystemExit(f'Secret initialization failed ({type(exc).__name__}); restore persistent secret volumes; values suppressed')
