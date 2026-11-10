"""T099: schema 1.0 ETL metadata parsing before any registry/target writes."""
import importlib
from pathlib import Path
import tempfile
import unittest
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]


def workbook():
    book=load_workbook(ROOT/'templates/ETL Definition.xlsx')
    book['ETL_Definitions'].append(['safe_dag','Example','DB','pg_etl','public','source',None,'mysql_etl','etl_test','target',
        'Manual',None,'UTC','FALSE','APPEND',None,None,None,None,'Paused',None,None])
    return book


class ETLWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('aat_api.validation.etl_definitions')
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'input.xlsx'

    def validate(self,book):
        book.save(self.path);book.close();return self.module.validate(self.path)

    def test_defaults_are_typed_and_new_dag_is_always_paused(self):
        book=workbook();book['ETL_Definitions']['T2']='Enabled';result=self.validate(book)
        self.assertFalse(result.issues);row=result.definitions[0]
        self.assertEqual(row.values['dag_id'],'safe_dag')
        self.assertEqual((row.values['batch_size'],row.values['retry_count'],row.values['retry_delay']),(1000,0,60))
        self.assertTrue(row.values['is_paused']);self.assertTrue(row.requested_enabled)

    def test_duplicate_dag_rejects_whole_workbook_at_actual_row(self):
        book=workbook();book['ETL_Definitions'].append([cell.value for cell in book['ETL_Definitions'][2]])
        result=self.validate(book);self.assertFalse(result.definitions)
        self.assertTrue(any(i['row']==3 and i['column']==1 for i in result.issues))

    def test_mapping_reference_and_duplicate_enabled_targets(self):
        for rows in ([['other','id','id',None,None,'TRUE']],
                     [['safe_dag','id','id',None,None,'TRUE'],['safe_dag','other','id',None,None,'TRUE']]):
            with self.subTest(rows=rows):
                book=workbook()
                for row in rows:book['Column_Mappings'].append(row)
                result=self.validate(book);self.assertFalse(result.definitions);self.assertTrue(result.issues)

    def test_disabled_mapping_and_constant_scalar_remain_metadata(self):
        book=workbook();book['Column_Mappings'].append(['safe_dag',None,'note','Constant Value','"unknown"','TRUE'])
        book['Column_Mappings'].append(['safe_dag','id','note','Direct Mapping',None,'FALSE'])
        result=self.validate(book);self.assertFalse(result.issues)
        mappings=result.definitions[0].mappings
        self.assertEqual(mappings[0]['transformation'],'CONSTANT');self.assertEqual(mappings[0]['default_json'],'"unknown"')
        self.assertFalse(mappings[1]['enabled'])

    def test_unsafe_filter_bad_cron_and_ambiguous_start_are_located(self):
        for column,value,extra in (('U','id > 0',{}),('K','@daily',{}),('M','Invalid/Zone',{}),
                ('L','2026-11-01T01:30:00',{'K':'0 0 * * *','M':'America/New_York'}),
                ('Q',0,{}),('R',11,{}),('S',3601,{}),('O','UPSERT',{}),('N','false',{})):
            with self.subTest(column=column):
                book=workbook();sheet=book['ETL_Definitions'];sheet[column+'2']=value
                for key,item in extra.items():sheet[key+'2']=item
                result=self.validate(book);self.assertFalse(result.definitions);self.assertTrue(result.issues)
                self.assertTrue(all(i.get('row')==2 for i in result.issues))

    def test_file_union_disallows_db_fields_and_filter(self):
        book=workbook();sheet=book['ETL_Definitions'];sheet['C2']='CSV';sheet['G2']='11111111-1111-4111-8111-111111111111'
        result=self.validate(book);self.assertTrue(result.issues)
        for cell in ('D2','E2','F2'):sheet[cell]=None
        result=self.validate(book);self.assertFalse(result.issues)
        sheet['U2']='{"and":[{"column":"id","operator":">","value":1}]}'
        self.assertTrue(self.validate(book).issues)

    def test_101_dags_and_formula_never_return_partial_definitions(self):
        book=workbook();sheet=book['ETL_Definitions'];original=[c.value for c in sheet[2]]
        for index in range(100):row=list(original);row[0]='dag_'+str(index);sheet.append(row)
        result=self.validate(book);self.assertFalse(result.definitions);self.assertTrue(result.issues)
        book=workbook();book['ETL_Definitions']['B2']='=1+1'
        self.assertTrue(self.validate(book).issues)

    def test_repository_sample_uses_the_existing_seed_references(self):
        result=self.module.validate(ROOT/'samples/definitions/ETL Definition.sample.xlsx')
        self.assertFalse(result.issues)
        self.assertTrue(result.definitions)
        codes={item.values['target_connection_code'] for item in result.definitions}
        self.assertTrue(codes<={'pg_etl','mysql_etl'})

    def test_confirmation_covers_100_revisions_within_the_bounded_token_limit(self):
        from aat_api.services.etl_preview import confirmation_scope
        from aat_api.services.confirmation import ConfirmationSigner
        from uuid import uuid4
        signer=ConfirmationSigner(b'x'*32)
        identities=[dict(id=str(uuid4()),config_sha256='a'*64,dependency_fingerprint='b'*64,previous_revision_id=str(uuid4())) for _ in range(100)]
        identity=uuid4();scope=confirmation_scope(identity,'c'*64,identities);token=signer.issue(scope)
        self.assertLess(len(token),16384);self.assertEqual(signer.verify(token,scope),scope)
        identities[99]['config_sha256']='d'*64
        with self.assertRaises(ValueError):signer.verify(token,confirmation_scope(identity,'c'*64,identities))
