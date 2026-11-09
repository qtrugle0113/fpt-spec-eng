"""Process durable operations with independent short metadata transactions."""
import json
import os
from pathlib import Path
import time
import psycopg
from aat_metadata.repositories.base import database_url
from aat_api.services.operations import Operations
from aat_api.logging import logger
from uuid import uuid4


def connect():
    url=database_url()
    return psycopg.connect(host=url.host,port=url.port or 5432,dbname=url.database,user=url.username,
        password=url.password,connect_timeout=3,options='-c statement_timeout=5000 -c lock_timeout=2000')


def main():
    owner=str(os.getpid())+'-'+uuid4().hex;heartbeat=Path(os.environ.get('AAT_FOUNDATION_HEARTBEAT','/tmp/aat-worker-heartbeat.json'))
    while True:
        try:
            with connect() as connection:
                connection.execute("""INSERT INTO worker_heartbeats(id,owner_process_id,heartbeat_at)
                    VALUES(%s,%s,now()) ON CONFLICT(owner_process_id) DO UPDATE SET heartbeat_at=now()""",(uuid4(),owner))
                operation=Operations(connection).claim(owner)
            temporary=heartbeat.with_suffix('.tmp')
            temporary.write_text(json.dumps({'stage':'foundation','pid':os.getpid(),'owner':owner,'timestamp':time.time()}));temporary.replace(heartbeat)
            if operation is not None:
                # Concrete business handlers are introduced with their own phases.
                # Unknown kinds fail visibly; never claim that their side effect ran.
                with connect() as connection:
                    Operations(connection).finish(operation['id'],owner,state='FAILED',error_code='OPERATION_HANDLER_UNAVAILABLE')
        except (psycopg.Error,OSError,ValueError) as exc:
            logger.error('worker_dependency_unavailable exception_type=%s',type(exc).__name__)
        time.sleep(1)


if __name__=='__main__':main()
