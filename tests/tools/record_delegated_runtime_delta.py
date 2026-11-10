"""Record the continuation owner's delegated decision for a reviewed exact runtime delta."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True)
args=parser.parse_args();path=(ROOT/args.manifest).resolve()
if not path.is_relative_to(ROOT):parser.error('Manifest must stay in workspace')
manifest=json.loads(path.read_text(encoding='utf-8'));review=json.loads((path.parent/'owner-review-delta.json').read_text(encoding='utf-8'))
payload=json.loads((path.parent/'packaged-source.json').read_text(encoding='utf-8'))
delegation=json.loads((ROOT/'docs/decisions/continuation-autonomy-20261111.json').read_text(encoding='utf-8'))
baseline=json.loads((ROOT/delegation['local_approval_reference']).read_text(encoding='utf-8'))
if delegation['status']!='EXPLICIT_USER_DELEGATION' or datetime.now(timezone.utc)>=datetime.fromisoformat(baseline['expires_at']):
    raise RuntimeError('The explicit conditional local delegation is unavailable or expired')
if manifest.get('phase')!='phase8' or payload['status']!='PASS':raise RuntimeError('Reviewed Phase8 payload proof required')
stages=review['all_stage_comparisons']
if len(stages)!=6 or any(row['new_high_critical_contexts'] for row in stages):
    raise RuntimeError('New-context or incomplete deltas require a separate concrete proposal')
if {row['image_id'] for row in stages}!={row['image_id'] for row in manifest['images']}:
    raise RuntimeError('Review and candidate image IDs differ')
decision={'status':'USER_DELEGATED_EXACT_LOCAL_DELTA_APPROVAL','recorded_at':datetime.now(timezone.utc).isoformat(),
    'authority':delegation['authority'],'delegation_record':'docs/decisions/continuation-autonomy-20261111.json',
    'scope':'Exact reviewed Phase8 runtime/build IDs, unchanged local controls, no public deployment or blanket approval',
    'images':manifest['images'],'stage_deltas':stages,'expires_at':baseline['expires_at'],'review_due':baseline['review_due'],
    'T014_FULL':'BLOCKED','security':'FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS',
    'artifact_sha256':{name:hashlib.sha256((path.parent/name).read_bytes()).hexdigest() for name in
        ('candidate-images.json','candidate-security.json','owner-review-delta.json','packaged-source.json','source-sha256.json')}}
target=ROOT/'docs/decisions/phase8-local-image-approvals.json'
records=json.loads(target.read_text(encoding='utf-8')) if target.exists() else []
if any({r['image_id'] for r in old['images']}=={r['image_id'] for r in decision['images']} for old in records):
    raise RuntimeError('Decision already recorded; history must not be overwritten')
records.append(decision);target.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(path.parent/'delegated-decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':decision['status'],'phase':'phase8','new_high_critical_contexts':0}))
