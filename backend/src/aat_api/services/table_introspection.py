"""Normalize supported real database columns without replacing stored definitions."""
from datetime import date,datetime
from decimal import Decimal
import re
from sqlalchemy import inspect,types
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.dialects import mysql
from aat_api.validation.tables import TableSpec,ColumnSpec


def _default(value,logical):
    text=str(value).strip()
    while text.startswith('(') and text.endswith(')'):text=text[1:-1].strip()
    if text.upper()=='NULL':return None
    if text.startswith("'"):
        match=re.fullmatch(r"'((?:[^']|'')*)'(?:\:\:[A-Za-z_ ]+(?:\(\d+(?:,\d+)?\))?)?",text)
        if not match:raise ValueError('Unsupported target default expression.')
        value=match[1].replace("''", "'")
    else:value=text
    if logical in ('integer','bigint'):return int(value)
    if logical=='boolean':
        if value.lower() not in ('true','false','1','0'):raise ValueError('Unsupported boolean default.')
        return value.lower() in ('true','1')
    if logical=='decimal':return str(Decimal(value))
    if logical=='date':return date.fromisoformat(value).isoformat()
    if logical=='timestamp':return datetime.fromisoformat(value).isoformat()
    if not text.startswith("'"):raise ValueError('Unsupported text default expression.')
    return value


def actual_definition(engine,stored):
    inspector=inspect(engine)
    # Some dialect has_table() implementations turn permission failures into
    # False. Only a real missing-table result may mean NOT_CREATED/DRIFTED.
    try: reflected=inspector.get_columns(stored.name,schema=stored.target_schema)
    except NoSuchTableError:return None
    primary=inspector.get_pk_constraint(stored.name,schema=stored.target_schema).get('constrained_columns') or []
    columns=[]
    for ordinal,item in enumerate(reflected,1):
        datatype=item['type']
        if isinstance(datatype,types.Boolean) or isinstance(datatype,mysql.TINYINT) and datatype.display_width==1:logical='boolean'
        elif isinstance(datatype,types.BigInteger):logical='bigint'
        elif isinstance(datatype,types.Integer):logical='integer'
        elif isinstance(datatype,types.Numeric):logical='decimal'
        elif isinstance(datatype,types.DateTime):logical='timestamp'
        elif isinstance(datatype,types.Date):logical='date'
        elif isinstance(datatype,types.Text):logical='text'
        elif isinstance(datatype,types.String):logical='varchar'
        else:raise ValueError('Target column type is unsupported.')
        default=item.get('default')
        columns.append(ColumnSpec(name=item['name'],ordinal=ordinal,logical_type=logical,nullable=item['nullable'],
            length=datatype.length if logical=='varchar' else None,
            precision=datatype.precision if logical=='decimal' else None,scale=datatype.scale if logical=='decimal' else None,
            primary_key_ordinal=primary.index(item['name'])+1 if item['name'] in primary else None,
            has_default=default is not None,default_literal={'logical_type':logical,'value':_default(default,logical)} if default is not None else None,
            description=item.get('comment')))
    return TableSpec(stored.name,stored.target_schema,columns)


def equivalent(stored,actual):
    if stored.primary_key!=actual.primary_key or len(stored.columns)!=len(actual.columns):return False
    for expected,found in zip(stored.columns,actual.columns):
        for field in ('name','logical_type','nullable','length','precision','scale','primary_key_ordinal'):
            if getattr(expected,field)!=getattr(found,field):return False
        if expected.has_default!=found.has_default:return False
        if expected.has_default:
            left=expected.default_literal['value'];right=found.default_literal['value']
            if expected.logical_type=='decimal' and left is not None and right is not None:
                if Decimal(left)!=Decimal(right):return False
            elif expected.logical_type=='timestamp' and left is not None and right is not None:
                if datetime.fromisoformat(left)!=datetime.fromisoformat(right):return False
            elif left!=right:return False
    return True
