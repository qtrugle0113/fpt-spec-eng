"""Scan frozen candidate IDs and current approved runtime baselines in one DB snapshot."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import scan_phase1_images as scanner

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',required=True)
parser.add_argument('--cache-volume')
args=parser.parse_args()
path=(ROOT/args.manifest).resolve()
if not path.is_relative_to(ROOT):parser.error('Manifest must stay in workspace')
manifest=json.loads(path.read_text(encoding='utf-8'))
phase=manifest.get('phase','phase6')
targets={phase+'-'+row['name']:row['image_id'] for row in manifest['images']}
targets.update({'baseline-backend':'b1943b235931110c0fa61e5c8e66111e565efd08fdfe6ffe0e1210b29843b352',
                'baseline-airflow':'b5e9745e9bd836d28b7c085b653a315eaa34832f1cb92491cdf9c8f73cf1d52e',
                'baseline-frontend':'03bd4469931a7e3f0f6681f0158c808864b1acd6e44bcfed9464d87c74754cc8'})
if manifest.get('phase')=='phase7':
    approval=json.loads((ROOT/'docs/decisions/phase6-local-image-approval.json').read_text(encoding='utf-8'))
    targets.update({'baseline-'+row['name']:row['image_id'] for row in approval['images']})
elif manifest.get('phase')=='phase8':
    approval=json.loads((ROOT/'docs/decisions/phase7-local-image-approval.json').read_text(encoding='utf-8'))
    targets.update({'baseline-'+row['target']:row['image_id'] for row in [*approval['images_requiring_new_approval'],*approval['unchanged_approved_images']]})
scanner.TARGETS=targets
os.environ['AAT_SCAN_REPORT']=str((path.parent/'candidate-security.json').relative_to(ROOT))
os.environ.pop('AAT_SCAN_TARGETS',None)
if args.cache_volume:os.environ['AAT_SCAN_CACHE_VOLUME']=args.cache_volume
print(phase.upper()+'_SCAN_START '+str(len(targets))+' exact IDs',flush=True)
with (path.parent/'scan.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):scanner.scan()
print(phase.upper()+'_SCAN_COMPLETE '+os.environ['AAT_SCAN_REPORT']+'; owner mapping remains pending',flush=True)
