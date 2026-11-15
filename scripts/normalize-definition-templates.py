"""Chuẩn hóa câu chữ Instructions, giữ nguyên Version/sheet/header và cập nhật hash artifact."""
from pathlib import Path
import hashlib
import json
import re
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


def main():
    changed = []
    for folder in ('templates', 'samples/definitions'):
        for path in (ROOT / folder).glob('*.xlsx'):
            book = load_workbook(path)
            if 'Instructions' not in book: continue
            kind = book['Instructions']['B1'].value
            name = 'ETL Definition' if 'ETL' in str(kind) or 'etl' in path.name.lower() else 'Table Definition'
            modified = False
            for row in book['Instructions']:
                for cell in row:
                    if isinstance(cell.value, str) and re.search(r'\bworkbooks?\b', cell.value, re.I):
                        value = cell.value.replace('ETL Definition workbook', 'ETL Definition').replace('Table Definition workbook', 'Table Definition')
                        value = re.sub(r'\bworkbooks\b', name + ' files', value, flags=re.I)
                        value = re.sub(r'\bworkbook\b', name, value, flags=re.I)
                        cell.value = value; modified = True
            if modified: book.save(path); changed.append(str(path.relative_to(ROOT)))
    manifest = ROOT / 'specs/001-airflow-automation-tool/contracts/design-validation.json'
    data = json.loads(manifest.read_text(encoding='utf-8'))
    for entry in data['workbooks']:
        path = ROOT / entry['path']
        if entry['path'] in changed:
            content = path.read_bytes(); entry['bytes'] = len(content); entry['sha256'] = hashlib.sha256(content).hexdigest()
    if changed: manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'changed_instructions': changed}))


if __name__ == '__main__': main()
