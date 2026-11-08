"""Kiểm skeleton import và metadata mà không cần dependency nghiệp vụ."""

import json
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PackageBoundaryTests(unittest.TestCase):
    def test_shared_packages_import_without_api_or_airflow(self) -> None:
        code = """
import sys
sys.path[:0] = ['packages', 'etl_engine/src', 'backend/src']
import aat_metadata
import aat_etl
import aat_api
assert aat_metadata.__version__ == aat_etl.__version__ == aat_api.__version__ == '0.1.0'
assert not any(name.split('.')[0] in {'fastapi', 'airflow'} for name in sys.modules)
"""
        subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, check=True)

    def test_distribution_boundaries(self) -> None:
        for folder, expected in (("backend", "aat-api"), ("packages/aat_metadata", "aat-metadata"), ("etl_engine", "aat-etl-engine")):
            with self.subTest(package=expected):
                data = tomllib.loads((ROOT / folder / "pyproject.toml").read_text(encoding="utf-8"))
                self.assertEqual(data["project"]["name"], expected)
                self.assertEqual(data["project"]["version"], "0.1.0")
                if expected != "aat-api":
                    dependencies = data["project"]["dependencies"]
                    self.assertFalse(any("fastapi" in d.lower() or "airflow" in d.lower() for d in dependencies))

    def test_frontend_manifest_uses_planned_runtime(self) -> None:
        data = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
        self.assertTrue(data["private"])
        self.assertEqual(data["dependencies"]["react"], "19.2.0")
        self.assertEqual(data["devDependencies"]["typescript"], "5.9.3")


if __name__ == "__main__":
    unittest.main()
