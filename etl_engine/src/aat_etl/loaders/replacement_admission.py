"""Commit and read back short metadata admissions while a native lock is held."""
from dataclasses import dataclass
from uuid import UUID
import psycopg
from psycopg.rows import dict_row
from aat_metadata.repositories.authorizations import AuthorizationRepository


@dataclass(frozen=True)
class AdmissionDataset:
    dataset_id:UUID
    manifest_sha256:str
    binding_sha256:str
    run_uuid:UUID
    validated_rows:int


class AdmissionAdapter:
    def __init__(self,connection_factory,*,authorization_id,run_intent_id,binding_id,scope_sha256):
        self.connection_factory=connection_factory
        self.request=dict(authorization_id=authorization_id,run_intent_id=run_intent_id,binding_id=binding_id,scope_sha256=scope_sha256)

    def admit(self,target,dataset:AdmissionDataset,*,owner_process_id):
        target.require_owned();target.connection.rollback()
        request=dict(self.request,target_identity=target.physical_identity,dataset_sha256=dataset.manifest_sha256,
            dataset_rows=dataset.validated_rows,target_session_identity=str(target.session_id),owner_process_id=owner_process_id)
        try:
            with self.connection_factory() as c:
                with c.cursor(row_factory=dict_row) as cursor:
                    binding=cursor.execute('SELECT b.dataset_id,b.binding_hash,i.run_uuid FROM execution_bindings b JOIN run_intents i ON i.id=b.run_intent_id WHERE b.id=%s',(request['binding_id'],)).fetchone()
                if not binding or str(binding['dataset_id'])!=str(dataset.dataset_id) or binding['binding_hash']!=dataset.binding_sha256 or str(binding['run_uuid'])!=str(dataset.run_uuid):
                    raise ValueError('Admission dataset/binding/run identity mismatch.')
                admitted=AuthorizationRepository(c).admit(**request)
        except (psycopg.Error,OSError):
            # The metadata COMMIT may have succeeded. Only a matching committed
            # row can authorize DML; an unavailable readback is a closed gate.
            admitted=None
        try:
            with self.connection_factory() as c,c.cursor(row_factory=dict_row) as cursor:
                row=cursor.execute("SELECT a.*,b.dataset_id,b.binding_hash,i.run_uuid FROM replacement_admissions a JOIN execution_bindings b ON b.id=a.binding_id JOIN run_intents i ON i.id=b.run_intent_id WHERE a.binding_id=%s AND a.owner_process_id=%s AND a.target_session_identity=%s AND a.state='ADMITTED' ORDER BY a.admission_epoch DESC LIMIT 1",
                    (request['binding_id'],owner_process_id,str(target.session_id))).fetchone()
            if row is None or any(row[k]!=request[k] for k in ('authorization_id','run_intent_id','scope_sha256','target_identity','dataset_sha256')):
                raise ValueError('Committed replacement admission could not be verified; no target write is permitted.')
            if admitted is not None and row['id']!=admitted['id']:raise ValueError('Admission readback identity mismatch.')
            if str(row['dataset_id'])!=str(dataset.dataset_id) or row['binding_hash']!=dataset.binding_sha256 or str(row['run_uuid'])!=str(dataset.run_uuid):
                raise ValueError('Committed admission has a different dataset/binding/run identity.')
            target.require_owned();target.connection.rollback()
            return row
        except (psycopg.Error,OSError):
            raise ValueError('Metadata admission is unavailable; target writes are blocked.') from None

    def reconcile(self,identity,*,outcome,writer_finished=False):
        with self.connection_factory() as c:
            return AuthorizationRepository(c).reconcile(identity,outcome=outcome,writer_finished=writer_finished)

    def reconcile_committed(self,dataset_sha256):
        with self.connection_factory() as c:
            row=c.execute('SELECT id FROM replacement_admissions WHERE binding_id=%s AND dataset_sha256=%s ORDER BY admission_epoch DESC LIMIT 1',
                (self.request['binding_id'],dataset_sha256)).fetchone()
            if row is None:raise ValueError('Committed replacement has no matching admission evidence.')
            return AuthorizationRepository(c).reconcile(row[0],outcome='COMMIT_VERIFIED',writer_finished=True)

    def reconcile_rollback(self,dataset_sha256,target,old_session_id):
        from ..recovery.coordinator import require_old_session_finished
        require_old_session_finished(target,old_session_id)
        with self.connection_factory() as c:
            row=c.execute('SELECT id FROM replacement_admissions WHERE binding_id=%s AND dataset_sha256=%s AND target_session_identity=%s ORDER BY admission_epoch DESC LIMIT 1',
                (self.request['binding_id'],dataset_sha256,str(old_session_id))).fetchone()
            if row is None:raise ValueError('No prior admission matches the ended target session.')
            return AuthorizationRepository(c).reconcile(row[0],outcome='ROLLBACK_VERIFIED',writer_finished=True)

    def close_terminal(self,*,terminal_verified,retry_possible,writer_finished):
        with self.connection_factory() as c:
            return AuthorizationRepository(c).close_terminal(self.request['binding_id'],terminal_verified=terminal_verified,
                retry_possible=retry_possible,writer_finished=writer_finished)
