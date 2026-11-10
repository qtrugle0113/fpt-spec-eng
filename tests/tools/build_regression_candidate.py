"""Freeze and build the test-only candidate; never start unreviewed images."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
identity=secrets.token_hex(4)
context=ROOT/'.tools'/('regression-source-'+identity)
evidence=ROOT/'docs/testing/resume-20261111'/('regression-candidate-'+identity)
context.mkdir();evidence.mkdir(parents=True)
def ignore(_,names):
    return [name for name in names if name in ('node_modules','dist','build','__pycache__','.pytest_cache','test-results','playwright-report') or name.endswith('.egg-info')]
for folder in ('backend','packages','etl_engine','docker','airflow','frontend','specs','samples','templates','tests'):
    shutil.copytree(ROOT/folder,context/folder,ignore=ignore)
for filename in ('.gitattributes','.dockerignore','docker-compose.yml'):
    shutil.copy2(ROOT/filename,context/filename)
snapshot={p.relative_to(context).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in context.rglob('*') if p.is_file()}
(evidence/'source-sha256.json').write_text(json.dumps(snapshot,indent=2,sort_keys=True)+'\n')
reference='localhost/aat-regression-candidate-'+identity+':0.1.0'
with (evidence/'build.log').open('w',encoding='utf-8') as log:
    checked=subprocess.run(['podman','build','--memory','1g','-f','docker/tests/Dockerfile','-t',reference,'.'],cwd=context,stdout=log,stderr=subprocess.STDOUT)
result={'captured_at':datetime.now(timezone.utc).isoformat(),'source_context':str(context.relative_to(ROOT)),
        'ref':reference,'build_exit_code':checked.returncode,'status':'BUILT_PENDING_REVIEW' if checked.returncode==0 else 'FAIL',
        'candidate_runtime_executed':False,'existing_services_modified':False}
if checked.returncode==0:result['image_id']=subprocess.check_output(['podman','image','inspect',reference,'--format','{{.Id}}'],text=True).strip()
(evidence/'candidate.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(checked.returncode)
