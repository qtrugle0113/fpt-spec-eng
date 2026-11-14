from pathlib import Path
import ast,hashlib,json,re,shutil
root=Path(__file__).resolve().parents[2]; out=root/'docs/testing/resume-20261114/t152-closure'
accepted='docs/testing/resume-20261114/accepted-handover/'
base='docs/testing/resume-20261114/t152-closure/'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads((root/p).read_text(encoding='utf8'))
def save(p,v):(root/p).write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
for source in out.rglob('*.log'):shutil.copyfile(source,source.with_suffix('.txt'))
definitions={
 'ah':(base+'ah-storage/regression-results.json',base+'ah-storage','suite'),
 'policies':(base+'etl-policies/regression-results.json',base+'etl-policies','suite'),
 'api':(base+'aj-ak-api/regression-profile-results.json',base+'aj-ak-api','suite'),
 'registration':(base+'registration-workbook-settings/regression-profile-results.json',base+'registration-workbook-settings','suite'),
 'implicit':(base+'implicit-mapping/sdk-unit-results.json',base+'implicit-mapping','suite'),
 'blank':(base+'blank-workbook-rows/regression-profile-results.json',base+'blank-workbook-rows','suite'),
 'native':(base+'native-db-concurrency/regression-results.json',base+'native-db-concurrency','suite'),
 'revision':(base+'revision-credentials-selected-results.json',base+'native-revision-credentials-dashboard','suite'),
 'dashboard':(base+'native-dashboard-r2/airflow-fixture-results.json',base+'native-dashboard-r2','suite'),
 'tables':(base+'table-e2e/regression-results.json',base+'table-e2e','browser'),
 'language':(base+'language-e2e/regression-results.json',base+'language-e2e','browser'),
 'full':(accepted+'full-workflow/regression-results.json',accepted+'full-workflow','browser'),
 'unit':(base+'final-unit-api/regression-results.json',base+'final-unit-api','suite'),
 'routes':('docs/testing/resume-20261114/t014-closeout/dnspython/routes-r2-result.json','docs/testing/resume-20261114/t014-closeout/dnspython','suite'),
 'memory':('docs/testing/resume-20261114/memory-r6/regression-results.json','docs/testing/resume-20261114/memory-r6','suite'),
 'response':(base+'response-security/regression-profile-results.json',base+'response-security','suite'),
 'security':(base+'response-security/regression-profile-results.json',base+'response-security','suite'),
 'retry':(base+'native-dependency-recovery/airflow-fixture-results.json',base+'native-dependency-recovery','suite'),
 'restart':('docs/testing/resume-20261112/aat-t140-045d42c5/result.json','docs/testing/resume-20261112/aat-t140-045d42c5','json')}
registry={}
for key,(receipt,directory,kind) in definitions.items():
    data=load(receipt);assert data['status']=='PASS',(key,data['status'])
    logs={};passed=set();observations=[]
    for path in (root/directory).rglob('*.txt'):
        text=path.read_text(encoding='utf8',errors='replace')
        py=re.findall(r'^(tests/\S+)\s+PASSED\b',text,re.M)
        native=re.findall(r'^test_\w+\s+\((tests\.[\w.]+)\)\s+\.\.\.\s+ok\b',text,re.M)
        passed.update(py)
        for test in native:
            parts=test.split('.');passed.add('/'.join(parts[:-2])+'.py::'+parts[-2]+'::'+parts[-1])
        if py or native or re.search(r'\d+ passed',text):logs[path.relative_to(root).as_posix()]=digest(path)
        for line in text.splitlines():
            for prefix in ('AIRFLOW_MEMORY_VERIFIED ','RESPONSE_LIMITS_VERIFIED ','CONCURRENT_RUNS_VERIFIED ','FULL_WORKFLOW_VERIFIED '):
                if prefix in line:observations.append(line[line.index(prefix):])
    if kind=='suite':assert passed,(key,'no passed test IDs found')
    registry[key]={'receipt':receipt,'receipt_sha256':digest(root/receipt),'kind':kind,'passed_selectors':sorted(passed),'logs_sha256':logs,
 'artifact_ids':data.get('images') or {'image':data.get('airflow_image') or data.get('image_id')},'observations':sorted(set(observations)),
        'execution_scope':data.get('scope') or ('Current accepted artifact fixture' if key not in ('memory','restart') else 'Historical execution on original artifact IDs; original source/results retained; not relabeled as new execution')}
for key,path in [('memory',base+'memory-equivalence.json'),('restart',accepted+'t140-equivalence.json')]:
    registry[key]['equivalence_proof']=path
    registry[key]['equivalence_sha256']=digest(root/path)
def check(name,key,*patterns):
    proof=registry[key];selected=[]
    for pattern in patterns:
        matches=[s for s in proof['passed_selectors'] if re.search(pattern,s)]
        assert matches,(name,key,pattern)
        selected.extend(matches)
    if proof['kind']=='suite':assert selected,(name,key)
    return {'condition':name,'evidence_id':key,'selectors':sorted(set(selected)),'status':'PASS',
            'actual':f'Receipt PASS; {len(set(selected))} specific passed test IDs verified' if selected else 'Receipt PASS; detailed browser/phase results and original artifact IDs retained'}
checks={}
def put(codes,*items):
    for code in codes.split():checks[code]=list(items)
put('A B',check('DDL PostgreSQL/MySQL through browser','tables'))
for code,name in [('C','pg_to_pg'),('D','mysql_to_mysql'),('E','pg_to_mysql'),('F','mysql_to_pg')]:put(code,check('Typed real database route','native','test_'+name+'$'))
put('G',check('CSV PostgreSQL real SDK','routes','test_csv_to_pg$'))
put('H',check('TXT MySQL real SDK','routes','test_txt_to_mysql$'))
put('U',check('Remaining file directions','routes','test_csv_to_mysql$','test_txt_to_pg$'))
put('I',check('Explicit cross-database column mapping','native','test_cross_database.py'))
put('J',check('Stable UPSERT across repeated runs','policies','test_key_only_composite_upsert_is_stable_across_three_runs$'))
put('K',check('APPEND preserves committed batches and duplicate semantics','policies','test_new_append_run_can_duplicate_without_unique_constraint$'))
put('L',check('Authorized complete replacement','policies','test_postgres_replacement_and_consumed_once_retry$','test_mysql_replacement_and_consumed_once_retry$'))
put('M AC',check('Replacement failures preserve old target','policies','test_midinsert_failure_rolls_back_whole_replacement$','test_corrupt_complete_dataset_preserves_target_and_never_admits$'))
put('N',check('Real scheduled execution','routes','ScheduledExecutionTests'))
put('O',check('Large dataset exceeds RAM and uses disk batches','memory','test_large_postgres_route_uses_bounded_rss_and_disk_staging$'))
put('P AL',check('Twenty invalid workbooks and explicit ETL schema semantics','registration','test_twenty_invalid_workbooks_have_locations_and_no_validated_tables$'),check('ETL duplicate/orphan/implicit mapping guards','api','test_etl_workbook.py'))
checks['AL']=[*checks['AL'],check('Exact-name implicit mapping without coercion','implicit','test_implicit_mapping_acceptance.py'),check('Blank rows ignored; partial rows reject without partial output','blank','test_fully_blank_rows_are_ignored_but_partial_rows_reject_the_workbook$','test_fully_blank_rows_are_ignored_but_partial_rows_reject_definitions$')]
put('Q',check('Real connection boundary and safe errors','unit','test_connections.py'))
put('R',check('Actual dependency/retry recovery','retry','test_'))
put('S',check('Actual Airflow inventory and dashboard truth','dashboard','test_dashboard_truth.py'),check('Dashboard API and date windows','registration','test_dashboard.py'))
put('T',check('Open correct DAG and verify target from browser','full'))
put('V',check('Disk write failure preserves evidence','ah','test_failed_write_keeps_reservation_and_never_publishes_manifest$'),check('Cancellation rolls back replacement','policies','test_confirmed_cancellation_rolls_back_and_closes_once$'),check('Concurrent writers serialize','native','test_concurrent_runs.py'))
put('W',check('Registration bounded deadline, ownership and parse errors','registration','test_registration.py'),check('Old revision cannot execute after redeploy','revision','test_new_revision_registers_and_old_clear_cannot_write_again$'),check('Admission guards protect external DAGs','api','test_external_even_with_forged_aat_tag_is_not_claimed$'))
put('X',check('Retention protects uncertain datasets','ah','test_uncertain_dataset_is_never_deleted_to_free_capacity$'),check('Settings persist with optimistic revision','registration','test_settings.py'),check('Fresh boot/restart/persistence','restart'))
put('Y',check('Dangerous inputs and secret surfaces','security','test_security_surfaces.py'),check('Macro/ZIP/path workbook guards','unit','test_zip_payloads_and_formula_are_rejected_before_parse_side_effects$'),check('Current API secret redaction','unit','test_log_projection_redacts_actual_encrypted_credentials_and_caps_bytes$'))
put('Z',check('Current English/responsive UI and unavailable states','language'))
put('AA',check('One consistent snapshot under source mutation/loss','ah','test_postgres_snapshot_survives_concurrent_updates_without_primary_key$','test_mysql_snapshot_survives_concurrent_updates_without_primary_key$'))
put('AB',check('Schema/key drift rejected without implicit ALTER','policies','test_postgres_key_drift_and_missing_used_column_fail$','test_mysql_key_drift_and_missing_used_column_fail$'))
put('AD',check('Oversized rows and resource limits','ah','test_postgres_oversized_cell_is_null_on_wire_before_materialization$','test_mysql_oversized_cell_is_null_on_wire_before_materialization$'),check('Large batch/disk measurement','memory','test_large_postgres_route_uses_bounded_rss_and_disk_staging$'))
put('AE',check('NULL/Unicode/decimal/temporal values on real targets','native','test_cross_database.py'),check('Unsafe coercions are rejected','api','test_no_rounding_truncation_timezone_inference_or_invalid_calendar$'))
put('AF',check('Malformed/changed file cannot load','policies','test_bad_full_format_or_changed_checksum_never_loads$'),check('Parser snapshot/revalidation','unit','test_files.py'))
put('AG',check('All strategies reconcile target rows','policies','test_load_policies.py','test_full_refresh.py'))
put('AH',check('io_failure','ah','test_failed_write_keeps_reservation_and_never_publishes_manifest$'),check('checksum_failure','ah','test_corrupt_last_part_is_rejected_before_first_row_is_yielded$'),check('sigkill','ah','test_sigkill_rolls_back_open_target_transaction_without_releasing_quota$'),check('post_commit_recovery','ah','test_missing_staging_after_partial_commit_blocks_until_original_files_return$'))
put('AI',check('Aliases share physical target lock','native','test_concurrent_runs.py'))
put('AJ',check('lost_response','api','test_lost_post_response_is_read_back_without_another_post$','test_response_loss_reconciles_same_file_without_republication$'),check('expired_pending','api','test_expired_worker_cannot_dispatch_file_after_closing_gate$'),check('stale_revision','api','test_revision_changed_during_lookup_blocks_publication$'))
put('AK',check('manual_scheduled','native','test_concurrent_runs.py'),check('utc_iana_dst','api','test_mixed_in_types_duplicate_targets_and_offset_conflict_rejected$'),check('credential_revision','revision','test_postgres_changed_credential_invalidates_before_admission$','test_mysql_changed_credential_invalidates_before_admission$'),check('binding_snapshot','unit','test_active_binding_blocks_location_change_and_keeps_credential_reference$'))
put('AM',check('Fresh startup, phase restart and secret loss fail-closed','restart'))
spec=(root/'specs/001-airflow-automation-tool/spec.md').read_text(encoding='utf8')
case_rows={}
for m in re.finditer(r'^\| ([A-Z]{1,2}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|',spec,re.M):
    code,title,expected,refs=[s.strip() for s in m.groups()]
    if code in checks:case_rows[code]={'case':code,'title':title,'requirements':refs,'expected':expected,'actual':'All listed condition checks have valid PASS receipts and matching selectors. See checks for actual IDs and original execution scope.','status':'PASS','checks':checks[code]}
assert len(case_rows)==39 and set(case_rows)==set(checks)
sc_cases={1:'AM X',2:'A T',3:'C D E F G H U',4:'P AL',5:'J K',6:'L M AC',7:'O AD AH',8:'S',9:'C D E F G H U T W',10:'S Q W',11:'Y',12:' '.join(checks),13:'AA M',14:'AH AI AJ AK',15:'AE'}
success=[]
for m in re.finditer(r'- \*\*(SC-\d{3})\*\*: (.*?)(?=\n- \*\*SC-|\n###|\Z)',spec,re.S):
    code,expected=m.groups();n=int(code[-3:]);cases=sc_cases[n].split()
    success.append({'id':code,'expected':' '.join(expected.split()),'case_ids':cases,'status':'PASS','actual':'Covered by explicit case condition checks and retained current/historical artifact scopes'})
assert len(success)==15
next(row for row in success if row['id']=='SC-010')['checks']=[check('Real HTTP list/detail/preview p95 and connection budget','response','test_list_detail_preview_and_connection_probe_meet_published_budgets$')]
measurement=next(json.loads(re.search(r'RESPONSE_LIMITS_VERIFIED (\{.*\})',line)[1]) for line in registry['response']['observations'] if 'RESPONSE_LIMITS_VERIFIED ' in line)
next(row for row in success if row['id']=='SC-010')['actual']='Measured p95_ms='+str({k:v['p95_ms'] for k,v in measurement['observations'].items()})+'; connection_probe_ms='+str(measurement['connection_probe_ms'])+'; registration deadline/parse guards are in case W'
stories_map={1:'AM X',2:'Q',3:'AF X',4:'A B P AL',5:'N W AJ AK AL',6:'C D E F I O AA AB AD AG AH',7:'G H U AE AF',8:'J K L M R AC AG',9:'N S T W AJ',10:'S Z',11:'X Z'}
stories=[]
for n,codes in stories_map.items():
    m=re.search(r'^\| US-'+str(n).zfill(2)+r' \| ([^|]+) \| ([^|]+) \|',spec,re.M);assert m
    stories.append({'id':'US'+str(n),'requirements':m[1].strip(),'expected':m[2].strip(),'case_ids':codes.split(),'status':'PASS','actual':'Every referenced case has explicit passing condition evidence'})
matrix={'schema_version':2,'status':'PASS_WITH_OWNER_ACCEPTED_KNOWN_RISKS','cases':[case_rows[k] for k in checks], 'success_criteria':success,'stories':stories,
        'business_rules':[{'id':'BR-08','expected':'ONCE/SCHEDULED and confirmed replacement policies remain enforced under uncertainty/retry/revision changes','case_ids':'K L M N AI AJ AK'.split(),'status':'PASS',
            'actual':'ONCE reservations and SCHEDULED scope verified on actual metadata; native overlap and credential invalidation verified through real SDK',
            'checks':[check('Once reservations and scheduled/manual scope','api','test_two_requests_cannot_transfer_one_once$','test_scheduled_is_not_manual_authority$')]}],
        'evidence':registry,'note':'No result inferred from checkbox state. Individual selectors required for suite evidence. Browser/phase receipts retain their detailed artifacts. Historical tests retain original IDs and are not relabeled as current executions.'}
save(base+'acceptance-matrix-v2.json',matrix)
print('T152 matrix v2 built:',len(case_rows),'cases,',len(success),'SC,',len(stories),'stories')
