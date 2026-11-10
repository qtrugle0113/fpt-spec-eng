"""Apply the owner's explicit delegated decision only to a zero-new-context test delta."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True)
args=parser.parse_args();path=(ROOT/args.manifest).resolve()
if not path.is_relative_to(ROOT):parser.error('Manifest must stay in workspace')
delegation=json.loads((ROOT/'docs/decisions/continuation-autonomy-20261111.json').read_text(encoding='utf-8'))
approval=json.loads((ROOT/delegation['local_approval_reference']).read_text(encoding='utf-8'))
if delegation['status']!='EXPLICIT_USER_DELEGATION' or datetime.now(timezone.utc)>=datetime.fromisoformat(approval['expires_at']):
    raise RuntimeError('The explicit local delegation is unavailable or expired')
manifest=json.loads(path.read_text(encoding='utf-8'));scan=json.loads((path.parent/'candidate-security.json').read_text(encoding='utf-8'))
records={row['name']:row for row in scan['images']};current=records['regression-candidate'];baseline=records['baseline-tests']
if current['image_id']!=manifest['image_id']:raise RuntimeError('Exact image mismatch')
def keys(row):return {tuple(item.get(key) for key in ('VulnerabilityID','PkgName','InstalledVersion','Severity')) for item in row['high_critical']}
if keys(current)-keys(baseline):raise RuntimeError('A new-context proposal is required before applying any delegated decision')
decision={'status':'USER_DELEGATED_EXACT_LOCAL_DELTA_APPROVAL','recorded_at':datetime.now(timezone.utc).isoformat(),
    'authority':delegation['authority'],'delegation_record':'docs/decisions/continuation-autonomy-20261111.json',
    'image_id':current['image_id'],'baseline_image_id':baseline['image_id'],'counts':current['counts'],
    'new_high_critical_contexts':[],'recommended_decision_applied':'Approve this exact test-only delta under unchanged conditional local controls',
    'expires_at':approval['expires_at'],'review_due':approval['review_due'],'T014_FULL':'BLOCKED',
    'artifact_sha256':{name:hashlib.sha256((path.parent/name).read_bytes()).hexdigest() for name in ('candidate.json','candidate-security.json','source-sha256.json')}}
destination=ROOT/'docs/decisions/phase8-regression-local-approvals.json'
prior=json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else []
if any(item['image_id']==decision['image_id'] for item in prior):raise RuntimeError('Decision already recorded; do not overwrite history')
prior.append(decision);destination.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(path.parent/'delegated-review.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':decision['status'],'image_id':decision['image_id'],'counts':decision['counts']}))
