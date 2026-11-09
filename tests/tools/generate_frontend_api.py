"""Chạy codegen bằng dependency OpenAPI đã pin trong Airflow image."""
import argparse
from pathlib import Path
import secrets
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
name='aat-api-codegen-'+secrets.token_hex(4)
def run(*command):
    result=subprocess.run(['podman',*command],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise RuntimeError('Codegen command failed: '+command[0])
try:
    run('create','--name',name,'--network=none','--memory','256m','--entrypoint','python',args.image,
        '/tmp/generate-api.py','/tmp/openapi.yaml','/tmp/api.generated.ts')
    run('cp',str(root/'frontend/scripts/generate-api.py'),name+':/tmp/generate-api.py')
    run('cp',str(root/'specs/001-airflow-automation-tool/contracts/openapi.yaml'),name+':/tmp/openapi.yaml')
    run('start','-a',name)
    if subprocess.check_output(['podman','inspect',name,'--format','{{.State.ExitCode}}'],text=True).strip()!='0':
        raise RuntimeError('OpenAPI code generation failed')
    target=root/'frontend/src/lib/api.generated.ts';target.parent.mkdir(parents=True,exist_ok=True)
    run('cp',name+':/tmp/api.generated.ts',str(target))
finally:subprocess.run(['podman','rm','-f',name],capture_output=True)
