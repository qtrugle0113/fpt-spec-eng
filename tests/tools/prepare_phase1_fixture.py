"""Tạo fixture source sạch và kiểm raw bytes; không phải bước startup sản phẩm."""

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / '.tools/phase1-clean'


def ignore(folder, names):
    return [name for name in names if name in {
        'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache', 'test-results', 'playwright-report'
    } or name.endswith('.egg-info')]


def prepare() -> None:
    TARGET.mkdir(exist_ok=True, parents=True)
    for name in ('backend','frontend','packages','etl_engine','airflow','docker','tests','samples','templates','specs'):
        shutil.copytree(ROOT / name, TARGET / name, ignore=ignore, dirs_exist_ok=True)
    for name in ('docker-compose.yml','.dockerignore','.gitattributes','.env.example'):
        shutil.copy2(ROOT / name, TARGET / name)
    hashes = {}
    for path in TARGET.rglob('*'):
        if path.is_file():
            relative = path.relative_to(TARGET)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), str(relative)
            hashes[relative.as_posix()] = digest
    (ROOT / '.tools/phase1-fixture-manifest.json').write_text(json.dumps(hashes, indent=2))
    print(f'Clean source fixture: {len(hashes)} files, raw SHA256 identical')


if __name__ == '__main__':
    prepare()
