import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[4]
out = root / 'docs/testing/resume-20261114/t014-closeout'
out.mkdir(parents=True, exist_ok=True)
snapshot = root / '.tools/t014-closeout-snapshot'
snapshot.mkdir(exist_ok=True)
paths = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
hashes = {}
for relative in paths:
    if not relative or relative.startswith('docs/'):
        continue
    source = root / relative
    if not source.is_file():
        continue
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    hashes[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
selectors = ['tests.unit.test_sample_artifacts', 'tests.unit.test_image_baseline',
             'tests.unit.test_airflow_constraints', 'tests.unit.test_airflow_offline_patch',
             'tests.integration.test_image_compatibility.ImageCompatibilityTests.test_source_pins_match_image_lock']
result = {'captured_at': datetime.now(timezone.utc).isoformat(),
          'head': subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip(),
          'source_files_sha256': hashes, 'selectors': selectors,
          'scope': 'Local byte-preserving working-tree snapshot, not remote CI or Git checkout proof',
          'remote_ci': 'NOT_RUN', 'checks': []}
def run(name, command, **kwargs):
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=180, **kwargs)
    (out / (name + '.txt')).write_bytes(proc.stdout)
    result['checks'].append({'name': name, 'command': command, 'exit_code': proc.returncode,
                              'status': 'PASS' if proc.returncode == 0 else 'FAIL'})
    (out / 'source-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(name, proc.returncode, flush=True)
run('windows', [sys.executable, '-B', '-m', 'unittest', *selectors, '-v'], cwd=snapshot,
    env={**os.environ, 'PYTHONUTF8': '1'})
image = '313cf8f190a1abab00472c1f0c950c10486c22114bcd8aef2a8198fb587a6d18'
archive = io.BytesIO()
with tarfile.open(fileobj=archive, mode='w') as tar:
    for relative in hashes:
        tar.add(snapshot / relative, arcname=relative, recursive=False)
linux = "import sys,tarfile,tempfile,os,subprocess; d=tempfile.mkdtemp(); tarfile.open(fileobj=sys.stdin.buffer,mode='r|').extractall(d,filter='data'); os.chdir(d); print(sys.version,flush=True); sys.exit(subprocess.call([sys.executable,'-B','-m','unittest',*sys.argv[1:],'-v']))"
run('linux', ['podman', 'run', '--rm', '--network=none', '--memory=512m', '--entrypoint=python',
              '-i', image, '-c', linux, *selectors], input=archive.getvalue())
for relative, digest in hashes.items():
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest, relative
assert all(hashlib.sha256((snapshot / p).read_bytes()).hexdigest() == h for p,h in hashes.items())
print('snapshot files', len(hashes), flush=True)
