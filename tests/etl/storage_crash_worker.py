"""T095 child intentionally killed inside open target/staging contexts."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import time
from uuid import UUID,uuid4
from sqlalchemy import create_engine,text
from aat_etl.loaders.session import TargetSession
from aat_etl.staging.manager import StagingWriter
from aat_etl.staging.quota import QuotaManager


def main():
    if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable crash fixture required')
    root=Path(sys.argv[1]);table=sys.argv[2];run=UUID(sys.argv[3])
    if table!='crash_'+run.hex:raise ValueError('Unexpected crash fixture target')
    engine=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
    with TargetSession(engine,schema='public',table=table) as target:
        with StagingWriter(root,dag_id='crash',run_id=str(run),dataset_id=uuid4(),binding_sha256='a'*64,
            source_schema_hash='b'*64,target_schema_hash='c'*64,mapping_hash='d'*64,columns=[dict(name='id',logical_type='integer')],
            source_snapshot_time=datetime.now(timezone.utc),quota=QuotaManager(engine,root),run_uuid=run,reservation_bytes=4096) as writer:
            writer.append([1]);writer.part.flush();os.fsync(writer.part.fileno())
            with target.connection.begin():
                target.connection.execute(text(f'INSERT INTO {table} VALUES (1)'))
                (root/'ready.json').write_text(json.dumps(dict(session_id=target.session_id,manifest=str(writer.path/'manifest.json'))))
                while True:time.sleep(1)


if __name__=='__main__':main()
