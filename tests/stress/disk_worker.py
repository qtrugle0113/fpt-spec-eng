"""Supervised T095 child: >1 GiB Unicode source through the real standalone engine."""
import json
import os
from pathlib import Path
import sys
from uuid import UUID,uuid4
from sqlalchemy import create_engine,text
from tests.unit.test_mapping import configuration
from aat_etl.contracts.config import ETLConfig
from aat_etl.engine import inspect_inputs,PreparationPins,execute_database
from aat_etl.staging.quota import QuotaManager


def main():
    if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':raise RuntimeError('Disposable stress fixture required')
    root=Path(sys.argv[1]);run=UUID(sys.argv[2]);rows=270000
    engine=create_engine(os.environ['AAT_FOUNDATION_TEST_DSN'].replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
    source='stress_source_'+run.hex;target='stress_target_'+run.hex
    print('stress_source_seed_start rows='+str(rows),flush=True)
    with engine.begin() as c:
        c.execute(text("SET LOCAL statement_timeout='120s'"))
        c.execute(text(f'CREATE TABLE {source} (id BIGINT NOT NULL, payload TEXT NOT NULL)'))
        c.execute(text(f"INSERT INTO {source} SELECT n,repeat('0123456789abcdef',256)||:unicode FROM generate_series(1,:rows) AS n"),{'unicode':'\U0001f680','rows':rows})
        c.execute(text(f'CREATE TABLE {target} (id BIGINT PRIMARY KEY, payload TEXT NOT NULL)'))
    print('stress_source_seed_complete',flush=True)
    raw=configuration();raw['source'].update(schema='public',table=source);raw['target'].update(schema='public',table=target)
    config=ETLConfig.model_validate(raw);left,right=inspect_inputs(config,engine,engine)
    raw['target']['physical_target_id']=right.physical_identity;config=ETLConfig.model_validate(raw)
    pins=PreparationPins(left.physical_identity,left.fingerprint,right.physical_identity,right.fingerprint)
    def prepared(dataset):
        files=list(root.rglob('*.jsonl'))
        info=dict(staging_payload_bytes=sum(p.stat().st_size for p in files),staging_allocated_bytes=sum(p.stat().st_blocks*512 for p in files),
            part_count=len(files),manifest_sha256=dataset.manifest_sha256)
        (root/'staging-evidence.json').write_text(json.dumps(info))
        print('stress_preparation_complete '+json.dumps(info),flush=True)
    result=execute_database(config,engine,engine,root=root,quota=QuotaManager(engine,root),run_uuid=run,dataset_id=uuid4(),
        binding_sha256='a'*64,pins=pins,support_consent=True,on_prepared=prepared)
    with engine.connect() as c:
        actual=c.execute(text(f'SELECT count(*),sum(octet_length(payload)),sum(id),count(*) FILTER (WHERE payload<>repeat(\'0123456789abcdef\',256)||:unicode) FROM {target}'),{'unicode':'\U0001f680'}).one()
        batches=c.scalar(text('SELECT count(*) FROM _aat_control.batch_commits WHERE run_uuid=:run'),{'run':run})
    evidence=dict(rows=rows,loaded_rows=result.loaded_rows,target_rows=actual[0],target_bytes=int(actual[1]),
        id_sum=int(actual[2]),bad_payload_rows=actual[3],batch_commits=batches,source_table=source,target_table=target,run_uuid=str(run),
        staging=json.loads((root/'staging-evidence.json').read_text()))
    (root/'result.json').write_text(json.dumps(evidence))
    print('stress_transfer_complete '+json.dumps(evidence),flush=True)
    engine.dispose()


if __name__=='__main__':main()
