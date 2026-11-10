"""Inspect packaged bytes without executing unreviewed candidate runtime images."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);args=parser.parse_args()
manifest_path=(ROOT/args.manifest).resolve()
if not manifest_path.is_relative_to(ROOT):parser.error('Manifest must stay in workspace')
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
artifact=ROOT/'.tools'/('phase6-packaged-'+manifest['run_id']);artifact.mkdir(parents=True,exist_ok=True)
records=[]
packages={'aat_api':ROOT/'backend/src/aat_api','aat_etl':ROOT/'etl_engine/src/aat_etl','aat_metadata':ROOT/'packages/aat_metadata'}
for target in ('backend','airflow','frontend'):
    row=next(item for item in manifest['images'] if item['name']==target)
    name='aat-package-inspect-'+secrets.token_hex(4)
    def run(*command):subprocess.run(['podman',*command],check=True,capture_output=True,timeout=120)
    destination=artifact/target;destination.mkdir(exist_ok=True)
    try:
        run('create','--name',name,'--network','none','--entrypoint','/bin/true',row['image_id'])
        run('cp',name+(':/usr/share/nginx/html/.' if target=='frontend' else ':/wheels/.'),str(destination))
        verified={}
        if target!='frontend':
            for wheel in destination.glob('*.whl'):
                with zipfile.ZipFile(wheel) as archive:
                    for package,source in packages.items():
                        names={item for item in archive.namelist() if item.startswith(package+'/') and (item.endswith(('.py','.json')) or item.endswith('/py.typed'))}
                        if not names:continue
                        expected={package+'/'+path.relative_to(source).as_posix():path for path in source.rglob('*')
                            if path.is_file() and (path.suffix in ('.py','.json') or path.name=='py.typed')
                            and not any(part in path.parts for part in ('__pycache__','build'))}
                        if set(expected)!=names or any(archive.read(key)!=path.read_bytes() for key,path in expected.items()):
                            raise RuntimeError('Packaged source differs from workspace: '+target+'/'+package)
                        verified[package]=len(names)
            required={'aat_api','aat_metadata','aat_etl'} if target=='backend' else {'aat_metadata','aat_etl'}
            if set(verified)!=required:raise RuntimeError('Required runtime wheel payload missing')
        records.append({'target':target,'image_id':row['image_id'],'payload_files_verified':verified,
                        'artifact_sha256':{path.relative_to(destination).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in destination.rglob('*') if path.is_file()}})
    finally:subprocess.run(['podman','rm','-f',name],capture_output=True)
result={'status':'PASS','candidate_runtime_executed':False,'existing_services_modified':False,
        'artifact_dir':str(artifact.relative_to(ROOT)),'images':records}
(manifest_path.parent/'packaged-source.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','candidate_runtime_executed':False,'payloads':[{row['target']:row['payload_files_verified']} for row in records]}))
