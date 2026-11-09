"""Strict canonical execution inputs; no credentials, SQL or executable expressions."""
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
import hashlib
import json
import re
from typing import Annotated,Literal
from uuid import UUID
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt,StrictStr,field_validator,model_validator

LogicalType=Literal['integer','bigint','decimal','varchar','text','boolean','date','timestamp']
Transformation=Literal['DIRECT','CONSTANT','NULL_HANDLING','TYPE_CONVERSION']
HEX64=r'^[a-f0-9]{64}$'
IDENTIFIER=r'^[A-Za-z_][A-Za-z0-9_]{0,63}$'


class Contract(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True,populate_by_name=True)


def identifier(value):
    if not re.fullmatch(IDENTIFIER,value):raise ValueError('A portable identifier is required.')
    return value


def parse_timestamp(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?',value):
        raise ValueError('An ISO timestamp with seconds and at most six fractional digits is required.')
    return datetime.fromisoformat(value)


class TypedLiteral(Contract):
    logical_type:LogicalType
    value:StrictStr|StrictInt|StrictBool|None

    @model_validator(mode='after')
    def typed(self):
        v=self.value;t=self.logical_type
        if v is None:return self
        if t in ('integer','bigint'):
            bits=32 if t=='integer' else 64
            if type(v) is not int or not -(2**(bits-1))<=v<2**(bits-1):raise ValueError('Integer literal is outside its logical range.')
        elif t=='boolean':
            if type(v) is not bool:raise ValueError('A boolean literal is required.')
        else:
            if type(v) is not str:raise ValueError('A lossless text literal is required.')
            try:v.encode('utf-8')
            except UnicodeError:raise ValueError('Literal must be valid Unicode.') from None
            if '\0' in v:raise ValueError('NUL text is unsupported.')
            if t=='decimal':
                if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',v):raise ValueError('A finite invariant decimal string is required.')
                try:
                    if not Decimal(v).is_finite():raise ValueError('Decimal must be finite.')
                except InvalidOperation:raise ValueError('Invalid decimal literal.') from None
            elif t=='date':
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError('An ISO calendar date is required.')
                date.fromisoformat(v)
            elif t=='timestamp':parse_timestamp(v)
        return self


class ETLSource(Contract):
    type:Literal['DB','CSV','TXT']
    connection_revision_id:UUID|None=None
    schema_:StrictStr|None=Field(default=None,alias='schema')
    table:StrictStr|None=None
    file_id:UUID|None=None
    parser_revision:Annotated[StrictInt,Field(ge=1)]|None=None
    file_sha256:Annotated[StrictStr,Field(pattern=HEX64)]|None=None

    @field_validator('connection_revision_id','file_id',mode='before')
    @classmethod
    def uuid_text(cls,value):return UUID(value) if type(value) is str else value

    @model_validator(mode='after')
    def union(self):
        db={'connection_revision_id','schema_','table'};file={'file_id','parser_revision','file_sha256'}
        required,forbidden=(db,file) if self.type=='DB' else (file,db)
        if any(getattr(self,k) is None for k in required) or self.model_fields_set&forbidden:
            raise ValueError('Exactly one complete DB or file source is required.')
        if self.type=='DB':identifier(self.schema_);identifier(self.table)
        return self


class ETLTarget(Contract):
    connection_revision_id:UUID
    schema_:StrictStr=Field(alias='schema')
    table:StrictStr
    physical_target_id:StrictStr=Field(min_length=1,max_length=1024)

    @field_validator('connection_revision_id',mode='before')
    @classmethod
    def uuid_text(cls,value):return UUID(value) if type(value) is str else value

    @field_validator('schema_','table')
    @classmethod
    def safe_identifier(cls,value):return identifier(value)


class ETLMapping(Contract):
    source_column:StrictStr|None=None
    target_column:StrictStr
    transformation:Transformation
    default_literal:TypedLiteral|None=None
    enabled:StrictBool

    @field_validator('target_column')
    @classmethod
    def target_identifier(cls,value):return identifier(value)

    @model_validator(mode='after')
    def required_fields(self):
        if not self.enabled:return self
        if self.transformation!='CONSTANT' and not self.source_column:raise ValueError('Source column is required.')
        if self.transformation in ('CONSTANT','NULL_HANDLING') and self.default_literal is None:raise ValueError('An explicit typed literal is required.')
        return self


class SourcePredicate(Contract):
    column:StrictStr
    operator:Literal['=','!=','<','<=','>','>=','IN','IS NULL','IS NOT NULL']
    value:TypedLiteral|list[TypedLiteral]|None=None

    @field_validator('column')
    @classmethod
    def column_identifier(cls,value):return identifier(value)

    @model_validator(mode='after')
    def operands(self):
        if self.operator in ('IS NULL','IS NOT NULL'):
            if 'value' in self.model_fields_set:raise ValueError('NULL predicates cannot contain a value.')
        elif self.operator=='IN':
            if type(self.value) is not list or not 1<=len(self.value)<=1000:raise ValueError('IN requires 1 to 1000 typed literals.')
            if len({v.logical_type for v in self.value})!=1:raise ValueError('IN literals must have one logical type.')
        elif not isinstance(self.value,TypedLiteral):raise ValueError('Comparison requires one typed literal.')
        return self


class SourceFilter(Contract):
    and_:list[SourcePredicate]=Field(alias='and',min_length=1,max_length=20)


def validate_cron(value):
    fields=value.split()
    if len(fields)!=5:raise ValueError('Schedule must be Manual or a five-field cron expression.')
    names=[{}, {}, {}, {n:i+1 for i,n in enumerate(('JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'))},
           {n:i for i,n in enumerate(('SUN','MON','TUE','WED','THU','FRI','SAT'))}]
    for field,(low,high),named in zip(fields,[(0,59),(0,23),(1,31),(1,12),(0,7)],names):
        def number(token):
            if token.upper() in named:return named[token.upper()]
            if not re.fullmatch(r'\d{1,2}',token) or not low<=int(token)<=high:raise ValueError('Cron field is outside its range.')
            return int(token)
        for item in field.split(','):
            parts=item.split('/')
            if len(parts)>2:raise ValueError('Invalid cron step.')
            if len(parts)==2 and (not re.fullmatch(r'\d{1,2}',parts[1]) or not 1<=int(parts[1])<=high-low+1):raise ValueError('Invalid cron step.')
            span=parts[0]
            if span=='*':continue
            bounds=span.split('-')
            if len(bounds)>2:raise ValueError('Invalid cron range.')
            values=[number(b) for b in bounds]
            if len(values)==2 and values[0]>values[1]:raise ValueError('Cron range must ascend.')
    return value


class ETLConfig(Contract):
    dag_id:StrictStr=Field(pattern=r'^[A-Za-z0-9_.-]{1,200}$')
    source:ETLSource
    target:ETLTarget
    schedule:StrictStr
    start_date:StrictStr|None=None
    timezone:StrictStr
    catchup:StrictBool
    is_paused:StrictBool
    load_strategy:Literal['APPEND','UPSERT','FULL_REFRESH']
    conflict_keys:list[StrictStr]
    batch_size:Annotated[StrictInt,Field(ge=1,le=10000)]=1000
    retry_count:Annotated[StrictInt,Field(ge=0,le=10)]=0
    retry_delay:Annotated[StrictInt,Field(ge=0,le=3600)]=60
    mappings:list[ETLMapping]
    filter:SourceFilter|None=None

    @model_validator(mode='after')
    def execution_rules(self):
        if self.load_strategy=='UPSERT':
            if not self.conflict_keys or len(set(self.conflict_keys))!=len(self.conflict_keys):raise ValueError('UPSERT requires unique conflict keys.')
        elif self.conflict_keys:raise ValueError('Conflict keys apply only to UPSERT.')
        for k in self.conflict_keys:identifier(k)
        enabled=[m.target_column for m in self.mappings if m.enabled]
        if len(set(enabled))!=len(enabled):raise ValueError('Enabled target mappings must be unique.')
        if self.source.type!='DB' and 'filter' in self.model_fields_set:raise ValueError('File sources do not support DB filters.')
        try:zone=ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('A valid IANA timezone is required.') from None
        if self.schedule!='Manual':
            validate_cron(self.schedule)
            if self.start_date is None:raise ValueError('Cron schedules require Start Date.')
        if self.start_date is not None:
            start=parse_timestamp(self.start_date)
            if start.tzinfo is not None and start.utcoffset()!=start.astimezone(zone).utcoffset():raise ValueError('Start Date offset conflicts with the configured timezone.')
            if start.tzinfo is None:
                localized=start.replace(tzinfo=zone)
                if localized.astimezone(ZoneInfo('UTC')).astimezone(zone).replace(tzinfo=None)!=start:raise ValueError('Start Date does not exist in the configured timezone.')
                if localized.utcoffset()!=localized.replace(fold=1).utcoffset():raise ValueError('Ambiguous Start Date requires an explicit offset.')
                object.__setattr__(self,'start_date',localized.isoformat())
        return self

    def canonical_sha256(self):
        payload=self.model_dump(mode='json',by_alias=True,exclude_none=True)
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


EXCEL_TRANSFORMATIONS={'Direct Mapping':'DIRECT','Constant Value':'CONSTANT','NULL Handling':'NULL_HANDLING','Type Conversion':'TYPE_CONVERSION'}
