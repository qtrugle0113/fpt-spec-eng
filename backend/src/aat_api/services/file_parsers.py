"""Immutable parser revisions and closed future admission after source changes."""
from datetime import datetime,timezone
from sqlalchemy import select,or_
from sqlalchemy.dialects.postgresql import insert
from aat_metadata.models.file_parsers import FileParserRevision
from aat_metadata.models.etl import ETLDefinitionRevision,ETLDefinition
from aat_metadata.models.authorizations import DataReplacementAuthorization
from aat_metadata.models.operations import AdmissionState
from aat_metadata.models.runtime import ExecutionBinding,RuntimeLease
from aat_metadata.models.replacement_runs import ReplacementAdmission
from aat_metadata.repositories.revisions import StaleRevision
from aat_api.errors import APIError
from aat_api.services.connections.service import transaction
from aat_api.services import files


def dependents(session,identity):
    return list(session.scalars(select(ETLDefinitionRevision).where(ETLDefinitionRevision.config_json['source']['file_id'].astext==str(identity))))


def active_binding(session,identity):
    parsers=select(FileParserRevision.id).where(FileParserRevision.file_id==identity)
    bindings=select(ExecutionBinding.id).where(ExecutionBinding.file_parser_revision.in_(parsers))
    if session.scalar(select(ExecutionBinding.id).outerjoin(RuntimeLease,RuntimeLease.binding_id==ExecutionBinding.id)
        .where(ExecutionBinding.file_parser_revision.in_(parsers),or_(ExecutionBinding.commit_uncertain.is_(True),
            ExecutionBinding.last_reconciled_at.is_(None),RuntimeLease.id.is_not(None))).limit(1)):
        return True
    return session.scalar(select(ReplacementAdmission.id).where(ReplacementAdmission.binding_id.in_(bindings),
        ReplacementAdmission.state.in_(['ADMITTED','NEEDS_RECONCILIATION'])).limit(1)) is not None


def patch(identity,expected_revision,value):
    config=files.parser_config(value)
    with transaction() as session:
        revisions=dependents(session,identity)
        revision_ids=[revision.id for revision in revisions]
        # Follow authorization-before-binding/admission lock order. Recheck the
        # dependency set under the file lock instead of acquiring new auth locks
        # in reverse order if another definition appeared concurrently.
        authorizations=list(session.scalars(select(DataReplacementAuthorization)
            .where(DataReplacementAuthorization.etl_revision_id.in_(revision_ids))
            .order_by(DataReplacementAuthorization.id).with_for_update()))
        file=files.require(session,identity,lock=True)
        if file.revision!=expected_revision:raise StaleRevision('Source file revision changed')
        if active_binding(session,identity):raise APIError('FILE_ACTIVE_OR_RECOVERY','Parser cannot change while a source binding is active or unreconciled.',409)
        current_revisions=dependents(session,identity)
        current_ids={revision.id for revision in current_revisions}
        current_auth=set(session.scalars(select(DataReplacementAuthorization.id).where(DataReplacementAuthorization.etl_revision_id.in_(current_ids))))
        if current_ids!=set(revision_ids) or current_auth!={row.id for row in authorizations}:
            raise APIError('FILE_DEPENDENCIES_CHANGED','Source dependencies changed concurrently. Refresh and try again.',409)
        old=files.current_parser(session,file)
        if config.model_dump()==files.parser_public(old):return files.project(session,file)
        with files.open_source(file):pass
        revision=FileParserRevision(file_id=file.id,revision=old.revision+1,**files.parser_fields(config))
        session.add(revision);session.flush()
        file.parser_revision=revision.revision;file.validation_status='PENDING'
        for authorization in authorizations:
            if authorization.state in ('GRANTED','RESERVED'):
                authorization.state='INVALIDATED';authorization.invalidated_at=datetime.now(timezone.utc)
        session.flush()
        for dependent in current_revisions:
            dependent.status='INVALID'
            dag=session.get(ETLDefinition,dependent.definition_id)
            gate=insert(AdmissionState).values(dag_id=dag.dag_id,gate_state='BLOCKED',reason='FILE_PARSER_CHANGED',etl_revision_id=dependent.id)
            session.execute(gate.on_conflict_do_update(index_elements=['dag_id'],set_={
                'gate_state':'BLOCKED','reason':'FILE_PARSER_CHANGED','generation':AdmissionState.generation+1}))
        session.flush()
        return files.project(session,file)
