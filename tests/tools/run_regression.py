"""Coordinate existing isolated container runners; preserve per-selector evidence."""
import argparse
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import secrets
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--group',choices=['unit-api','integration','etl','airflow','e2e','stress','all'],required=True)
parser.add_argument('--images',help='Explicit artifact manifest; default is the locally prepared .tools/local-images.json')
parser.add_argument('--prepare-images',action='store_true',help='Build local images and scan policy before running tests')
parser.add_argument('--evidence-dir')
parser.add_argument('--preflight-only',action='store_true',help='Verify required local images without starting fixtures')
parser.add_argument('--owner-accepted-handover',action='store_true',help='Validate exact owner-reviewed baseline under Constitution2.0.0')
parser.add_argument('--etl-part',choices=['all','engine','runtime'],default='all',help='Rerun only the affected ETL selector after a failure')
parser.add_argument('--etl-path',action='append',help='Focused tests/etl/test_*.py selector for the engine group')
parser.add_argument('--airflow-module',action='append')
parser.add_argument('--e2e-suite',action='append',choices=['connections','tables','files','dag_builder','monitoring','phase7','full_workflow','language'])
parser.add_argument('--missing-source-check',action='store_true',help='Verify unavailable-source guards on the installed full-workflow E2E fixture')
parser.add_argument('--e2e-extra-spec',action='append',default=[],help='Focused additional Playwright test source on a full_workflow fixture')
parser.add_argument('--integration-path',action='append',help='Focused tests/integration/test_*.py selector')
parser.add_argument('--current-test-sources',action='store_true',help='Refresh only test source on unit/API, integration or ETL fixtures')
parser.add_argument('--show-passed-output',action='store_true',help='Include reviewed test measurements in passing profile evidence')
args=parser.parse_args()
if args.integration_path:
    import re
    if args.group!='integration' or any(not re.fullmatch(r'tests/integration/test_[A-Za-z0-9_]+\.py',p) for p in args.integration_path):
        parser.error('Integration paths require the integration group and tests/integration/test_*.py files')
if args.current_test_sources and args.group not in ('unit-api','integration','etl'):
    parser.error('Current test sources require a unit/API, integration or ETL group')
if args.show_passed_output and args.group not in ('unit-api','integration','etl'):
    parser.error('Passed profile output requires a unit/API, integration or ETL group')
if args.e2e_extra_spec and (args.group!='e2e' or args.e2e_suite!=['full_workflow']):
    parser.error('Additional E2E specs require exactly the full_workflow E2E suite')
if args.etl_path:
    import re
    if any(not re.fullmatch(r'tests/etl/test_[A-Za-z0-9_]+\.py',value) for value in args.etl_path):parser.error('ETL selectors must be tests/etl/test_*.py')
    if args.group not in ('etl','all') or args.etl_part=='runtime':parser.error('ETL paths require the ETL engine group')
if args.missing_source_check and (args.group not in ('e2e','all') or 'full_workflow' not in (args.e2e_suite or [])):
    parser.error('Missing-source checks require an explicit full_workflow E2E suite')
if args.prepare_images:
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tests/tools/prepare_local_images.py')],check=True)
    prepared=json.loads((ROOT/'.tools/local-images-provenance.json').read_text(encoding='utf-8'))
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tests/tools/scan_portable_images.py'),
        '--manifest',prepared['manifest']],check=True)
path=(ROOT/(args.images or '.tools/local-images.json')).resolve()
if not path.is_relative_to(ROOT):parser.error('Image manifest must stay in workspace')
images=json.loads(path.read_text(encoding='utf-8'))
stamp=datetime.now(timezone(timedelta(hours=9))).strftime('%Y%m%d')
evidence=(ROOT/(args.evidence_dir or 'docs/testing/regression-'+stamp+'-'+secrets.token_hex(4))).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
groups=['unit-api','integration','etl','airflow','e2e','stress'] if args.group=='all' else [args.group]
result={'status':'NOT_RUN','images':images,'planned_groups':groups,'selectors':[],'existing_services_modified':False}

def save_result():
    (evidence/'regression-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


# Inspect every required image so a checkout on another machine produces a
# complete actionable record instead of failing at the first missing image.
required=set()
for group in groups:
    if group in ('unit-api','integration','etl'):
        required.update(('tests','backend','postgres','mysql'))
        if group=='unit-api':required.add('airflow')
    elif group=='airflow':required.update(('airflow','postgres','mysql','workbook_deps'))
    elif group=='e2e':required.update(('backend','frontend','e2e','airflow','postgres','mysql'))
    else:required.update(('postgres','airflow','workbook_deps'))
provenance_path=path.parent/(path.stem+'-provenance.json')
if args.owner_accepted_handover:
    from full_handover_policy import validate
    try:
        result['handover_policy']=validate(ROOT, images)
    except (OSError,ValueError,KeyError) as error:
        result.update(status='BLOCKED',reason='OWNER_HANDOVER_APPROVAL_INVALID',detail=str(error))
        save_result()
        raise SystemExit(2)
if not args.owner_accepted_handover and (not args.preflight_only or args.images is None or provenance_path.exists()):
    import hashlib
    from portable_policy import check_expiry
    try:
        local=json.loads(provenance_path.read_text(encoding='utf-8'))
        built_path=(ROOT/local['manifest']).resolve()
        if not built_path.is_relative_to(ROOT):raise ValueError('Provenance path outside workspace')
        review=json.loads((built_path.parent/'local-policy-review.json').read_text(encoding='utf-8'))
        check_expiry(review['policy_provenance']['expires_at'])
        if review['status']!='LOCAL_POLICY_MATCH':raise ValueError('Local scan policy has unresolved findings')
        for artifact,key in ((built_path,'manifest_sha256'),(built_path.parent/'candidate-security.json','scan_sha256')):
            if hashlib.sha256(artifact.read_bytes()).hexdigest()!=review[key]:raise ValueError('Reviewed artifact changed')
        ledger=ROOT/review['policy_provenance']['ledger']
        if hashlib.sha256(ledger.read_bytes()).hexdigest()!=review['policy_provenance']['ledger_sha256']:
            raise ValueError('Reviewed policy changed')
        policy=review['policy_provenance']
        if hashlib.sha256((ROOT/policy['approval']).read_bytes()).hexdigest()!=policy['approval_sha256']:
            raise ValueError('Local approval changed; review policy again')
        for decision in policy['additional_owner_decisions']:
            if hashlib.sha256((ROOT/decision['decision']).read_bytes()).hexdigest()!=decision['decision_sha256']:
                raise ValueError('Additional approval changed or revoked')
        reviewed={row['target']:row['image_id'] for row in review['images']}
        aliases={'tests':'backend-tests','e2e':'e2e-tests','workbook_deps':'backend'}
        if any(reviewed.get(aliases.get(name,name))!=images.get(name) for name in required):
            raise ValueError('Resolved image differs from scanned artifact')
        result['local_policy_review']=str((built_path.parent/'local-policy-review.json').relative_to(ROOT))
    except (OSError,ValueError,KeyError) as error:
        result.update(status='BLOCKED',reason='LOCAL_SCAN_POLICY_NOT_READY',detail=str(error))
        save_result()
        print('BLOCKED: local scan policy is not ready; see regression-results.json',flush=True)
        raise SystemExit(2)
preflight=[]
for name in sorted(required):
    identity=images.get(name)
    item={'name':name,'expected_image_id':identity,'status':'BLOCKED'}
    if identity:
        try:
            checked=subprocess.run(['podman','image','inspect',identity,'--format','{{.Id}}'],
                text=True,encoding='utf-8',capture_output=True,timeout=30)
            actual=checked.stdout.strip()
            if checked.returncode==0 and actual==identity:
                item.update(status='PASS',actual_image_id=actual)
            else:item['reason']='EXACT_IMAGE_UNAVAILABLE_OR_MISMATCH'
        except (OSError,subprocess.TimeoutExpired):
            item['reason']='CONTAINER_ENGINE_UNAVAILABLE_OR_TIMEOUT'
    else:item['reason']='IMAGE_NOT_IN_MANIFEST'
    preflight.append(item)
result['preflight']=preflight
if any(item['status']!='PASS' for item in preflight):
    result.update(status='BLOCKED',reason='REQUIRED_EXACT_IMAGES_UNAVAILABLE')
    save_result()
    print('BLOCKED: required exact local images are unavailable; see regression-results.json',flush=True)
    raise SystemExit(2)
if args.preflight_only:
    result.update(status='PREFLIGHT_PASS',tests_executed=False)
    save_result()
    print('PREFLIGHT_PASS: images verified; no tests executed',flush=True)
    raise SystemExit(0)

def execute(label,script,arguments):
    directory=evidence/label
    command=[sys.executable,'-X','utf8',str(ROOT/'tests/tools'/script),*arguments,'--evidence-dir',str(directory.relative_to(ROOT))]
    result.update(status='RUNNING',active_selector=label)
    (evidence/'regression-results.json').write_text(json.dumps(result,indent=2)+'\n')
    process=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',capture_output=True,timeout=3600)
    # Child runners redact their own synthetic credentials before writing or
    # emitting output. No DSN/credential is passed by this coordinator.
    (evidence/(label+'-driver.log')).write_text(process.stdout+process.stderr,encoding='utf-8')
    result['selectors'].append({'label':label,'command':command,'exit_code':process.returncode,'evidence':str(directory.relative_to(ROOT))})
    result.update(status='RUNNING' if process.returncode==0 else 'FAIL',active_selector=None)
    (evidence/'regression-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(label+': '+('PASS' if process.returncode==0 else 'FAIL'),flush=True)
    if process.returncode:raise SystemExit(process.returncode)

for group in groups:
    if group in ('unit-api','integration','etl'):
        arguments=[value for name in ('tests','backend','postgres','mysql') for value in ('--'+name+'-image',images[name])]
        if args.current_test_sources:arguments+=['--current-test-sources']
        if args.show_passed_output:arguments+=['--show-passed-output']
        if group=='etl':
            runtime_files=('test_runtime_adapter.py','test_runtime_lifecycle.py','test_runtime_recovery_projection.py','test_worker_maintenance.py')
            engine_args=list(arguments)
            for selected in args.etl_path or ['tests/etl']:engine_args+=['--path',selected]
            for filename in runtime_files:engine_args+=['--ignore','tests/etl/'+filename]
            if args.etl_part in ('all','engine'):execute('etl-engine','run_regression_profile.py',engine_args)
            runtime_args=list(arguments)
            for filename in runtime_files:runtime_args+=['--path','tests/etl/'+filename]
            if args.etl_part in ('all','runtime'):execute('etl-runtime','run_regression_profile.py',runtime_args)
            continue
        if group=='unit-api':arguments+=['--ignore','tests/unit/test_dag_factory.py']
        if group=='integration':
            defaults=('test_metadata_foundation.py','test_authorization_repository.py','test_phase2_repositories.py',
                      'test_phase2_operations.py','test_phase2_api.py','test_connections.py','test_table_ddl.py','test_file_sources.py')
            for path in args.integration_path or ['tests/integration/'+filename for filename in defaults]:
                arguments+=['--path',path]
        execute(group,'run_regression_profile.py',arguments)
        if group=='unit-api':
            execute('unit-sdk','run_sdk_unit.py',['--image',images['airflow'],'--module','tests.unit.test_dag_factory'])
    elif group=='airflow':
        modules=args.airflow_module or ['tests.airflow.test_execution.RouteExecutionTests']
        for index,module in enumerate(modules):
            arguments=['--runtime-execution-tests','--packaged-runtime','--runtime-execution-module',module,'--runtime-label','regression-airflow-'+str(index),
                '--airflow-image',images['airflow'],'--postgres-image',images['postgres'],'--runner-image',images['airflow'],
                '--mysql-image',images['mysql'],'--workbook-deps-image',images['workbook_deps']]
            execute('airflow-'+str(index),'run_airflow_foundation.py',arguments)
    elif group=='e2e':
        for suite in args.e2e_suite or ['connections','tables','files','dag_builder','monitoring','phase7']:
            arguments=['--suite',suite]+[value for name in ('backend','frontend','e2e','airflow','postgres','mysql') for value in ('--'+name+'-image',images[name])]
            if args.missing_source_check and suite=='full_workflow':arguments+=['--missing-source-check']
            for filename in args.e2e_extra_spec:arguments+=['--extra-spec',filename]
            execute('e2e-'+suite,'run_connections_e2e.py',arguments)
    else:
        arguments=['--unittest-module','tests.stress.test_disk_staging','--task-label','regression-stress','--disk-databases','--runner-memory','1g',
            '--postgres-image',images['postgres'],'--runner-image',images['airflow'],'--workbook-deps-image',images['workbook_deps']]
        execute('stress','run_metadata_foundation.py',arguments)
result['status']='PASS'
(evidence/'regression-results.json').write_text(json.dumps(result,indent=2)+'\n')
