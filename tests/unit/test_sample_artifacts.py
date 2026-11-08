"""Kiểm bytes artifact gốc; không normalize dữ liệu trong kiểm thử."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "specs/001-airflow-automation-tool/contracts/design-validation.json"


class SampleArtifactTests(unittest.TestCase):
    def test_raw_sample_bytes_match_manifest(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["sample_datasets"]:
            with self.subTest(path=entry["path"]):
                content = (ROOT / entry["path"]).read_bytes()
                self.assertNotIn(b"\r", content, "Dataset mẫu phải dùng LF")
                self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])

    def test_binary_workbooks_match_manifest(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["workbooks"]:
            with self.subTest(path=entry["path"]):
                content = (ROOT / entry["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])
                self.assertEqual(len(content), entry["bytes"])

    def test_checkout_policy_is_explicit(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        for rule in ("samples/data/*.csv text eol=lf", "samples/data/*.txt text eol=lf", "*.xlsx -text"):
            self.assertIn(rule, attributes)


if __name__ == "__main__":
    unittest.main()
