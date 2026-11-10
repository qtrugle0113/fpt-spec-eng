"""Pause/unpause with verified ownership and readback; no run cancellation."""
from datetime import datetime,timezone
import time
from uuid import UUID
from sqlalchemy import select
from aat_metadata.models.operations import Operation
from aat_api.airflow_client.client import AirflowError,DeadlineTransport
from aat_api.airflow_client.deployment import DeploymentClient
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import fence
from aat_api.services.dag_control import managed,verify_live
from aat_api.services.dag_activation import check_authority
from aat_api.services.etl_dependencies import lock_current
from aat_api.services.runtime_binding import airflow


def check(session,payload):
    revision,gate,_=managed(session,payload['dag_id'],UUID(payload['revision_id']))
    if gate.generation!=payload['generation'] or gate.desired_paused!=payload['is_paused']:
        raise APIError('DAG_CONTROL_SUPERSEDED','A newer command or deployment superseded this request.',409)
    if not payload['is_paused']:lock_current(session,revision.config_json)
    check_authority(session,revision,UUID(payload['authorization_id']) if payload.get('authorization_id') else None,payload['is_paused'])


def execute(operation,owner):
    with transaction() as session:
        current=fence(session,operation,owner);payload=dict(current.progress_json)
        try:check(session,payload)
        except APIError as error:return 'FAILED',error.code
        remaining=(current.deadline_at-datetime.now(timezone.utc)).total_seconds() if current.deadline_at else 120
    if remaining<=0:return 'FAILED','DEADLINE_EXPIRED'
    client=DeploymentClient(DeadlineTransport(airflow().client,time.monotonic()+min(120,remaining)))
    try:verify_live(client,payload['dag_id'],UUID(payload['revision_id']))
    except (APIError,AirflowError,ValueError):return 'FAILED','DAG_CONTROL_NOT_VERIFIED'
    with transaction() as session:
        current=fence(session,operation,owner)
        try:check(session,payload)
        except APIError as error:return 'FAILED',error.code
        payload['dispatched']=True;current.progress_json=payload
    try:client.pause(payload['dag_id'],payload['is_paused'])
    except AirflowError:pass
    try:
        actual=client.dag(payload['dag_id'])
        if actual.get('is_paused') is not payload['is_paused']:
            return 'NEEDS_RECONCILIATION','DAG_STATE_UNCONFIRMED'
    except AirflowError:return 'NEEDS_RECONCILIATION','DAG_STATE_UNCONFIRMED'
    with transaction() as session:
        fence(session,operation,owner)
        try:check(session,payload)
        except APIError as error:return 'FAILED',error.code
    return 'SUCCEEDED',None


def reconcile_pending(limit=10):
    with transaction() as session:
        pending=[(row.id,dict(row.progress_json)) for row in session.scalars(select(Operation).where(
            Operation.kind=='DAG_STATE',Operation.state=='NEEDS_RECONCILIATION').order_by(Operation.created_at).limit(limit))]
    deadline=time.monotonic()+120
    for identity,payload in pending:
        if time.monotonic()>=deadline:break
        with transaction() as session:
            current=session.scalar(select(Operation).where(Operation.id==identity).with_for_update())
            if current.state!='NEEDS_RECONCILIATION':continue
            try:check(session,payload)
            except APIError as error:
                current.state='FAILED';current.error_code=error.code
                continue
        try:
            client=DeploymentClient(DeadlineTransport(airflow().client,deadline))
            verify_live(client,payload['dag_id'],UUID(payload['revision_id']))
            actual=client.dag(payload['dag_id'])
        except (AirflowError,APIError,ValueError):continue
        with transaction() as session:
            current=session.scalar(select(Operation).where(Operation.id==identity).with_for_update())
            if current.state!='NEEDS_RECONCILIATION':continue
            try:check(session,payload)
            except APIError as error:
                current.state='FAILED';current.error_code=error.code
                continue
            if actual.get('is_paused') is payload['is_paused']:
                current.state='SUCCEEDED';current.error_code=None
