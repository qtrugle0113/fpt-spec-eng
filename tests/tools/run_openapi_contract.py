"""Run T015 with explicit candidate dependencies; no rebuild or downloads."""

from pathlib import Path
import secrets
import subprocess
import sys
import argparse

ROOT = Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',default='399adacf113fd269d4dd5d587b956a9167bc02ef8f656d3ff9ef94e11039e2fc')
parser.add_argument('--log',default='docs/testing/t014-round2-logs/local-t015-contract-harness.log')
args=parser.parse_args()
IMAGE=args.image
log=(ROOT/args.log).resolve()
if not log.is_relative_to(ROOT):parser.error('Log must stay in workspace')
log.parent.mkdir(parents=True,exist_ok=True)
name = 'aat-t015-' + secrets.token_hex(4)
created = False


def run(*args):
    return subprocess.check_output(['podman', *args], text=True, encoding='utf-8').strip()


try:
    run('create', '--name', name, '--network=none', '--entrypoint', 'python', IMAGE,
        '-m', 'unittest', 'discover', '-s', '/tmp/tests/api', '-p', 'test_openapi_contract.py', '-v')
    created = True
    for source in ('tests', 'specs'):
        run('cp', str(ROOT / source), name + ':/tmp/' + source)
    result = subprocess.run(['podman', 'start', '-a', name], text=True,
                            encoding='utf-8', capture_output=True, timeout=120)
    output = result.stdout + result.stderr
    log.write_bytes(output.encode())
    print(output)
    exit_code = int(run('inspect', name, '--format', '{{.State.ExitCode}}'))
finally:
    if created:
        run('rm', '-f', name)

sys.exit(exit_code)
