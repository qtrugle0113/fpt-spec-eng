"""Verify parsed ownership/revision evidence within one bounded polling deadline."""
from datetime import datetime
from pathlib import PurePosixPath
import random
import time
from uuid import UUID

from aat_api.airflow_client.client import AirflowError,DeadlineTransport as _DeadlineTransport
from aat_api.airflow_client.deployment import DeploymentClient


class RegistrationTimeout(RuntimeError):
    pass


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('REGISTRATION_TIMESTAMP_MISSING')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('REGISTRATION_TIMESTAMP_UNAVAILABLE')
    return parsed


def _parse_errors(expected, errors):
    published = timestamp(expected['published_at'])
    for error in errors:
        if error.get('filename') == expected['fileloc']:
            if timestamp(error.get('timestamp')) >= published:
                raise ValueError('REGISTRATION_PARSE_ERROR')


def verify_candidate(expected: dict, dag: dict, details: dict, errors: list) -> dict:
    _parse_errors(expected, errors)
    tags = {tag.get('name') for tag in dag.get('tags', []) if isinstance(tag, dict)}
    if (dag.get('dag_id') != expected['dag_id']
            or not {expected['owner_tag'], 'aat_revision:' + expected['revision_sha256']} <= tags
            or dag.get('fileloc') != expected['fileloc']
            or dag.get('has_import_errors') is True or dag.get('is_stale') is True):
        raise ValueError('REGISTRATION_IDENTITY_MISMATCH')
    if details.get('dag_id', expected['dag_id']) != expected['dag_id']:
        raise ValueError('REGISTRATION_IDENTITY_MISMATCH')
    if details.get('fileloc', expected['fileloc']) != expected['fileloc']:
        raise ValueError('REGISTRATION_IDENTITY_MISMATCH')
    parsed = timestamp(details.get('last_parsed_time'))
    if parsed < timestamp(expected['published_at']):
        raise ValueError('REGISTRATION_PARSE_NOT_CURRENT')
    version = details.get('latest_dag_version')
    try:
        version_id = str(UUID(version['id']))
        number = version['version_number']
        if type(number) is not int or number < 1:
            raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError('REGISTRATION_VERSION_UNAVAILABLE') from None
    return dict(version_id=version_id, version_number=number, parsed_at=parsed.isoformat())


def wait(expected: dict, airflow: DeploymentClient, *, timeout: float = 120,
         clock=time.monotonic, sleep=time.sleep, jitter=random.uniform) -> dict:
    if not 0 < timeout <= 120 or not PurePosixPath(expected['fileloc']).is_absolute():
        raise ValueError('A bounded registration window and internal file path are required.')
    timestamp(expected['published_at'])
    deadline = clock() + timeout
    bounded = DeploymentClient(_DeadlineTransport(airflow.client, deadline))
    delay = 1
    while clock() < deadline:
        try:
            errors = bounded.import_errors(expected['fileloc'])
            _parse_errors(expected, errors)
            dag = bounded.dag(expected['dag_id'])
            details = bounded.details(expected['dag_id'])
            result = verify_candidate(expected, dag, details, errors)
            if expected.get('revision_id'):
                # Tags may advance before the serialized DAG is persisted.
                # Confirm revision metadata from the public task definition.
                from aat_api.airflow_client.client import segment
                task=bounded.client.request('GET','/dags/'+segment(expected['dag_id'])+'/tasks/execute_etl')
                params=task.get('params') or {}
                for key,value in (('aat_revision_id',expected['revision_id']),('aat_revision_sha256',expected['revision_sha256'])):
                    parameter=params.get(key)
                    if not isinstance(parameter,dict) or parameter.get('value')!=value:
                        raise ValueError('REGISTRATION_SERIALIZED_REVISION_MISMATCH')
                stable=bounded.details(expected['dag_id']).get('latest_dag_version') or {}
                if stable.get('id')!=result['version_id']:
                    raise ValueError('REGISTRATION_VERSION_CHANGED')
            if clock() >= deadline:
                break
            return result
        except AirflowError as error:
            if error.status in (401, 403):
                raise
        except ValueError as error:
            if str(error) == 'REGISTRATION_PARSE_ERROR':
                raise
        remaining = deadline - clock()
        if remaining <= 0:
            break
        sleep(min(remaining, min(5, delay + jitter(0, .25))))
        delay = min(5, delay * 2)
    raise RegistrationTimeout('DAG registration is unconfirmed; reconcile the same deployment identity.')
