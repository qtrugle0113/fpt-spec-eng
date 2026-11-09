"""Prepare public browser workbooks with an explicitly reviewed dependency image."""
import argparse
from pathlib import Path
import secrets
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
name='aat-table-public-fixtures-'+secrets.token_hex(4)

def run(*arguments):
    result=subprocess.run(['podman',*arguments],cwd=root,capture_output=True,text=True)
    if result.returncode:raise RuntimeError('Public workbook fixture preparation failed.')
    return result.stdout

try:
    run('create','--name',name,'--network=none','--entrypoint','python',args.image,'/tmp/make_table_fixtures.py')
    run('cp',str(root/'samples/definitions'),name+':/tmp/aat-table-fixture-source')
    run('cp',str(root/'tests/tools/make_table_fixtures.py'),name+':/tmp/make_table_fixtures.py')
    run('start','-a',name)
    (root/'.tools/table-e2e-fixtures').mkdir(exist_ok=True)
    run('cp',name+':/tmp/aat-table-fixtures/.',str(root/'.tools/table-e2e-fixtures'))
    print('Public TABLE fixtures prepared')
finally:
    subprocess.run(['podman','rm','-f',name],capture_output=True)
