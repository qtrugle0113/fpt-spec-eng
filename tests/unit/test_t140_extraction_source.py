"""T140 fixture must preserve NULL provenance while assigning distinct keys."""
import csv
from pathlib import Path
import tempfile
import unittest

from tests.tools.verify_running_workflow import make_extraction_source, expected_extraction_rows, restart_target_is_safe


ROOT = Path(__file__).resolve().parents[2]


class ExtractionSourceTests(unittest.TestCase):
    def test_repeated_sample_preserves_quoted_literal_and_unquoted_null(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'source.csv'
            make_extraction_source(ROOT / 'samples/data/customers.csv', destination, 8)
            raw = destination.read_bytes()
            self.assertIn(b'4,"\\N",\\N,2026-01-04T00:00:00\n', raw)
            self.assertIn(b'8,"\\N",\\N,2026-01-04T00:00:00\n', raw)
            with destination.open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row['customer_id'] for row in rows], [str(i) for i in range(1, 9)])
            self.assertEqual(rows[1]['customer_name'], 'Line one\nLine two')
            self.assertEqual(rows[2]['customer_name'], 'Quote "sample"')
            self.assertEqual(rows[4]['customer_name'], 'Nguyễn, An')
            expected = expected_extraction_rows(destination)
            self.assertEqual(expected[3], [4, r'\N', None, '2026-01-04T00:00:00'])
            self.assertEqual(expected[7], [8, r'\N', None, '2026-01-04T00:00:00'])


class RestartTargetTests(unittest.TestCase):
    def test_extraction_allows_exact_committed_prefix_before_final_verification(self):
        expected=[[number,'value'] for number in range(1,6)]
        for current in ([],expected[:2],expected[:4],expected):
            with self.subTest(rows=len(current)):
                self.assertTrue(restart_target_is_safe('EXTRACTION',[],current,expected,batch_size=2))
        for current in (expected[:1],[[1,'wrong'],expected[1]],expected+[[6,'value']]):
            with self.subTest(current=current):
                self.assertFalse(restart_target_is_safe('EXTRACTION',[],current,expected,batch_size=2))

    def test_blocked_commit_and_refresh_must_preserve_previous_target(self):
        before=[[1,'old']]
        expected=[[1,'new'],[2,'new']]
        for phase in ('COMMIT','FULL_REFRESH'):
            with self.subTest(phase=phase):
                self.assertTrue(restart_target_is_safe(phase,before,before,expected))
                self.assertFalse(restart_target_is_safe(phase,before,expected,expected))


if __name__ == '__main__':
    unittest.main()
