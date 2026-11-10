"""Verify live Airflow identity before short immutable metadata publication."""
from pathlib import Path
import os
import threading
from uuid import UUID
import psycopg
from aat_metadata.repositories.base import database_url
from aat_metadata.repositories.bindings import BindingRepository,VerifiedRun
from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
from aat_etl.contracts.config import ETLConfig
from sqlalchemy import select
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.airflow_client.client import AirflowClient,AirflowError
from aat_api.airflow_client.deployment import DeploymentClient

_client=None
_client_lock=threading.Lock()


def airflow():
    global _client
    with _client_lock:
        if _client is None:
            try:password=Path(os.environ.get('AAT_AIRFLOW_PASSWORD_FILE','/secrets/backend/airflow_service_password')).read_text().strip()
            except OSError:raise APIError('AIRFLOW_AUTH_UNAVAILABLE','Airflow service credentials are unavailable.',503) from None
            _client=AirflowClient(os.environ.get('AAT_AIRFLOW_ORIGIN','http://airflow-apiserver:8080'),username='aat_service',password=password)
        return DeploymentClient(_client)


def close_airflow():
    global _client
    with _client_lock:
        if _client is not None:_client.close();_client=None


def bind(value):
    try:expected=UUID(value.expected_revision)
    except ValueError:raise APIError('REVISION_MISMATCH','Wrapper revision is invalid.',409) from None
    with transaction() as session:
        revision=session.scalar(select(ETLDefinitionRevision).join(ETLDefinition,ETLDefinition.id==ETLDefinitionRevision.definition_id).where(ETLDefinitionRevision.id==expected,ETLDefinition.dag_id==value.dag_id))
        if revision is None:raise APIError('ETL_REVISION_NOT_FOUND','ETL revision not found.',404)
        ETLConfig.model_validate(revision.config_json);expected_hash=revision.config_sha256
    if value.task_id!='execute_etl':raise APIError('RUNTIME_IDENTITY_REJECTED','Runtime task identity is not managed by this application.',403)
    try:
        client=airflow();run=client.run(value.dag_id,value.run_id);task=client.task(value.dag_id,value.run_id,value.task_id)
        dag=client.dag(value.dag_id);details=client.details(value.dag_id)
        version=UUID(task['dag_version']['id'])
        latest=UUID(details['latest_dag_version']['id'])
        tags={entry['name'] for entry in dag.get('tags',[])}
        if run.get('dag_id')!=value.dag_id or run.get('dag_run_id')!=value.run_id or task.get('dag_id')!=value.dag_id or task.get('dag_run_id')!=value.run_id or task.get('task_id')!=value.task_id:
            raise ValueError()
        if latest!=version or value.dag_version_id is not None and value.dag_version_id!=version or 'aat' not in tags or 'aat_revision:'+expected_hash not in tags:
            raise ValueError()
    except AirflowError as error:
        raise APIError('AIRFLOW_IDENTITY_UNAVAILABLE','Airflow run/task identity could not be verified.',error.status if error.status in (403,404) else 503,error.retryable) from None
    except (ValueError,KeyError,TypeError,AttributeError):raise APIError('REVISION_MISMATCH','Airflow task version or wrapper revision does not match the deployed revision.',409) from None
    facts=VerifiedRun(value.dag_id,value.run_id,value.task_id,version,run['run_type'],expected)
    url=database_url()
    try:
        with psycopg.connect(host=url.host,port=url.port or 5432,dbname=url.database,user=url.username,password=url.password,
            connect_timeout=3,options='-c statement_timeout=10000 -c lock_timeout=3000') as connection:
            return BindingRepository(connection).bind(facts)
    except ValueError as error:
        known={'RUNTIME_IDENTITY_REJECTED','ETL_REVISION_NOT_FOUND','REVISION_MISMATCH','DAG_ADMISSION_BLOCKED','DEPENDENCY_CHANGED',
               'ONCE_INTENT_REQUIRED','AUTHORIZATION_UNAVAILABLE','SCHEDULED_AUTHORIZATION_REQUIRED','AUTHORIZATION_SCOPE_MISMATCH','RUN_INTENT_MISMATCH'}
        code=error.args[0] if error.args and isinstance(error.args[0],str) and error.args[0] in known else 'BINDING_REJECTED'
        raise APIError(code,'Runtime binding was rejected. Verify deployment, dependencies and replacement authorization.',409) from None
    except psycopg.Error:raise APIError('BINDING_UNAVAILABLE','Runtime binding could not be confirmed. Retry the same run identity.',503,True) from None
