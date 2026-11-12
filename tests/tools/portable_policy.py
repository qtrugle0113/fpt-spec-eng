"""Compare fresh artifact scans with previously approved, target-specific policy."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def finding_key(row):
    return tuple(row.get(k) for k in ('VulnerabilityID','PkgName','InstalledVersion','Severity'))


def compare_findings(target, findings, allowed):
    return [r for r in findings if finding_key(r) not in allowed.get(target,set())]


def verified_json(path, expected):
    data=path.read_bytes()
    # Git may check out Windows-generated evidence with LF. Reconstruct only
    # the two line-ending representations; never reserialize JSON or ignore
    # differences in values, whitespace or field order.
    lf=data.replace(b'\r\n',b'\n')
    representations=(data,lf,lf.replace(b'\n',b'\r\n'))
    if not any(hashlib.sha256(value).hexdigest()==expected for value in representations):
        raise ValueError('Approved evidence hash mismatch: '+str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def check_expiry(expires_at, now=None):
    if (now or datetime.now(timezone.utc)) >= datetime.fromisoformat(expires_at):
        raise ValueError('Conditional local approval expired')


def load_policy():
    approval=json.loads((ROOT/'docs/decisions/phase7-local-image-approval.json').read_text(encoding='utf-8'))
    if approval.get('approved') is not True or approval['status']!='OWNER_APPROVED_EXACT_LOCAL_DELTA':
        raise ValueError('Local approval revoked or unavailable')
    check_expiry(approval['expires_at'])
    allowed={}
    source=ROOT/'docs/testing/resume-20261111/phase7-candidates-57ede3cf/candidate-security.json'
    report=verified_json(source,approval['reviewed_artifact_sha256']['candidate-security.json'])
    approved={r['image_id']:r['target'] for r in approval['images_requiring_new_approval']+approval['unchanged_approved_images']}
    for row in report['images']:
        if row['image_id'] in approved:
            allowed.setdefault(approved[row['image_id']],set()).update(finding_key(r) for r in row['high_critical'])
    runner_approvals=json.loads((ROOT/'docs/decisions/phase8-regression-local-approvals.json').read_text(encoding='utf-8'))
    runner_sources=[]
    for record in runner_approvals:
        check_expiry(record['expires_at'])
        expected=record['artifact_sha256']['candidate-security.json']
        for candidate in (ROOT/'docs/testing/resume-20261111').glob('regression-candidate-*/candidate-security.json'):
            try:runner_report=verified_json(candidate,expected)
            except ValueError:continue
            matching=[r for r in runner_report['images'] if r['image_id']==record['image_id']]
            if len(matching)!=1:raise ValueError('Approved runner scan identity missing')
            allowed.setdefault('backend-tests',set()).update(finding_key(r) for r in matching[0]['high_critical'])
            runner_sources.append({'path':str(candidate.relative_to(ROOT)),'approved_sha256':expected})
            break
        else:raise ValueError('Approved runner scan evidence unavailable')
    ledger=json.loads((ROOT/'docs/decisions/t014-local-approved-findings.json').read_text(encoding='utf-8'))
    if ledger['D2']!='APPROVED_147_C_GROUPS_ONLY': raise ValueError('Approved ledger unavailable')
    for entry in ledger['entries']:
        if entry.get('approved') is not True or entry['category']!='PROPOSED_TEMPORARY_RISK_ACCEPTANCE':continue
        for row in entry['contexts']:
            key=(entry['advisory'],row['package'],row['installed'],row['severity'])
            allowed.setdefault(row['target'],set()).add(key)
    extra_path=ROOT/'docs/decisions/portable-local-finding-approvals.json'
    extra_proof=[]
    if extra_path.exists():
        for extra in json.loads(extra_path.read_text(encoding='utf-8')):
            if extra['status']!='OWNER_APPROVED_PORTABLE_LOCAL_FINDINGS':raise ValueError('Unapproved finding decision')
            check_expiry(extra['expires_at'])
            if datetime.fromisoformat(extra['expires_at'])>datetime.fromisoformat(approval['expires_at']):
                raise ValueError('Finding decision may not extend local expiry')
            proposal=ROOT/extra['proposal']
            if not proposal.resolve().is_relative_to(ROOT):raise ValueError('Proposal outside workspace')
            concrete=verified_json(proposal,extra['proposal_sha256'])
            for row in concrete['requested_contexts']:
                allowed.setdefault(row['target'],set()).add(finding_key(row))
            extra_proof.append({'decision':'docs/decisions/portable-local-finding-approvals.json',
                'decision_sha256':hashlib.sha256(extra_path.read_bytes()).hexdigest(),
                'proposal':extra['proposal'],'proposal_sha256':extra['proposal_sha256']})
    return allowed, {'approval':'docs/decisions/phase7-local-image-approval.json',
        'approval_sha256':hashlib.sha256((ROOT/'docs/decisions/phase7-local-image-approval.json').read_bytes()).hexdigest(),
        'approved_scan':str(source.relative_to(ROOT)),
        'approved_scan_sha256':approval['reviewed_artifact_sha256']['candidate-security.json'],
        'approved_runner_scans':runner_sources,
        'additional_owner_decisions':extra_proof,
        'ledger':'docs/decisions/t014-local-approved-findings.json',
        'ledger_sha256':hashlib.sha256((ROOT/'docs/decisions/t014-local-approved-findings.json').read_bytes()).hexdigest(),
        'hash_representation':'Exact raw, LF or CRLF bytes; JSON values never reserialized',
        'expires_at':approval['expires_at'],'review_due':approval['review_due']}


def not_affected_zlib(target, finding, actual_hash, contexts):
    return finding['VulnerabilityID']=='CVE-2023-45853' and finding['Severity']=='CRITICAL' and any(
        row['target']==target and row['scanner_package']==finding['PkgName']
        and row['installed']==finding['InstalledVersion'] and row['libz_sha256']==actual_hash
        for row in contexts)
