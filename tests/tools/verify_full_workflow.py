"""Read real targets and public Airflow state after the browser's full workflow."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from sqlalchemy import text
from aat_api.services.connections.service import transaction
from aat_api.services.runtime_binding import airflow,close_airflow
from aat_api.services.table_preview import target_engine

references=json.loads(Path('/tmp/full-workflows.json').read_text())
if len(references)!=2:raise RuntimeError('Desktop and mobile workflow evidence required')
expected=[(1,'Nguyễn, An',Decimal('12345.6789'),datetime(2026,1,1,12,30,0,123456)),
    (2,'Line one\nLine two',Decimal('0.0000'),None),
    (3,'Quote "sample"',Decimal('-12.3400'),datetime(2026,1,3)),
    (4,'\\N',None,datetime(2026,1,4))]
try:
    for item in references:
        if not re.fullmatch(r'full_(desktop|mobile)_[0-9]+',item['table']):raise RuntimeError('Invalid owned fixture table')
        if item['elapsed_ms']>=600000:raise RuntimeError('Workflow exceeded10minutes')
        runs=airflow().runs(item['dag'])
        if not any(r['dag_run_id']==item['run'] and r['state']=='success' for r in runs):raise RuntimeError('Actual Airflow success missing')
        with transaction() as session:
            revision=session.scalar(text('SELECT current_revision_id FROM connections WHERE normalized_code=:code'),{'code':item['code']})
            metrics=session.execute(text("SELECT b.state,b.commit_uncertain,m.loaded_rows,m.phase FROM execution_bindings b JOIN execution_metrics m ON m.binding_id=b.id WHERE b.dag_id=:dag AND b.airflow_run_id=:run"),{'dag':item['dag'],'run':item['run']}).one()
            if tuple(metrics)!=('COMMIT_VERIFIED',False,4,'COMPLETE'):raise RuntimeError('Committed metrics missing')
        # Restrict identifiers to owned fixture tables and quote by dialect.
        with target_engine(revision) as engine,engine.connect() as connection:
            identifier=engine.dialect.identifier_preparer.quote_identifier(item['table'])
            actual=connection.execute(text('SELECT customer_id,customer_name,balance,registered_at FROM public.'+identifier+' ORDER BY customer_id')).all()
            if [tuple(row) for row in actual]!=expected:raise RuntimeError('Actual target values differ from the uploaded CSV')
        print('FULL_WORKFLOW_VERIFIED '+json.dumps({'dag':item['dag'],'rows':4,'real_airflow_success':True,'exact_target_values':True,'elapsed_ms':item['elapsed_ms']}))
finally:close_airflow()
