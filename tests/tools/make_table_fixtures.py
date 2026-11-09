"""Derive public browser fixtures from the repository's canonical sample."""
from pathlib import Path
import shutil
import zipfile
from openpyxl import load_workbook

root=Path('/tmp/aat-table-fixture-source')
output=Path('/tmp/aat-table-fixtures');output.mkdir(exist_ok=True)
source=root/'Table Definition.sample.xlsx'
shutil.copyfile(source,output/'postgres.xlsx')
book=load_workbook(source)
for sheet in ('Tables','Columns'):
    for row in book[sheet].iter_rows(min_row=2):
        if row[0].value:
            row[0].value='mysql_etl';row[1].value='etl_test';row[2].value='aat_workbook_'+row[2].value
book.save(output/'mysql.xlsx')
shutil.copyfile(output/'mysql.xlsx',output/'boundary.xlsx')
with zipfile.ZipFile(output/'boundary.xlsx','a') as archive:
    archive.writestr('docProps/aat-boundary.txt',b'Public upload boundary fixture.\n'+b'x'*(1200*1024),compress_type=zipfile.ZIP_STORED)
book['Instructions']['B1']='unsupported'
book.save(output/'invalid.xlsx');book.close()
