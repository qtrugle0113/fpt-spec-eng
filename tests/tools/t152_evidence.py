"""Kiểm bằng chứng từng điều kiện nghiệm thu; không suy PASS từ checkbox."""
import hashlib
import json
import re
from pathlib import Path

MATRIX='docs/testing/resume-20261114/t152-closure/acceptance-matrix-v2.json'

def passed_ids(text):
    values=set(re.findall(r'^(tests/\S+)\s+PASSED\b',text,re.M))
    for test in re.findall(r'^test_\w+\s+\((tests\.[\w.]+)\)\s+\.\.\.\s+ok\b',text,re.M):
        parts=test.split('.');values.add('/'.join(parts[:-2])+'.py::'+parts[-2]+'::'+parts[-1])
    return values

CRITICAL_CONDITIONS={
    'AH':{'io_failure':'test_failed_write_keeps_reservation','checksum_failure':'test_corrupt_last_part',
          'sigkill':'test_sigkill_rolls_back_open_target','post_commit_recovery':'test_missing_staging_after_partial_commit'},
    'AJ':{'lost_response':'test_lost_post_response','expired_pending':'test_expired_worker_cannot_dispatch',
          'stale_revision':'test_revision_changed_during_lookup'},
    'AK':{'manual_scheduled':'test_concurrent_runs.py','utc_iana_dst':'test_mixed_in_types_duplicate_targets',
          'credential_revision':'test_postgres_changed_credential','binding_snapshot':'test_active_binding_blocks_location_change'}}


def validate(root: Path,matrix=None):
    root=root.resolve()
    def read(path,sha=None):
        target=(root/path).resolve()
        if not target.is_relative_to(root):raise ValueError('Evidence outside workspace')
        data=target.read_bytes()
        if sha and hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Evidence checksum changed: '+path)
        return data
    matrix=matrix or json.loads(read(MATRIX))
    required={chr(65+i) for i in range(26)}|{'A'+chr(65+i) for i in range(13)}
    cases={r['case']:r for r in matrix['cases']}
    if set(cases)!=required or len(matrix['cases'])!=39:raise ValueError('Mandatory cases missing or duplicated')
    spec=(root/'specs/001-airflow-automation-tool/spec.md').read_text(encoding='utf8')
    intent={m[1]:(m[3].strip(),m[4].strip()) for m in re.finditer(r'^\| ([A-Z]{1,2}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|',spec,re.M)}
    for key,proof in matrix['evidence'].items():
        receipt=json.loads(read(proof['receipt'],proof['receipt_sha256']))
        if receipt.get('status')!='PASS':raise ValueError('Receipt is not PASS: '+key)
        if 'equivalence_proof' in proof:
            equivalence=json.loads(read(proof['equivalence_proof'],proof['equivalence_sha256']))
            if equivalence['status']!='PASS':raise ValueError('Historical evidence equivalence not verified')
        if 'parent_suite_status' in receipt:
            parent=json.loads(read(receipt['parent_receipt'],receipt['parent_sha256']))
            if parent['status']!=receipt['parent_suite_status']:raise ValueError('Parent suite status changed')
            text=read(receipt['log'],receipt['log_sha256']).decode('utf8')
            selected=set()
            for test in receipt['passed_test_ids']:
                parts=test.split('.');selected.add('/'.join(parts[:-2])+'.py::'+parts[-2]+'::'+parts[-1])
            if not selected<=passed_ids(text):raise ValueError('Selected test was not passed in parent log')
        observed=set();browser_pass=False
        for path,sha in proof['logs_sha256'].items():
            text=read(path,sha).decode('utf8',errors='replace')
            observed.update(passed_ids(text))
            browser_pass=browser_pass or bool(re.search(r'\b[1-9]\d* passed\b',text))
        if not set(proof['passed_selectors'])<=observed:raise ValueError('Declared test ID absent from real logs')
        if proof['kind']=='browser' and not browser_pass:raise ValueError('Browser execution output missing')
        if key=='restart' and (set(receipt.get('phase_restart_runs',{}))!={'EXTRACTION','COMMIT','FULL_REFRESH'} or not receipt.get('canonical_startup')):
            raise ValueError('Phase restart evidence incomplete')
    def verify_check(check):
        proof=matrix['evidence'][check['evidence_id']]
        if check['status']!='PASS' or not check['actual'].strip():raise ValueError('Unverified condition')
        if proof['kind']=='suite' and not check['selectors']:raise ValueError('Suite selector missing')
        if not set(check['selectors'])<=set(proof['passed_selectors']):raise ValueError('Test ID was not passed')
    for code,case in cases.items():
        if (case['expected'],case['requirements'])!=intent[code]:raise ValueError('Acceptance meaning differs from spec: '+code)
        if case['status']!='PASS' or not case['expected'].strip() or not case['actual'].strip() or not case['requirements'].strip():
            raise ValueError('Incomplete acceptance outcome: '+code)
        if not case['checks']:raise ValueError('No condition evidence: '+code)
        for check in case['checks']:
            verify_check(check)
        if code in CRITICAL_CONDITIONS:
            conditions={c['condition']:c for c in case['checks']}
            for name,selector in CRITICAL_CONDITIONS[code].items():
                if name not in conditions or not any(selector in s for s in conditions[name]['selectors']):
                    raise ValueError('Missing exact '+code+' condition: '+name)
    for field,prefix,count in [('success_criteria','SC-',15),('stories','US',11)]:
        rows=matrix[field]
        ids={prefix+(str(i).zfill(3) if prefix=='SC-' else str(i)) for i in range(1,count+1)}
        if len(rows)!=count or {r['id'] for r in rows}!=ids:raise ValueError('Acceptance trace missing: '+field)
        for row in rows:
            if row['status']!='PASS' or not row['expected'].strip() or not row['actual'].strip() or not row['case_ids']:
                raise ValueError('Outcome missing: '+row['id'])
            if not set(row['case_ids'])<=required:raise ValueError('Unknown acceptance case')
            for check in row.get('checks',[]):verify_check(check)
            if row['id']=='SC-010' and not any('test_list_detail_preview_and_connection_probe_meet_published_budgets' in selector
                for check in row.get('checks',[]) for selector in check['selectors']):raise ValueError('Performance measurement proof missing')
    if set(next(r for r in matrix['success_criteria'] if r['id']=='SC-012')['case_ids'])!=required:
        raise ValueError('SC-012 must cover every mandatory case')
    if not any(r['id']=='BR-08' and r['status']=='PASS' and r['case_ids'] for r in matrix['business_rules']):
        raise ValueError('BR-08 evidence missing')
    for row in matrix['business_rules']:
        if not row.get('expected') or not row.get('actual') or not row.get('checks'):raise ValueError('Business rule outcome missing')
        for check in row['checks']:verify_check(check)
    return {'status':'PASS','cases':39,'success_criteria':15,'stories':11,'business_rules':['BR-08'],
            'matrix_sha256':hashlib.sha256(json.dumps(matrix,sort_keys=True).encode()).hexdigest()}


if __name__=='__main__':
    import sys,subprocess
    root=Path(__file__).resolve().parents[2]
    result=validate(root)
    if '--require-tracked' in sys.argv:
        matrix=json.loads((root/MATRIX).read_text(encoding='utf8'))
        required={MATRIX,'specs/001-airflow-automation-tool/spec.md'}
        for proof in matrix['evidence'].values():
            required.add(proof['receipt']);required.update(proof['logs_sha256'])
            if 'equivalence_proof' in proof:required.add(proof['equivalence_proof'])
            receipt=json.loads((root/proof['receipt']).read_text(encoding='utf8'))
            if 'parent_receipt' in receipt:required.update((receipt['parent_receipt'],receipt['log']))
        tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0'))
        missing=required-tracked
        if missing:raise ValueError('Evidence exists locally but is not tracked: '+', '.join(sorted(missing)))
        result['tracked_evidence_files']=len(required)
    print(json.dumps(result))
