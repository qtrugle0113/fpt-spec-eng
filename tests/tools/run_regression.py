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
parser.add_argument('--images',default='tests/fixtures/regression-images.json')
parser.add_argument('--evidence-dir')
parser.add_argument('--airflow-module',action='append')
parser.add_argument('--e2e-suite',action='append',choices=['connections','tables','files','dag_builder','monitoring','phase7'])
args=parser.parse_args()
path=(ROOT/args.images).resolve()
if not path.is_relative_to(ROOT):parser.error('Image manifest must stay in workspace')
images=json.loads(path.read_text(encoding='utf-8'))
stamp=datetime.now(timezone(timedelta(hours=9))).strftime('%Y%m%d')
evidence=(ROOT/(args.evidence_dir or 'docs/testing/regression-'+stamp+'-'+secrets.token_hex(4))).resolve()
if not evidence.is_relative_to(ROOT):parser.error('Evidence must stay in workspace')
evidence.mkdir(parents=True,exist_ok=True)
groups=['unit-api','integration','etl','airflow','e2e','stress'] if args.group=='all' else [args.group]
result={'status':'NOT_RUN','images':images,'planned_groups':groups,'selectors':[],'existing_services_modified':False}

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

for name,identity in images.items():
    actual=subprocess.check_output(['podman','image','inspect',identity,'--format','{{.Id}}'],text=True).strip()
    if actual!=identity:raise RuntimeError('Exact image mismatch: '+name)
for group in groups:
    if group in ('unit-api','integration','etl'):
        arguments=[value for name in ('tests','backend','postgres','mysql') for value in ('--'+name+'-image',images[name])]
        if group=='etl':
            runtime_files=('test_runtime_adapter.py','test_runtime_lifecycle.py','test_runtime_recovery_projection.py','test_worker_maintenance.py')
            engine_args=[*arguments,'--path','tests/etl']
            for filename in runtime_files:engine_args+=['--ignore','tests/etl/'+filename]
            execute('etl-engine','run_regression_profile.py',engine_args)
            runtime_args=list(arguments)
            for filename in runtime_files:runtime_args+=['--path','tests/etl/'+filename]
            execute('etl-runtime','run_regression_profile.py',runtime_args)
            continue
        if group=='unit-api':arguments+=['--ignore','tests/unit/test_dag_factory.py']
        if group=='integration':
            for filename in ('test_metadata_foundation.py','test_authorization_repository.py','test_phase2_repositories.py',
                             'test_phase2_operations.py','test_phase2_api.py','test_connections.py','test_table_ddl.py','test_file_sources.py'):
                arguments+=['--path','tests/integration/'+filename]
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
            execute('e2e-'+suite,'run_connections_e2e.py',arguments)
    else:
        arguments=['--unittest-module','tests.stress.test_disk_staging','--task-label','regression-stress','--disk-databases','--runner-memory','1g',
            '--postgres-image',images['postgres'],'--runner-image',images['airflow'],'--workbook-deps-image',images['workbook_deps']]
        execute('stress','run_metadata_foundation.py',arguments)
result['status']='PASS'
(evidence/'regression-results.json').write_text(json.dumps(result,indent=2)+'\n')
