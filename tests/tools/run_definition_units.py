"""Chạy unit Definition/auth trên dependency image hiện hữu, không network/secret/volume demo."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import uuid

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    output=(ROOT/args.evidence).resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Evidence must stay in workspace')
    suffix=uuid.uuid4().hex[:8]
    source=ROOT/'.tools'/('definition-unit-source-'+suffix)
    source.mkdir(parents=True)
    for folder in ('backend','packages','docker','templates','samples','specs'):
        shutil.copytree(ROOT/folder,source/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/'frontend/src',source/'frontend/src')
    shutil.copytree(ROOT/'tests/unit',source/'tests/unit',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'tests/__init__.py',source/'tests/__init__.py')
    shutil.copy2(ROOT/'.gitattributes',source/'.gitattributes')
    name='aat-definition-unit-'+suffix
    def run(*command):
        process=subprocess.run(['podman',*map(str,command)],capture_output=True,text=True,encoding='utf-8',timeout=180)
        if process.returncode:raise RuntimeError('Unit runner command failed: '+str(command[0]))
        return process
    tests=['test_local_airflow_admin','test_bootstrap_secrets','test_definition_terminology','test_sample_artifacts','test_table_workbook','test_etl_workbook']
    run('create','--name',name,'--network=none','--memory=512m','--entrypoint=python',
        '-e','PYTHONPATH=/tmp/aat-feature003/backend/src:/tmp/aat-feature003/packages:/tmp/aat-feature003',
        '-w','/tmp/aat-feature003',args.image,'-m','unittest',*['tests.unit.'+test for test in tests])
    try:
        run('cp',source,name+':/tmp/aat-feature003')
        result=subprocess.run(['podman','start','-a',name],capture_output=True,text=True,encoding='utf-8',timeout=180)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(result.stdout+result.stderr,encoding='utf-8')
        print(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Definition/auth unit tests failed')
    finally:run('rm',name)


if __name__=='__main__':main()
