"""Tổng hợp evidence hiện có; không scan mới, không phê duyệt finding."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/testing/resume-20261114/full-baseline-final'
scan_path = BASE / 'candidate-security.json'
scan = json.loads(scan_path.read_text(encoding='utf8'))
groups = {}
targets = []
for image in scan['images']:
    path = BASE / 'raw-reports' / (image['name'] + '.json')
    raw = json.loads(path.read_text(encoding='utf8'))
    assert raw['Metadata']['ImageID'].removeprefix('sha256:') == image['image_id'].removeprefix('sha256:')
    findings = [(r, v) for r in raw.get('Results', []) for v in r.get('Vulnerabilities', [])
                if v['Severity'] in ('HIGH', 'CRITICAL')]
    assert len(findings) == len(image['high_critical']), image['name']
    targets.append({'name': image['name'], 'image_id': image['image_id'],
                    'raw_report': path.relative_to(ROOT).as_posix(),
                    'raw_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'occurrences': len(findings)})
    for result, finding in findings:
        key = (finding['VulnerabilityID'], finding['PkgName'], finding['InstalledVersion'],
               finding.get('FixedVersion') or '', finding['Severity'])
        group = groups.setdefault(key, {
            'advisory': key[0], 'package': key[1], 'installed': key[2], 'fixed': key[3] or None,
            'severity': key[4], 'source_url_from_scan': finding.get('PrimaryURL'),
            'vendor_status': finding.get('Status'),
            'disposition': 'PENDING_REMEDIATION_OR_AUTHORIZED_REVIEW',
            'action': ('Compare fixed package with locks/constraints; rebuild and rescan exact artifacts'
                       if key[3] else 'Vendor fix/backport or authorized review required; absence of FixedVersion is not not-affected'),
            'contexts': []})
        group['contexts'].append({'target': image['name'], 'image_id': image['image_id'],
                                  'package_target': result.get('Target'), 'type': result.get('Type'),
                                  'package_path': finding.get('PkgPath'), 'layer': finding.get('Layer')})
packet = {'status': 'BLOCKED', 'scope': 'All HIGH/CRITICAL in existing 21-target scan; no new scan or approval',
          'source_scan': scan_path.relative_to(ROOT).as_posix(),
          'source_scan_sha256': hashlib.sha256(scan_path.read_bytes()).hexdigest(),
          'target_count': len(targets), 'occurrences': sum(t['occurrences'] for t in targets),
          'group_count': len(groups), 'groups_with_fixed_version': sum(bool(k[3]) for k in groups),
          'groups_without_fixed_version': sum(not k[3] for k in groups),
          'targets': targets, 'groups': list(groups.values())}
(HERE / 'security-review-packet.json').write_text(json.dumps(packet, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: v for k,v in packet.items() if k not in ('groups', 'targets')}, indent=2))
