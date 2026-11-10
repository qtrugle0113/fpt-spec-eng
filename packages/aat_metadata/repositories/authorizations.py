"""Serialized FULL_REFRESH control, never target commit inference or DML."""
from uuid import uuid4
from .replacement_runs import row,transition_admission


def transition_authorization(state,event,*,scope,commit_verified=False,terminal_verified=False,retry_possible=False,commit_unknown=False):
    if scope not in ('ONCE','SCHEDULED'):raise ValueError('Unsupported authorization scope')
    if event=='reconcile_commit' and commit_verified:
        if scope=='SCHEDULED' and state=='GRANTED':return 'GRANTED'
        if scope=='ONCE' and state in ('RESERVED','REVOKED','INVALIDATED'):return 'CONSUMED'
    if event=='close' and scope=='ONCE' and state in ('RESERVED','REVOKED','INVALIDATED') and terminal_verified and not retry_possible and not commit_unknown:return 'CLOSED'
    if state in ('GRANTED','RESERVED') and event in ('revoke','invalidate'):return 'REVOKED' if event=='revoke' else 'INVALIDATED'
    if state=='GRANTED' and scope=='ONCE' and event=='reserve':return 'RESERVED'
    if state=='RESERVED' and scope=='ONCE' and event=='extraction_retry':return 'RESERVED'
    if event=='admit' and ((scope=='ONCE' and state=='RESERVED') or (scope=='SCHEDULED' and state=='GRANTED')):return state
    raise ValueError('Illegal authorization transition')


class AuthorizationRepository:
    def __init__(self,connection):self.connection=connection

    def authorization(self,identity):
        result=row(self.connection,'SELECT * FROM replacement_authorizations WHERE id=%s FOR UPDATE',(identity,))
        if result is None:raise ValueError('AUTHORIZATION_NOT_FOUND')
        return result

    def check_scope(self,authorization,request):
        for key in ('dag_id','etl_revision_id','physical_target_id','scope_sha256'):
            if key in request and str(request[key])!=str(authorization[key]):raise ValueError('AUTHORIZATION_SCOPE_MISMATCH')

    def reserve_once(self,**request):return self._intent(request,scheduled=False)
    def schedule_intent(self,**request):return self._intent(request,scheduled=True)

    def _intent(self,request,scheduled):
        c=self.connection;a=self.authorization(request['authorization_id']);self.check_scope(a,request)
        existing=row(c,"SELECT i.*,o.request_sha256 AS operation_request FROM operations o JOIN run_intents i ON i.operation_id=o.id WHERE o.kind='DAG_TRIGGER' AND o.idempotency_key=%s",(str(request['idempotency_key']),))
        if existing:
            if existing['operation_request']!=request['request_sha256'] or existing['authorization_id']!=a['id']:raise ValueError('IDEMPOTENCY_CONFLICT')
            existing.pop('operation_request');return existing
        if scheduled:
            if a['scope']!='SCHEDULED' or a['state']!='GRANTED' or request.get('run_type')!='scheduled' or request.get('schedule_sha256')!=a['schedule_sha256']:raise ValueError('AUTHORIZATION_SCOPE_MISMATCH')
        else:
            if a['scope']!='ONCE' or a['state']!='GRANTED' or a['reserved_intent_id'] is not None:raise ValueError('AUTHORIZATION_ALREADY_RESERVED')
        if a['revoked_at'] is not None or a['invalidated_at'] is not None:raise ValueError('AUTHORIZATION_REVOKED')
        operation_id=request.get('operation_id') or uuid4();intent_id=uuid4()
        c.execute("INSERT INTO operations(id,kind,idempotency_key,request_sha256,state) VALUES (%s,'DAG_TRIGGER',%s,%s,'QUEUED')",(operation_id,str(request['idempotency_key']),request['request_sha256']))
        intent=row(c,"""INSERT INTO run_intents(id,operation_id,run_uuid,dag_id,airflow_run_id,run_type,
            etl_revision_id,authorization_id,request_sha256,state) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'RESERVED') RETURNING *""",
            (intent_id,operation_id,request['run_uuid'],a['dag_id'],request['airflow_run_id'],'scheduled' if scheduled else 'manual',a['etl_revision_id'],a['id'],request['request_sha256']))
        if not scheduled:c.execute("UPDATE replacement_authorizations SET state='RESERVED',reserved_intent_id=%s WHERE id=%s",(intent_id,a['id']))
        return intent

    def revoke(self,identity):
        a=self.authorization(identity)
        return row(self.connection,"UPDATE replacement_authorizations SET state=CASE WHEN state IN ('GRANTED','RESERVED') THEN 'REVOKED' ELSE state END,revoked_at=coalesce(revoked_at,now()) WHERE id=%s RETURNING *",(a['id'],))

    def invalidate(self,identity):
        a=self.authorization(identity)
        return row(self.connection,"UPDATE replacement_authorizations SET state=CASE WHEN state IN ('GRANTED','RESERVED') THEN 'INVALIDATED' ELSE state END,invalidated_at=coalesce(invalidated_at,now()) WHERE id=%s RETURNING *",(a['id'],))

    def close_terminal(self,binding_id,*,terminal_verified,retry_possible,writer_finished):
        if terminal_verified is not True or retry_possible is not False or writer_finished is not True:
            raise ValueError('TERMINAL_WRITER_PROOF_REQUIRED')
        c=self.connection
        hint=row(c,'SELECT authorization_id,run_intent_id FROM execution_bindings WHERE id=%s',(binding_id,))
        if not hint or hint['authorization_id'] is None:raise ValueError('BINDING_AUTHORIZATION_NOT_FOUND')
        authorization=self.authorization(hint['authorization_id'])
        row(c,'SELECT id FROM run_intents WHERE id=%s FOR UPDATE',(hint['run_intent_id'],))
        binding=row(c,'SELECT * FROM execution_bindings WHERE id=%s FOR UPDATE',(binding_id,))
        if binding['commit_uncertain']:raise ValueError('REPLACEMENT_RECONCILIATION_REQUIRED')
        pending=row(c,"SELECT id FROM replacement_admissions WHERE binding_id=%s AND state IN ('ADMITTED','NEEDS_RECONCILIATION') LIMIT 1 FOR UPDATE",(binding_id,))
        if pending:raise ValueError('REPLACEMENT_RECONCILIATION_REQUIRED')
        if authorization['scope']=='SCHEDULED' or authorization['state'] in ('CONSUMED','CLOSED'):return authorization
        state=transition_authorization(authorization['state'],'close',scope=authorization['scope'],terminal_verified=True,retry_possible=False,commit_unknown=False)
        return row(c,'UPDATE replacement_authorizations SET state=%s,closed_at=now() WHERE id=%s RETURNING *',(state,authorization['id']))

    def admit(self,**request):
        c=self.connection;a=self.authorization(request['authorization_id'])
        transition_authorization(a['state'],'admit',scope=a['scope'])
        if a['revoked_at'] is not None or a['invalidated_at'] is not None:raise ValueError('AUTHORIZATION_REVOKED')
        intent=row(c,'SELECT * FROM run_intents WHERE id=%s FOR UPDATE',(request['run_intent_id'],))
        binding=row(c,'SELECT * FROM execution_bindings WHERE id=%s FOR UPDATE',(request['binding_id'],))
        if not intent or not binding or intent['authorization_id']!=a['id'] or binding['authorization_id']!=a['id'] or binding['run_intent_id']!=intent['id']:raise ValueError('BINDING_SCOPE_MISMATCH')
        if intent['etl_revision_id']!=a['etl_revision_id'] or binding['etl_revision_id']!=a['etl_revision_id'] or binding['dag_id']!=a['dag_id'] or intent['dag_id']!=a['dag_id']:raise ValueError('BINDING_SCOPE_MISMATCH')
        if a['scope']=='ONCE' and a['reserved_intent_id']!=intent['id']:raise ValueError('AUTHORIZATION_ALREADY_RESERVED')
        if a['scope']=='SCHEDULED' and (intent['run_type']!='scheduled' or binding['airflow_run_type']!='scheduled'):raise ValueError('AUTHORIZATION_SCOPE_MISMATCH')
        if request['scope_sha256']!=a['scope_sha256'] or request['target_identity']!=a['physical_target_id']:raise ValueError('AUTHORIZATION_SCOPE_MISMATCH')
        dataset=row(c,'SELECT * FROM dataset_manifests WHERE id=%s AND execution_binding_id=%s',(binding['dataset_id'],binding['id']))
        if not dataset or dataset['state'] not in ('COMPLETE','PROTECTED') or dataset['manifest_sha256']!=request['dataset_sha256']:raise ValueError('DATASET_NOT_VERIFIED')
        if 'dataset_rows' in request and request['dataset_rows']!=dataset['validated_rows']:raise ValueError('DATASET_SCOPE_MISMATCH')
        if dataset['validated_rows']==0 and not (a['allow_empty'] and a['allow_empty_acknowledged_at'] is not None):raise ValueError('EMPTY_REPLACEMENT_NOT_AUTHORIZED')
        previous=row(c,'SELECT * FROM replacement_admissions WHERE binding_id=%s ORDER BY admission_epoch DESC LIMIT 1 FOR UPDATE',(binding['id'],))
        if previous:
            if previous['state']=='ADMITTED':
                if all(previous[k]==request[k] for k in ('owner_process_id','target_session_identity','scope_sha256','dataset_sha256','target_identity')):return previous
                raise ValueError('REPLACEMENT_RECONCILIATION_REQUIRED')
            if previous['state']!='ROLLBACK_VERIFIED' or not previous['writer_finished']:raise ValueError('REPLACEMENT_RECONCILIATION_REQUIRED')
        epoch=previous['admission_epoch']+1 if previous else 1
        return row(c,"""INSERT INTO replacement_admissions(id,binding_id,run_intent_id,authorization_id,admission_epoch,
            authorization_revision,scope_sha256,dataset_sha256,target_identity,owner_process_id,target_session_identity,state)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ADMITTED') RETURNING *""",
            (uuid4(),binding['id'],intent['id'],a['id'],epoch,a['revision'],request['scope_sha256'],request['dataset_sha256'],
             request['target_identity'],request['owner_process_id'],request['target_session_identity']))

    def reconcile(self,identity,*,outcome,writer_finished=False):
        c=self.connection;hint=row(c,'SELECT * FROM replacement_admissions WHERE id=%s',(identity,))
        if not hint:raise ValueError('ADMISSION_NOT_FOUND')
        a=self.authorization(hint['authorization_id'])
        row(c,'SELECT id FROM run_intents WHERE id=%s FOR UPDATE',(hint['run_intent_id'],))
        row(c,'SELECT id FROM execution_bindings WHERE id=%s FOR UPDATE',(hint['binding_id'],))
        admission=row(c,'SELECT * FROM replacement_admissions WHERE id=%s FOR UPDATE',(identity,))
        if admission['state']==outcome:return admission
        event={'COMMIT_VERIFIED':'commit_verified','ROLLBACK_VERIFIED':'rollback_verified','NEEDS_RECONCILIATION':'unknown_outcome'}.get(outcome)
        state=transition_admission(admission['state'],event)
        if state=='ROLLBACK_VERIFIED' and not writer_finished:raise ValueError('PREVIOUS_WRITER_NOT_FINISHED')
        result=row(c,'UPDATE replacement_admissions SET state=%s,writer_finished=%s,reconciled_at=now() WHERE id=%s RETURNING *',(state,writer_finished,identity))
        if outcome=='COMMIT_VERIFIED' and a['scope']=='ONCE':
            transition_authorization(a['state'],'reconcile_commit',scope=a['scope'],commit_verified=True)
            c.execute("UPDATE replacement_authorizations SET state='CONSUMED',consumed_at=now() WHERE id=%s",(a['id'],))
        c.execute('UPDATE execution_bindings SET commit_uncertain=%s,last_reconciled_at=now() WHERE id=%s',(outcome=='NEEDS_RECONCILIATION',hint['binding_id']))
        return result
