"""Process durable operations with independent short metadata transactions."""
import json
import os
from pathlib import Path
import time
import threading
import psycopg
from aat_metadata.repositories.base import database_url
from aat_api.services.operations import Operations
from aat_api.logging import logger
from uuid import uuid4


def connect():
    url=database_url()
    return psycopg.connect(host=url.host,port=url.port or 5432,dbname=url.database,user=url.username,
        password=url.password,connect_timeout=3,options='-c statement_timeout=5000 -c lock_timeout=2000')


def write_heartbeat(owner):
    heartbeat=Path(os.environ.get('AAT_FOUNDATION_HEARTBEAT','/tmp/aat-worker-heartbeat.json'))
    temporary=heartbeat.with_name(heartbeat.name+'.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps({'stage':'foundation','pid':os.getpid(),'owner':owner,'timestamp':time.time()}))
    temporary.replace(heartbeat)


def dispatch(operation,owner):
    """Renew leases during bounded target I/O; handlers fence every metadata commit."""
    stopped=threading.Event()
    def renew():
        while not stopped.wait(5):
            try:
                with connect() as connection:
                    connection.execute("UPDATE operations SET lease_until=now()+interval '30 seconds',heartbeat_at=now() WHERE id=%s AND state='RUNNING' AND lease_owner=%s AND lease_until>now()",(operation['id'],owner))
                    connection.execute('UPDATE worker_heartbeats SET heartbeat_at=now() WHERE owner_process_id=%s',(owner,))
                write_heartbeat(owner)
            except (psycopg.Error,OSError):
                logger.error('worker_lease_renewal_unavailable')
    thread=threading.Thread(target=renew,daemon=True);thread.start()
    try:
        if operation['kind']=='TABLE_VALIDATE':
            from aat_api.services.definition_uploads import execute_validation
            state,code=execute_validation(operation,owner)
        elif operation['kind']=='TABLE_CREATE':
            from aat_api.workers.tables import execute
            state,code=execute(operation,owner)
        elif operation['kind']=='FILE_VALIDATE':
            from aat_api.workers.files import execute
            state,code=execute(operation,owner)
        elif operation['kind']=='ETL_VALIDATE':
            from aat_api.services.etl_validation import execute
            state,code=execute(operation,owner)
        else: state,code='FAILED','OPERATION_HANDLER_UNAVAILABLE'
        with connect() as connection: Operations(connection).finish(operation['id'],owner,state=state,error_code=code)
    except Exception as error:
        # Preserve any dispatched DDL as uncertain on unexpected faults.
        logger.error('worker_operation_failed exception_type=%s',type(error).__name__)
        with connect() as connection:
            Operations(connection).finish(operation['id'],owner,state='NEEDS_RECONCILIATION' if operation['kind']=='TABLE_CREATE' else 'FAILED',error_code='OPERATION_FAILED')
    finally: stopped.set();thread.join(timeout=6)


def maintenance(stopped):
    while not stopped.is_set():
        try:
            from aat_api.workers.recovery import recover_pending,collect_expired_sources,collect_terminal_staging
            # Establish dependency readiness before starting the recovery budget.
            with connect() as connection:connection.execute('SELECT 1').fetchone()
            recover_pending(connect)
            collect_expired_sources(connect)
            collect_terminal_staging(connect,limit=1)
        except Exception as error:
            logger.warning('worker_maintenance_blocked exception_type=%s',type(error).__name__)
        stopped.wait(60)


def main():
    owner=str(os.getpid())+'-'+uuid4().hex
    stopped=threading.Event()
    # Maintenance cannot delay a claimed Operation past its lease or stop the
    # ordinary worker heartbeat while a target is unavailable.
    threading.Thread(target=maintenance,args=(stopped,),daemon=True).start()
    while True:
        try:
            with connect() as connection:
                connection.execute("""INSERT INTO worker_heartbeats(id,owner_process_id,heartbeat_at)
                    VALUES(%s,%s,now()) ON CONFLICT(owner_process_id) DO UPDATE SET heartbeat_at=now()""",(uuid4(),owner))
                operation=Operations(connection).claim(owner,ttl=30)
                # Expired DDL leases are quarantined by claim(), never reclaimed.
                # Surface their persisted dispatch state honestly in job history.
                connection.execute("""UPDATE table_creation_results r SET state='UNKNOWN',
                    error_code='DDL_OUTCOME_UNKNOWN',safe_error='Worker ownership was lost after DDL dispatch. Reconciliation is required.'
                    FROM table_creation_jobs j JOIN operations o ON o.id=j.operation_id
                    WHERE r.job_id=j.id AND r.state='CREATING' AND o.state='NEEDS_RECONCILIATION'""")
            write_heartbeat(owner)
            if operation is not None:
                dispatch(operation,owner)
        except (psycopg.Error,OSError,ValueError) as exc:
            logger.error('worker_dependency_unavailable exception_type=%s',type(exc).__name__)
        time.sleep(1)


if __name__=='__main__':main()
