"""Bảo vệ tên user-facing và khóa thông báo tương thích với bản ghi lịch sử."""
from pathlib import Path
import re
import unittest
from aat_api.validation.messages import MESSAGES, message_key
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]


class DefinitionTerminologyTests(unittest.TestCase):
    def test_current_messages_resolve_to_stable_keys(self):
        for key, message in MESSAGES.items():
            self.assertEqual(message_key(message), key)
            self.assertNotRegex(message, r'(?i)\bworkbooks?\b')
        self.assertEqual(message_key('Workbook sheets and order must match the template.'), 'validation.8e3faa49f6d252342d61')
        self.assertEqual(message_key('Definition file sheets and order must match the template.'), 'validation.8e3faa49f6d252342d61')

    def test_frontend_and_template_instructions_use_definition_names(self):
        paths=list((ROOT/'frontend/src').rglob('*.tsx'))
        self.assertGreater(len(paths),10)
        for path in paths:
            self.assertNotRegex(path.read_text(encoding='utf-8'), r'(?i)\bworkbooks?\b', str(path))
        for path in (ROOT/'templates').glob('*.xlsx'):
            book=load_workbook(path,read_only=True)
            for row in book['Instructions']:
                for cell in row:
                    if isinstance(cell.value,str): self.assertNotRegex(cell.value,r'(?i)\bworkbooks?\b')
            book.close()
