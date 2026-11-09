"""Kiểm hash trước giải mã deb, cài backport cố định trong RUN không có mạng."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys


def install(directory: Path) -> None:
    policy = json.loads((directory / 'brotli.lock.json').read_text(encoding='utf8'))
    identity = (policy['package'], policy['version'], policy['architecture'])
    if identity != ('libbrotli1', '1.0.9-2+deb12u1', 'amd64'):
        raise ValueError('Unapproved offline security patch identity')
    archive = directory / 'libbrotli1.deb'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != policy['sha256']:
        raise ValueError('Offline security patch SHA256 mismatch')
    # Chỉ giải mã/cài deb sau khi kiểm hash; không apt/resolver/network fallback.
    subprocess.run(['dpkg', '-i', str(archive)], check=True)
    result = subprocess.run(
        ['dpkg-query', '-W', '-f=${Version}', 'libbrotli1'],
        check=True, text=True, capture_output=True)
    if result.stdout.strip() != policy['version']:
        raise RuntimeError('Installed offline security patch version mismatch')
    archive.unlink()
    print('BROTLIPATCH_OFFLINE_VERIFIED_1.0.9-2+deb12u1')


if __name__ == '__main__':
    install(Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/opt/aat/security'))
