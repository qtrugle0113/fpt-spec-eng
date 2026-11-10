"""Readiness follows shipped migrations and rejects stale/unknown database heads."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from alembic.script import ScriptDirectory
from aat_api.services.health import migration_heads_match


class MigrationHeadReadinessTests(unittest.TestCase):
    def test_actual_shipped_head_is_healthy_and_old_or_unknown_heads_are_not(self):
        root=Path(os.environ.get('AAT_ASSETS_ROOT') or Path(__file__).resolve().parents[2])
        current=ScriptDirectory(str(root/'backend/alembic')).get_heads()
        self.assertTrue(current)
        with patch.dict(os.environ,{'AAT_ASSETS_ROOT':str(root)}):
            self.assertTrue(migration_heads_match([(head,) for head in current]))
            self.assertFalse(migration_heads_match([]))
            self.assertFalse(migration_heads_match([('0002_staging_quota',)]))
            self.assertFalse(migration_heads_match([(head,) for head in current]+[('unknown_future_head',)]))
