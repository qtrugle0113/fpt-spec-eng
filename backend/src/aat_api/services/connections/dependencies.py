"""Read real metadata references; invalidate future admissions without changing history."""
from datetime import datetime,timezone
from sqlalchemy import or_,select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from aat_metadata.models.connections import ConnectionRevision
from aat_metadata.models.definitions import TableDefinition,DefinitionUpload
from aat_metadata.models.etl import ETLDefinition,ETLDefinitionRevision
from aat_metadata.models.runtime import ExecutionBinding
from aat_metadata.models.authorizations import DataReplacementAuthorization
from aat_metadata.models.operations import AdmissionState


def revision_ids(session:Session,identity) -> list:
    return list(session.scalars(select(ConnectionRevision.id).where(ConnectionRevision.connection_id==identity)))


def _references(value,identities:set[str]) -> bool:
    if isinstance(value,str):return value in identities
    if isinstance(value,dict):return any(_references(v,identities) for v in value.values())
    if isinstance(value,list):return any(_references(v,identities) for v in value)
    return False


def referenced_etl(session:Session,identity) -> list:
    identities={str(identity),*(str(value) for value in revision_ids(session,identity))}
    return [row for row in session.scalars(select(ETLDefinitionRevision)).yield_per(100)
            if _references(row.config_json,identities)]


def list_dependencies(session:Session,identity) -> list[dict]:
    revisions=revision_ids(session,identity)
    references=[]
    for table in session.scalars(select(TableDefinition).where(TableDefinition.target_connection_revision_id.in_(revisions))):
        references.append({'resource_type':'DEFINITION','resource_id':str(table.upload_id),'label':'Table '+table.table_name})
    for revision in referenced_etl(session,identity):
        dag=session.get(ETLDefinition,revision.definition_id)
        references.append({'resource_type':'DAG','resource_id':dag.dag_id,'label':dag.dag_id})
    for binding in session.scalars(select(ExecutionBinding).where(or_(ExecutionBinding.source_revision_id.in_(revisions),ExecutionBinding.target_revision_id.in_(revisions)))):
        references.append({'resource_type':'RUN','resource_id':binding.airflow_run_id,'label':binding.dag_id+' / '+binding.airflow_run_id})
    unique={(r['resource_type'],r['resource_id'],r['label']):r for r in references}
    return list(unique.values())


def has_active_binding(session:Session,identity) -> bool:
    revisions=revision_ids(session,identity)
    # No heartbeat or guessed Airflow state may declare an unreconciled run safe.
    return session.scalar(select(ExecutionBinding.id).where(
        or_(ExecutionBinding.source_revision_id.in_(revisions),ExecutionBinding.target_revision_id.in_(revisions)),
        or_(ExecutionBinding.commit_uncertain.is_(True),ExecutionBinding.last_reconciled_at.is_(None))).limit(1)) is not None


def invalidate_dependents(session:Session,identity) -> None:
    revisions=revision_ids(session,identity)
    for table in session.scalars(select(TableDefinition).where(TableDefinition.target_connection_revision_id.in_(revisions))):
        upload=session.get(DefinitionUpload,table.upload_id)
        upload.status='INVALID'
    for revision in referenced_etl(session,identity):
        revision.status='INVALID'
        dag=session.get(ETLDefinition,revision.definition_id)
        gate=insert(AdmissionState).values(dag_id=dag.dag_id,gate_state='BLOCKED',reason='CONNECTION_CHANGED',
                                          etl_revision_id=revision.id)
        session.execute(gate.on_conflict_do_update(index_elements=['dag_id'],set_={
            'gate_state':'BLOCKED','reason':'CONNECTION_CHANGED','generation':AdmissionState.generation+1}))
        authorizations=session.scalars(select(DataReplacementAuthorization).where(
            DataReplacementAuthorization.etl_revision_id==revision.id).order_by(DataReplacementAuthorization.id).with_for_update())
        for authorization in authorizations:
            if authorization.state in ('GRANTED','RESERVED'):
                authorization.state='INVALIDATED'
                authorization.invalidated_at=datetime.now(timezone.utc)
