"""Host wrapper to freeze schema on an approved, network-disabled test image."""
from pathlib import Path
import secrets
import subprocess

ROOT=Path(__file__).resolve().parents[2]
name='aat-phase2-schema-'+secrets.token_hex(4)
def run(*args):return subprocess.check_output(['podman',*args],text=True,encoding='utf-8').strip()
try:
    run('create','--name',name,'--network=none','-e','PYTHONPATH=/tmp/packages','--entrypoint','python',
        '89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4','/tmp/tests/tools/freeze_metadata_schema.py')
    for source in ['packages','tests','backend']:run('cp',str(ROOT/source),name+':/tmp/'+source)
    print(run('start','-a',name))
    if run('inspect',name,'--format','{{.State.ExitCode}}')!='0':raise RuntimeError('Schema freeze failed')
    run('cp',name+':/tmp/backend/alembic/versions/0001_metadata.py',str(ROOT/'backend/alembic/versions/0001_metadata.py'))
finally:run('rm','-f',name)
