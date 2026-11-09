"""Entrypoint setup only for explicit disposable PostgreSQL fixtures."""
import os
from pathlib import Path
import json
import sys
from uuid import uuid4
from cryptography.fernet import Fernet

if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable fixture required')
root=Path(os.environ['AAT_APP_KEYRING']);root.mkdir(mode=0o700)
key_id=uuid4().hex
(root/(key_id+'.key')).write_bytes(Fernet.generate_key())
(root/(key_id+'.key')).chmod(0o600)
(root/'current.json').write_text(json.dumps({'key_id':key_id}))
if os.environ.get('AAT_FOUNDATION_INITIALIZE')=='1':
    from docker.bootstrap.app_init import initialize
    initialize()
os.execv(sys.executable,[sys.executable,'-m','pytest',*sys.argv[1:]])
