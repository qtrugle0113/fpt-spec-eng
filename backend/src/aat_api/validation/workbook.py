"""Bounded ZIP/OpenXML preflight and read-only workbook loading."""
from pathlib import Path,PurePosixPath
from io import BytesIO
import posixpath
import re
import zipfile
from defusedxml.ElementTree import iterparse
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError
from openpyxl import load_workbook

TABLE_HEADERS={
    'Tables':['Target Connection Code','Target Schema','Table Name','Table Description'],
    'Columns':['Target Connection Code','Target Schema','Table Name','Column Name','Column Order','Data Type','Length','Precision','Scale','Nullable','Primary Key','Default Value','Column Description'],
}
ETL_HEADERS={
    'ETL_Definitions':['DAG ID','DAG Description','Source Type','Source Connection Code','Source Schema','Source Table','Source File Reference',
        'Target Connection Code','Target Schema','Target Table','Schedule','Start Date','Timezone','Catchup','Load Strategy','Conflict Key',
        'Batch Size','Retry Count','Retry Delay','Enabled/Paused','Optional Source Filtering','Column Mapping Reference'],
    'Column_Mappings':['DAG ID','Source Column','Target Column','Optional Transformation Type','Optional Default Value','Enabled'],
}


class WorkbookFailure(ValueError):
    def __init__(self,code:str,message:str,*,sheet=None,row=None,column=None):
        self.issue={'scope':'cell' if row is not None else 'sheet' if sheet else 'workbook',
                    'code':code,'message':message}
        if sheet:self.issue['sheet']=sheet
        if row is not None:self.issue.update(row=row,column=column)
        super().__init__(message)


def _elements(stream):
    stack=[]
    for event,element in iterparse(stream,events=('start','end'),forbid_dtd=True,forbid_entities=True,forbid_external=True):
        if event=='start':
            stack.append(element)
            yield event,element
        else:
            yield event,element
            stack.pop()
            if stack:stack[-1].remove(element)
            element.clear()


def _column(value:str) -> tuple[int,int]:
    found=re.fullmatch(r'([A-Z]+)([1-9][0-9]*)',value)
    if not found:raise WorkbookFailure('INVALID_CELL_REFERENCE','Workbook contains an invalid cell reference.')
    number=0
    for character in found[1]:number=number*26+ord(character)-64
    return int(found[2]),number


def preflight(path:Path,headers:dict[str,list[str]]) -> None:
    if path.stat().st_size>10*1024*1024:raise WorkbookFailure('WORKBOOK_TOO_LARGE','Definition upload exceeds 10 MiB.')
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist()
        if len(entries)>2000 or sum(e.file_size for e in entries)>100*1024*1024:
            raise WorkbookFailure('WORKBOOK_LIMIT','Workbook expanded size or entry limit exceeded.')
        seen=set()
        for entry in entries:
            name=entry.filename;folded=name.casefold()
            if folded in seen or '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or ':' in name:
                raise WorkbookFailure('UNSAFE_ARCHIVE_PATH','Workbook archive paths are invalid or ambiguous.')
            seen.add(folded)
            if entry.flag_bits&1 or entry.file_size/max(entry.compress_size,1)>100:
                raise WorkbookFailure('UNSAFE_ARCHIVE','Encrypted or excessively compressed workbook is not supported.')
            if any(value in folded for value in ('vbaproject','/embeddings/','/externallinks/')) or Path(folded).suffix in ('.exe','.dll','.js','.vbs','.py','.ps1','.bat','.cmd','.sh'):
                raise WorkbookFailure('EXECUTABLE_WORKBOOK','Macro, embedded payload or external link is not allowed.')
        names=set(archive.namelist())
        required={'[Content_Types].xml','xl/workbook.xml','xl/_rels/workbook.xml.rels'}
        if not required<=names:raise WorkbookFailure('INVALID_XLSX','A valid XLSX package is required.')
        sheets=[];relationships={}
        with archive.open('xl/workbook.xml') as stream:
            for event,element in _elements(stream):
                if event=='start' and element.tag.rsplit('}',1)[-1]=='sheet':
                    sheets.append((element.attrib.get('name'),next((v for k,v in element.attrib.items() if k.endswith('}id')),None)))
        with archive.open('xl/_rels/workbook.xml.rels') as stream:
            for event,element in _elements(stream):
                if event=='start' and element.tag.rsplit('}',1)[-1]=='Relationship':
                    target=element.attrib.get('Target','')
                    relationships[element.attrib.get('Id')]=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
        if [s[0] for s in sheets]!=['Instructions',*headers]:
            raise WorkbookFailure('INVALID_SHEETS','Workbook sheets and order must match the template.')
        limits={relationships.get(rid):(name,2 if name=='Instructions' else len(headers[name])) for name,rid in sheets}
        rows=0
        for entry in entries:
            if entry.is_dir():continue
            if not entry.filename.lower().endswith(('.xml','.rels')):
                with archive.open(entry) as stream:magic=stream.read(8)
                if magic.startswith((b'MZ',b'\x7fELF',b'\xd0\xcf\x11\xe0')):
                    raise WorkbookFailure('EXECUTABLE_WORKBOOK','Executable or OLE payload is not allowed.')
                continue
            sheet,maximum=limits.get(entry.filename,(None,None))
            current=None;has_value=False;last_row=0;columns=set()
            with archive.open(entry) as stream:
                for event,element in _elements(stream):
                    tag=element.tag.rsplit('}',1)[-1]
                    if event=='start':
                        if element.attrib.get('TargetMode','').lower()=='external' or any('macroenabled' in str(v).lower() for v in element.attrib.values()):
                            raise WorkbookFailure('EXTERNAL_WORKBOOK','External relationships and macros are not allowed.')
                        if sheet and tag=='row':
                            number=int(element.attrib.get('r','0'))
                            if number<=last_row:raise WorkbookFailure('DUPLICATE_ROW','Workbook rows are duplicated or out of order.')
                            last_row=number;columns=set();rows+=1
                            if rows>100000:raise WorkbookFailure('WORKBOOK_ROW_LIMIT','Workbook metadata exceeds 100000 rows.')
                        if sheet and tag=='c':
                            current=_column(element.attrib.get('r',''));has_value=False
                            if current[0]!=last_row or current[1] in columns:raise WorkbookFailure('DUPLICATE_CELL','Workbook cell coordinates are invalid or duplicated.')
                            columns.add(current[1])
                    else:
                        if tag=='f':
                            raise WorkbookFailure('FORMULA_NOT_ALLOWED','Formula cells are not allowed.',sheet=sheet,
                                                  row=current[0] if current and sheet else None,column=current[1] if current and sheet else None)
                        if current and tag in ('t','v') and element.text not in (None,''):has_value=True
                        if sheet and tag=='c':
                            if has_value and current[1]>maximum:
                                raise WorkbookFailure('EXTRA_COLUMN','Workbook contains data outside the declared columns.',sheet=sheet,row=current[0],column=current[1])
                            current=None


def read(path:Path,kind='TABLE') -> dict[str,list[tuple[int,tuple]]]:
    if kind not in ('TABLE','ETL'):raise WorkbookFailure('UNSUPPORTED_WORKBOOK','Workbook kind is not supported by this validator.')
    headers=TABLE_HEADERS if kind=='TABLE' else ETL_HEADERS
    label='Table Definition' if kind=='TABLE' else 'ETL Definition'
    try:
        preflight(path,headers)
        # Storage keys intentionally carry no user-controlled suffix. The bounded
        # compressed payload is supplied as a stream, avoiding extension guessing.
        book=load_workbook(BytesIO(path.read_bytes()),read_only=True,data_only=False,keep_links=False)
        try:
            if book['Instructions']['A1'].value!='Template Version' or book['Instructions']['B1'].value!='1.0' or book['Instructions']['B2'].value!=label:
                raise WorkbookFailure('TEMPLATE_VERSION','Template Version must be text 1.0 and match '+label+'.',sheet='Instructions',row=1,column=2)
            result={};count=0
            for name,expected in headers.items():
                sheet=book[name];sheet.reset_dimensions()
                records=[]
                for number,cells in enumerate(sheet.iter_rows(max_col=len(expected)),start=1):
                    count+=1
                    if count>100000:raise WorkbookFailure('WORKBOOK_ROW_LIMIT','Workbook metadata exceeds 100000 rows.')
                    values=tuple(cell.value for cell in cells)
                    if number==1:
                        if list(values)!=expected:raise WorkbookFailure('INVALID_HEADERS','Sheet headers must match the template exactly.',sheet=name,row=1,column=1)
                        continue
                    if all(value in (None,'') for value in values):continue
                    for column,value in enumerate(values,start=1):
                        if isinstance(value,str) and value.startswith('='):
                            raise WorkbookFailure('FORMULA_NOT_ALLOWED','Formula values are not allowed.',sheet=name,row=number,column=column)
                    records.append((number,values))
                result[name]=records
            return result
        finally:book.close()
    except WorkbookFailure:raise
    except (zipfile.BadZipFile,DefusedXmlException,ParseError,KeyError,ValueError,OSError,NotImplementedError):
        raise WorkbookFailure('INVALID_XLSX','Workbook package could not be parsed safely.') from None
