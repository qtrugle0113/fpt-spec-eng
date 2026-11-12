"""Build portable local artifacts from Compose and record immutable evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-candidate', help='Optional previously built source snapshot manifest')
    parser.add_argument('--output', default='.tools/local-images.json')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT): parser.error('Output must stay in workspace')
    run_id = secrets.token_hex(4)
    evidence = ROOT / 'docs/testing/resume-20261111' / ('portable-' + run_id)
    context = ROOT / '.tools' / ('portable-source-' + run_id)
    evidence.mkdir(parents=True)
    context.mkdir(parents=True)
    def ignore(_, names):
        return [n for n in names if n in ('node_modules','dist','build','__pycache__','.pytest_cache','test-results','playwright-report') or n.endswith('.egg-info')]
    for name in ('backend','frontend','packages','etl_engine','airflow','docker','tests','samples','templates','specs'):
        shutil.copytree(ROOT / name, context / name, ignore=ignore)
    for name in ('docker-compose.yml','.dockerignore','.gitattributes','.env.example'):
        shutil.copy2(ROOT / name, context / name)
    snapshot = {p.relative_to(context).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in context.rglob('*') if p.is_file()}
    (evidence / 'source-sha256.json').write_text(json.dumps(snapshot, indent=2)+'\n', encoding='utf-8')
    environment = dict(os.environ)
    environment['PODMAN_COMPOSE_PROVIDER'] = str(ROOT / '.tools/docker-compose-5.6.0.exe')
    def run(command, **kwargs):
        return subprocess.check_output(command, cwd=context, env=environment, text=True, encoding='utf-8', **kwargs).strip()
    config = json.loads(run(['podman','compose','-f',str(context/'docker-compose.yml'),'--profile','test','config','--format','json']))
    reuse = {}
    previous = {}
    if args.reuse_candidate:
        candidate = (ROOT / args.reuse_candidate).resolve()
        if not candidate.is_relative_to(ROOT): parser.error('Candidate must stay in workspace')
        reuse = {r['name']:r for r in json.loads(candidate.read_text(encoding='utf-8'))['images']}
        previous = json.loads((candidate.parent/'source-sha256.json').read_text(encoding='utf-8'))
    rows = []
    manifest = {'phase':'portable','run_id':run_id,'source_context':str(context.relative_to(ROOT)),
        'captured_at':datetime.now(timezone.utc).isoformat(), 'images':rows,
        'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
        'environment':json.loads(run(['podman','version','--format','json'])),
        'compose_version':run(['podman','compose','version']),
        'existing_services_modified':False,'acceptance':'PENDING_SCAN_POLICY_CHECK'}
    stages = [('backend-wheels','backend','wheels'),('backend','backend',None),
        ('airflow-wheels','airflow-scheduler','wheels'),('airflow','airflow-scheduler',None),
        ('frontend-build','frontend','build'),('frontend','frontend',None),
        ('backend-tests','backend-tests',None),('e2e-tests','e2e-tests',None),
        ('postgres','postgres','postgres'),('mysql','mysql','mysql')]
    for name, service, target in stages:
        build = config['services'][service]['build']
        dockerfile = build['dockerfile']
        if name.startswith('frontend'):prefixes=('frontend/','docker/nginx/')
        elif name.startswith('airflow'):prefixes=('airflow/','packages/','etl_engine/','docker/bootstrap/health.py')
        elif name in ('postgres','mysql'):prefixes=('docker/gosu/',)
        elif name=='e2e-tests':prefixes=('tests/e2e/','docker/tests/playwright.Dockerfile','docker/tests/os-packages.lock')
        elif name=='backend-tests':prefixes=('backend/','frontend/','packages/','etl_engine/','airflow/',
            'docker/','tests/','samples/','templates/','specs/','docker-compose.yml')
        else:prefixes=('backend/','packages/','etl_engine/','docker/','airflow/dags/aat_wrapper_template.py',
            'samples/','templates/','specs/001-airflow-automation-tool/contracts/design-validation.json')
        prefixes+=('.dockerignore','.gitattributes')
        relevant = {k:v for k,v in snapshot.items() if k.startswith(prefixes)}
        old = reuse.get(name)
        reused = bool(old and relevant and all(previous.get(k)==v for k,v in relevant.items())
                      and {k for k in previous if k.startswith(prefixes)}==set(relevant))
        if reused:
            inspected = subprocess.run(['podman','image','inspect',old['image_id'],'--format','{{.Id}}'],capture_output=True,text=True)
            reused = inspected.returncode==0 and inspected.stdout.strip()==old['image_id']
        reference = old['image_id'] if reused else 'localhost/aat-portable-'+name+'-'+run_id+':0.1.0'
        command = ['podman','build','--memory','1g','-f',dockerfile,'-t',reference]
        if target: command += ['--target',target]
        command += ['.']
        if not reused:
            print('BUILD_START '+name, flush=True)
            with (evidence/(name+'-build.log')).open('w',encoding='utf-8') as log:
                subprocess.run(command,cwd=context,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
        identity = run(['podman','image','inspect',reference,'--format','{{.Id}}'])
        rows.append({'name':name,'ref':reference,'image_id':identity,'dockerfile':dockerfile,'target':target,
                     'build':'REUSED_VERIFIED_SOURCE' if reused else 'PASS','command':None if reused else command})
        (evidence/'candidate-images.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        print(('REUSE_PASS ' if reused else 'BUILD_PASS ')+name+' '+identity, flush=True)
    images = {r['name']:r['image_id'] for r in rows}
    selected = {k:images[v] for k,v in {'backend':'backend','frontend':'frontend','airflow':'airflow',
        'postgres':'postgres','mysql':'mysql','tests':'backend-tests','e2e':'e2e-tests','workbook_deps':'backend'}.items()}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(selected,indent=2)+'\n',encoding='utf-8')
    (output.parent/(output.stem+'-provenance.json')).write_text(json.dumps({'manifest':str((evidence/'candidate-images.json').relative_to(ROOT)),
        'source_sha256':str((evidence/'source-sha256.json').relative_to(ROOT)),'security':'PENDING_SCAN_POLICY_CHECK'},indent=2)+'\n',encoding='utf-8')
    print('MANIFEST '+str((evidence/'candidate-images.json').relative_to(ROOT)),flush=True)


if __name__ == '__main__': main()
