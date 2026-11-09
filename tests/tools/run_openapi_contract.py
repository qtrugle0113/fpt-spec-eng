"""Run T015 using already-approved candidate dependencies; no rebuild or downloads."""

from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
IMAGE = '399adacf113fd269d4dd5d587b956a9167bc02ef8f656d3ff9ef94e11039e2fc'
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
    (ROOT / 'docs/testing/t014-round2-logs/local-t015-contract-harness.log').write_bytes(output.encode())
    print(output)
    exit_code = int(run('inspect', name, '--format', '{{.State.ExitCode}}'))
finally:
    if created:
        run('rm', '-f', name)

sys.exit(exit_code)
