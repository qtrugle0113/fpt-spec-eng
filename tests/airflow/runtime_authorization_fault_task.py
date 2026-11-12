"""Fixture-only import seam; production binding and supervision remain unchanged."""
import os
from unittest.mock import patch
from aat_etl.resources import run_supervised
from aat_etl.runtime_task import execute_task as actual_execute


def execute_task(*,expected_revision,mode):
    def injected(command):
        command=list(command);command[2]='tests.airflow.runtime_authorization_fault_child'
        command.append(mode)
        return run_supervised(command)
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch('aat_etl.runtime_task.run_supervised',side_effect=injected))
        if mode=='commit-unresolved':
            stack.enter_context(patch('aat_etl.runtime_lifecycle.revision_engine',side_effect=OSError('Synthetic target unavailable during post-reap reconciliation')))
        if mode=='file-diagnostic':
            import json
            import re
            from urllib.error import HTTPError
            from aat_etl import runtime
            actual_opener=runtime.build_opener
            class ObservedOpener:
                def __init__(self,delegate):self.delegate=delegate
                def open(self,*args,**kwargs):
                    try:return self.delegate.open(*args,**kwargs)
                    except HTTPError as error:
                        try:code=json.loads(error.read(65536)).get('error',{}).get('code','UNKNOWN')
                        except (ValueError,AttributeError):code='UNKNOWN'
                        if not isinstance(code,str) or not re.fullmatch('[A-Z0-9_]{1,80}',code):code='UNKNOWN'
                        print('BIND_DIAGNOSTIC_'+str(error.code)+'_'+code,flush=True)
                        raise
            stack.enter_context(patch.object(runtime,'build_opener',side_effect=lambda *args:ObservedOpener(actual_opener(*args))))
        return actual_execute(expected_revision=expected_revision)
