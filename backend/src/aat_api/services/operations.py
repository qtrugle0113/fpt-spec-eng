"""Durable operation identity and bounded worker leases; no implicit side effects."""
from uuid import uuid4
from aat_metadata.repositories.replacement_runs import row


class Operations:
    def __init__(self,connection):self.connection=connection

    def enqueue(self,kind,key,request_sha256):
        c=self.connection
        result=row(c,"""INSERT INTO operations(id,kind,idempotency_key,request_sha256,state)
            VALUES (%s,%s,%s,%s,'QUEUED') ON CONFLICT(kind,idempotency_key) DO NOTHING RETURNING *""",
            (uuid4(),kind,str(key),request_sha256))
        if result:return result
        result=row(c,'SELECT * FROM operations WHERE kind=%s AND idempotency_key=%s',(kind,str(key)))
        if not result or result['request_sha256']!=request_sha256:raise ValueError('IDEMPOTENCY_CONFLICT')
        return result

    def claim(self,owner,ttl=15,kinds=None):
        if not owner or not 1<=ttl<=300:raise ValueError('Invalid lease')
        c=self.connection
        c.execute("""WITH expired AS (SELECT id FROM operations WHERE state='RUNNING' AND lease_until<now() FOR UPDATE SKIP LOCKED)
            UPDATE operations o SET state='NEEDS_RECONCILIATION',error_code='LEASE_EXPIRED',error_summary='operation.reconcile_required'
            FROM expired WHERE o.id=expired.id""")
        c.execute("""WITH expired AS (SELECT id FROM operations WHERE state='QUEUED' AND deadline_at<now() FOR UPDATE SKIP LOCKED)
            UPDATE operations o SET state='FAILED',error_code='DEADLINE_EXPIRED',error_summary='operation.deadline_expired'
            FROM expired WHERE o.id=expired.id""")
        return row(c,"""WITH candidate AS (SELECT id FROM operations WHERE state='QUEUED'
            AND (deadline_at IS NULL OR deadline_at>now()) AND (%s::text[] IS NULL OR kind=ANY(%s))
            ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1)
            UPDATE operations o SET state='RUNNING',attempt=attempt+1,lease_owner=%s,
            lease_until=now()+make_interval(secs=>%s),heartbeat_at=now() FROM candidate
            WHERE o.id=candidate.id RETURNING o.*""",(kinds,kinds,owner,ttl))

    def finish(self,identity,owner,*,state,error_code=None):
        if state not in ('SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION'):raise ValueError('Invalid terminal state')
        result=row(self.connection,"""UPDATE operations SET state=%s,error_code=%s,
            error_summary=CASE WHEN %s::text IS NOT NULL THEN 'operation.failed' ELSE NULL END,heartbeat_at=now()
            WHERE id=%s AND state='RUNNING' AND lease_owner=%s AND lease_until>now() RETURNING *""",(state,error_code,error_code,identity,owner))
        if result is None:raise ValueError('OPERATION_LEASE_LOST')
        return result
