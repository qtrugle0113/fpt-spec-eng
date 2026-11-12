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
    elif mode=='invalidate-before-admission':
        actual=AdmissionAdapter.admit
        def invalidate(adapter,*args,**kwargs):
            import httpx
            with adapter.connection_factory() as connection:
                identity=connection.execute('SELECT r.connection_id FROM connection_revisions r JOIN execution_bindings b ON b.target_revision_id=r.id WHERE b.id=%s',(adapter.request['binding_id'],)).fetchone()[0]
            with httpx.Client(trust_env=False,timeout=10) as client:
                url='http://backend:8000/api/v1/connections/'+str(identity)
                current=client.get(url);current.raise_for_status()
                changed=client.patch(url,headers={'If-Match':current.headers['etag']},json={'password':'synthetic-invalidated-revision'})
                changed.raise_for_status()
                authority=client.get('http://backend:8000/api/v1/replacement-authorizations/'+str(adapter.request['authorization_id']))
                authority.raise_for_status()
                if authority.json()['state']!='INVALIDATED':raise RuntimeError('Credential revision did not invalidate replacement authority')
            marker.write_text('invalidated_before_admission')
            return actual(adapter,*args,**kwargs)
        stack.enter_context(patch.object(AdmissionAdapter,'admit',invalidate))
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
    elif mode in ('target-commit-loss','commit-unresolved'):
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
    elif mode=='full-refresh-dependency':
        from aat_etl.loaders import full_refresh
        actual=full_refresh.check_dependencies
        def dependency(session):
            quote=session.engine.dialect.identifier_preparer.quote_identifier
            child='incoming_'+sys.argv[1].replace('-','')
            target=quote(session.schema)+'.'+quote(session.table)
            with session.engine.begin() as connection:
                connection.exec_driver_sql('CREATE TABLE '+quote(session.schema)+'.'+quote(child)+' (id INTEGER REFERENCES '+target+'(id))' if session.engine.dialect.name=='postgresql' else
                    'CREATE TABLE '+quote(session.schema)+'.'+quote(child)+' (id INTEGER, FOREIGN KEY(id) REFERENCES '+target+'(id)) ENGINE=InnoDB')
            marker.write_text('dependency_installed_before_admission')
            return actual(session)
        stack.enter_context(patch.object(full_refresh,'check_dependencies',dependency))
    elif mode=='full-refresh-midinsert':
        from aat_etl.loaders.ledger import TargetLedger
        actual=TargetLedger.record_run
        def record_run(ledger,connection,value):
            result=actual(ledger,connection,value)
            marker.write_text('replacement_rows_inserted_before_rollback')
            connection.exec_driver_sql('SELECT * FROM aat_intentionally_missing_recovery_fixture')
            return result
        stack.enter_context(patch.object(TargetLedger,'record_run',record_run))
    elif mode=='full-refresh-visibility':
        from aat_etl.loaders import full_refresh
        actual=full_refresh.execute
        def visible(dataset,session,ledger,*args,**kwargs):
            original=ledger.record_run
            quote=session.engine.dialect.identifier_preparer.quote_identifier
            query='SELECT id,note FROM '+quote(session.schema)+'.'+quote(session.table)+' ORDER BY id'
            def record_run(current,connection,value):
                with session.engine.connect() as reader:
                    if [tuple(r) for r in reader.exec_driver_sql(query)]!=[(99,'old protected row')]:
                        raise RuntimeError('Concurrent supported reader did not see the old committed generation')
                marker.write_text('old_generation_visible')
                return original(connection,value)
            # The method on this ledger instance receives no implicit self.
            def observe(connection,value):return record_run(ledger,connection,value)
            with patch.object(ledger,'record_run',side_effect=observe):
                result=actual(dataset,session,ledger,*args,**kwargs)
            with session.engine.connect() as reader:
                if [tuple(r) for r in reader.exec_driver_sql(query)]!=[(1,'first'),(2,None)]:
                    raise RuntimeError('Reader did not see the new generation after replacement commit')
            marker.write_text('old_and_new_generations_verified')
            return result
        stack.enter_context(patch.object(full_refresh,'execute',visible))
    elif mode=='app-metrics-fail':
        from aat_etl.runtime_state import RuntimeState
        actual=RuntimeState.project
        def project(state,snapshot):
            if not marker.exists():
                marker.write_text('injected')
                raise psycopg.OperationalError('Synthetic application projection outage after target commit')
            return actual(state,snapshot)
        stack.enter_context(patch.object(RuntimeState,'project',project))
    elif mode=='target-disconnect':
        from aat_etl.loaders.ledger import TargetLedger
        actual=TargetLedger.record_batch
        def record_batch(ledger,connection,value):
            result=actual(ledger,connection,value)
            if not marker.exists():
                marker.write_text('injected')
                connection.connection.driver_connection.close()
            return result
        stack.enter_context(patch.object(TargetLedger,'record_batch',record_batch))
    elif mode in ('extraction-kill','terminal-extraction','source-disconnect'):
        from aat_etl.readers.postgres import SnapshotReader
        actual=SnapshotReader.rows
        def rows(reader):
            if mode=='source-disconnect' and not marker.exists():
                marker.write_text('injected')
                reader.connection.connection.driver_connection.close()
            if mode=='terminal-extraction':
                marker.write_text('injected');raise ValueError('Synthetic terminal extraction failure')
            for row in actual(reader):
                yield row
                if mode=='extraction-kill' and not marker.exists():
                    marker.write_text('injected');os.kill(os.getpid(),signal.SIGKILL)
        stack.enter_context(patch.object(SnapshotReader,'rows',rows))
    else:raise RuntimeError('Unknown fixture fault mode')
    sys.exit(main())
