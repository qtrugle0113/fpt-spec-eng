"""Schema 1.0 ETL workbook metadata; registry/schema compilation is separate."""
from dataclasses import dataclass,field
from decimal import Decimal
import json
import re
from uuid import UUID
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from aat_etl.contracts.config import EXCEL_TRANSFORMATIONS,validate_cron,parse_timestamp
from .workbook import read,WorkbookFailure,ETL_HEADERS
from .tables import _boolean,_integer,_description


@dataclass
class ETLSpec:
    row:int
    values:dict
    mappings:list[dict]=field(default_factory=list)
    requested_enabled:bool=False


@dataclass
class ValidationResult:
    definitions:list[ETLSpec]=field(default_factory=list)
    issues:list[dict]=field(default_factory=list)


def text(value,*,required=True,maximum=200):
    if value in (None,'') and not required:return None
    if not isinstance(value,str) or not value or len(value)>maximum or '\0' in value:
        raise ValueError('A text value within the allowed length is required.')
    value.encode('utf-8');return value


def identifier(value):
    value=text(value,maximum=64)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',value):raise ValueError('A portable SQL identifier is required.')
    return value


def scalar(value):
    if not isinstance(value,str):raise ValueError('A JSON scalar literal is required.')
    try:parsed=json.loads(value,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,TypeError):raise ValueError('A valid JSON scalar literal is required.') from None
    if isinstance(parsed,(dict,list)):raise ValueError('A JSON scalar literal is required.')
    return value


def filtering(value):
    if not isinstance(value,str):raise ValueError('Source Filtering must be a JSON predicate object.')
    try:parsed=json.loads(value,parse_float=Decimal,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,TypeError):raise ValueError('Source Filtering must be a JSON predicate object.') from None
    if not isinstance(parsed,dict) or set(parsed)!={'and'} or not isinstance(parsed['and'],list) or not 1<=len(parsed['and'])<=20:
        raise ValueError('Source Filtering requires one to twenty AND predicates.')
    for predicate in parsed['and']:
        if not isinstance(predicate,dict) or not {'column','operator'}<=set(predicate) or set(predicate)-{'column','operator','value'}:
            raise ValueError('Invalid source predicate fields.')
        identifier(predicate['column']);operator=predicate['operator']
        if operator not in ('=','!=','<','<=','>','>=','IN','IS NULL','IS NOT NULL'):raise ValueError('Unsupported source predicate operator.')
        if operator in ('IS NULL','IS NOT NULL'):
            if 'value' in predicate:raise ValueError('NULL predicates must not contain a value.')
        else:
            if 'value' not in predicate:raise ValueError('A predicate value is required.')
            values=predicate['value'] if operator=='IN' else [predicate['value']]
            if not isinstance(values,list) or not 1<=len(values)<=1000 or any(isinstance(v,(dict,list)) or v is None for v in values):
                raise ValueError('Predicate values must be non-null scalar literals.')
            if operator=='IN' and len({type(v) for v in values})!=1:raise ValueError('IN values must have the same literal type.')
    return parsed


def validate(path):
    try:data=read(path,'ETL')
    except WorkbookFailure as error:return ValidationResult(issues=[error.issue])
    issues=[];definitions={}
    def issue(sheet,row,column,message,code='INVALID_ETL_DEFINITION'):
        issues.append(dict(scope='cell',sheet=sheet,row=row,column=column,column_name=ETL_HEADERS[sheet][column-1],code=code,message=message))
    records=data['ETL_Definitions']
    if not 1<=len(records)<=100:
        return ValidationResult(issues=[dict(scope='sheet',sheet='ETL_Definitions',code='DAG_COUNT_LIMIT',message='An ETL workbook must define one to one hundred DAGs.')])
    for row,cells in records:
        column=1
        try:
            dag=text(cells[0]);
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}',dag):raise ValueError('DAG ID contains unsupported characters.')
            if dag in definitions:raise ValueError('DAG ID is duplicated in this workbook.')
            values={'dag_id':dag};column=2;values['description']=_description(cells[1])
            column=7;file=text(cells[6],required=False,maximum=36)
            if file is not None:file=str(UUID(file))
            column=3;source_type=cells[2]
            if source_type in (None,''):source_type='FILE' if file else 'DB'
            if source_type not in ('DB','CSV','TXT','FILE'):raise ValueError('Source Type must be DB, CSV or TXT.')
            if source_type=='DB':
                if file is not None:raise ValueError('Database sources must not contain a file reference.')
                column=4;values['source_connection_code']=text(cells[3])
                column=5;values['source_schema']=identifier(cells[4]) if cells[4] not in (None,'') else None
                column=6;values['source_table']=identifier(cells[5])
            else:
                if file is None or any(cells[i] not in (None,'') for i in (3,4,5)):raise ValueError('File sources require a file reference and no database source fields.')
                values['source_file_id']=file
            values['source_type']=source_type
            column=8;values['target_connection_code']=text(cells[7])
            column=9;values['target_schema']=identifier(cells[8]) if cells[8] not in (None,'') else None
            column=10;values['target_table']=identifier(cells[9])
            column=11;values['schedule']=text(cells[10])
            if values['schedule']!='Manual':validate_cron(values['schedule'])
            column=13;values['timezone']=text(cells[12]);zone=ZoneInfo(values['timezone'])
            column=12;start=text(cells[11],required=False)
            if start is None and values['schedule']!='Manual':raise ValueError('Cron schedules require Start Date.')
            if start is not None:
                stamp=parse_timestamp(start)
                if stamp.tzinfo is None:
                    localized=stamp.replace(tzinfo=zone)
                    if localized.astimezone(ZoneInfo('UTC')).astimezone(zone).replace(tzinfo=None)!=stamp:raise ValueError('Start Date does not exist in the configured timezone.')
                    if localized.utcoffset()!=localized.replace(fold=1).utcoffset():raise ValueError('Ambiguous Start Date requires an explicit offset.')
                    start=localized.isoformat()
                elif stamp.utcoffset()!=stamp.astimezone(zone).utcoffset():raise ValueError('Start Date offset conflicts with the configured timezone.')
            values['start_date']=start
            column=14;values['catchup']=_boolean(cells[13])
            column=15;values['load_strategy']=cells[14]
            if cells[14] not in ('APPEND','UPSERT','FULL_REFRESH'):raise ValueError('Unsupported load strategy.')
            column=16;keys=text(cells[15],required=False,maximum=64000)
            values['conflict_keys']=[identifier(v.strip()) for v in keys.split(',')] if keys else []
            if (cells[14]=='UPSERT')!=bool(values['conflict_keys']) or len(set(values['conflict_keys']))!=len(values['conflict_keys']):raise ValueError('Unique conflict keys are required only for UPSERT.')
            for column,name,default,low,high in ((17,'batch_size',1000,1,10000),(18,'retry_count',0,0,10),(19,'retry_delay',60,0,3600)):
                values[name]=default if cells[column-1] in (None,'') else _integer(cells[column-1],low,high)
            column=20
            if cells[19] not in ('Enabled','Paused'):raise ValueError('Enabled/Paused must be Enabled or Paused.')
            values['is_paused']=True
            column=21
            if cells[20] not in (None,''):
                if source_type!='DB':raise ValueError('Source Filtering is supported only for database sources.')
                values['filter']=filtering(cells[20])
            column=22
            if cells[21] not in (None,'',dag):raise ValueError('Column Mapping Reference must equal this DAG ID.')
            definitions[dag]=ETLSpec(row,values,requested_enabled=cells[19]=='Enabled')
        except (ValueError,TypeError,OverflowError,ZoneInfoNotFoundError):
            issue('ETL_Definitions',row,column,'Invalid '+ETL_HEADERS['ETL_Definitions'][column-1]+' value or incompatible ETL fields.')
    targets={}
    for row,cells in data['Column_Mappings']:
        column=1
        try:
            dag=text(cells[0])
            if dag not in definitions:
                issue('Column_Mappings',row,1,'DAG ID does not exist in ETL_Definitions.','EXCEL_REFERENCE_NOT_FOUND');continue
            column=4;transformation=EXCEL_TRANSFORMATIONS.get(cells[3] or 'Direct Mapping')
            if transformation is None:raise ValueError('Unsupported transformation.')
            column=2;source=identifier(cells[1]) if cells[1] not in (None,'') else None
            if (transformation=='CONSTANT')!=(source is None):raise ValueError('Source Column must match the transformation.')
            column=3;target=identifier(cells[2])
            column=5;default=scalar(cells[4]) if cells[4] is not None else None
            if (transformation in ('CONSTANT','NULL_HANDLING'))!=(default is not None):raise ValueError('Default Value must match the transformation.')
            column=6;enabled=_boolean(cells[5])
            column=3
            if enabled and target in targets.setdefault(dag,set()):raise ValueError('Enabled target mappings must be unique.')
            if enabled:targets[dag].add(target)
            definitions[dag].mappings.append(dict(row=row,source_column=source,target_column=target,transformation=transformation,default_json=default,enabled=enabled))
        except (ValueError,TypeError,OverflowError):issue('Column_Mappings',row,column,'Invalid '+ETL_HEADERS['Column_Mappings'][column-1]+' value or incompatible mapping fields.')
    issues.sort(key=lambda v:(list(ETL_HEADERS).index(v['sheet']),v.get('row',0),v.get('column',0)))
    return ValidationResult(definitions=[] if issues else list(definitions.values()),issues=issues)
