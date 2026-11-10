"""Freeze source and build distinct review candidates without starting app services."""
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--phase',choices=['phase6','phase7','phase8'],default='phase6')
args=parser.parse_args()
run_id=secrets.token_hex(4)
context=ROOT/'.tools'/(args.phase+'-source-'+run_id)
evidence=ROOT/('docs/testing/resume-20261111' if args.phase!='phase6' else 'docs/testing/resume-20261110')/(args.phase+'-candidates-'+run_id)
context.mkdir(parents=True);evidence.mkdir(parents=True)


def ignore(folder,names):
    return [name for name in names if name in ('node_modules','dist','build','__pycache__','.pytest_cache','test-results','playwright-report') or name.endswith('.egg-info')]


for name in ('backend','frontend','packages','etl_engine','airflow','docker','tests','samples','templates','specs'):
    shutil.copytree(ROOT/name,context/name,ignore=ignore)
for name in ('docker-compose.yml','.dockerignore','.gitattributes','.env.example'):
    shutil.copy2(ROOT/name,context/name)
snapshot={}
for path in context.rglob('*'):
    if path.is_file():
        relative=path.relative_to(context)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest():raise RuntimeError('Source snapshot changed during preparation')
        snapshot[relative.as_posix()]=actual
(evidence/'source-sha256.json').write_text(json.dumps(snapshot,indent=2,sort_keys=True)+'\n',encoding='utf-8')
manifest={'captured_at':datetime.now(timezone.utc).isoformat(),'run_id':run_id,'phase':args.phase,'source_context':str(context.relative_to(ROOT)),
          'acceptance':'PENDING_EXACT_IMAGE_REVIEW','existing_services_modified':False,'images':[]}
targets=[('backend-wheels','backend/Dockerfile','wheels'),('backend','backend/Dockerfile',None),
         ('airflow-wheels','airflow/docker/Dockerfile','wheels'),('airflow','airflow/docker/Dockerfile',None),
         ('frontend-build','frontend/Dockerfile','build'),('frontend','frontend/Dockerfile',None)]
for name,dockerfile,target in targets:
    reference='localhost/aat-'+args.phase+'-'+name+'-'+run_id+':0.1.0'
    command=['podman','build','--memory','1g','-f',dockerfile,'-t',reference]
    if target:command+=['--target',target]
    command+=['.']
    print('BUILD_START '+name,flush=True)
    path=evidence/(name+'-build.log')
    with path.open('w',encoding='utf-8') as log:
        checked=subprocess.run(command,cwd=context,stdout=log,stderr=subprocess.STDOUT)
    if checked.returncode:raise RuntimeError('Candidate build failed: '+name+'; inspect '+str(path.relative_to(ROOT)))
    identity=subprocess.check_output(['podman','image','inspect',reference,'--format','{{.Id}}'],text=True).strip()
    manifest['images'].append({'name':name,'ref':reference,'image_id':identity,'target':target,
                               'dockerfile':dockerfile,'build':'PASS','log':str(path.relative_to(ROOT))})
    (evidence/'candidate-images.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('BUILD_PASS '+name+' '+identity,flush=True)
print('CANDIDATE_MANIFEST '+str((evidence/'candidate-images.json').relative_to(ROOT)),flush=True)
