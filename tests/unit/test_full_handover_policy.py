"""Approval đúng snapshot; không cho findings/artifacts mới hoặc approval hết hiệu lực."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tests.tools.full_handover_policy import validate, DECISION


class FullHandoverPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        def put(path, data):
            p = self.root/path; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
            return hashlib.sha256(p.read_bytes()).hexdigest()
        self.put = put
        raw_sha = put('scan.json', {'Metadata': {'ImageID': 'sha256:'+'a'*64}, 'Results': [{'Vulnerabilities': [
            {'Severity':'HIGH','VulnerabilityID':'CVE-test','PkgName':'test','InstalledVersion':'1'}]}]})
        packet = {'targets':[{'name':'backend','image_id':'a'*64,'raw_path':'scan.json','raw_sha256':raw_sha}],
                  'groups':[{'advisory':'CVE-test','package':'test','version':'1','severity':'HIGH',
                             'contexts':[{'target':'backend','image':'a'*64}]}]}
        self.decision = {'status':'OWNER_ACCEPTED_KNOWN_RISKS','governance_approval':'OWNER_APPROVED',
            'revoked':False,'expires_at':'2026-11-23T00:00:00+09:00','review_due':'2026-11-16',
            'controls':{'operator_count':1,'exposure':'loopback','data':'synthetic','public_deploy':False,'important_data':False},
            'constitution_sha256':put('.specify/memory/constitution.md', b'Constitution2.0.0'),
            'governance_proposal':'proposal.md','proposal_sha256':put('proposal.md',b'reviewed proposal'),
            'scope_packet':'packet.json','scope_packet_sha256':put('packet.json',packet),
            'targets':1,'groups':1,'occurrences':1}
        self.put(DECISION,self.decision)

    def test_exact_approval_preserves_findings(self):
        proof = validate(self.root,{'backend':'a'*64},self.now)
        self.assertEqual(proof['finding_occurrences'],1)
        self.assertFalse(proof['scan_security_clean'])

    def test_new_artifact_is_rejected(self):
        with self.assertRaises(ValueError): validate(self.root,{'backend':'b'*64},self.now)

    def test_changed_raw_finding_or_packet_or_governance_is_rejected(self):
        for path in ('scan.json','packet.json','proposal.md','.specify/memory/constitution.md'):
            p=self.root/path; old=p.read_bytes(); p.write_bytes(old+b' ')
            with self.subTest(path=path), self.assertRaises(ValueError): validate(self.root,{},self.now)
            p.write_bytes(old)

    def test_revoked_or_expired_or_review_due_is_rejected(self):
        self.decision['revoked']=True; self.put(DECISION,self.decision)
        with self.assertRaises(ValueError): validate(self.root,{},self.now)
        self.decision['revoked']=False; self.put(DECISION,self.decision)
        for date in (datetime(2026,11,15,15,tzinfo=timezone.utc),datetime(2026,11,24,tzinfo=timezone.utc)):
            with self.assertRaises(ValueError): validate(self.root,{},date)

    def test_scope_extension_is_rejected(self):
        self.decision['controls']['exposure']='public'; self.put(DECISION,self.decision)
        with self.assertRaises(ValueError): validate(self.root,{},self.now)

    def test_evidence_outside_workspace_is_rejected(self):
        self.decision['scope_packet']='../outside.json'; self.put(DECISION,self.decision)
        with self.assertRaises(ValueError): validate(self.root,{},self.now)
