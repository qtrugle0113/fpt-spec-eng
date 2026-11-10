"""Write one read-only external DAG only inside an owned Monitoring E2E project."""
import os
from pathlib import Path

if not os.environ.get('AAT_E2E_PROJECT','').startswith(('aat-monitoring-e2e-','aat-dag_builder-e2e-')):
    raise RuntimeError('An owned isolated Monitoring fixture is required')
root=Path(os.environ.get('AAT_DAGS_ROOT','/data/generated_dags'))
source="from datetime import datetime,timezone\nfrom airflow.sdk import DAG,task\ndef noop():pass\nwith DAG('external_monitoring_fixture',schedule=None,start_date=datetime(2026,1,1,tzinfo=timezone.utc),is_paused_upon_creation=True,tags=['aat']):\n    task(task_id='noop')(noop)()\n"
(root/'external_monitoring_fixture.py').write_text(source)
print('EXTERNAL_MONITORING_FIXTURE_WRITTEN')
