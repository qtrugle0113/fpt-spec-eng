"""Prepare exact-ID security deltas for owner review, without granting exceptions."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',required=True)
args=parser.parse_args()
path=(ROOT/args.manifest).resolve()
if not path.is_relative_to(ROOT):parser.error('Manifest must remain in workspace')
manifest=json.loads(path.read_text(encoding='utf-8'))
phase=manifest.get('phase','phase6')
scan=json.loads((path.parent/'candidate-security.json').read_text(encoding='utf-8'))
images={row['name']:row for row in scan['images']}
def key(row):return tuple(row.get(field) for field in ('VulnerabilityID','PkgName','InstalledVersion','Severity'))
comparisons=[]
for name in (('backend-wheels','backend','airflow-wheels','airflow','frontend-build','frontend') if phase in ('phase7','phase8') else ('backend','airflow','frontend')):
    current=images[phase+'-'+name];prior=images['baseline-'+name]
    baseline={key(row) for row in prior['high_critical']}
    candidates={key(row) for row in current['high_critical']}
    comparisons.append({'target':name,'image_id':current['image_id'],'baseline_image_id':prior['image_id'],
        'counts':current['counts'],'shared_high_critical_contexts':len(candidates&baseline),
        'new_high_critical_contexts':[list(value) for value in sorted(candidates-baseline)],
        'removed_high_critical_contexts':[list(value) for value in sorted(baseline-candidates)]})
review={'status':'OWNER_REVIEW_REQUIRED','automatic_risk_acceptance':False,'T014_FULL':'BLOCKED',
    'scope':'Chỉ chuẩn bị delta package/advisory/version/severity; không xác nhận not-affected hoặc phê duyệt image mới.',
    'manifest':str(path.relative_to(ROOT)),'scanner':scan['scanner'],'captured_at':scan['captured_at'],
    'final_images':[row for row in comparisons if row['target'] in ('backend','airflow','frontend')],
    'all_stage_comparisons':comparisons,'all_candidate_images':manifest['images'],
    'build_stage_review':'Các stage build/wheels cần review findings riêng trong candidate-security.json; không dùng runtime baseline để miễn trừ.'}
(path.parent/'owner-review-delta.json').write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
lines=['# Review image '+phase+' — chờ chủ dự án','',
    'Bản source local đã chạy được; quyền local hiện có không tự áp dụng cho image IDs mới.',
    'T014_FULL vẫn BLOCKED. Đây là delta kỹ thuật, không phải approval hoặc security PASS.','',
    '| Image cuối | Image ID | HIGH | CRITICAL | Context mới so baseline runtime |',
    '| --- | --- | --- | --- | --- |']
for row in comparisons:
    lines.append('| '+row['target']+' | `'+row['image_id']+'` | '+str(row['counts'].get('HIGH',0))+' | '+str(row['counts'].get('CRITICAL',0))+' | '+str(len(row['new_high_critical_contexts']))+' |')
lines+=['','Chi tiết context mới/đã bỏ và cả sáu stage candidate trong [delta](owner-review-delta.json).',
    'Các finding đầy đủ, counts và snapshot scanner trong [scan](candidate-security.json).',
    'Payload wheel đã đối chiếu mã hiện tại trong [kiểm chứng package](packaged-source.json).','',
    'Quy tắc hiện hành tại `docs/proposals/t014-conditional-local-gate.md`: “owner phải ký delta trước mốc tiếp theo”.',
    'Cần quyết định riêng cho đúng image IDs/context, giữ hạn/controls local; không tự mở gate tiếp theo hoặc miễn trừ findings.']
(path.parent/'owner-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'status':review['status'],'final_images':[{k:row[k] for k in ('target','counts')} for row in comparisons]}))
