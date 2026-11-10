"""Verify browser-created runs against public Airflow state and actual targets."""
import time
from sqlalchemy import text
from aat_api.services.connections.service import transaction
from aat_api.services.runtime_binding import airflow,close_airflow
from aat_api.services.table_preview import target_engine

try:
    deadline=time.monotonic()+180
    while True:
        with transaction() as session:
            dags=session.scalars(text("SELECT dag_id FROM etl_definitions WHERE dag_id LIKE 'aat_browser_append_%' OR dag_id LIKE 'aat_browser_runrefresh_%'")).all()
        runs=[run for dag in dags for run in airflow().runs(dag)]
        if len(runs)>=2 and all(run['state']=='success' for run in runs):break
        if any(run['state']=='failed' for run in runs):raise RuntimeError('Browser ETL run failed')
        if time.monotonic()>deadline:raise RuntimeError('Browser ETL runs did not finish before the deadline')
        time.sleep(2)
    with transaction() as session:
        metrics=session.execute(text("""SELECT b.state,b.commit_uncertain,m.extracted_rows,m.validated_rows,m.loaded_rows,m.failed_rows_nullable,m.phase
            FROM execution_bindings b JOIN execution_metrics m ON m.binding_id=b.id WHERE b.dag_id LIKE 'aat_browser_append_%' OR b.dag_id LIKE 'aat_browser_runrefresh_%'""")).all()
        if len(metrics)<2 or any(tuple(row)!=('COMMIT_VERIFIED',False,3,3,3,0,'COMPLETE') for row in metrics):
            raise RuntimeError('Browser execution metrics do not prove committed rows')
        revision=session.scalar(text("SELECT current_revision_id FROM connections WHERE normalized_code='pg_etl'"))
    with target_engine(revision) as engine,engine.connect() as connection:
        source=connection.execute(text('SELECT * FROM sample.customers_source ORDER BY customer_id')).all()
        target=connection.execute(text('SELECT * FROM sample.customers_target ORDER BY customer_id')).all()
        if len(target)!=3 or source!=target:raise RuntimeError('Browser target values differ from the source')
    print('BROWSER_ETL_VERIFIED real_airflow_success=true committed_bindings='+str(len(metrics))+' rows=3 target_values_match=true')
finally:close_airflow()
