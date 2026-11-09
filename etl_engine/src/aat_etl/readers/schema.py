"""Physical identity and used-schema fingerprints, without repairing drift."""
from dataclasses import dataclass
import hashlib
import json
from sqlalchemy import inspect,text,types
from sqlalchemy.dialects import mysql,postgresql
from ..contracts.config import identifier


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class TableSchema:
    dialect:str
    server_fingerprint:str
    physical_identity:str
    schema:str
    table:str
    columns:tuple
    keys:tuple
    fingerprint:str

    def require_fingerprint(self,expected):
        if self.fingerprint!=expected:raise ValueError('The pinned schema changed; revalidation is required.')
        return self


def column_profile(item,dialect):
    datatype=item['type'];extra={}
    if isinstance(datatype,types.Boolean) or isinstance(datatype,mysql.TINYINT) and datatype.display_width==1:
        logical='boolean'
    elif isinstance(datatype,types.BigInteger):logical='bigint'
    elif isinstance(datatype,types.Integer):logical='integer'
    elif isinstance(datatype,types.Float):raise ValueError('Floating-point source or target types are unsupported.')
    elif isinstance(datatype,types.Numeric):
        logical='decimal';p=datatype.precision;s=datatype.scale
        if p is None or s is None or not 1<=p<=38 or not 0<=s<=p:raise ValueError('Decimal precision and scale must fit the supported lossless range.')
        extra.update(precision=p,scale=s)
    elif isinstance(datatype,types.DateTime):
        logical='timestamp'
        aware=isinstance(datatype,postgresql.TIMESTAMP) and datatype.timezone or isinstance(datatype,mysql.TIMESTAMP)
        extra.update(timezone_semantics='aware' if aware else 'naive',precision=(getattr(datatype,'precision',None) if getattr(datatype,'precision',None) is not None else 6) if dialect=='postgresql' else getattr(datatype,'fsp',None) or 0)
    elif isinstance(datatype,types.Date):logical='date'
    elif isinstance(datatype,types.Text):logical='text'
    elif isinstance(datatype,types.String) and not isinstance(datatype,(types.Enum,mysql.ENUM,mysql.SET)):
        logical='varchar';extra['length']=datatype.length
    else:raise ValueError('A used column has an unsupported logical type.')
    if getattr(datatype,'unsigned',False):raise ValueError('Unsigned database types need an explicit supported range contract.')
    extra['collation']=getattr(datatype,'collation',None)
    default=item.get('default')
    return dict(name=item['name'],logical_type=logical,nullable=bool(item['nullable']),has_default=default is not None,
        default_fingerprint=digest(str(default)) if default is not None else None,generated=bool(item.get('computed') or item.get('identity')),**extra)


def inspect_table(engine,*,schema,table,used_columns):
    identifier(schema);identifier(table)
    if not used_columns or len(set(used_columns))!=len(used_columns):raise ValueError('Used columns must be nonempty and unique.')
    dialect=engine.dialect.name
    if dialect not in ('postgresql','mysql'):raise ValueError('Unsupported database adapter.')
    if dialect=='postgresql' and (len(schema)>63 or len(table)>63):raise ValueError('PostgreSQL identifiers cannot exceed 63 bytes.')
    with engine.connect() as connection:
        if dialect=='mysql':
            server_uuid,lower=connection.execute(text('SELECT @@server_uuid,@@lower_case_table_names')).one()
            if lower:schema=schema.lower();table=table.lower()
        inspector=inspect(connection)
        # A genuine missing/permission failure must propagate as a failed
        # preflight. has_table() can hide permission errors on some dialects.
        reflected=inspector.get_columns(table,schema=schema)
        by_name={c['name']:c for c in reflected}
        if any(c not in by_name for c in used_columns):raise ValueError('A used source or target column is missing.')
        columns=tuple(column_profile(by_name[name],dialect) for name in used_columns)
        if dialect=='postgresql':
            collations=connection.execute(text('SELECT a.attname,cn.nspname,co.collname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_collation co ON co.oid=a.attcollation JOIN pg_namespace cn ON cn.oid=co.collnamespace WHERE n.nspname=:schema AND c.relname=:table AND a.attnum>0 AND NOT a.attisdropped'),
                {'schema':schema,'table':table}).all()
            actual_collations={r[0]:[r[1],r[2]] for r in collations}
        else:
            collations=connection.execute(text('SELECT COLUMN_NAME,CHARACTER_SET_NAME,COLLATION_NAME FROM information_schema.COLUMNS WHERE BINARY TABLE_SCHEMA=BINARY :schema AND BINARY TABLE_NAME=BINARY :table'),
                {'schema':schema,'table':table}).all()
            actual_collations={r[0]:[r[1],r[2]] for r in collations}
        for profile in columns:profile['collation']=actual_collations.get(profile['name'])
        keys=[]
        primary=inspector.get_pk_constraint(table,schema=schema).get('constrained_columns') or []
        if primary:keys.append(dict(columns=primary,primary=True,predicate=None))
        for constraint in inspector.get_unique_constraints(table,schema=schema):
            keys.append(dict(columns=constraint.get('column_names'),primary=False,predicate=None))
        for index in inspector.get_indexes(table,schema=schema):
            if index.get('unique') and not index.get('duplicates_constraint'):
                keys.append(dict(columns=index.get('column_names'),primary=False,
                    predicate=str(index.get('dialect_options',{})),expressions=index.get('expressions')))
        keys=tuple(sorted(keys,key=lambda k:json.dumps(k,sort_keys=True)))
        if dialect=='postgresql':
            endpoint=connection.execute(text('SELECT inet_server_addr()::text,inet_server_port(),oid::text FROM pg_database WHERE datname=current_database()')).one()
            server=digest(['POSTGRESQL',*endpoint])
            relation=connection.execute(text('SELECT c.oid::bigint,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=:schema AND c.relname=:table'),
                {'schema':schema,'table':table}).one()
            if relation[1] not in ('r','p'):raise ValueError('Source and target must be base tables.')
            physical=digest(['POSTGRESQL',server,relation[0]])
        else:
            server=hashlib.sha256(('MYSQL:'+server_uuid).encode()).hexdigest()
            actual=connection.execute(text('SELECT TABLE_SCHEMA,TABLE_NAME,ENGINE,TABLE_TYPE,TABLE_COLLATION FROM information_schema.TABLES WHERE BINARY TABLE_SCHEMA=BINARY :schema AND BINARY TABLE_NAME=BINARY :table'),
                {'schema':schema,'table':table}).one()
            if actual[2]!='InnoDB' or actual[3]!='BASE TABLE':raise ValueError('MySQL source and target must be InnoDB base tables.')
            physical=digest(['MYSQL',server,actual[0],actual[1]])
        fingerprint=digest(dict(identity=physical,columns=columns,keys=keys))
        return TableSchema(dialect,server,physical,schema,table,columns,keys,fingerprint)


def preflight(source,target,*,expected_source_hash,expected_target_hash,expected_source_identity,expected_target_identity):
    source.require_fingerprint(expected_source_hash);target.require_fingerprint(expected_target_hash)
    if source.physical_identity!=expected_source_identity or target.physical_identity!=expected_target_identity:
        raise ValueError('A pinned physical database identity changed; revalidation is required.')
    if source.physical_identity==target.physical_identity:raise ValueError('Source and target cannot resolve to the same physical table.')
    return source,target
