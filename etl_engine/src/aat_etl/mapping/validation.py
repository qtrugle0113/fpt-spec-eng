"""Streaming target-typed validation and on-disk chosen-key uniqueness scratch."""
from dataclasses import dataclass
from uuid import uuid4
from sqlalchemy import Column, MetaData, Table, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from ..contracts.config import identifier
from ..staging.codec import scalar
from ..staging.manager import encoded
from ..readers.schema import column_profile
from ..contracts.values import driver_row

MAX_ROWS = 5_000_000
MAX_BYTES = 10 * 1024**3


@dataclass(frozen=True)
class ValidationResult:
    validated_rows: int
    scratch_bytes: int


def validate_rows(connection, *, schema, table, columns, rows, conflict_keys=(),
                  max_rows=MAX_ROWS, max_bytes=MAX_BYTES) -> ValidationResult:
    """No target DML. Own the scratch transaction and drop it on every exit.

    MySQL temporary InnoDB sizes are not exposed to ordinary target accounts.
    Charge 2 MiB initial page headroom plus 4x (encoded bytes + 256) per row,
    capped independently of row count. PG additionally checks actual
    relation/index allocation. No in-memory set of dataset keys is maintained.
    """
    identifier(schema);identifier(table)
    if connection.in_transaction():raise ValueError('Validation requires an idle target session.')
    if not columns or len(set(columns)) != len(columns):raise ValueError('Distinct mapped columns are required.')
    for name in (*columns, *conflict_keys):identifier(name)
    if len(set(conflict_keys)) != len(conflict_keys) or not set(conflict_keys) <= set(columns):
        raise ValueError('Chosen keys must be distinct mapped columns.')
    if type(max_rows) is not int or not 1<=max_rows<=MAX_ROWS or type(max_bytes) is not int or not 1<=max_bytes<=MAX_BYTES:
        raise ValueError('Scratch limits cannot exceed the configured budgets.')
    dialect = connection.dialect.name
    if dialect not in ('postgresql','mysql'):raise ValueError('Unsupported scratch adapter.')
    target = Table(table, MetaData(), schema=schema, autoload_with=connection)
    inspector=inspect(connection)
    keys=[inspector.get_pk_constraint(table,schema=schema).get('constrained_columns')]
    keys += [k.get('column_names') for k in inspector.get_unique_constraints(table,schema=schema)]
    keys += [k.get('column_names') for k in inspector.get_indexes(table,schema=schema)
             if k.get('unique') and not k.get('expressions') and not k.get('dialect_options')]
    if conflict_keys and list(conflict_keys) not in keys:
        connection.rollback();raise ValueError('UPSERT requires an exact primary or unconditional unique key.')
    if any(name not in target.c for name in columns):
        connection.rollback();raise ValueError('A mapped target column is missing.')
    profiles={name:column_profile(dict(name=name,type=target.c[name].type,nullable=target.c[name].nullable),dialect) for name in columns}
    quote=connection.dialect.identifier_preparer.quote
    scratch='aat_validate_'+uuid4().hex
    name=quote(scratch)
    created=False;count=0;charged=2*1024**2;physical=0
    try:
        if dialect=='mysql':
            connection.execute(text("SET time_zone='+00:00'"))
            mode=connection.scalar(text('SELECT @@session.sql_mode'))
            if not {'STRICT_TRANS_TABLES','STRICT_ALL_TABLES'} & set(mode.split(',')):
                raise ValueError('Strict MySQL mode is required for validation.')
        definitions=[]
        if dialect=='postgresql':
            collation_rows=connection.execute(text('SELECT a.attname,cn.nspname,co.collname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_collation co ON co.oid=a.attcollation JOIN pg_namespace cn ON cn.oid=co.collnamespace WHERE n.nspname=:schema AND c.relname=:table'),{'schema':schema,'table':table})
            collations={r[0]:quote(r[1])+'.'+quote(r[2]) for r in collation_rows}
        else:
            collations={r[0]:quote(r[1]) for r in connection.execute(text('SELECT COLUMN_NAME,COLLATION_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=:schema AND TABLE_NAME=:table AND COLLATION_NAME IS NOT NULL'),{'schema':schema,'table':table})}
        for column_name in columns:
            datatype=target.c[column_name].type.copy()
            if hasattr(datatype,'collation'):datatype.collation=None
            definition=quote(column_name)+' '+datatype.compile(dialect=connection.dialect)
            if column_name in collations:definition+=' COLLATE '+collations[column_name]
            if not target.c[column_name].nullable:definition+=' NOT NULL'
            definitions.append(definition)
        if conflict_keys:definitions.append('UNIQUE ('+','.join(quote(k) for k in conflict_keys)+')')
        suffix=' ON COMMIT PRESERVE ROWS' if dialect=='postgresql' else ' ENGINE=InnoDB'
        connection.execute(text(f'CREATE TEMPORARY TABLE {name} ({",".join(definitions)}){suffix}'))
        created=True
        scratch_table=Table(scratch,MetaData(),*[Column(n,target.c[n].type) for n in columns])
        batch=[];batch_bytes=0
        def flush():
            nonlocal physical
            if not batch:return
            connection.execute(scratch_table.insert(),batch)
            if dialect=='postgresql':
                physical=int(connection.scalar(text('SELECT pg_total_relation_size(CAST(:name AS regclass))'),{'name':scratch}))
                if physical>max_bytes:raise ValueError('Scratch physical byte quota exceeded.')
            batch.clear()
        for value in rows:
            count+=1
            if count>max_rows:raise ValueError('Scratch row quota exceeded.')
            if any(value.get(k) is None for k in conflict_keys):raise ValueError('UPSERT keys cannot be NULL.')
            validated={n:scalar(value[n],profiles[n]) for n in columns}
            size=len(encoded(list(validated.values())))
            if size>1024**2:raise ValueError('Mapped row exceeds 1 MiB.')
            charged+=4*(size+256)
            if charged>max_bytes:raise ValueError('Scratch reserved byte quota exceeded.')
            if batch and (len(batch)>=1000 or batch_bytes+size>8*1024**2):flush();batch_bytes=0
            # Python-native types are passed to the driver; encoding is only
            # used for byte accounting and never coerces decimal to a float.
            batch.append(driver_row({n:value[n] for n in columns},profiles.values(),dialect));batch_bytes+=size
        flush()
        connection.commit()
        return ValidationResult(count,max(charged,physical))
    except (SQLAlchemyError,KeyError,TypeError,ValueError):
        connection.rollback()
        raise ValueError(f'Dataset validation failed at row {count}; target data was not changed.') from None
    finally:
        if created:
            try:
                drop=f'DROP TABLE IF EXISTS pg_temp.{name}' if dialect=='postgresql' else f'DROP TEMPORARY TABLE IF EXISTS {name}'
                connection.execute(text(drop));connection.commit()
            except SQLAlchemyError:
                connection.invalidate()
