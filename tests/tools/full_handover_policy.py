"""Kiểm approval nghiệm thu exact snapshot; không thay đổi kết quả scanner."""
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path

DECISION = 'docs/decisions/t014-owner-review-20261114.json'


def validate(root: Path, images: dict, now=None):
    root = root.resolve()
    now = now or datetime.now(timezone.utc)

    def read(relative, digest=None):
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Evidence path outside workspace')
        raw = path.read_bytes()
        if digest and hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Approved evidence changed: ' + relative)
        return raw

    decision = json.loads(read(DECISION))
    if (decision['status'] != 'OWNER_ACCEPTED_KNOWN_RISKS'
            or decision['governance_approval'] != 'OWNER_APPROVED'
            or decision['revoked'] is not False):
        raise ValueError('Owner approval unavailable or revoked')
    if now >= datetime.fromisoformat(decision['expires_at']):
        raise ValueError('Owner approval expired')
    if now.astimezone(timezone(timedelta(hours=9))).date().isoformat() >= decision['review_due']:
        raise ValueError('Owner review due; new review required')
    if decision['expires_at'] != '2026-11-23T00:00:00+09:00' or decision['review_due'] != '2026-11-16':
        raise ValueError('Approval deadline changed')
    if decision['controls'] != {'operator_count': 1, 'exposure': 'loopback', 'data': 'synthetic',
                                'public_deploy': False, 'important_data': False}:
        raise ValueError('Approval scope changed')
    constitution = read('.specify/memory/constitution.md', decision['constitution_sha256'])
    if b'2.0.0' not in constitution:
        raise ValueError('Approved governance missing')
    read(decision['governance_proposal'], decision['proposal_sha256'])
    packet = json.loads(read(decision['scope_packet'], decision['scope_packet_sha256']))
    targets = {row['name']: row for row in packet['targets']}
    if len(targets) != decision['targets'] or len(packet['groups']) != decision['groups']:
        raise ValueError('Review scope count mismatch')
    actual = Counter()
    for name, row in targets.items():
        raw = json.loads(read(row['raw_path'], row['raw_sha256']))
        if raw['Metadata']['ImageID'].removeprefix('sha256:') != row['image_id'].removeprefix('sha256:'):
            raise ValueError('Raw scan image mismatch')
        for result in raw.get('Results', []):
            for item in result.get('Vulnerabilities', []):
                if item['Severity'] in ('HIGH', 'CRITICAL'):
                    actual[(name, item['VulnerabilityID'], item['PkgName'],
                            item['InstalledVersion'], item['Severity'])] += 1
    expected = Counter()
    for group in packet['groups']:
        for context in group['contexts']:
            if context['image'] != targets[context['target']]['image_id']:
                raise ValueError('Reviewed context image mismatch')
            expected[(context['target'], group['advisory'], group['package'],
                      group['version'], group['severity'])] += 1
    if actual != expected or sum(actual.values()) != decision['occurrences']:
        raise ValueError('Reviewed finding context mismatch')
    aliases = {'tests': 'backend-tests', 'e2e': 'e2e-tests', 'workbook_deps': 'backend'}
    for name, image in images.items():
        target = aliases.get(name, name)
        if target not in targets or targets[target]['image_id'] != image.removeprefix('sha256:'):
            raise ValueError('Artifact outside owner approval: ' + name)
    return {'status': 'OWNER_ACCEPTED_KNOWN_RISKS', 'scan_security_clean': False,
            'approval': DECISION, 'packet_sha256': decision['scope_packet_sha256'],
            'targets': len(targets), 'finding_occurrences': sum(actual.values()),
            'expires_at': decision['expires_at'], 'review_due': decision['review_due']}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    decision = json.loads((root / DECISION).read_text(encoding='utf8'))
    packet = json.loads((root / decision['scope_packet']).read_text(encoding='utf8'))
    print(json.dumps(validate(root, {row['name']: row['image_id'] for row in packet['targets']})))
