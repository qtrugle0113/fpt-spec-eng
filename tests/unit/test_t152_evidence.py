"""Không cho memory-only receipt hoặc tổng hợp PASS che thiếu điều kiện mandatory."""
from copy import deepcopy
import json
from pathlib import Path
import hashlib
import tempfile
import unittest
from tests.tools.t152_evidence import validate,MATRIX

ROOT=Path(__file__).resolve().parents[2]

class T152EvidenceTests(unittest.TestCase):
    def setUp(self):
        # Unit tests own tiny files; the real repository matrix is checked separately by CI.
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        from tests.tools.t152_evidence import CRITICAL_CONDITIONS
        codes=[chr(65+i) for i in range(26)]+['A'+chr(65+i) for i in range(13)]
        names={name for row in CRITICAL_CONDITIONS.values() for name in row.values()}
        names|={'test_probe','test_list_detail_preview_and_connection_probe_meet_published_budgets'}
        def selector(name):
            return 'tests/airflow/test_concurrent_runs.py::Suite::test_probe' if name=='test_concurrent_runs.py' else 'tests/unit/test_fixture.py::Suite::'+name
        ids=[selector(name) for name in names]
        def check(condition='probe',test='test_probe'):
            return {'condition':condition,'evidence_id':'ah','selectors':[selector(test)],'status':'PASS','actual':'Đã kiểm chứng'}
        spec=self.root/'specs/001-airflow-automation-tool/spec.md';spec.parent.mkdir(parents=True)
        spec.write_text('\n'.join('| '+code+' | Fixture | Expected '+code+' | FR-001 |' for code in codes),encoding='utf8')
        receipt=self.root/'receipt.json';receipt.write_text(json.dumps({'status':'PASS'}))
        log=self.root/'passed.txt';log.write_text('\n'.join(test+' PASSED' for test in ids))
        cases=[{'case':code,'expected':'Expected '+code,'requirements':'FR-001','actual':'Đã kiểm chứng','status':'PASS','checks':[check()]} for code in codes]
        for code,conditions in CRITICAL_CONDITIONS.items():
            next(c for c in cases if c['case']==code)['checks']=[check(name,test) for name,test in conditions.items()]
        criteria=[{'id':'SC-'+str(i).zfill(3),'expected':'Expected','actual':'Verified','status':'PASS','case_ids':codes if i==12 else ['A']} for i in range(1,16)]
        criteria[9]['checks']=[check('performance','test_list_detail_preview_and_connection_probe_meet_published_budgets')]
        self.matrix={'cases':cases,'evidence':{'ah':{'receipt':'receipt.json','receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),
            'kind':'suite','passed_selectors':ids,'logs_sha256':{'passed.txt':hashlib.sha256(log.read_bytes()).hexdigest()}}},
            'success_criteria':criteria,'stories':[{'id':'US'+str(i),'expected':'Expected','actual':'Verified','status':'PASS','case_ids':['A']} for i in range(1,12)],
            'business_rules':[{'id':'BR-08','expected':'Expected','actual':'Verified','status':'PASS','case_ids':['A'],'checks':[check()]}]}
    def test_complete_matrix_has_verified_receipts(self):self.assertEqual(validate(self.root,self.matrix)['cases'],39)
    def test_memory_receipt_cannot_prove_ah(self):
        row=next(c for c in self.matrix['cases'] if c['case']=='AH')
        row['checks']=next(c for c in self.matrix['cases'] if c['case']=='O')['checks']
        with self.assertRaises(ValueError):validate(self.root,self.matrix)
    def test_missing_condition_or_unknown_selector_rejected(self):
        row=next(c for c in self.matrix['cases'] if c['case']=='AJ');row['checks'].pop()
        with self.assertRaises(ValueError):validate(self.root,self.matrix)
    def test_modified_receipt_checksum_rejected(self):
        next(iter(self.matrix['evidence'].values()))['receipt_sha256']='0'*64
        with self.assertRaises(ValueError):validate(self.root,self.matrix)
    def test_missing_success_criterion_rejected(self):
        self.matrix['success_criteria'].pop()
        with self.assertRaises(ValueError):validate(self.root,self.matrix)
    def test_unknown_unexecuted_test_id_rejected(self):
        row=next(c for c in self.matrix['cases'] if c['case']=='AH')
        row['checks'][0]['selectors']=['tests/etl/test_storage_failures.py::Fake::test_never_run']
        with self.assertRaises(ValueError):validate(self.root,self.matrix)
    def test_forged_passed_selector_not_present_in_logs_rejected(self):
        proof=self.matrix['evidence']['ah'];proof['passed_selectors'].append('tests/etl/test_storage_failures.py::Fake::test_never_run')
        with self.assertRaises(ValueError):validate(self.root,self.matrix)
