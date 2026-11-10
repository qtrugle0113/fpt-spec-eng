"""T070: lossless typed configuration and mapping boundaries."""
from datetime import date,datetime,timezone
from decimal import Decimal
import importlib
import unittest
from uuid import uuid4


def module(name):
    try:return importlib.import_module('aat_etl.'+name)
    except ModuleNotFoundError as error:
        if error.name.startswith('aat_etl'):raise AssertionError('Engine implementation missing: '+name) from None
        raise


def configuration():
    return dict(dag_id='typed_fixture',source=dict(type='DB',connection_revision_id=str(uuid4()),schema='public',table='source'),
        target=dict(connection_revision_id=str(uuid4()),schema='public',table='target',physical_target_id='fixture:target'),
        schedule='Manual',timezone='Asia/Seoul',catchup=False,is_paused=True,load_strategy='APPEND',conflict_keys=[],
        batch_size=1000,retry_count=0,retry_delay=60,mappings=[])


class ExecutionContractTests(unittest.TestCase):
    def setUp(self):self.config=module('contracts.config')

    def test_canonical_hash_ignores_object_order_but_preserves_semantic_values(self):
        raw=configuration();a=self.config.ETLConfig.model_validate(raw)
        b=self.config.ETLConfig.model_validate(dict(reversed(list(raw.items()))))
        self.assertEqual(a.canonical_sha256(),b.canonical_sha256())
        raw['batch_size']=999
        self.assertNotEqual(a.canonical_sha256(),self.config.ETLConfig.model_validate(raw).canonical_sha256())

    def test_source_union_and_strategy_keys_are_strict(self):
        cases=[];raw=configuration();raw['source']['file_id']=str(uuid4());cases.append(raw)
        raw=configuration();raw['source']={'type':'CSV','file_id':str(uuid4()),'parser_revision':1,'file_sha256':'a'*64};raw['filter']={'and':[{'column':'id','operator':'IS NULL'}]};cases.append(raw)
        raw=configuration();raw['load_strategy']='UPSERT';cases.append(raw)
        raw=configuration();raw['conflict_keys']=['id'];cases.append(raw)
        raw=configuration();raw['batch_size']=True;cases.append(raw)
        raw=configuration();raw['source']['sql']='SELECT * FROM secret';cases.append(raw)
        for raw in cases:
            with self.subTest(raw=raw),self.assertRaises(ValueError):self.config.ETLConfig.model_validate(raw)

    def test_enabled_mapping_and_filter_grammar_require_explicit_typed_literals(self):
        for mapping in ({'target_column':'x','transformation':'CONSTANT','enabled':True},
                        {'target_column':'x','transformation':'DIRECT','enabled':True},
                        {'target_column':'x','transformation':'eval','enabled':True}):
            with self.subTest(mapping=mapping),self.assertRaises(ValueError):self.config.ETLMapping.model_validate(mapping)
        for predicate in ({'column':'x','operator':'IN','value':[]},
                          {'column':'x','operator':'IS NULL','value':{'logical_type':'integer','value':1}},
                          {'column':'x','operator':'LIKE','value':{'logical_type':'text','value':'%'}}):
            with self.subTest(predicate=predicate),self.assertRaises(ValueError):self.config.SourcePredicate.model_validate(predicate)

    def test_schedule_timezone_and_numeric_ranges_reject_invalid_inputs(self):
        for changes in ({'schedule':'* * * * * *'},{'schedule':'0 1 * * *'}, {'timezone':'Invented/Zone'},
                        {'batch_size':10001},{'retry_count':11},{'retry_delay':3601},{'catchup':'false'}):
            raw=configuration();raw.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.config.ETLConfig.model_validate(raw)

    def test_typed_literal_never_coerces_float_bool_or_numeric_string(self):
        for logical,value in [('decimal',0.1),('integer',True),('integer','7'),('boolean',1),('date','2026-02-30'),('timestamp','2026-01-01')]:
            with self.subTest(logical=logical,value=value),self.assertRaises(ValueError):
                self.config.TypedLiteral.model_validate({'logical_type':logical,'value':value})
        literal=self.config.TypedLiteral.model_validate({'logical_type':'decimal','value':'12345678901234567890.123456'})
        self.assertEqual(literal.value,'12345678901234567890.123456')

    def test_valid_file_and_cron_inputs_roundtrip_canonical_openapi_schema(self):
        import jsonschema,yaml
        from pathlib import Path
        schemas=yaml.safe_load(Path('/tmp/specs/001-airflow-automation-tool/contracts/openapi.yaml').read_text())['components']['schemas']
        document={'$ref':'#/components/schemas/ETLConfig','components':{'schemas':schemas}}
        raw=configuration();raw['source']={'type':'TXT','file_id':str(uuid4()),'parser_revision':2,'file_sha256':'a'*64}
        raw.update(schedule='0 1 * * MON-FRI',start_date='2026-11-10T01:00:00+09:00')
        config=self.config.ETLConfig.model_validate(raw)
        encoded=config.model_dump(mode='json',by_alias=True,exclude_none=True)
        jsonschema.Draft202012Validator(document,format_checker=jsonschema.FormatChecker()).validate(encoded)
        self.assertEqual(encoded,raw)
        self.assertEqual(config.canonical_sha256(),self.config.ETLConfig.model_validate(encoded).canonical_sha256())
        raw['start_date']='2026-11-10T01:00:00'
        localized=self.config.ETLConfig.model_validate(raw).model_dump(mode='json',by_alias=True,exclude_none=True)
        self.assertEqual(localized['start_date'],'2026-11-10T01:00:00+09:00')
        jsonschema.Draft202012Validator(document,format_checker=jsonschema.FormatChecker()).validate(localized)

    def test_mixed_in_types_duplicate_targets_and_offset_conflict_rejected(self):
        raw=configuration();raw['filter']={'and':[{'column':'id','operator':'IN','value':[{'logical_type':'integer','value':1},{'logical_type':'text','value':'1'}]}]}
        with self.assertRaises(ValueError):self.config.ETLConfig.model_validate(raw)
        raw=configuration();raw['mappings']=[{'source_column':'id','target_column':'id','transformation':'DIRECT','enabled':True}]*2
        with self.assertRaises(ValueError):self.config.ETLConfig.model_validate(raw)
        for changes in ({'start_date':'2026-11-10T01:00:00+00:00'},{'schedule':'*/0 * * * *'},
                        {'schedule':'60 * * * *'},{'start_date':'2026-03-08T02:30:00','timezone':'America/New_York'},
                        {'start_date':'2026-11-01T01:30:00','timezone':'America/New_York'}):
            raw=configuration();raw.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.config.ETLConfig.model_validate(raw)


class LosslessTypeTests(unittest.TestCase):
    def setUp(self):self.types=module('mapping.types')

    def convert(self,value,source,target,**constraints):
        return self.types.convert_value(value,source_type=source,target_type=target,**constraints)

    def test_exact_decimal_integer_unicode_and_null(self):
        self.assertEqual(self.convert('12345678901234567890.123456','text','decimal',precision=30,scale=6),Decimal('12345678901234567890.123456'))
        self.assertEqual(self.convert(2147483647,'integer','bigint'),2147483647)
        self.assertEqual(self.convert('Nguy\u1ec5n \U0001f680','text','varchar',length=20),'Nguy\u1ec5n \U0001f680')
        self.assertIsNone(self.convert(None,'text','integer'))
        self.assertEqual(self.convert('','text','varchar',length=1),'')

    def test_no_rounding_truncation_timezone_inference_or_invalid_calendar(self):
        cases=[('1.234','text','decimal',dict(precision=4,scale=2)),('2147483648','text','integer',{}),
               ('abc','text','varchar',dict(length=2)),('2026-02-30','text','date',{}),
               (datetime(2026,1,1,tzinfo=timezone.utc),'timestamp','timestamp',dict(timezone_semantics='naive')),
               (datetime(2026,1,1),'timestamp','timestamp',dict(timezone_semantics='aware'))]
        for value,source,target,limits in cases:
            with self.subTest(value=value),self.assertRaises(ValueError):self.convert(value,source,target,**limits)

    def test_iso_temporal_values_keep_microseconds_and_offset(self):
        self.assertEqual(self.convert('2026-11-10','text','date'),date(2026,11,10))
        value='2026-11-10T12:34:56.123456+09:00'
        self.assertEqual(self.convert(value,'text','timestamp',timezone_semantics='aware'),datetime.fromisoformat(value))

    def test_direct_mapping_does_not_guess_numeric_strings(self):
        mapper=module('mapping.mapper')
        with self.assertRaises(ValueError):
            mapper.map_row({'id':'7'},source_schema=[{'name':'id','logical_type':'text','nullable':False}],
                target_schema=[{'name':'id','logical_type':'integer','nullable':False}],mappings=[])

    def test_explicit_mapping_preserves_unmapped_target_columns(self):
        mapper=module('mapping.mapper')
        mapped=mapper.map_row({'id':7,'note':None},
            source_schema=[{'name':'id','logical_type':'integer','nullable':False},{'name':'note','logical_type':'text','nullable':True}],
            target_schema=[{'name':'id','logical_type':'integer','nullable':False},{'name':'note','logical_type':'text','nullable':True},{'name':'retained','logical_type':'text','nullable':True}],
            mappings=[{'source_column':'id','target_column':'id','transformation':'DIRECT','enabled':True},
                      {'source_column':'note','target_column':'note','transformation':'NULL_HANDLING','enabled':True,'default_literal':{'logical_type':'text','value':'fallback'}}])
        self.assertEqual(mapped,{'id':7,'note':'fallback'});self.assertNotIn('retained',mapped)

    def test_conversion_rejects_float_bool_exponents_and_numeric_overflow(self):
        for value,source,target,limits in [
            (True,'integer','decimal',dict(precision=10,scale=0)),
            (1.5,'decimal','decimal',dict(precision=10,scale=2)),
            ('1e3','text','decimal',dict(precision=10,scale=0)),
            (' 7','text','integer',{}),
            (Decimal('1E+999999'),'decimal','bigint',{}),
            (2147483648,'integer','bigint',{})]:
            with self.subTest(source=source,target=target),self.assertRaises(ValueError):self.convert(value,source,target,**limits)

    def test_constants_null_handling_and_zero_false_empty_remain_distinct(self):
        mapper=module('mapping.mapper')
        schema=[dict(name='value',logical_type='boolean',nullable=True)]
        mapping=[dict(source_column='value',target_column='value',transformation='NULL_HANDLING',enabled=True,
                      default_literal=dict(logical_type='boolean',value=True))]
        self.assertEqual(mapper.map_row({'value':False},source_schema=schema,target_schema=schema,mappings=mapping),{'value':False})
        self.assertEqual(mapper.map_row({'value':None},source_schema=schema,target_schema=schema,mappings=mapping),{'value':True})
        mapping=[dict(target_column='value',transformation='CONSTANT',enabled=True,
                      default_literal=dict(logical_type='boolean',value=False))]
        self.assertEqual(mapper.map_row({},source_schema=[],target_schema=schema,mappings=mapping),{'value':False})

    def test_error_identifies_position_without_disclosing_row(self):
        mapper=module('mapping.mapper')
        with self.assertRaises(mapper.MappingError) as caught:
            mapper.map_row({'secret':'sensitive-invalid-number'},source_schema=[dict(name='secret',logical_type='text')],
                target_schema=[dict(name='id',logical_type='integer')],row_number=42,
                mappings=[dict(source_column='secret',target_column='id',transformation='TYPE_CONVERSION',enabled=True)])
        self.assertEqual(caught.exception.row_number,42);self.assertEqual(caught.exception.column,'id')
        self.assertNotIn('sensitive',str(caught.exception))

    def test_unmapped_required_target_without_default_is_rejected(self):
        mapper=module('mapping.mapper')
        with self.assertRaises(ValueError):
            mapper.map_row({'id':1},source_schema=[dict(name='id',logical_type='integer')],
                target_schema=[dict(name='id',logical_type='integer'),dict(name='required',logical_type='text',nullable=False)],mappings=[])
