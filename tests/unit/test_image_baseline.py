"""Phát hiện lock lệch FROM trước khi dùng tag hoặc scan của image khác để nghiệm thu."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.tools.record_image_baseline import image_sources, validate_lock

class ImageBaselineTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = 'docker.io/library/python:3.12@sha256:' + 'a' * 64
        (self.root / 'Dockerfile').write_text(
            f'FROM {self.source} AS build\nFROM build AS final\n', encoding='utf-8')
        patcher = patch('tests.tools.record_image_baseline.DOCKERFILES', ('Dockerfile',))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.lock = {'images': [{'ref': self.source.split('@')[0],
                                'repo_digest': 'docker.io/library/python@sha256:' + 'a' * 64,
                                'platform': 'linux/amd64'}]}

    def test_pinned_sources_and_internal_stages_match_lock(self):
        self.assertEqual(image_sources(self.root), {self.source.split('@')[0]: self.source})
        validate_lock(self.lock, self.root)

    def test_lock_drift_missing_and_duplicate_entries_are_rejected(self):
        for failure in ('digest', 'missing', 'duplicate'):
            with self.subTest(failure=failure):
                changed = copy.deepcopy(self.lock)
                if failure == 'digest':
                    changed['images'][0]['repo_digest'] = 'docker.io/library/python@sha256:' + '0' * 64
                elif failure == 'missing':
                    changed['images'].pop()
                else:
                    changed['images'].append(copy.deepcopy(changed['images'][0]))
                with self.assertRaises(ValueError):
                    validate_lock(changed, self.root)

    def test_unpinned_and_conflicting_from_are_rejected(self):
        for content in (
            'FROM docker.io/library/python:3.12\n',
            'FROM docker.io/library/python:3.12@sha256:' + 'a' * 64 + ' AS build\n'
            'FROM docker.io/library/python:3.12@sha256:' + 'b' * 64 + '\n',
        ):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'Dockerfile').write_text(content, encoding='utf-8')
                with patch('tests.tools.record_image_baseline.DOCKERFILES', ('Dockerfile',)):
                    with self.assertRaises(ValueError):
                        image_sources(root)
