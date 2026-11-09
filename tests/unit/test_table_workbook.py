"""T048: real workbook fixtures derived from the existing schema1.0 template."""
import importlib
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
import zipfile
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]


def workbook():
    book=load_workbook(ROOT/'templates/Table Definition.xlsx')
    book['Tables'].append(['pg_etl','public','safe_table','Example table'])
    book['Columns'].append(['pg_etl','public','safe_table','id',1,'Integer',None,None,None,'FALSE','TRUE',None,'Identifier'])
    book['Columns'].append(['pg_etl','public','safe_table','name',2,'Varchar',80,None,None,'TRUE','FALSE','"unknown"','Name'])
    return book


def implementation():
    name='aat_api.validation.tables'
    try:return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if name.startswith(error.name):raise AssertionError('T050/T051 workbook validation missing') from None
        raise


class TableWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.module=implementation()
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'input.xlsx'
        self.target=self.module.TargetContext(code='pg_etl',database_type='POSTGRESQL',database_name='etl_test',
            schema_name='public',revision_id=str(uuid4()),server_fingerprint='a'*64)

    def validate(self,book):
        book.save(self.path);book.close()
        return self.module.validate(self.path,self.target)

    def test_valid_workbook_typed_defaults_and_composite_key_order(self):
        book=workbook();book['Columns']['E2']=10
        book['Columns'].append(['pg_etl','public','safe_table','tenant_id',2,'Big Integer',None,None,None,'FALSE','TRUE',None,None])
        book['Columns']['E3']=3
        result=self.validate(book)
        self.assertFalse(result.issues)
        self.assertEqual(result.tables[0].primary_key,['tenant_id','id'])
        name=next(c for c in result.tables[0].columns if c.name=='name')
        self.assertTrue(name.has_default);self.assertEqual(name.default_literal,{'logical_type':'varchar','value':'unknown'})

    def test_repository_sample_and_template_guidance_are_reused(self):
        result=self.module.validate(ROOT/'samples/definitions/Table Definition.sample.xlsx',self.target)
        self.assertFalse(result.issues);self.assertEqual(len(result.tables),2)
        book=load_workbook(ROOT/'templates/Table Definition.xlsx')
        try:
            self.assertEqual(book['Instructions']['B1'].value,'1.0')
            self.assertTrue(book['Columns'].data_validations.count)
            self.assertTrue(any(cell.comment for row in book['Columns'].iter_rows(min_row=1,max_row=1) for cell in row))
        finally:book.close()

    def test_twenty_invalid_workbooks_have_locations_and_no_validated_tables(self):
        def put(sheet,cell,value):return lambda w:w[sheet].__setitem__(cell,value)
        def decimal(precision,scale):
            def mutate(w):
                w['Columns']['F3']='Decimal';w['Columns']['G3']=None
                w['Columns']['H3']=precision;w['Columns']['I3']=scale
            return mutate
        cases=[('numeric_version',put('Instructions','B1',1.0)),('wrong_kind',put('Instructions','B2','ETL Definition')),
            ('missing_sheet',lambda w:w.remove(w['Tables'])),('extra_sheet',lambda w:w.create_sheet('Extra')),
            ('bad_header',put('Tables','A1','Unexpected Header')),('missing_header',put('Columns','M1',None)),
            ('blank_table',put('Tables','C2',None)),('unsafe_identifier',put('Tables','C2','x; DROP TABLE users')),
            ('wrong_connection',put('Tables','A2','other')),('duplicate_table',lambda w:w['Tables'].append(['pg_etl','public','safe_table',None])),
            ('orphan_column',put('Columns','C3','missing')),('duplicate_column',put('Columns','D3','id')),
            ('duplicate_order',put('Columns','E3',1)),('zero_order',put('Columns','E2',0)),
            ('unknown_type',put('Columns','F2','Money')),('missing_length',put('Columns','G3',None)),
            ('precision',decimal(39,2)),('scale',decimal(18,19)),('nullable_key',put('Columns','J2','TRUE')),
            ('expression_default',put('Columns','L3','CURRENT_TIMESTAMP'))]
        self.assertEqual(len(cases),20)
        for name,mutate in cases:
            with self.subTest(case=name):
                book=workbook();mutate(book);result=self.validate(book)
                self.assertTrue(result.issues,'Invalid workbook was accepted')
                self.assertFalse(result.tables,'Partial workbook validation was published')
                for issue in result.issues:
                    self.assertIn(issue['scope'],['workbook','sheet','cell'])
                    if issue['scope']=='cell':
                        self.assertGreaterEqual(issue['row'],1);self.assertGreaterEqual(issue['column'],1)

    def test_zip_payloads_and_formula_are_rejected_before_parse_side_effects(self):
        for name,payload in [('../escape.xml',b'x'),('xl/vbaProject.bin',b'vba'),
                             ('xl/externalLinks/externalLink1.xml',b'<externalLink/>'),('bomb.xml',b'x'*(2*1024*1024))]:
            with self.subTest(member=name):
                book=workbook();book.save(self.path);book.close()
                with zipfile.ZipFile(self.path,'a',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr(name,payload)
                result=self.module.validate(self.path,self.target)
                self.assertTrue(result.issues);self.assertFalse(result.tables)
                self.assertEqual(result.issues[0]['scope'],'workbook')
        book=workbook();book['Tables']['D2']='=1+1'
        result=self.validate(book);self.assertTrue(result.issues);self.assertFalse(result.tables)
