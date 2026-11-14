"""Không cho memory-only receipt hoặc tổng hợp PASS che thiếu điều kiện mandatory."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from tests.tools.t152_evidence import validate,MATRIX

ROOT=Path(__file__).resolve().parents[2]

class T152EvidenceTests(unittest.TestCase):
    def setUp(self):self.matrix=json.loads((ROOT/MATRIX).read_text(encoding='utf8'))
    def test_complete_matrix_has_verified_receipts(self):self.assertEqual(validate(ROOT,self.matrix)['cases'],39)
    def test_memory_receipt_cannot_prove_ah(self):
        row=next(c for c in self.matrix['cases'] if c['case']=='AH')
        row['checks']=next(c for c in self.matrix['cases'] if c['case']=='O')['checks']
        with self.assertRaises(ValueError):validate(ROOT,self.matrix)
    def test_missing_condition_or_unknown_selector_rejected(self):
        row=next(c for c in self.matrix['cases'] if c['case']=='AJ');row['checks'].pop()
        with self.assertRaises(ValueError):validate(ROOT,self.matrix)
    def test_modified_receipt_checksum_rejected(self):
        next(iter(self.matrix['evidence'].values()))['receipt_sha256']='0'*64
        with self.assertRaises(ValueError):validate(ROOT,self.matrix)
    def test_missing_success_criterion_rejected(self):
        self.matrix['success_criteria'].pop()
        with self.assertRaises(ValueError):validate(ROOT,self.matrix)
    def test_unknown_unexecuted_test_id_rejected(self):
        row=next(c for c in self.matrix['cases'] if c['case']=='AH')
        row['checks'][0]['selectors']=['tests/etl/test_storage_failures.py::Fake::test_never_run']
        with self.assertRaises(ValueError):validate(ROOT,self.matrix)
    def test_forged_passed_selector_not_present_in_logs_rejected(self):
        proof=self.matrix['evidence']['ah'];proof['passed_selectors'].append('tests/etl/test_storage_failures.py::Fake::test_never_run')
        with self.assertRaises(ValueError):validate(ROOT,self.matrix)
