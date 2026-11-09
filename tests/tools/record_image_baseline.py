"""Ghi digest base/build/browser tá»« chÃ­nh FROM Ä‘Ã£ khÃ³a, khÃ´ng resolve láº¡i mutable tag."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILES = (
    'backend/Dockerfile', 'frontend/Dockerfile', 'airflow/docker/Dockerfile',
    'docker/tests/Dockerfile', 'docker/tests/playwright.Dockerfile', 'docker/gosu/Dockerfile',
)


def image_sources(root: Path = ROOT) -> dict[str, str]:
    """Map tag mÃ´ táº£ sang FROM immutable; phÃ¡t hiá»‡n pin thiáº¿u hoáº·c mÃ¢u thuáº«n trÆ°á»›c runtime."""
    sources: dict[str, str] = {}
    for relative in DOCKERFILES:
        stages: set[str] = set()
        for line in (root / relative).read_text(encoding='utf-8').splitlines():
            words = line.split()
            if not words or words[0].upper() != 'FROM':
                continue
            position = 2 if words[1].startswith('--platform=') else 1
            source = words[position]
            if source.lower() not in stages and source.lower() != 'scratch':
                if not re.fullmatch(r'[^\s@]+:[^\s@]+@sha256:[0-9a-f]{64}', source):
                    raise ValueError(f'{relative}: FROM must include an exact tag and sha256: {source}')
                ref = source.split('@', 1)[0]
                if sources.get(ref, source) != source:
                    raise ValueError(f'Conflicting FROM digests for {ref}')
                sources[ref] = source
            if len(words) > position + 2 and words[position + 1].upper() == 'AS':
                stages.add(words[position + 2].lower())
    return sources


def validate_lock(lock: dict, root: Path = ROOT) -> None:
    sources = image_sources(root)
    entries = {entry['ref']: entry for entry in lock['images']}
    if len(entries) != len(lock['images']) or entries.keys() != sources.keys():
        raise ValueError('Image lock must cover exactly the unique Dockerfile base references')
    for ref, source in sources.items():
        entry = entries[ref]
        repository = ref.rsplit(':', 1)[0]
        if entry['repo_digest'] != repository + '@' + source.split('@', 1)[1]:
            raise ValueError(f'Image lock digest differs from FROM: {ref}')
        if entry['platform'] != 'linux/amd64':
            raise ValueError(f'Unexpected image platform: {ref}')


def record() -> None:
    podman = os.environ.get('PODMAN_BIN','podman')
    entries = []
    for ref, source in image_sources().items():
        data = json.loads(subprocess.check_output([podman,'image','inspect',source],text=True))[0]
        assert (data['Os'],data['Architecture']) == ('linux','amd64'), ref
        digest = ref.rsplit(':', 1)[0] + '@' + source.split('@', 1)[1]
        assert digest in data['RepoDigests'], f'Pinned FROM digest missing from inspect: {source}'
        entries.append({'ref':ref,'repo_digest':digest, 'image_id':data['Id'],'platform':'linux/amd64'})
    output = {'schema':1,'captured_at':datetime.now(timezone.utc).isoformat(), 'images':entries}
    validate_lock(output)
    (ROOT/'docker/images.lock').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(f'Recorded {len(entries)} real image digests')


if __name__ == '__main__':
    record()
