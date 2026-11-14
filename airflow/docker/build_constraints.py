"""Tạo constraints hiệu lực từ upstream bất biến và các ngoại lệ đã duyệt."""

import hashlib
import json
from pathlib import Path
import sys

APPROVED = {'certifi': ('2026.7.22', '2026.10.18'), 'urllib3': ('2.7.0', '2.8.0'),
            'dnspython': ('2.8.0', '2.9.2')}


def derive_constraints(upstream: bytes, policy: dict) -> bytes:
    if hashlib.sha256(upstream).hexdigest() != policy['upstream_sha256']:
        raise ValueError('Upstream constraints SHA256 mismatch')
    overrides = policy['overrides']
    if set(overrides) != set(APPROVED):
        raise ValueError('Only the approved dependency overrides are allowed')
    effective = upstream
    for name, (old, new) in APPROVED.items():
        override = overrides[name]
        if (override['from'], override['to']) != (old, new):
            raise ValueError(f'Override outside approved policy: {name}')
        original = f'{name}=={old}'.encode()
        if upstream.splitlines().count(original) != 1:
            raise ValueError(f'Expected exactly one upstream pin: {name}')
        effective = b''.join(
            line.replace(original, f'{name}=={new}'.encode(), 1)
            if line.rstrip(b'\r\n') == original else line
            for line in effective.splitlines(keepends=True)
        )
    return effective


def build(directory: Path) -> None:
    upstream = (directory / 'constraints-3.12.txt').read_bytes()
    policy_bytes = (directory / 'constraints-policy.json').read_bytes()
    policy = json.loads(policy_bytes)
    effective = derive_constraints(upstream, policy)
    (directory / 'constraints-effective-3.12.txt').write_bytes(effective)
    provenance = {
        'upstream_sha256': hashlib.sha256(upstream).hexdigest(),
        'policy_sha256': hashlib.sha256(policy_bytes).hexdigest(),
        'effective_sha256': hashlib.sha256(effective).hexdigest(),
        'overrides': policy['overrides'],
    }
    (directory / 'constraints-provenance.json').write_text(
        json.dumps(provenance, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/opt/aat'))
