"""Fill browser-downloaded templates as an operator would; no database setup."""
import json
import sys
from openpyxl import load_workbook

kind, template, output, raw = sys.argv[1:]
data=json.loads(raw)
book=load_workbook(template)
if kind=='table':
    book['Tables'].append([data['code'],'public',data['table'],'Full workflow acceptance'])
    columns=[('customer_id','Integer',None,None,None,False,True),
        ('customer_name','Varchar',120,None,None,True,False),
        ('balance','Decimal',None,18,4,True,False),
        ('registered_at','Timestamp',None,None,None,True,False)]
    for ordinal,(name,type_,length,precision,scale,nullable,key) in enumerate(columns,1):
        book['Columns'].append([data['code'],'public',data['table'],name,ordinal,type_,length,precision,scale,
            str(nullable).upper(),str(key).upper(),None,'Full workflow column'])
elif kind=='etl':
    strategy=data.get('strategy','UPSERT')
    if strategy not in ('UPSERT','FULL_REFRESH'):raise ValueError('Unsupported T140 load strategy')
    conflict_key='customer_id' if strategy=='UPSERT' else None
    batch_size=int(data.get('batch_size',2))
    if batch_size<1:raise ValueError('Batch size must be positive')
    retry_count=int(data.get('retry_count',0))
    retry_delay=int(data.get('retry_delay',60))
    if not 0<=retry_count<=10 or not 0<=retry_delay<=3600:raise ValueError('Retry configuration is outside supported bounds')
    book['ETL_Definitions'].append([data['dag'],'Full file workflow','CSV',None,None,None,data['file'],
        data['code'],'public',data['table'],'Manual',None,'UTC','FALSE',strategy,conflict_key,batch_size,
        retry_count,retry_delay,'Paused',None,data['dag']])
    # CSV columns are text. Numeric and timestamp targets require the explicit
    # conversion selected by the operator; implicit mappings remain strict.
    for name in ('customer_id','customer_name','balance','registered_at'):
        book['Column_Mappings'].append([data['dag'],name,name,
            'Direct Mapping' if name=='customer_name' else 'Type Conversion',None,'TRUE'])
else:raise ValueError('Unknown public workbook kind')
book.save(output);book.close()
