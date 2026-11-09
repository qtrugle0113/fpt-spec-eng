"""T018 source-only checks on approved images, network none; no service replacement."""

import argparse
from pathlib import Path
import secrets
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--phase', choices=['red', 'green'], required=True)
parser.add_argument('--backend', action='store_true', help='Run schema/HTTP checks with exact backend test-runner dependencies')
parser.add_argument('--foundation-http',action='store_true')
parser.add_argument('--image',help='Explicit image reference for a rebuilt environment')
parser.add_argument('--evidence-dir',help='Workspace-relative output directory; preserves historical evidence')
parser.add_argument('--http-evidence',default='docs/testing/phase2-http-evidence.json')
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[2]
image = ('89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4' if args.backend
         else '399adacf113fd269d4dd5d587b956a9167bc02ef8f656d3ff9ef94e11039e2fc')
if args.image:image=args.image
evidence_dir=(ROOT/args.evidence_dir).resolve() if args.evidence_dir else None
if evidence_dir and not evidence_dir.is_relative_to(ROOT):parser.error('Evidence directory must stay in workspace')
if evidence_dir:evidence_dir.mkdir(parents=True,exist_ok=True)
name = 'aat-t018-' + secrets.token_hex(4)
created = False


def run(*args):
    return subprocess.check_output(['podman', *args], text=True, encoding='utf-8').strip()


try:
    selectors = ['tests.unit.test_common_schemas', 'tests.integration.test_health_source']
    if not args.backend:
        selectors += ['tests.api.test_health_contract', 'tests.api.test_openapi_contract']
    if args.foundation_http:selectors=['tests.api.test_foundation_contract']
    run('create', '--name', name, '--network=none', '--memory', '512m', '--workdir', '/tmp',
        '-e', 'PYTHONPATH=/tmp/backend/src:/tmp/packages:/tmp', '--entrypoint', 'python', image,
        '-m', 'unittest', *selectors, '-v')
    created = True
    for source in ('backend', 'packages', 'tests', 'specs', 'docker'):
        run('cp', str(ROOT / source), name + ':/tmp/' + source)
    if args.foundation_http:
        run('cp',str(ROOT/args.http_evidence),name+':/tmp/tests/fixtures/phase2-http-evidence.json')
    result = subprocess.run(['podman', 'start', '-a', name], text=True,
                            encoding='utf-8', capture_output=True, timeout=120)
    output = result.stdout + result.stderr
    suffix = '-backend' if args.backend else ''
    if args.foundation_http:suffix='-foundation-http'
    log=evidence_dir/('t018-'+args.phase+suffix+'.log') if evidence_dir else ROOT/('docs/testing/t014-round2-logs/local-t018-'+args.phase+suffix+'.log')
    log.write_bytes(output.encode())
    print(output)
    exit_code = int(run('inspect', name, '--format', '{{.State.ExitCode}}'))
finally:
    if created:
        run('rm', '-f', name)

sys.exit(exit_code)
