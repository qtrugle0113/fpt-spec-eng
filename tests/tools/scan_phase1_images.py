"""Scan image archives cô lập; không cấp engine socket hoặc secret volumes cho scanner."""

from collections import Counter
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import subprocess
import uuid

if __package__:
    from .record_image_baseline import image_sources
else:
    from record_image_baseline import image_sources

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.tools/security'
# Trivy0.76.1 đã duyệt; inspect đúng digest dù local store không có mutable tag.
SCANNER = 'ghcr.io/aquasecurity/trivy@sha256:2e6c00d711ab4ae41d8a30c2c1fd3bd3b62704c177bb120f95012e939edfb3df'
TARGETS = {
    'python-build-base':'docker.io/library/python:3.12.16-slim-bookworm',
    'airflow-build-base':'docker.io/apache/airflow:slim-3.3.2-python3.12',
    'airflow-security-stage':'localhost/aat-airflow-security-base:0.1.0',
    'nginx-build-base':'docker.io/library/nginx:1.30.6-alpine3.24',
    'playwright-build-base':'mcr.microsoft.com/playwright:v1.65.0-resolute',
    'go-build-base':'docker.io/library/golang:1.27.3-alpine3.24',
    'node-build-base':'docker.io/library/node:22.23.4-bookworm-slim',
    'frontend-build':'localhost/aat-frontend-build:0.1.0',
    'backend-wheels':'localhost/aat-backend-wheels:0.1.0',
    'airflow-wheels':'localhost/aat-airflow-wheels:0.1.0',
    'e2e-dependencies':'localhost/aat-e2e-dependencies:0.1.0',
    'backend':'localhost/aat-backend:0.1.0',
    'airflow':'localhost/aat-airflow:0.1.0',
    'frontend':'localhost/aat-frontend:0.1.0',
    'postgres':'localhost/aat-postgres:17.11',
    'postgres-build-base':'docker.io/library/postgres:17.11-bookworm',
    'mysql-build-base':'docker.io/library/mysql:8.4.13',
    'gosu-build':'localhost/aat-gosu-build:0.1.0',
    'mysql':'localhost/aat-mysql:8.4.13',
    'backend-tests':'localhost/aat-backend-tests:0.1.0',
    'e2e-tests':'localhost/aat-e2e:0.1.0',
}


def scan() -> None:
    selected = os.environ.get('AAT_SCAN_TARGETS', '')
    targets = TARGETS
    if selected:
        names = selected.split(',')
        if any(name not in TARGETS for name in names):
            raise ValueError('Unknown scan target')
        targets = {name: TARGETS[name] for name in names}
    source_refs = image_sources(ROOT)
    targets = {name: (ref if re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', ref) else source_refs[ref])
               if name.endswith('-build-base') else ref
               for name, ref in targets.items()}
    report_path = (ROOT / os.environ.get('AAT_SCAN_REPORT', 'docs/testing/phase1-security.json')).resolve()
    if not report_path.is_relative_to(ROOT):
        raise ValueError('Scan report must stay in workspace')
    podman = os.environ.get('PODMAN_BIN','podman')
    def run(*args):
        return subprocess.check_output([podman,*args],text=True,encoding='utf-8').strip()
    # Preflight toàn bộ trước khi tạo archive/report volumes; không phụ thuộc mutable tags.
    scanner = json.loads(run('image','inspect',SCANNER))[0]
    assert SCANNER in scanner['RepoDigests'], 'Pinned scanner digest missing from inspect'
    digest = SCANNER
    inspected = {name: json.loads(run('image','inspect',ref))[0] for name,ref in targets.items()}
    for name,data in inspected.items():
        assert (data['Os'], data['Architecture']) == ('linux','amd64'), name
    print(f'SCAN_PREFLIGHT_PASS {len(targets)} targets', flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    prefix = 'aat-phase1-scan-' + uuid.uuid4().hex[:8]
    inputs, reports, cache = (prefix+'-'+name for name in ('input','reports','cache'))
    reused_cache=os.environ.get('AAT_SCAN_CACHE_VOLUME')
    if reused_cache:
        if not re.fullmatch(r'aat-phase1-scan-[0-9a-f]{8}-cache',reused_cache):
            raise ValueError('Only an explicit scanner-owned cache volume may be reused')
        run('volume','inspect',reused_cache)
        cache=reused_cache
    for name in (inputs,reports) if reused_cache else (inputs,reports,cache):
        run('volume','create',name)
    (OUT/'scan-resources.json').write_text(json.dumps({'input':inputs,'reports':reports,'cache':cache},indent=2))
    mountpoint = json.loads(run('volume','inspect',inputs))[0]['Mountpoint']
    assert mountpoint == f'/var/lib/containers/storage/volumes/{inputs}/_data', mountpoint
    records = []
    for name, ref in targets.items():
        data = inspected[name]
        print(f'SCAN_START {name} {data["Id"]}',flush=True)
        run('machine','ssh','sudo','podman','save','--format','docker-archive','--output',f'{mountpoint}/{name}.tar',data['Id'])
        run('run','--rm','--memory','1g','--cpus','2','-v',f'{inputs}:/scan:ro',
            '-v',f'{reports}:/reports','-v',f'{cache}:/root/.cache',digest,
            'image','--input',f'/scan/{name}.tar','--scanners','vuln','--parallel','1',
            '--timeout','10m','--format','json','--output',f'/reports/{name}.json')
        records.append({'name':name,'ref':ref,'image_id':data['Id']})
        print(f'SCAN_COMPLETE {name}',flush=True)
    version = run('run','--rm','-v',f'{cache}:/root/.cache',digest,'--version')
    copy = prefix+'-copy'
    try:
        run('create','--name',copy,'-v',f'{reports}:/reports:ro','--entrypoint','/bin/true',digest)
        run('cp',f'{copy}:/reports/.',str(OUT))
    finally:
        run('rm','-f',copy)
    for record in records:
        data = json.loads((OUT/(record['name']+'.json')).read_text(encoding='utf-8'))
        assert data['Metadata']['ImageID'].removeprefix('sha256:') == record['image_id'].removeprefix('sha256:'), record['name']
        findings = [v for result in data.get('Results',[]) for v in result.get('Vulnerabilities',[])]
        record['counts'] = dict(Counter(v['Severity'] for v in findings))
        record['high_critical'] = [{k:v.get(k) for k in ('VulnerabilityID','PkgName','InstalledVersion','FixedVersion','Severity','PrimaryURL')}
                                   for v in findings if v['Severity'] in ('HIGH','CRITICAL')]
        record['scan_execution'] = 'PASS'
        record['security_assessment'] = 'BLOCKED' if record['high_critical'] else 'PASS'
    summary = {'captured_at':datetime.now(timezone.utc).isoformat(),'scanner':SCANNER,
               'scanner_digest':digest,'scanner_version_db':version,'scope':'OS and language vulnerabilities; all severities, no ignore-unfixed',
               'images':records,'raw_reports':'.tools/security/<name>.json','cache_volume':cache}
    report_path.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    # Chỉ xóa volumes archive/report do lượt scan này tạo; cache DB giữ để tái kiểm.
    run('volume','rm',inputs,reports)
    print(f'SCAN_REPORT_WRITTEN {report_path.relative_to(ROOT)}',flush=True)


if __name__ == '__main__':
    scan()
