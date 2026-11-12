"""Đối chiếu policy không được miễn findings mới hoặc context khác target."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import hashlib
import unittest
from tests.tools.portable_policy import finding_key, compare_findings, verified_json, check_expiry, not_affected_zlib


class PortablePolicyTests(unittest.TestCase):
    def test_unknown_version_severity_and_target_are_blocked(self):
        known = {'VulnerabilityID':'CVE-X','PkgName':'libx','InstalledVersion':'1','Severity':'HIGH'}
        allowed = {'backend':{finding_key(known)}}
        self.assertEqual(compare_findings('backend',[known],allowed), [])
        for field, value in [('InstalledVersion','2'),('Severity','CRITICAL'),('VulnerabilityID','CVE-Y')]:
            changed = dict(known, **{field:value})
            self.assertEqual(compare_findings('backend',[changed],allowed), [changed])
        self.assertEqual(compare_findings('frontend',[known],allowed), [known])

    def test_approval_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json';path.write_text('{}',encoding='utf-8')
            with self.assertRaises(ValueError): verified_json(path,'0'*64)

    def test_git_line_endings_preserve_original_approved_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json';path.write_bytes(b'{\n  "value": 1\n}\n')
            original=path.read_bytes().replace(b'\n',b'\r\n')
            self.assertEqual(verified_json(path,hashlib.sha256(original).hexdigest()),{'value':1})
            path.write_bytes(b'{\n  "value": 2\n}\n')
            with self.assertRaises(ValueError):verified_json(path,hashlib.sha256(original).hexdigest())

    def test_expired_approval_cannot_authorize_new_artifact(self):
        with self.assertRaises(ValueError):
            check_expiry('2026-11-23T00:00:00+09:00',datetime(2026,11,23,tzinfo=timezone.utc))

    def test_not_affected_requires_same_target_package_version_and_binary(self):
        finding={'VulnerabilityID':'CVE-2023-45853','PkgName':'zlib1g','InstalledVersion':'1','Severity':'CRITICAL'}
        contexts=[{'target':'backend','scanner_package':'zlib1g','installed':'1','libz_sha256':'original'}]
        self.assertTrue(not_affected_zlib('backend',finding,'original',contexts))
        self.assertFalse(not_affected_zlib('backend',finding,'changed',contexts))
        self.assertFalse(not_affected_zlib('frontend',finding,'original',contexts))
        self.assertFalse(not_affected_zlib('backend',dict(finding,InstalledVersion='2'),'original',contexts))
