"""Entrypoint setup only for explicit disposable PostgreSQL fixtures."""
import os
from pathlib import Path
import json
import sys
import hashlib
from uuid import uuid4
from cryptography.fernet import Fernet

if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable fixture required')
snapshot={}
for source_root in ('backend','etl_engine','packages','tests','docker','airflow'):
    for source in sorted((Path('/tmp')/source_root).rglob('*.py')):
        if not any(part in ('node_modules','__pycache__','.pytest_cache','build') for part in source.parts):
            snapshot[source.relative_to('/tmp').as_posix()]=hashlib.sha256(source.read_bytes()).hexdigest()
for relative in ('docker/mysql/samples.sql','docker/postgres/samples.sql','specs/001-airflow-automation-tool/contracts/openapi.yaml'):
    source=Path('/tmp')/relative
    snapshot[relative]=hashlib.sha256(source.read_bytes()).hexdigest()
Path('/tmp/aat-fixture-source-sha256.json').write_text(json.dumps(snapshot,sort_keys=True,indent=2))
if os.environ.get('AAT_TEST_ENGINE_WHEEL')=='1':
    import zipfile
    wheels=Path('/tmp/aat-fixture-wheels')
    if {wheel.name for wheel in wheels.iterdir()}!={'aat_metadata-0.1.0-py3-none-any.whl','aat_etl_engine-0.1.0-py3-none-any.whl'}:
        raise RuntimeError('Exactly the current metadata/engine wheel artifacts are required')
    installed=Path('/tmp/aat-fixture-installed');installed.mkdir()
    evidence={}
    for wheel in wheels.glob('*.whl'):
        evidence[wheel.name]=hashlib.sha256(wheel.read_bytes()).hexdigest()
        with zipfile.ZipFile(wheel) as archive:
            if any(Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name for name in archive.namelist()):
                raise RuntimeError('Unsafe wheel archive path')
            archive.extractall(installed)
    # Re-exec removes source paths and any modules loaded during build. Only
    # this disposable process uses the offline wheel extraction directory.
    Path('/tmp/aat-fixture-wheel-sha256.json').write_text(json.dumps(evidence,sort_keys=True,indent=2))
    os.environ['PYTHONPATH']='/tmp/aat-fixture-installed:/tmp/backend/src:/tmp/test-deps:/tmp'
    os.environ['AAT_TEST_ENGINE_WHEEL']='2'
    os.execv(sys.executable,[sys.executable,__file__,*sys.argv[1:]])
if os.environ.get('AAT_TEST_ENGINE_WHEEL')=='2':
    import aat_etl,aat_metadata
    if not all(Path(module.__file__).is_relative_to('/tmp/aat-fixture-installed') for module in (aat_etl,aat_metadata)):
        raise RuntimeError('Fixture is not executing the current built wheels')
    print('OFFLINE_WHEEL_EXECUTION '+Path('/tmp/aat-fixture-wheel-sha256.json').read_text(),flush=True)
root=Path(os.environ['AAT_APP_KEYRING']);root.mkdir(mode=0o700)
key_id=uuid4().hex
(root/(key_id+'.key')).write_bytes(Fernet.generate_key())
(root/(key_id+'.key')).chmod(0o600)
(root/'current.json').write_text(json.dumps({'key_id':key_id}))
if os.environ.get('AAT_FOUNDATION_INITIALIZE')=='1':
    from docker.bootstrap.app_init import initialize
    initialize()
runner='unittest' if os.environ.get('AAT_FOUNDATION_TEST_RUNNER')=='unittest' else 'pytest'
os.execv(sys.executable,[sys.executable,'-m',runner,*sys.argv[1:]])
