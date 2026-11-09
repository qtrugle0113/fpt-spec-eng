"""Scan every distinct affected runtime/build-stage ID without expanding approval."""
import contextlib
import json
import os
from pathlib import Path
import scan_phase1_images as scanner

ROOT=Path(__file__).resolve().parents[2]
manifest=json.loads((ROOT/'docs/testing/phase2-candidate-images.json').read_text())
unique={}
for image in manifest['images']:
    unique.setdefault(image['image_id'],image)
scanner.TARGETS={'phase2-'+image['name']:image['ref'] for image in unique.values()}
os.environ['AAT_SCAN_REPORT']='docs/testing/phase2-candidate-security.json'
os.environ.pop('AAT_SCAN_TARGETS',None)
print('SCAN_PHASE2_START '+str(len(unique))+' distinct image IDs; all build stage aliases covered',flush=True)
with (ROOT/'docs/testing/t014-round2-logs/phase2-candidate-scan.log').open('w',encoding='utf-8') as log:
    with contextlib.redirect_stdout(log):scanner.scan()
print('SCAN_PHASE2_COMPLETE; raw findings retained, acceptance pending owner review',flush=True)
