"""Render a fixed wrapper with strictly validated canonical configuration."""
import json
import os
from pathlib import Path
import re
from uuid import UUID

from aat_etl.contracts.config import ETLConfig


def render(config: dict, *, revision_id: UUID | str, revision_sha256: str) -> bytes:
    identity = str(UUID(str(revision_id)))
    if not isinstance(revision_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', revision_sha256):
        raise ValueError('A SHA256 revision is required.')
    validated = ETLConfig.model_validate(config)
    payload = json.dumps(validated.model_dump(mode='json', by_alias=True, exclude_none=True),
                         sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    template = Path(os.environ.get('AAT_ASSETS_ROOT', '/opt/aat')) / 'airflow/dags/aat_wrapper_template.py'
    source = template.read_text(encoding='utf-8')
    return (source + '\n\ndag = build_dag(json.loads(' + repr(payload) + '), '
            + repr(identity) + ', ' + repr(revision_sha256) + ')\n').encode('utf-8')
