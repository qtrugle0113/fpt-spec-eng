"""Build distinct review candidates; never retag existing approved images."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
records=[]
targets=[('backend-wheels','backend/Dockerfile','wheels','aat-backend-wheels-phase2-candidate'),
         ('backend','backend/Dockerfile',None,'aat-backend-phase2-candidate'),
         ('backend-test-wheels','docker/tests/Dockerfile','wheels','aat-backend-test-wheels-phase2-candidate'),
         ('backend-tests','docker/tests/Dockerfile',None,'aat-backend-tests-phase2-candidate')]
for name,dockerfile,target,tag in targets:
    reference='localhost/'+tag+':0.1.0'
    command=['podman','build','--memory=1g','-f',dockerfile,'-t',reference]
    if target:command+=['--target',target]
    command+=['.']
    print('BUILD_START '+name,flush=True)
    path=ROOT/('docs/testing/t014-round2-logs/phase2-build-'+name+'.log')
    with path.open('w',encoding='utf-8') as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Candidate build failed: '+name+'; inspect '+str(path))
    identity=subprocess.check_output(['podman','image','inspect',reference,'--format','{{.Id}}'],text=True).strip()
    records.append({'name':name,'ref':reference,'image_id':identity,'dockerfile':dockerfile,'target':target,'build':'PASS','log':str(path.relative_to(ROOT))})
    (ROOT/'docs/testing/phase2-candidate-images.json').write_bytes((json.dumps({'captured_at':datetime.now(timezone.utc).isoformat(),
        'baseline_acceptance':'PENDING_EXACT_FINDINGS_REVIEW','images':records},indent=2)+'\n').encode())
    print('BUILD_PASS '+name+' '+identity,flush=True)
