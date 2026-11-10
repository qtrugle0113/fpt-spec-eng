"""Fixed SDK wrapper; workbook values are validated data, never Python source."""
from datetime import timedelta
import json

import pendulum
from airflow.sdk import DAG, task


def execute_etl(expected_revision: str) -> None:
    from aat_etl.runtime_task import execute_task
    execute_task(expected_revision=expected_revision)


def build_dag(config: dict, revision_id: str, revision_sha256: str) -> DAG:
    start = (pendulum.parse(config['start_date']).in_timezone(config['timezone'])
             if config.get('start_date') else pendulum.datetime(2026, 1, 1, tz=config['timezone']))
    with DAG(
        config['dag_id'],
        schedule=None if config['schedule'] == 'Manual' else config['schedule'],
        start_date=start,
        catchup=config['catchup'],
        max_active_runs=1,
        is_paused_upon_creation=True,
        tags=['aat', 'aat_revision:' + revision_sha256],
    ) as dag:
        task(task_id='execute_etl', retries=config['retry_count'],
             retry_delay=timedelta(seconds=config['retry_delay']),
             params={'aat_revision_id': revision_id, 'aat_revision_sha256': revision_sha256},
             do_xcom_push=False)(execute_etl)(expected_revision=revision_id)
    return dag
