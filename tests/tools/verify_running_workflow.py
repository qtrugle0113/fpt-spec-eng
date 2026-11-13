"""Run the real browser workflow on an explicitly selected owned local stack."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]


def make_extraction_source(source,destination,row_count):
    with source.open('r',encoding='utf-8',newline='') as stream:
        reader=csv.reader(stream)
        header=next(reader)
        rows=list(reader)
    if not rows or len(header)!=4 or any(len(row)!=len(header) for row in rows):
        raise ValueError('The T140 sample CSV does not match the expected synthetic schema.')
    with destination.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(header)
        for index in range(row_count):
            row=list(rows[index%len(rows)])
            row[0]=str(index+1)
            writer.writerow(row)


def expected_extraction_rows(path):
    rows=[]
    with path.open('r',encoding='utf-8',newline='') as stream:
        for row in csv.DictReader(stream):
            registered=row['registered_at']
            rows.append([
                int(row['customer_id']),row['customer_name'],
                None if row['balance']=='\\N' else row['balance'],
                None if registered=='\\N' else datetime.fromisoformat(registered).isoformat(),
            ])
    return rows


def verify(project,base_url,airflow_url,evidence,images_path=None,restart_phase=None):
    if not re.fullmatch(r'aat-(?:t140|portable-demo)-[0-9a-f]{8}',project):
        raise ValueError('Only an explicit owned local namespace is supported')
    if restart_phase not in (None,'EXTRACTION','COMMIT','FULL_REFRESH'):
        raise ValueError('Unsupported T140 restart phase')
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
    libraries=None
    result={'status':'NOT_RUN','project':project,'base_url':base_url,'airflow_url':airflow_url,
            'application_source_overlay':False,'sample_namespace':'full_<desktop|mobile>_<timestamp>',
            'sample_data_retained':True,'test_source_sha256':{},
            'phase_restart':restart_phase,'phase_restart_checks':[]}
    expected_rows=80000 if restart_phase=='EXTRACTION' else 4
    def run(command,check=True,input=None,timeout=180):
        process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',input=input,timeout=timeout)
        if check and process.returncode:raise RuntimeError('Owned workflow command failed; inspect evidence')
        return process
    def safe(value):
        for secret in values:value=value.replace(secret,'[REDACTED]')
        return value

    def run_phase_control(*arguments,check=True,timeout=30,input=None):
        return run(['podman','exec',backend,'python','/tmp/t140_phase_control.py',*arguments],
                   check=check,timeout=timeout,input=input)

    def read_browser_marker(remote,local,process,deadline):
        while time.monotonic()<deadline:
            copied=run(['podman','cp',browser+':'+remote,str(local)],check=False,timeout=10)
            if copied.returncode==0:return json.loads(local.read_text(encoding='utf-8'))
            if process.poll() is not None:raise RuntimeError('Browser scenario ended before writing its T140 marker')
            time.sleep(.25)
        raise TimeoutError('Timed out waiting for the owned browser phase marker')

    def run_t140_restart(phase,expected_rows):
        lock_process=None
        events=evidence/'phase-events.jsonl'
        def record(event,**details):
            with events.open('a',encoding='utf-8') as stream:
                stream.write(json.dumps({'event':event,**details},default=str)+'\n')
        command=['podman','exec',browser,'node','node_modules/@playwright/test/cli.js','test',
                 'full_workflow.spec.ts','--project=desktop','--timeout=900000','--reporter=line']
        with tempfile.TemporaryFile() as browser_output:
            process=subprocess.Popen(command,cwd=ROOT,stdout=browser_output,stderr=subprocess.STDOUT)
            try:
                marker=read_browser_marker('/tmp/aat-t140/ready.json',evidence/'t140-ready.json',
                                           process,time.monotonic()+240)
                record('browser_fixture_ready',marker=marker)
                lock_row_id=2 if phase=='COMMIT' else 1
                if phase in ('COMMIT','FULL_REFRESH'):
                    lock_process=subprocess.Popen(
                        ['podman','exec','-i',backend,'python','/tmp/t140_phase_control.py','hold'],
                        cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                        text=True,encoding='utf-8')
                    lock_process.stdin.write(json.dumps({**marker,'lock_row_id':lock_row_id})+'\n')
                    lock_process.stdin.flush()
                    lock_ready=lock_process.stdout.readline().strip()
                    if lock_ready!='LOCK_HELD':
                        error=lock_process.stderr.read()
                        raise RuntimeError('Could not establish the owned target row lock: '+safe(error))
                    record('target_row_lock_held',row_id=lock_row_id)
                run(['podman','exec',browser,'touch','/tmp/aat-t140/start'])
                run_marker=read_browser_marker('/tmp/aat-t140/run.json',evidence/'t140-run.json',
                                              process,time.monotonic()+300)

                def state():
                    output=run_phase_control('state',run_marker['dag'],run_marker['run'],
                                             run_marker['code'],run_marker['table'])
                    return json.loads(output.stdout)

                def target():
                    output=run_phase_control('target',run_marker['code'],run_marker['table'])
                    return json.loads(output.stdout)

                def task_state():
                    output=run_phase_control('task',run_marker['dag'],run_marker['run'])
                    return json.loads(output.stdout)

                def task_logs(task):
                    attempt=task.get('try_number')
                    if type(attempt) is not int:
                        return {'available':False,'unavailable_reason':'Task attempt number is unavailable.'}
                    output=run_phase_control('logs',run_marker['dag'],run_marker['run'],str(attempt),check=False)
                    if output.returncode:
                        return {'available':False,'exit_code':output.returncode,'error':safe(output.stderr[-4000:])}
                    return json.loads(output.stdout)

                def pause_during_extraction():
                    script="""import json,os,re,signal,sys,time,uuid
from pathlib import Path
pid=int(sys.argv[1])
identity=sys.argv[2]
relative=Path(sys.argv[3])
owner=sys.argv[4]
root=Path('/data/staging').resolve()
valid=(not relative.is_absolute() and len(relative.parts)==3
    and re.fullmatch(r'[0-9a-f]{64}',relative.parts[0])
    and re.fullmatch(r'[0-9a-f]{64}',relative.parts[1]))
valid=bool(valid) and str(uuid.UUID(relative.parts[2]))==relative.parts[2]
path=root/relative
valid=valid and path.resolve().is_relative_to(root)
valid=valid and not any(root.joinpath(*relative.parts[:i]).is_symlink() for i in range(1,4))
args=Path('/proc',str(pid),'cmdline').read_bytes().rstrip(b'\\0').split(b'\\0')
valid=valid and args[1:4]==[b'-m',b'aat_etl.runtime_child',identity.encode()]
journal=root/'.aat-runtime-journals'/(identity+'.json')
temporary=journal.with_suffix('.part')
if not valid or journal.is_symlink() or temporary.is_symlink():
    raise RuntimeError('Owned extraction process or journal is not verifiable')
if not journal.exists() or temporary.exists():
    print(json.dumps({'paused':False,'reason':'WAITING_FOR_JOURNAL'}))
    sys.exit(0)
if not journal.is_file():
    raise RuntimeError('Owned extraction journal is not a regular file')
if (path/'manifest.json').exists():
    print(json.dumps({'paused':False,'reason':'MANIFEST_PUBLISHED'}))
    sys.exit(0)
value=json.loads(journal.read_text())
if value.get('binding_id')!=identity or value.get('pid')!=pid or value.get('owner')!=owner:
    raise RuntimeError('Attempt journal does not match the observed extraction owner')
attempts={item['attempt'] for item in value['attempts']}
parts=sorted(path.glob('attempts/*/part-*.jsonl.part'))
part=next((item for item in parts if item.parent.name in attempts and item.stat().st_size>0),None)
if part is None:
    print(json.dumps({'paused':False,'reason':'WAITING_FOR_PARTIAL_WRITE'}))
    sys.exit(0)
size=part.stat().st_size
os.kill(pid,signal.SIGSTOP)
deadline=time.monotonic()+5
status=Path('/proc',str(pid),'status')
while time.monotonic()<deadline and status.exists() and not re.search(r'^State:\\s+T',status.read_text(),re.M):
    time.sleep(.02)
stopped=status.exists() and bool(re.search(r'^State:\\s+T',status.read_text(),re.M))
print(json.dumps({'paused':stopped,'reason':'PAUSED' if stopped else 'PAUSE_NOT_CONFIRMED',
    'pid':pid,'partial_bytes':size,'partial_path':part.relative_to(root).as_posix(),
    'manifest_absent':not (path/'manifest.json').exists()}))
sys.exit(0 if stopped else 1)
"""
                    owner=phase_before.get('owner_process_id','')
                    match=re.fullmatch(r'([1-9][0-9]*):[0-9a-f]{32}',owner)
                    if not match:raise AssertionError('The extraction owner identity is invalid')
                    scheduler=project+'-airflow-scheduler-1'
                    output=run(['podman','exec',scheduler,'python','-c',script,match.group(1),
                                phase_before['binding_id'],phase_before['path_key'],owner],
                               check=False,timeout=15)
                    if output.returncode:raise RuntimeError('Could not pause the owned extraction child')
                    return json.loads(output.stdout)

                expected_operations={'COMMIT':'UPSERT_INSERT','FULL_REFRESH':'FULL_REFRESH_DELETE'}
                deadline=time.monotonic()+240
                phase_before=None
                extraction_paused=False
                while time.monotonic()<deadline:
                    phase_before=state()
                    if phase_before:
                        if phase=='EXTRACTION' and phase_before.get('recovery_state')=='EXTRACTING' and phase_before.get('dataset_state')=='INCOMPLETE':
                            progress=pause_during_extraction()
                            if progress.get('paused'):
                                extraction_paused=True
                                record('extraction_child_paused',progress=progress)
                                break
                            if progress.get('reason')=='MANIFEST_PUBLISHED':
                                raise RuntimeError('Extraction completed before a partial writer could be paused')
                        if phase in expected_operations and phase_before.get('recovery_state')=='WRITING' \
                                and phase_before.get('dataset_state')=='COMPLETE' \
                                and expected_operations[phase] in phase_before.get('blocked_operations',[]):
                            break
                    if process.poll() is not None:
                        raise RuntimeError('Browser scenario completed before reaching the required T140 phase')
                    time.sleep(.05 if phase=='EXTRACTION' else .2)
                else:
                    raise TimeoutError('The required T140 runtime phase was not observed')
                if phase=='COMMIT':
                    expected_before_restart=[
                        [1,'Nguyễn, An','12345.6789','2026-01-01T12:30:00.123456'],
                        [2,'old protected row','0.0000',None],
                    ]
                elif phase=='FULL_REFRESH':
                    expected_before_restart=[[1,'old protected row','0.0000',None]]
                else:
                    expected_before_restart=[]
                target_before=target()
                record('observed_phase_before_restart',state=phase_before,target=target_before)
                task_before=task_state()
                record('airflow_task_before_restart',task=task_before)
                if phase_before.get('retry_count')!='2' or task_before.get('state')!='running' \
                        or type(task_before.get('max_tries')) is not int or task_before['max_tries']<2:
                    raise AssertionError('The active phase must have an Airflow retry available before restart')
                if target_before!=expected_before_restart:
                    raise AssertionError('Owned target contents differ before scheduler restart: '+json.dumps(target_before,ensure_ascii=False))

                scheduler=project+'-airflow-scheduler-1'
                if phase=='EXTRACTION':
                    if not extraction_paused:
                        raise AssertionError('The extraction child was not paused during its journaled partial write')
                before=run(['podman','inspect',scheduler,'--format','{{.State.StartedAt}}|{{.State.Status}}'])
                before_fields=before.stdout.strip().split('|')
                if len(before_fields)!=2 or before_fields[1]!='running':
                    raise AssertionError('Owned scheduler was not running before the restart')
                restarted=run(['podman','restart',scheduler],timeout=120)
                if restarted.returncode:raise RuntimeError('Owned Airflow scheduler restart failed')
                deadline=time.monotonic()+420
                after=''
                while time.monotonic()<deadline:
                    inspected=run(['podman','inspect',scheduler,
                                   '--format','{{.State.StartedAt}}|{{.State.Status}}|{{.State.Health.Status}}'],
                                  check=False,timeout=10)
                    if inspected.returncode==0:
                        after=inspected.stdout.strip()
                        fields=after.split('|')
                        if len(fields)==3 and fields[0]!=before_fields[0] \
                                and fields[1]=='running' and fields[2]=='healthy':
                            break
                    time.sleep(2)
                else:
                    raise TimeoutError('Restarted Airflow scheduler did not become healthy')
                record('scheduler_restarted',exit_code=restarted.returncode,
                       started_at_before=before.stdout.strip(),inspection_after=after)

                prior_owner=phase_before.get('owner_process_id')
                prior_dataset=phase_before.get('dataset_id')

                def dataset_recovered(current):
                    if not current or not current.get('dataset_id'):return False
                    if current['dataset_id']==prior_dataset:return True
                    if phase!='EXTRACTION':return False
                    generations=current.get('dataset_generations') or []
                    previous=next((item for item in generations if item['id']==prior_dataset),None)
                    latest=next((item for item in generations if item['id']==current['dataset_id']),None)
                    return bool(previous and latest and previous['state']=='EXPIRED'
                                and latest['generation']>previous['generation'])

                deadline=time.monotonic()+420
                phase_after=None
                task_after=None
                next_task_poll=0
                last_task_marker=None
                failed_since=None
                while time.monotonic()<deadline:
                    phase_after=state()
                    if time.monotonic()>=next_task_poll:
                        task_after=task_state()
                        task_marker=tuple(task_after.get(key) for key in ('state','try_number','max_tries','pid','end_date'))
                        if task_marker!=last_task_marker:
                            record('airflow_task_after_restart',task=task_after)
                            last_task_marker=task_marker
                        next_task_poll=time.monotonic()+5
                        if task_after.get('state')=='failed':
                            failed_since=failed_since or time.monotonic()
                            if time.monotonic()-failed_since>=20:
                                record('airflow_task_failed_after_restart',task=task_after,
                                       logs=task_logs(task_after))
                                break
                        else:
                            failed_since=None
                    if phase_after and phase_after.get('binding_id')==phase_before.get('binding_id') \
                            and phase_after.get('owner_process_id') \
                            and phase_after.get('owner_process_id')!=prior_owner \
                            and phase_after.get('dataset_id') \
                            and dataset_recovered(phase_after):
                        if phase in expected_operations:
                            if phase_after.get('dataset_id')==phase_before.get('dataset_id') \
                                    and phase_after.get('dataset_state')=='COMPLETE' \
                                    and phase_after.get('recovery_state')=='WRITING' \
                                    and expected_operations[phase] in phase_after.get('blocked_operations',[]):
                                break
                        elif phase_after.get('dataset_state')=='COMPLETE':
                            break
                    if process.poll() is not None:break
                    time.sleep(.5)
                else:
                    task_after=task_state()
                    phase_after=state()
                    record('recovery_timeout',airflow_task=task_after,state=phase_after,
                           logs=task_logs(task_after))
                    raise TimeoutError('A new runtime owner was not observed after the real scheduler restart: '
                                       +json.dumps({'airflow_task':task_after,'runtime':phase_after},default=str))
                if task_after and task_after.get('state')=='failed':
                    raise RuntimeError('Airflow task failed after the scheduler restart; inspect redacted phase logs.')
                if not phase_after or phase_after.get('binding_id')!=phase_before.get('binding_id') \
                        or not phase_after.get('dataset_id') \
                        or not dataset_recovered(phase_after) \
                        or not phase_after.get('owner_process_id') \
                        or phase_after.get('owner_process_id')==prior_owner:
                    raise AssertionError('The original runtime owner did not recover under the same binding')
                if phase_after.get('dataset_state')!='COMPLETE':
                    raise AssertionError('Runtime recovery did not publish a complete source generation')
                before_reservations={item['id'] for item in (phase_before.get('reservations') or [])}
                after_reservations={item['id'] for item in (phase_after.get('reservations') or [])}
                if not before_reservations or not before_reservations.issubset(after_reservations):
                    raise AssertionError('Staging reservation identity was not preserved across restart')
                if phase_after.get('dataset_state')=='COMPLETE' and phase_after.get('staging_artifacts',0)<1:
                    raise AssertionError('Completed dataset lost its staging artifact metadata across restart')
                target_after=target()
                expected_target=expected_extraction_rows(
                    evidence/'t140-extraction-source.csv' if phase=='EXTRACTION'
                    else ROOT/'samples/data/customers.csv')
                target_sha256=hashlib.sha256(json.dumps(target_after,ensure_ascii=False,
                    separators=(',',':')).encode()).hexdigest()
                record('target_snapshot_after_restart',rows=len(target_after),sha256=target_sha256,
                       first=target_after[0] if target_after else None,
                       last=target_after[-1] if target_after else None)
                if phase=='EXTRACTION':
                    target_is_expected=target_after==expected_target
                    target_is_unchanged=target_after==expected_before_restart
                    target_is_committed_prefix=target_after==expected_target[:len(target_after)] \
                        and (len(target_after)%1000==0 or target_is_expected)
                    if not target_is_committed_prefix:
                        raise AssertionError('Owned target is not an exact prefix ending at a committed batch boundary')
                    target_after_evidence={
                        'rows':len(target_after),
                        'sha256':target_sha256,
                        'first':target_after[0] if target_after else None,
                        'last':target_after[-1] if target_after else None,
                        'matches_expected':target_is_expected,
                        'unchanged_from_before_restart':target_is_unchanged,
                        'matches_committed_prefix':target_is_committed_prefix,
                        'batch_size':1000,
                        'expected_sha256':hashlib.sha256(json.dumps(expected_target,ensure_ascii=False,
                            separators=(',',':')).encode()).hexdigest(),
                    }
                else:
                    target_is_expected=target_after==expected_before_restart
                    target_after_evidence=target_after
                if not target_is_expected:
                    raise AssertionError('Owned target changed unexpectedly across scheduler restart')
                stage_result=None
                if phase_after.get('dataset_state')=='COMPLETE' and phase_after.get('path_key') \
                        and phase_after.get('manifest_sha256'):
                    script=("import hashlib,json,sys;from pathlib import Path;"
                            "root=Path('/data/staging').resolve();"
                            "path=(root/sys.argv[1]/'manifest.json');"
                            "safe=not path.is_symlink() and path.resolve().is_relative_to(root);"
                            "exists=safe and path.is_file();"
                            "sha=hashlib.sha256(path.read_bytes()).hexdigest() if exists else None;"
                            "print(json.dumps({'exists':exists,'sha256':sha,'matches':sha==sys.argv[2]}))")
                    checked_stage=run(['podman','exec',scheduler,'python','-c',script,
                                       phase_after['path_key'],phase_after['manifest_sha256']],
                                      check=False,timeout=15)
                    if checked_stage.returncode:raise RuntimeError('Could not verify protected staging after restart')
                    stage_result=json.loads(checked_stage.stdout)
                    if not stage_result['exists'] or not stage_result['matches']:
                        raise AssertionError('Complete staging manifest was not preserved across restart')
                check={'phase':phase,'run':run_marker['run'],'dag':run_marker['dag'],
                       'binding_id':phase_before['binding_id'],
                       'owner_before':prior_owner,'owner_after':phase_after['owner_process_id'],
                       'recovery_state_before':phase_before.get('recovery_state'),
                       'dataset_state_before':phase_before.get('dataset_state'),
                       'recovery_state_after':phase_after.get('recovery_state'),
                       'dataset_state_after':phase_after.get('dataset_state'),
                       'dataset_generations_after':phase_after.get('dataset_generations'),
                       'protected_artifacts_after':phase_after.get('protected_artifacts'),
                       'commit_uncertain_after_restart':phase_after.get('commit_uncertain'),
                       'blocked_operations_before':phase_before.get('blocked_operations'),
                       'blocked_operations_after':phase_after.get('blocked_operations'),
                       'target_before':target_before,'target_after':target_after_evidence,
                       'scheduler_started_at_before':before_fields[0],
                       'scheduler_started_at_after':after.split('|')[0],
                       'scheduler_health_after':after.split('|')[2],
                       'airflow_task_before':task_before,'airflow_task_after':task_after,
                       'staging_manifest_after':stage_result,
                       'reservations_before':phase_before.get('reservations'),
                       'reservations_after':phase_after.get('reservations')}
                record('observed_phase_after_restart',state=phase_after,target=target_after_evidence,
                       staging_manifest=stage_result)
                result['phase_restart_checks'].append(check)
                if lock_process:
                    lock_process.stdin.write('\n')
                    lock_process.stdin.flush()
                    lock_process.stdin.close()
                    lock_process.wait(timeout=30)
                    if lock_process.returncode:
                        raise RuntimeError('Owned target lock helper did not exit cleanly')
                    lock_process=None
                returncode=process.wait(timeout=900)
                browser_output.seek(0)
                (evidence/'browser.log').write_text(safe(browser_output.read().decode('utf-8','replace')),encoding='utf-8')
                if returncode:
                    raise RuntimeError('Browser scenario failed after the scheduler restart; inspect its redacted log.')
                deadline=time.monotonic()+120
                final_state=None
                final_task=None
                while time.monotonic()<deadline:
                    final_state=state()
                    final_task=task_state()
                    if final_task.get('state')=='success' and final_state \
                            and final_state.get('binding_id')==phase_before.get('binding_id') \
                            and final_state.get('binding_state')=='COMMIT_VERIFIED' \
                            and final_state.get('recovery_state')=='COMMIT_VERIFIED' \
                            and final_state.get('dataset_state')=='COMPLETE' \
                            and final_state.get('commit_uncertain') is False \
                            and final_state.get('loaded_rows')==expected_rows \
                            and final_state.get('phase')=='COMPLETE':
                        break
                    if final_task.get('state')=='failed':
                        record('airflow_task_failed_after_recovery',task=final_task,
                               logs=task_logs(final_task))
                        raise RuntimeError('Airflow task failed after the scheduler restart.')
                    time.sleep(.5)
                else:
                    raise TimeoutError('Recovered workflow did not reach a reconciled successful state.')
                final_target=target()
                if final_target!=expected_target:
                    raise AssertionError('Final target values differ from the exact synthetic source after recovery.')
                check.update(final_binding_state=final_state.get('binding_state'),
                             final_recovery_state=final_state.get('recovery_state'),
                             final_commit_uncertain=final_state.get('commit_uncertain'),
                             final_dataset_state=final_state.get('dataset_state'),
                             final_loaded_rows=final_state.get('loaded_rows'),
                             final_phase=final_state.get('phase'),
                             final_airflow_task=final_task,
                             final_target_rows=len(final_target),
                             final_target_sha256=hashlib.sha256(json.dumps(final_target,ensure_ascii=False,
                                 separators=(',',':')).encode()).hexdigest())
                record('workflow_completed_after_recovery',state=final_state,task=final_task,
                       target_rows=len(final_target),target_sha256=check['final_target_sha256'])
                return {'returncode':returncode}
            finally:
                if lock_process and lock_process.poll() is None:
                    lock_process.stdin.write('\n')
                    lock_process.stdin.flush()
                    lock_process.stdin.close()
                    try:lock_process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        lock_process.terminate()
                        lock_process.wait(timeout=10)
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=30)
                browser_output.seek(0)
                if not (evidence/'browser.log').exists():
                    (evidence/'browser.log').write_text(safe(browser_output.read().decode('utf-8','replace')),encoding='utf-8')

    created=False
    try:
        preflight=run(['python','-X','utf8','tests/tools/run_regression.py','--group','e2e','--preflight-only',
                      '--images',str(images_path.relative_to(ROOT)),
                      '--evidence-dir',str((evidence/'policy-preflight').relative_to(ROOT))])
        if 'PREFLIGHT_PASS' not in preflight.stdout:
            raise RuntimeError('Exact-image runtime preflight did not report PASS')
        for service,kind in (('backend','backend'),('frontend','frontend'),('airflow-apiserver','airflow')):
            actual=run(['podman','inspect',project+'-'+service+'-1','--format','{{.Image}}']).stdout.strip()
            if actual.removeprefix('sha256:')!=images[kind].removeprefix('sha256:'):
                raise RuntimeError('Running application differs from reviewed local artifact')
        browser_args=['podman','run','-d','--name',browser,'--network','host','--memory','768m','--cpus','2',
             '-e','PLAYWRIGHT_BASE_URL='+base_url,'-e','AIRFLOW_EXPECTED_ORIGIN='+airflow_url,
             ]
        if restart_phase:
            result['retry_policy']={'retries':2,'delay_seconds':1}
            browser_args.extend(['-e','AAT_T140_PHASE='+restart_phase,
                                 '-e','AAT_T140_EXPECTED_ROWS='+str(expected_rows)])
        browser_args.extend([images['e2e'],'sleep','infinity'])
        run(browser_args)
        created=True
        credentials=json.loads(run(['podman','exec',backend,'python','-c',
            "import json,pathlib;print(json.dumps({'pg_etl':pathlib.Path('/secrets/backend/pg_etl').read_text()}))"]).stdout)
        values.extend(credentials.values())
        install="const fs=require('node:fs');fs.mkdirSync('/run/aat-e2e',{mode:0o700});for(const [k,v] of Object.entries(JSON.parse(fs.readFileSync(0,'utf8'))))fs.writeFileSync('/run/aat-e2e/'+k,v,{mode:0o400});"
        run(['podman','exec','-i',browser,'node','-e',install],input=json.dumps(credentials))
        libraries_path=ROOT/'.tools'/(browser+'-workbook-libs')
        libraries_path.mkdir()
        libraries=libraries_path
        root=run(['podman','exec',backend,'python','-c',"import sysconfig;print(sysconfig.get_paths()['purelib'])"]).stdout.strip()
        for name in ('openpyxl','et_xmlfile','defusedxml'):
            run(['podman','cp',backend+':'+root+'/'+name,str(libraries/name)])
        result['workbook_library_sha256']={str(p.relative_to(libraries)):hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in libraries.rglob('*') if p.is_file()}
        run(['podman','cp',str(libraries),browser+':/tests/workbook-libs'])
        source_file=ROOT/'samples/data/customers.csv'
        if restart_phase=='EXTRACTION':
            source_file=evidence/'t140-extraction-source.csv'
            make_extraction_source(ROOT/'samples/data/customers.csv',source_file,expected_rows)
            result['synthetic_source']={'path':str(source_file.relative_to(ROOT)),
                'sha256':hashlib.sha256(source_file.read_bytes()).hexdigest(),
                'bytes':source_file.stat().st_size,'expected_rows':expected_rows}
        if restart_phase:
            run(['podman','exec',browser,'mkdir','-p','/tmp/aat-t140'])
            run(['podman','exec',backend,'mkdir','-p','/tmp/aat-t140'])
            run(['podman','cp',str(ROOT/'tests/tools/t140_phase_control.py'),
                 backend+':/tmp/t140_phase_control.py'])
            result['test_source_sha256']['tests/tools/t140_phase_control.py']=hashlib.sha256(
                (ROOT/'tests/tools/t140_phase_control.py').read_bytes()).hexdigest()
        for source,destination in [('tests/tools/make_full_workflow.py','make_full_workflow.py'),
                                   (str(source_file.relative_to(ROOT)),'full-customers.csv'),
                                   ('tests/e2e/playwright.config.ts','playwright.config.ts'),
                                   ('tests/e2e/full_workflow.spec.ts','full_workflow.spec.ts'),
                                   ('tests/e2e/bootstrap.spec.ts','bootstrap.spec.ts')]:
            source_path=ROOT/source if source.startswith('tests/') else source_file
            result['test_source_sha256'][source]=hashlib.sha256(source_path.read_bytes()).hexdigest()
            run(['podman','cp',str(source_path),browser+':/tests/'+destination])
        if restart_phase:
            browser_result=run_t140_restart(restart_phase,expected_rows)
        else:
            tested=run(['podman','exec',browser,'node','node_modules/@playwright/test/cli.js','test',
                        'full_workflow.spec.ts','bootstrap.spec.ts','--timeout=120000','--reporter=line'],
                       check=False,timeout=1800)
            (evidence/'browser.log').write_text(safe(tested.stdout+tested.stderr),encoding='utf-8')
            browser_result={'returncode':tested.returncode}
        result['browser_exit_code']=browser_result['returncode']
        if browser_result['returncode']:raise RuntimeError('Running-stack browser workflow failed')
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
        if libraries and libraries.exists():
            try:shutil.rmtree(libraries)
            except OSError as error:
                result['workbook_libraries_cleanup_error']=str(error)
                result['status']='CLEANUP_FAILED'
        (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--airflow-url',required=True)
    parser.add_argument('--evidence-dir',required=True)
    parser.add_argument('--images')
    parser.add_argument('--restart-phase',choices=('EXTRACTION','COMMIT','FULL_REFRESH'))
    args=parser.parse_args()
    result=verify(args.project,args.base_url,args.airflow_url,ROOT/args.evidence_dir,
                  ROOT/args.images if args.images else None,args.restart_phase)
    print(result['status'],flush=True)
    raise SystemExit(0 if result['status']=='PASS' else 1)
