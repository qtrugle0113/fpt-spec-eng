"""Submit each durable manual run once; reconcile the same ID after uncertainty."""
from datetime import datetime,timezone
import time
from sqlalchemy import select
from aat_metadata.models.operations import Operation
from aat_metadata.models.replacement_runs import RunIntent
from aat_metadata.models.authorizations import DataReplacementAuthorization
from aat_api.airflow_client.client import AirflowError,segment,DeadlineTransport
from aat_api.airflow_client.deployment import DeploymentClient
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services.definition_uploads import fence
from aat_api.services.dag_control import managed,verify_live
from aat_api.services.etl_dependencies import lock_current
from aat_api.services.runtime_binding import airflow


def _close(session,intent):
    if intent.authorization_id:
        authority=session.scalar(select(DataReplacementAuthorization).where(
            DataReplacementAuthorization.id==intent.authorization_id).with_for_update())
        if authority.scope=='ONCE' and authority.state in ('RESERVED','REVOKED','INVALIDATED'):
            authority.state='CLOSED';authority.closed_at=datetime.now(timezone.utc)
    intent.state='REJECTED'


def observe(client,dag_id,run_id):
    run=client.run(dag_id,run_id)
    if run.get('dag_id')!=dag_id or run.get('dag_run_id')!=run_id or run.get('run_type')!='manual':
        raise ValueError('AIRFLOW_RUN_IDENTITY_MISMATCH')
    return run


def _locked(session,operation_id):
    hint=session.scalar(select(RunIntent).where(RunIntent.operation_id==operation_id))
    if hint is None:return None
    if hint.authorization_id:
        session.scalar(select(DataReplacementAuthorization).where(
            DataReplacementAuthorization.id==hint.authorization_id).with_for_update())
    return session.scalar(select(RunIntent).where(RunIntent.id==hint.id).with_for_update())


def execute(operation,owner):
    fresh=False
    with transaction() as session:
        fence(session,operation,owner)
        hint=session.scalar(select(RunIntent).where(RunIntent.operation_id==operation['id']))
        if hint is None:return 'FAILED','RUN_INTENT_NOT_FOUND'
        valid=True
        if hint.state=='RESERVED':
            try:
                revision,_,_=managed(session,hint.dag_id,hint.etl_revision_id)
                lock_current(session,revision.config_json)
            except (APIError,ValueError):valid=False
        intent=_locked(session,operation['id'])
        if intent.state=='CREATED':return 'SUCCEEDED',None
        if intent.state=='REJECTED':return 'FAILED','TRIGGER_REJECTED'
        dag_id,run_id=intent.dag_id,intent.airflow_run_id
        if intent.state=='RESERVED':
            try:
                if not valid:raise APIError('DAG_NOT_READY','DAG changed before submission.',409)
                if intent.authorization_id:
                    authority=session.scalar(select(DataReplacementAuthorization).where(
                        DataReplacementAuthorization.id==intent.authorization_id).with_for_update())
                    if (authority.scope!='ONCE' or authority.state!='RESERVED' or authority.revoked_at
                            or authority.invalidated_at or authority.reserved_intent_id!=intent.id):
                        raise APIError('AUTHORIZATION_UNAVAILABLE','Replacement authority changed before submission.',409)
            except (APIError,ValueError):
                _close(session,intent)
                return 'FAILED','TRIGGER_REJECTED'
            intent.state='SUBMITTING';fresh=True
    client=airflow()
    known_rejection=False
    if fresh:
        try:verify_live(client,dag_id,intent.etl_revision_id)
        except (AirflowError,APIError,ValueError):
            with transaction() as session:
                fence(session,operation,owner)
                _close(session,_locked(session,operation['id']))
            return 'FAILED','DAG_CONTROL_NOT_VERIFIED'
        try:
            client.client.request('POST','/dags/'+segment(dag_id)+'/dagRuns',json={
                'dag_run_id':run_id,'logical_date':None,'conf':{}})
        except AirflowError as error:
            known_rejection=error.status in (400,401,403,404,422)
    try:
        observe(client,dag_id,run_id)
        observed=True
    except (AirflowError,ValueError):observed=False
    with transaction() as session:
        fence(session,operation,owner)
        intent=_locked(session,operation['id'])
        if observed:
            intent.state='CREATED';intent.last_reconciled_at=datetime.now(timezone.utc)
            return 'SUCCEEDED',None
        if known_rejection:
            _close(session,intent)
            return 'FAILED','TRIGGER_REJECTED'
        intent.state='NEEDS_RECONCILIATION'
        return 'NEEDS_RECONCILIATION','TRIGGER_UNCONFIRMED'


def reconcile_pending(limit=10):
    """Read-only Airflow reconciliation; no POST is replayed by maintenance."""
    with transaction() as session:
        identities=list(session.scalars(select(RunIntent.id).join(Operation,Operation.id==RunIntent.operation_id)
            .where(Operation.kind=='DAG_TRIGGER',Operation.state.in_(['NEEDS_RECONCILIATION','FAILED']),
                   RunIntent.state.in_(['RESERVED','SUBMITTING','NEEDS_RECONCILIATION','CREATED']))
            .order_by(RunIntent.created_at).limit(limit)))
    deadline=time.monotonic()+120
    for identity in identities:
        if time.monotonic()>=deadline:break
        with transaction() as session:
            intent=session.get(RunIntent,identity)
            dag_id,run_id=intent.dag_id,intent.airflow_run_id
            state=intent.state
        observed=False
        if state not in ('RESERVED','CREATED'):
            try:
                client=DeploymentClient(DeadlineTransport(airflow().client,deadline))
                observe(client,dag_id,run_id);observed=True
            except (AirflowError,ValueError,APIError):continue
        with transaction() as session:
            hint=session.get(RunIntent,identity)
            operation=session.scalar(select(Operation).where(Operation.id==hint.operation_id).with_for_update())
            if operation.state not in ('NEEDS_RECONCILIATION','FAILED'):continue
            intent=_locked(session,operation.id)
            if intent.state=='RESERVED':
                # The durable submit marker was never committed. A worker that
                # lost its lease cannot now pass fence() to send this request.
                _close(session,intent)
                if operation.state=='NEEDS_RECONCILIATION':operation.state='FAILED'
            elif observed or intent.state=='CREATED':
                intent.state='CREATED';intent.last_reconciled_at=datetime.now(timezone.utc)
                if operation.state=='NEEDS_RECONCILIATION':operation.state='SUCCEEDED'
