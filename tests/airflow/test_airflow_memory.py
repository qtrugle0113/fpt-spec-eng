"""T147: large database transfer through a real packaged Airflow SDK task."""
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import text
from tests.airflow.test_execution import WorkflowFixture


class AirflowMemoryTests(WorkflowFixture):
    def test_large_postgres_route_uses_bounded_rss_and_disk_staging(self):
        rows=22000
        payload_bytes=65536

        def expand(book,connection,source,target,revision):
            schema='public'
            with target_engine(revision) as engine:
                quote=engine.dialect.identifier_preparer.quote_identifier
                source_table=quote(schema)+'.'+quote(source)
                target_table=quote(schema)+'.'+quote(target)
                with engine.begin() as cursor:
                    cursor.exec_driver_sql('ALTER TABLE '+source_table+' ALTER COLUMN note TYPE TEXT')
                    cursor.exec_driver_sql('ALTER TABLE '+target_table+' ALTER COLUMN note TYPE TEXT')
                    cursor.exec_driver_sql('TRUNCATE TABLE '+source_table+', '+target_table)
                    cursor.execute(text('INSERT INTO '+source_table+' SELECT id, repeat(\'x\', :payload_bytes) FROM generate_series(1, :rows) AS series(id)'),
                        {'payload_bytes':payload_bytes,'rows':rows})
            sheet=book['ETL_Definitions']
            sheet['O2']='APPEND';sheet['Q2']=1000;sheet['R2']=0

        def verify_target(engine,context):
            target=engine.dialect.identifier_preparer.quote_identifier('public')+'.'+engine.dialect.identifier_preparer.quote_identifier(context['target'])
            with engine.connect() as cursor:
                actual=cursor.execute(text('SELECT count(*),sum(octet_length(note)),sum(id),min(octet_length(note)),max(octet_length(note)) FROM '+target)).one()
            self.assertEqual(tuple(actual),(rows,rows*payload_bytes,rows*(rows+1)//2,payload_bytes,payload_bytes))
            from aat_api.services.connections.service import transaction
            with transaction() as session:
                binding=session.execute(text('''SELECT b.id,b.state AS binding_state,i.run_uuid,d.path_key,d.state AS dataset_state,d.extracted_rows,d.validated_rows,d.total_bytes,
                    m.loaded_rows FROM execution_bindings b JOIN run_intents i ON i.id=b.run_intent_id
                    JOIN dataset_manifests d ON d.id=b.dataset_id JOIN execution_metrics m ON m.binding_id=b.id
                    WHERE b.dag_id=:dag AND b.airflow_run_id=:run'''),{'dag':context['dag'],'run':context['run_id']}).one()
                artifacts=session.execute(text('SELECT count(*) AS artifact_count,sum(bytes) AS artifact_bytes,sum(rows) AS artifact_rows FROM staging_artifacts WHERE dataset_id=(SELECT dataset_id FROM execution_bindings WHERE id=:id)'),{'id':binding.id}).one()
            with engine.connect() as cursor:
                batches=cursor.scalar(text('SELECT count(*) FROM "_aat_control".batch_commits WHERE run_uuid=:run'),{'run':binding.run_uuid})
            self.assertEqual((binding.binding_state,binding.dataset_state,binding.extracted_rows,binding.validated_rows,binding.loaded_rows),('COMMIT_VERIFIED','COMPLETE',rows,rows,rows))
            self.assertGreater(binding.total_bytes,1024**3)
            self.assertEqual(artifacts.artifact_rows,rows)
            self.assertGreater(artifacts.artifact_count,20)
            self.assertGreaterEqual(binding.total_bytes,artifacts.artifact_bytes)
            self.assertLessEqual(binding.total_bytes-artifacts.artifact_bytes,8*1024**2)
            self.assertGreater(batches,20)
            stage=Path(os.environ['AAT_STAGING_ROOT'])/binding.path_key
            manifests=list(stage.rglob('manifest.json'))
            parts=list(stage.rglob('*.jsonl'))
            self.assertTrue(manifests)
            self.assertGreater(sum(path.stat().st_size for path in parts),1024**3)
            self.assertGreater(sum(path.stat().st_blocks*512 for path in parts),1024**3)
            self.staging_evidence={'manifest_sha256':hashlib.sha256(manifests[-1].read_bytes()).hexdigest(),
                'payload_bytes':sum(path.stat().st_size for path in parts),'allocated_bytes':sum(path.stat().st_blocks*512 for path in parts),
                'part_count':len(parts),'batch_commits':batches}
            return rows

        from aat_api.services.table_preview import target_engine
        from aat_api.workers import deployments
        original_render=deployments.factory.render

        def instrument(*args,**kwargs):
            source=original_render(*args,**kwargs).decode()
            marker='from aat_etl.runtime_task import execute_task'
            observer='''import aat_etl.runtime_task as _aat_runtime_task
from airflow.sdk import get_current_context as _aat_get_context
from pathlib import Path as _aat_Path
import hashlib as _aat_hashlib, json as _aat_json
_aat_original_supervised = _aat_runtime_task.run_supervised
def _aat_measure(command):
    result = _aat_original_supervised(command)
    ti = _aat_get_context()['ti']
    key = _aat_hashlib.sha256((ti.dag_id + ti.run_id).encode()).hexdigest()
    metrics = {'pid':result.pid,'reason':result.reason,'exit_code':result.exit_code,
        'peak_rss_bytes':result.peak_rss_bytes,'memory_budget_bytes':result.memory_budget_bytes}
    (_aat_Path('/tmp/aat-runtime-staging') / ('airflow-memory-' + key + '.json')).write_text(_aat_json.dumps(metrics))
    return result
_aat_runtime_task.run_supervised = _aat_measure
'''
            if marker not in source:raise AssertionError('Generated DAG does not call the packaged runtime task.')
            source=source.replace(marker,observer.replace('\n','\n    ')+'\n    '+marker)
            compile(source,'<generated-airflow-memory-dag>','exec')
            return source.encode()

        with patch.object(deployments.factory,'render',side_effect=instrument):
            result=self.workflow(target_kind='POSTGRESQL',strategy='APPEND',workbook_edit=expand,target_verifier=verify_target)
        resource_key=hashlib.sha256((result['dag']+result['run_id']).encode()).hexdigest()
        resource_file=Path(os.environ['AAT_STAGING_ROOT'])/('airflow-memory-'+resource_key+'.json')
        resource=json.loads(resource_file.read_text())
        self.assertEqual(resource['reason'],'COMPLETED')
        self.assertEqual(resource['exit_code'],0)
        self.assertGreater(resource['peak_rss_bytes'],0)
        self.assertLessEqual(resource['peak_rss_bytes'],512*1024**2)
        print('AIRFLOW_MEMORY_VERIFIED '+json.dumps({'rows':rows,'payload_bytes':rows*payload_bytes,
            'peak_rss_bytes':resource['peak_rss_bytes'],'memory_budget_bytes':resource['memory_budget_bytes'],
            'staging':self.staging_evidence},sort_keys=True),flush=True)