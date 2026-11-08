"""Ghi digest thật của bảy base/build/browser images; không đổi version pin."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REFS = (
    'docker.io/library/golang:1.27.3-bookworm',
    'docker.io/library/python:3.12.16-slim-bookworm',
    'docker.io/apache/airflow:slim-3.3.2-python3.12',
    'docker.io/library/postgres:17.11-bookworm',
    'docker.io/library/mysql:8.4.13',
    'docker.io/library/node:22.23.4-bookworm-slim',
    'docker.io/library/nginx:1.30.6-alpine3.24',
    'mcr.microsoft.com/playwright:v1.56.1-noble',
)


def record() -> None:
    podman = os.environ.get('PODMAN_BIN','podman')
    entries = []
    for ref in REFS:
        data = json.loads(subprocess.check_output([podman,'image','inspect',ref],text=True))[0]
        assert (data['Os'],data['Architecture']) == ('linux','amd64'), ref
        candidates = [value for value in data['RepoDigests'] if value.startswith(ref.rsplit(':',1)[0]+'@sha256:')]
        assert candidates, f'No registry digest captured for {ref}'
        entries.append({'ref':ref,'repo_digest':candidates[0], 'image_id':data['Id'],'platform':'linux/amd64'})
    output = {'schema':1,'captured_at':datetime.now(timezone.utc).isoformat(), 'images':entries}
    (ROOT/'docker/images.lock').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(f'Recorded {len(entries)} real image digests')


if __name__ == '__main__':
    record()
