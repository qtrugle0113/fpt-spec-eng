"""APPEND and chosen-key UPSERT, with target DML and marker in one commit."""
from uuid import uuid4
from sqlalchemy import Table,MetaData,Column,PrimaryKeyConstraint,text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DBAPIError,IntegrityError
from .ledger import BatchMarker,RunMarker
from ..readers.schema import inspect_table
from ..contracts.values import driver_row
from ..contracts.cancellation import check_cancelled


class CommitUncertain(ValueError):pass


def write_batches(dataset,session,ledger,*,strategy,batch_rows=1000,conflict_keys=(),cancelled=None):
    if strategy not in ('APPEND','UPSERT'):raise ValueError('Unsupported batch load policy.')
    c=session.connection
    session.require_owned();c.rollback()
    if session.physical_identity!=dataset.target_identity:raise ValueError('Pinned target identity does not match its native session.')
    manifest=dataset.reader().manifest
    from ..readers.file_source import FileDataset
    file_stream=isinstance(dataset,FileDataset)
    if not file_stream and (manifest['validated_rows']!=dataset.validated_rows or dataset.validated_rows!=dataset.extracted_rows):
        raise ValueError('The whole dataset must be validated before target writes.')
    profiles=dataset.target_columns if file_stream else manifest['columns']
    names=[v['name'] for v in profiles]
    target_schema=inspect_table(session.engine,schema=session.schema,table=session.table,used_columns=names)
    target_schema.require_fingerprint(dataset.target_schema_hash)
    if strategy=='UPSERT':
        if not conflict_keys or list(conflict_keys) not in [k['columns'] for k in target_schema.keys if not k.get('predicate') and not k.get('expressions')]:
            raise ValueError('UPSERT requires an exact unconditional unique key.')
        if not set(conflict_keys)<=set(names):raise ValueError('All UPSERT keys must be mapped.')
    total=dataset.extracted_rows
    final=RunMarker(dataset.target_identity,dataset.run_uuid,dataset.manifest_sha256,dataset.binding_sha256,total)
    if ledger.verify_run(c,final):c.rollback();return total
    c.rollback()
    target=Table(session.table,MetaData(),schema=session.schema,autoload_with=c);c.rollback()
    scratch=None
    try:
        if strategy=='UPSERT' and c.dialect.name=='mysql':
            scratch=Table('aat_batch_'+uuid4().hex,MetaData(),*[Column(n,target.c[n].type.copy(),nullable=False if n in conflict_keys else target.c[n].nullable) for n in names],
                PrimaryKeyConstraint(*conflict_keys),prefixes=['TEMPORARY'],mysql_engine='InnoDB')
            scratch.create(c);c.commit()
        for batch in dataset.batches(batch_rows):
            check_cancelled(cancelled)
            marker=BatchMarker(dataset.target_identity,dataset.run_uuid,dataset.manifest_sha256,batch.index,dataset.binding_sha256,len(batch.rows),batch.payload_sha256,strategy)
            with c.begin():
                session.require_owned()
                if ledger.verify_batch(c,marker):continue
                values=[driver_row(value,profiles,c.dialect.name) for value in batch.rows]
                if strategy=='APPEND':c.execute(target.insert(),values)
                elif c.dialect.name=='postgresql':
                    insert=pg_insert(target).values(values)
                    updates={n:insert.excluded[n] for n in names if n not in conflict_keys}
                    statement=insert.on_conflict_do_update(index_elements=conflict_keys,set_=updates) if updates else insert.on_conflict_do_nothing(index_elements=conflict_keys)
                    c.execute(statement)
                else:
                    c.execute(scratch.delete());c.execute(scratch.insert(),values)
                    quote=c.dialect.identifier_preparer.quote
                    target_name=c.dialect.identifier_preparer.format_table(target);scratch_name=quote(scratch.name)
                    join=' AND '.join(f't.{quote(k)}=s.{quote(k)}' for k in conflict_keys)
                    updates=','.join(f't.{quote(n)}=s.{quote(n)}' for n in names if n not in conflict_keys)
                    if updates:c.execute(text(f'UPDATE {target_name} AS t JOIN {scratch_name} AS s ON {join} SET {updates}'))
                    mapped=','.join(quote(n) for n in names);projected=','.join('s.'+quote(n) for n in names)
                    c.execute(text(f'INSERT INTO {target_name} ({mapped}) SELECT {projected} FROM {scratch_name} AS s WHERE NOT EXISTS (SELECT 1 FROM {target_name} AS t WHERE {join})'))
                ledger.record_batch(c,marker)
        with c.begin():
            check_cancelled(cancelled)
            session.require_owned()
            if not ledger.verify_run(c,final):ledger.record_run(c,final)
        return total
    except IntegrityError:
        raise ValueError('Target batch violated a constraint; earlier committed batches remain verified.') from None
    except DBAPIError:
        c.invalidate()
        raise CommitUncertain('Target connection failed; reconcile commit markers under a new native lock before retrying.') from None
    finally:
        if scratch is not None and not c.closed and not c.invalidated:
            try:
                c.rollback();c.execute(text('DROP TEMPORARY TABLE '+c.dialect.identifier_preparer.quote(scratch.name)));c.commit()
            except DBAPIError:c.invalidate()
