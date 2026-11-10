"""Generate public browser fixtures from the versioned workbook template."""
from pathlib import Path
from openpyxl import load_workbook
import json
from uuid import uuid4

root=Path('/tmp/aat-dag-template')
output=Path('/tmp/aat-dag-fixtures');output.mkdir(exist_ok=True)
index={}
for name,strategy in [(kind+'-'+project,policy) for project in ('desktop','mobile') for kind,policy in
    [('append','UPSERT'),('refresh','FULL_REFRESH'),('runrefresh','FULL_REFRESH'),('scheduled','FULL_REFRESH')]]:
    book=load_workbook(root/'ETL Definition.xlsx')
    dag='aat_browser_'+name.replace('-','_')+'_'+uuid4().hex[:8];index[name]=dag
    book['ETL_Definitions'].append([dag,'Browser acceptance','DB','pg_etl','sample','customers_source',
        None,'pg_etl','sample','customers_target','Manual',None,'UTC','FALSE',strategy,
        'customer_id' if strategy=='UPSERT' else None,None,None,None,'Paused',None,None])
    if name.startswith('scheduled-'):
        book['ETL_Definitions']['K2']='0 0 1 1 *';book['ETL_Definitions']['L2']='2026-01-01T00:00:00+00:00'
    book.save(output/(name+'.xlsx'))
    if name=='append-desktop':
        book['ETL_Definitions']['M2']='Invalid/Timezone'
        book.save(output/'invalid.xlsx')
    book.close()
(output/'index.json').write_text(json.dumps(index))
