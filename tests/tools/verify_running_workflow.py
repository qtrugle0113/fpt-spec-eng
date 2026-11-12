"""Run the real browser workflow on an explicitly selected owned local stack."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]


def verify(project,base_url,airflow_url,evidence,images_path=None):
    if not re.fullmatch(r'aat-(?:t140|portable-demo)-[0-9a-f]{8}',project):
        raise ValueError('Only an explicit owned local namespace is supported')
    for url in (base_url,airflow_url):
        parsed=urlsplit(url)
        if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1') or parsed.path not in ('','/') or parsed.username or parsed.query or parsed.fragment:
            raise ValueError('Only loopback application URLs are supported')
    evidence=evidence.resolve()
    if not evidence.is_relative_to(ROOT):raise ValueError('Evidence must stay in workspace')
    evidence.mkdir(parents=True,exist_ok=True)
    images_path=(images_path or ROOT/'.tools/local-images.json').resolve()
    if not images_path.is_relative_to(ROOT):raise ValueError('Image manifest must stay in workspace')
    images=json.loads(images_path.read_text())
    browser='aat-running-workflow-'+secrets.token_hex(4)
    backend=project+'-backend-1'
    values=[]
    result={'status':'NOT_RUN','project':project,'base_url':base_url,'airflow_url':airflow_url,
            'application_source_overlay':False,'sample_namespace':'full_<desktop|mobile>_<timestamp>',
            'sample_data_retained':True,'test_source_sha256':{}}
    def run(command,check=True,input=None,timeout=180):
        process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',input=input,timeout=timeout)
        if check and process.returncode:raise RuntimeError('Owned workflow command failed; inspect evidence')
        return process
    def safe(value):
        for secret in values:value=value.replace(secret,'[REDACTED]')
        return value
    created=False
    try:
        preflight=run(['python','-X','utf8','tests/tools/run_regression.py','--group','e2e','--preflight-only',
                      '--images',str(images_path.relative_to(ROOT)),
                      '--evidence-dir',str((evidence/'policy-preflight').relative_to(ROOT))])
        for service,kind in (('backend','backend'),('frontend','frontend'),('airflow-apiserver','airflow')):
            actual=run(['podman','inspect',project+'-'+service+'-1','--format','{{.Image}}']).stdout.strip()
            if actual.removeprefix('sha256:')!=images[kind].removeprefix('sha256:'):
                raise RuntimeError('Running application differs from reviewed local artifact')
        run(['podman','run','-d','--name',browser,'--network','host','--memory','768m','--cpus','2',
             '-e','PLAYWRIGHT_BASE_URL='+base_url,'-e','AIRFLOW_EXPECTED_ORIGIN='+airflow_url,
             images['e2e'],'sleep','infinity'])
        created=True
        credentials=json.loads(run(['podman','exec',backend,'python','-c',
            "import json,pathlib;print(json.dumps({'pg_etl':pathlib.Path('/secrets/backend/pg_etl').read_text()}))"]).stdout)
        values.extend(credentials.values())
        install="const fs=require('node:fs');fs.mkdirSync('/run/aat-e2e',{mode:0o700});for(const [k,v] of Object.entries(JSON.parse(fs.readFileSync(0,'utf8'))))fs.writeFileSync('/run/aat-e2e/'+k,v,{mode:0o400});"
        run(['podman','exec','-i',browser,'node','-e',install],input=json.dumps(credentials))
        libraries=ROOT/'.tools'/(browser+'-workbook-libs')
        libraries.mkdir(exist_ok=True)
        root=run(['podman','exec',backend,'python','-c',"import sysconfig;print(sysconfig.get_paths()['purelib'])"]).stdout.strip()
        for name in ('openpyxl','et_xmlfile','defusedxml'):
            run(['podman','cp',backend+':'+root+'/'+name,str(libraries/name)])
        result['workbook_library_sha256']={str(p.relative_to(libraries)):hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in libraries.rglob('*') if p.is_file()}
        run(['podman','cp',str(libraries),browser+':/tests/workbook-libs'])
        for source,destination in [('tests/tools/make_full_workflow.py','make_full_workflow.py'),
                                   ('samples/data/customers.csv','full-customers.csv'),
                                   ('tests/e2e/playwright.config.ts','playwright.config.ts'),
                                   ('tests/e2e/full_workflow.spec.ts','full_workflow.spec.ts'),
                                   ('tests/e2e/bootstrap.spec.ts','bootstrap.spec.ts')]:
            result['test_source_sha256'][source]=hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
            run(['podman','cp',str(ROOT/source),browser+':/tests/'+destination])
        tested=run(['podman','exec',browser,'node','node_modules/@playwright/test/cli.js','test',
                    'full_workflow.spec.ts','bootstrap.spec.ts','--timeout=120000','--reporter=line'],check=False,timeout=1800)
        (evidence/'browser.log').write_text(safe(tested.stdout+tested.stderr),encoding='utf-8')
        result['browser_exit_code']=tested.returncode
        if tested.returncode:raise RuntimeError('Running-stack browser workflow failed')
        references=evidence/'full-workflows.json'
        run(['podman','cp',browser+':/tmp/aat-e2e-artifacts/full-workflows.json',str(references)])
        run(['podman','cp',str(references),backend+':/tmp/full-workflows.json'])
        run(['podman','cp',str(ROOT/'tests/tools/verify_full_workflow.py'),backend+':/tmp/verify_full_workflow.py'])
        verified=run(['podman','exec',backend,'python','/tmp/verify_full_workflow.py'],check=False)
        (evidence/'target-verification.log').write_text(safe(verified.stdout+verified.stderr),encoding='utf-8')
        result.update(status='PASS' if verified.returncode==0 else 'FAIL',target_exit_code=verified.returncode)
        if verified.returncode:raise RuntimeError('Actual target verification failed')
    except Exception:
        result['status']='FAIL'
        raise
    finally:
        if created:result['browser_cleanup_exit_code']=run(['podman','rm','-f',browser],check=False).returncode
        if result.get('browser_cleanup_exit_code',0):result['status']='CLEANUP_FAILED'
        (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--airflow-url',required=True)
    parser.add_argument('--evidence-dir',required=True)
    parser.add_argument('--images')
    args=parser.parse_args()
    result=verify(args.project,args.base_url,args.airflow_url,ROOT/args.evidence_dir,ROOT/args.images if args.images else None)
    print(result['status'],flush=True)
    raise SystemExit(0 if result['status']=='PASS' else 1)
