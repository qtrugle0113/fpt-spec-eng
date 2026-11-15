"""Cập nhật SimpleAuthManager chỉ local, giữ account khác và backup trong secret store."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid


def merge_users(users: str) -> str:
    entries = [entry.strip() for entry in users.split(',') if entry.strip()]
    if any(len(entry.split(':')) not in (2, 3) for entry in entries):
        raise ValueError('Invalid SimpleAuthManager user configuration')
    return ','.join([entry for entry in entries if entry.split(':')[0] != 'admin'] + ['admin:admin'])


def _read(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not value or any(not isinstance(k, str) or not isinstance(v, str) or not v for k, v in value.items()):
        raise ValueError('Invalid password store; restore its backup')
    if 'aat_service' not in value or 'operator' not in value:
        raise ValueError('Required existing accounts missing; do not regenerate secrets')
    return value


def _atomic(path: Path, content: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix='.admin-update-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name, 0o400)
        if hasattr(os, 'geteuid') and os.geteuid() == 0: os.chown(name, 50000, 50000)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def configure(path: Path, *, local_demo: bool, reset: bool = False) -> dict:
    if not local_demo: raise ValueError('Explicit local/demo authorization required')
    value = _read(path)
    if 'admin' in value and not reset:
        return {'changed': False, 'other_accounts_unchanged': True}
    original = path.read_bytes()
    backup_root = path.parent / '.local-admin-backups'
    backup_root.mkdir(mode=0o700, exist_ok=True)
    backup_root.chmod(0o700)
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8]
    backup = backup_root / identity
    with backup.open('xb') as stream:
        stream.write(original); stream.flush(); os.fsync(stream.fileno())
    backup.chmod(0o400)
    updated = {**value, 'admin': 'admin'}
    _atomic(path, json.dumps(updated, sort_keys=True).encode())
    verified = _read(path)
    if any(verified.get(key) != password for key, password in value.items() if key != 'admin'):
        _atomic(path, original)
        raise RuntimeError('Other account verification failed; original restored')
    return {'changed': True, 'backup': identity, 'other_accounts_unchanged': True}


def restore(path: Path, identity: str, *, local_demo: bool) -> dict:
    if not local_demo: raise ValueError('Explicit local/demo authorization required')
    if not identity or Path(identity).name != identity or '/' in identity or '\\' in identity:
        raise ValueError('Invalid backup identifier')
    backup = path.parent / '.local-admin-backups' / identity
    _read(backup)
    _atomic(path, backup.read_bytes())
    return {'restored': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['ensure', 'reset', 'restore', 'users'])
    parser.add_argument('--password-file', type=Path, default=Path('/secrets/airflow/simple_auth_passwords.json'))
    parser.add_argument('--local-demo', action='store_true')
    parser.add_argument('--backup')
    parser.add_argument('--users', default='aat_service:admin,operator:admin')
    args = parser.parse_args()
    try:
        if args.operation == 'users':
            if not args.local_demo: raise ValueError('Local/demo authorization required')
            print(merge_users(args.users))
        elif args.operation == 'restore': print(json.dumps(restore(args.password_file, args.backup, local_demo=args.local_demo)))
        else: print(json.dumps(configure(args.password_file, local_demo=args.local_demo, reset=args.operation == 'reset')))
    except Exception as error:
        raise SystemExit('Local Airflow account operation failed (' + type(error).__name__ + '); values suppressed') from None
