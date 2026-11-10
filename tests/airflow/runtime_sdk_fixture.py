"""Fixture-only SDK entry point; secrets remain in a private mounted file."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


def execute(revision,mode):
    os.environ.update(json.loads(Path('/tmp/aat-runtime-private/runtime-env.json').read_text()))
    # The SDK callback runner reconstructs its import path from the DAG bundle.
    # This source-copy fixture must explicitly select current wheels' source,
    # rather than silently execute the reviewed image's older installed package.
    for path in ('/tmp','/tmp/packages','/tmp/etl_engine/src'):
        if path in sys.path:sys.path.remove(path)
        sys.path.insert(0,path)
    os.environ['PYTHONPATH']='/tmp/etl_engine/src:/tmp/packages:/tmp'
    import aat_etl,aat_metadata
    if not Path(aat_etl.__file__).is_relative_to('/tmp/etl_engine/src') or not Path(aat_metadata.__file__).is_relative_to('/tmp/packages'):
        raise RuntimeError('Current runtime source was not selected by the SDK fixture')
    from aat_etl.runtime_task import execute_task
    if mode=='extraction-retry':
        from aat_etl.resources import run_supervised
        def fault(command):
            command=list(command);command[2]='tests.airflow.runtime_sdk_fault_child'
            return run_supervised(command)
        with patch('aat_etl.runtime_task.run_supervised',side_effect=fault):execute_task(expected_revision=revision)
    else:execute_task(expected_revision=revision)
