"""Schema1.0 table metadata validation; no database connection or target side effect."""
from dataclasses import dataclass,field
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
import json
from pathlib import Path
import re
from .workbook import read,WorkbookFailure


@dataclass(frozen=True)
class TargetContext:
    code:str
    database_type:str
    database_name:str
    schema_name:str|None
    revision_id:str
    server_fingerprint:str
    case_sensitive:bool=True


@dataclass
class ColumnSpec:
    name:str
    ordinal:int
    logical_type:str
    nullable:bool
    length:int|None=None
    precision:int|None=None
    scale:int|None=None
    primary_key_ordinal:int|None=None
    has_default:bool=False
    default_literal:dict|None=None
    description:str|None=None


@dataclass
class TableSpec:
    name:str
    target_schema:str
    columns:list[ColumnSpec]=field(default_factory=list)
    description:str|None=None
    @property
    def primary_key(self) -> list[str]:
        return [c.name for c in sorted((c for c in self.columns if c.primary_key_ordinal is not None),key=lambda c:c.primary_key_ordinal)]


@dataclass
class ValidationResult:
    tables:list[TableSpec]=field(default_factory=list)
    issues:list[dict]=field(default_factory=list)


def identifier(value,target:TargetContext) -> str:
    maximum=63 if target.database_type=='POSTGRESQL' else 64
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',value) or len(value.encode())>maximum:
        raise ValueError('An ASCII SQL identifier within the database length limit is required.')
    return value


def _integer(value,minimum,maximum):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or int(value)!=value or not minimum<=value<=maximum:
        raise ValueError('An integer within the allowed range is required.')
    return int(value)


def _boolean(value):
    if isinstance(value,bool):return value
    if value in ('TRUE','FALSE'):return value=='TRUE'
    raise ValueError('Boolean fields must be TRUE or FALSE.')


def _description(value):
    if value is None:return None
    if not isinstance(value,str) or len(value)>1000:raise ValueError('Description must be text within 1000 characters.')
    return value


def _literal(value,column:ColumnSpec) -> dict:
    if not isinstance(value,str):raise ValueError('Default Value must be JSON scalar text.')
    try:parsed=json.loads(value,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,TypeError):raise ValueError('Default Value must be valid JSON scalar text.') from None
    logical=column.logical_type
    if parsed is None:
        if not column.nullable:raise ValueError('A NOT NULL column cannot default to NULL.')
    elif logical in ('integer','bigint'):
        bits=32 if logical=='integer' else 64
        if isinstance(parsed,bool) or not isinstance(parsed,int) or not -(2**(bits-1))<=parsed<2**(bits-1):
            raise ValueError('Integer default is outside the supported range.')
    elif logical=='boolean':
        if not isinstance(parsed,bool):raise ValueError('Boolean default must be a JSON boolean.')
    elif not isinstance(parsed,str):raise ValueError('This logical type requires a lossless JSON string default.')
    elif logical=='varchar' and len(parsed)>column.length:raise ValueError('Default text exceeds the declared length.')
    elif logical=='decimal':
        try:number=Decimal(parsed)
        except InvalidOperation:raise ValueError('Decimal default must be finite decimal text.') from None
        if not number.is_finite() or number.as_tuple().exponent < -column.scale or abs(number)>=Decimal(10)**(column.precision-column.scale):
            raise ValueError('Decimal default exceeds precision or scale.')
    elif logical=='date':
        try:date.fromisoformat(parsed)
        except ValueError:raise ValueError('Date default must use ISO8601.') from None
    elif logical=='timestamp':
        try:stamp=datetime.fromisoformat(parsed)
        except ValueError:raise ValueError('Timestamp default must use ISO8601.') from None
        if stamp.tzinfo is not None:raise ValueError('Timestamp default must not have a timezone.')
    return {'logical_type':logical,'value':parsed}


def validate(path:Path,target:TargetContext) -> ValidationResult:
    try:data=read(path)
    except WorkbookFailure as error:return ValidationResult(issues=[error.issue])
    issues=[];tables={};coordinates={}
    def issue(sheet,row,column,message):
        issues.append({'scope':'cell','sheet':sheet,'row':row,'column':column,'code':'INVALID_TABLE_DEFINITION','message':message})
    def reference(code,schema,name):
        if not isinstance(code,str) or code.strip().casefold()!=target.code.strip().casefold():
            raise ValueError('Connection Code must match the selected target.')
        resolved=schema if schema not in (None,'') else target.schema_name if target.database_type=='POSTGRESQL' else target.database_name
        if target.database_type=='MYSQL' and resolved!=target.database_name:raise ValueError('MySQL Target Schema must match Database Name.')
        resolved=identifier(resolved or 'public',target);name=identifier(name,target)
        return (resolved,name) if target.case_sensitive else (resolved.lower(),name.lower())
    if not data['Tables']:issue('Tables',2,3,'At least one table is required.')
    if len(data['Tables'])>100:issue('Tables',data['Tables'][100][0],3,'A workbook may contain at most 100 tables.')
    for row,values in data['Tables']:
        try:
            key=reference(*values[:3])
            if key in tables:raise ValueError('Duplicate physical table reference.')
            tables[key]=TableSpec(name=key[1],target_schema=key[0],description=_description(values[3]));coordinates[key]=row
        except ValueError as error:issue('Tables',row,3,str(error))
    types={'Integer':'integer','Big Integer':'bigint','Varchar':'varchar','Text':'text','Decimal':'decimal','Boolean':'boolean','Date':'date','Timestamp':'timestamp'}
    used={};orders={};keys={}
    for row,values in data['Columns']:
        column=1
        try:
            key=reference(*values[:3])
            if key not in tables:raise ValueError('Column reference does not match a declared table.')
            column=4;name=identifier(values[3],target)
            folded=name if target.database_type=='POSTGRESQL' else name.casefold()
            if folded in used.setdefault(key,set()):raise ValueError('Column Name is duplicated.')
            used[key].add(folded)
            column=5;ordinal=_integer(values[4],1,1000)
            if ordinal in orders.setdefault(key,set()):raise ValueError('Column Order is duplicated.')
            orders[key].add(ordinal)
            column=6
            if values[5] not in types:raise ValueError('Data Type is not supported.')
            logical=types[values[5]]
            column=7;length=_integer(values[6],1,65535) if logical=='varchar' else None
            if logical!='varchar' and values[6] is not None:raise ValueError('Length applies only to Varchar.')
            column=8;precision=_integer(values[7],1,38) if logical=='decimal' else None
            column=9;scale=_integer(values[8],0,precision) if logical=='decimal' else None
            if logical!='decimal' and (values[7] is not None or values[8] is not None):raise ValueError('Precision and Scale apply only to Decimal.')
            column=10;nullable=_boolean(values[9]);column=11;primary=_boolean(values[10])
            if primary and nullable:raise ValueError('Primary key columns must not be nullable.')
            spec=ColumnSpec(name=name,ordinal=ordinal,logical_type=logical,nullable=nullable,length=length,precision=precision,scale=scale,description=_description(values[12]))
            column=12
            if values[11] is not None:
                spec.has_default=True;spec.default_literal=_literal(values[11],spec)
            tables[key].columns.append(spec)
            if primary:keys.setdefault(key,set()).add(name)
        except (ValueError,TypeError,OverflowError) as error:
            message=str(error) if isinstance(error,ValueError) else 'Column fields have invalid types or ranges.'
            issue('Columns',row,column,message)
    for key,table in tables.items():
        table.columns.sort(key=lambda c:c.ordinal)
        if not table.columns:issue('Tables',coordinates[key],3,'A table must have at least one valid column.')
        primary=0
        for column in table.columns:
            if column.name in keys.get(key,set()):primary+=1;column.primary_key_ordinal=primary
        if target.database_type=='MYSQL':
            inline=sum(c.length*4+2 if c.logical_type=='varchar' else 20 if c.logical_type=='text' else 16 for c in table.columns)
            if inline>65535:issue('Tables',coordinates[key],3,'MySQL utf8mb4 row width exceeds the supported inline row size.')
    return ValidationResult(tables=[] if issues else list(tables.values()),issues=issues)
