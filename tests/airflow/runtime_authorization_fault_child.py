"""Real SDK child fault injection; never print dataset, credentials or errors."""
from contextlib import ExitStack
import os
from pathlib import Path
import signal
import sys
from unittest.mock import patch
import psycopg
from aat_etl.runtime_child import main
from aat_etl.loaders.replacement_admission import AdmissionAdapter
from aat_metadata.repositories.authorizations import AuthorizationRepository

mode=sys.argv.pop()
marker=Path('/tmp/aat-runtime-staging')/('authorization-fault-'+sys.argv[1]+'-'+mode)
with ExitStack() as stack:
    if mode=='file-diagnostic':
        # Fixture-only diagnostics preserve the installed engine's behavior.
        # Record stack coordinates, never exception text, credentials or data.
        import json
        import traceback
        from aat_etl import runtime
        actual=runtime.run_binding
        def trace_binding(*args,**kwargs):
            try:return actual(*args,**kwargs)
            except Exception as error:
                marker.write_text(json.dumps({'type':type(error).__name__,'frames':[
                    {'file':Path(frame.filename).name,'function':frame.name,'line':frame.lineno}
                    for frame in traceback.extract_tb(error.__traceback__)]}))
                raise
        stack.enter_context(patch.object(runtime,'run_binding',trace_binding))
    elif mode=='admission-ack-loss':
        actual=AuthorizationRepository.admit
        def admit(repository,**request):
            result=actual(repository,**request)
            if not marker.exists():
                repository.connection.commit();marker.write_text('injected')
                raise psycopg.OperationalError('Synthetic admission acknowledgement loss')
            return result
        stack.enter_context(patch.object(AuthorizationRepository,'admit',admit))
    elif mode in ('revoke-before-admission','revoke-after-admission'):
        actual=AdmissionAdapter.admit
        def admit(adapter,*args,**kwargs):
            def revoke():
                # The ETL role intentionally cannot revoke authorization. Act as
                # the operator through the real backend HTTP surface instead.
                import httpx
                from uuid import uuid4
                url='http://backend:8000/api/v1/replacement-authorizations/'+str(adapter.request['authorization_id'])
                with httpx.Client(trust_env=False,timeout=10) as client:
                    current=client.get(url);current.raise_for_status()
                    response=client.post(url+'/revoke',headers={'If-Match':current.headers['etag'],'Idempotency-Key':str(uuid4())},json={'acknowledged':True})
                    response.raise_for_status()
                marker.write_text('injected')
            if mode=='revoke-before-admission' and not marker.exists():revoke()
            result=actual(adapter,*args,**kwargs)
            if mode=='revoke-after-admission' and not marker.exists():revoke()
            return result
        stack.enter_context(patch.object(AdmissionAdapter,'admit',admit))
    elif mode=='target-commit-loss':
        from aat_etl.loaders.ledger import TargetLedger
        actual=TargetLedger.record_run
        def record_run(ledger,connection,value):
            result=actual(ledger,connection,value)
            if not marker.exists():
                driver=connection.connection.driver_connection;commit=driver.commit
                def lost():
                    commit();marker.write_text('injected')
                    if connection.dialect.name=='postgresql':raise psycopg.OperationalError('Synthetic target acknowledgement loss')
                    import pymysql
                    raise pymysql.OperationalError(2013,'Synthetic target acknowledgement loss')
                stack.enter_context(patch.object(driver,'commit',side_effect=lost))
            return result
        stack.enter_context(patch.object(TargetLedger,'record_run',record_run))
    elif mode in ('extraction-kill','terminal-extraction'):
        from aat_etl.readers.postgres import SnapshotReader
        actual=SnapshotReader.rows
        def rows(reader):
            if mode=='terminal-extraction':
                marker.write_text('injected');raise ValueError('Synthetic terminal extraction failure')
            for row in actual(reader):
                yield row
                if not marker.exists():
                    marker.write_text('injected');os.kill(os.getpid(),signal.SIGKILL)
        stack.enter_context(patch.object(SnapshotReader,'rows',rows))
    else:raise RuntimeError('Unknown fixture fault mode')
    sys.exit(main())
