"""Scan every newly resolved artifact; compare policy without old image storage."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import scan_phase1_images as scanner
from portable_policy import load_policy, compare_findings, not_affected_zlib

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',required=True)
parser.add_argument('--cache-volume')
parser.add_argument('--review-only',action='store_true',help='Re-evaluate an existing scan of these exact artifacts without rescanning')
parser.add_argument('--reuse-scan',help='Reuse completed scan rows only for identical artifact IDs, verified by the prior receipt')
args=parser.parse_args()
path=(ROOT/args.manifest).resolve()
if not path.is_relative_to(ROOT):parser.error('Manifest must stay in workspace')
manifest=json.loads(path.read_text(encoding='utf-8'))
allowed,provenance=load_policy()
scanner.TARGETS={row['name']:row['image_id'] for row in manifest['images']}
all_targets=dict(scanner.TARGETS)
reused=[]
reuse_provenance=None
if args.reuse_scan:
    prior_path=(ROOT/args.reuse_scan).resolve()
    if not prior_path.is_relative_to(ROOT):parser.error('Prior scan must stay in workspace')
    receipt=json.loads((prior_path.parent/'local-policy-review.json').read_text(encoding='utf-8'))
    if hashlib.sha256(prior_path.read_bytes()).hexdigest()!=receipt['scan_sha256']:
        raise ValueError('Prior scan receipt hash mismatch')
    prior=json.loads(prior_path.read_text(encoding='utf-8'))
    if prior['scanner_digest']!=scanner.SCANNER:raise ValueError('Prior scanner differs')
    from datetime import datetime,timezone,timedelta
    if datetime.now(timezone.utc)-datetime.fromisoformat(prior['captured_at'])>timedelta(hours=24):
        raise ValueError('Prior artifact scan is older than24hours; scan again')
    reused=[r for r in prior['images'] if all_targets.get(r['name'])==r['image_id'] and r['scan_execution']=='PASS']
    reuse_provenance={'path':str(prior_path.relative_to(ROOT)),'sha256':receipt['scan_sha256'],
        'captured_at':prior['captured_at'],'scanner_version_db':prior['scanner_version_db']}
    scanner.TARGETS={name:identity for name,identity in all_targets.items() if name not in {r['name'] for r in reused}}
os.environ['AAT_SCAN_REPORT']=str((path.parent/'candidate-security.json').relative_to(ROOT))
os.environ.pop('AAT_SCAN_TARGETS',None)
if args.cache_volume:os.environ['AAT_SCAN_CACHE_VOLUME']=args.cache_volume
if not args.review_only and scanner.TARGETS:
    print('PORTABLE_SCAN_START '+str(len(scanner.TARGETS))+' artifacts; no previous-machine images required',flush=True)
    with (path.parent/'scan.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):scanner.scan()
scan=(dict(prior,images=[]) if reused and not scanner.TARGETS and not args.review_only
      else json.loads((path.parent/'candidate-security.json').read_text(encoding='utf-8')))
if reused and not args.review_only:
    scan['images']+=reused
    scan['reused_exact_artifact_scans']=reuse_provenance
    (path.parent/'candidate-security.json').write_text(json.dumps(scan,indent=2)+'\n',encoding='utf-8')
if {r['name']:r['image_id'] for r in scan['images']}!=all_targets or any(r['scan_execution']!='PASS' for r in scan['images']):
    raise ValueError('Completed scan must cover exactly the current artifact manifest')
rows=[]
activation=json.loads((ROOT/'docs/decisions/t014-local-activation.json').read_text(encoding='utf-8'))
expected_zlib=activation['LEX-079']['baseline_contexts'][0]['libz_sha256']
for item in scan['images']:
    unknown=compare_findings(item['name'],item['high_critical'],allowed)
    binary_proof=None
    zlib=[r for r in item['high_critical'] if r['VulnerabilityID']=='CVE-2023-45853']
    if zlib:
        name='aat-zlib-inspect-'+secrets.token_hex(4)
        try:
            subprocess.run(['podman','create','--name',name,'--network','none','--entrypoint','/bin/true',item['image_id']],check=True,capture_output=True)
            with tempfile.TemporaryDirectory() as folder:
                local=Path(folder)/'libz.so'
                copy=subprocess.run(['podman','cp',name+':/lib/x86_64-linux-gnu/libz.so.1.2.13',str(local)],capture_output=True)
                actual=hashlib.sha256(local.read_bytes()).hexdigest() if copy.returncode==0 else None
            binary_proof={'expected_sha256':expected_zlib,'actual_sha256':actual,'status':'PASS' if actual==expected_zlib else 'BLOCKED'}
            unknown=[r for r in unknown if not not_affected_zlib(item['name'],r,actual,activation['LEX-079']['baseline_contexts'])]
            if actual!=expected_zlib:unknown+= [r for r in zlib if r not in unknown]
        finally:subprocess.run(['podman','rm','-f',name],capture_output=True)
    rows.append({'target':item['name'],'image_id':item['image_id'],'counts':item['counts'],
        'unknown_high_critical':unknown,'not_affected_binary_proof':binary_proof})
blocked=any(row['unknown_high_critical'] for row in rows)
result={'status':'BLOCKED' if blocked else 'LOCAL_POLICY_MATCH',
    'security':'FAIL_WITH_UNAPPROVED_FINDINGS' if blocked else 'FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS',
    'comparison':'Fresh artifact scan against approved policy; not a same-snapshot delta',
    'policy_provenance':provenance,'images':rows,'T014_FULL':'BLOCKED','existing_services_modified':False,
    'scan_sha256':hashlib.sha256((path.parent/'candidate-security.json').read_bytes()).hexdigest(),
    'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(path.parent/'local-policy-review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(result['status'],flush=True)
raise SystemExit(2 if blocked else 0)
