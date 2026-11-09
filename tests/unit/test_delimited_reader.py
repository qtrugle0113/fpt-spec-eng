"""T062: bounded, strict CSV/TXT token semantics shared by preview and execution."""
import importlib
import io
import unittest


def implementation():
    try:return importlib.import_module('aat_etl.readers.delimited')
    except ModuleNotFoundError as error:
        if error.name.startswith('aat_etl'):raise AssertionError('T063 bounded delimited reader is not implemented') from None
        raise


class DelimitedReaderTests(unittest.TestCase):
    def setUp(self):self.reader=implementation()

    def config(self,**changes):
        return self.reader.ParserConfig(**dict(encoding='utf-8',delimiter=',',header_present=True,
            quote_character='"',escape_character=None,null_representation=r'\N',**changes))

    def records(self,data,**changes):
        config=dict(encoding='utf-8',delimiter=',',header_present=True,quote_character='"',escape_character=None,null_representation=r'\N')
        config.update(changes)
        return list(self.reader.read(io.BytesIO(data),self.reader.ParserConfig(**config)))

    def test_multiline_unicode_bom_and_quoted_null_provenance(self):
        rows=self.records(('\ufeffid,name,note\r\n1,"Nguyễn, An","line one\nline two"\r\n2,"\\N",\\N\r\n3,"",\r\n4,0,false\r\n').encode())
        self.assertEqual(rows[0].columns,['id','name','note'])
        self.assertEqual(rows[0].values,['1','Nguyễn, An','line one\nline two'])
        self.assertEqual(rows[1].values,['2',r'\N',None])
        self.assertTrue(rows[1].tokens[1].was_quoted);self.assertFalse(rows[1].tokens[2].was_quoted)
        self.assertEqual(rows[2].values,['3','','']);self.assertEqual(rows[3].values,['4','0','false'])
        self.assertEqual(rows[1].record,2);self.assertEqual(rows[1].line,4)

    def test_headerless_tab_delimited_txt_and_explicit_encoding(self):
        rows=self.records('café\t"a\tb"\n'.encode('cp1252'),encoding='cp1252',delimiter='\t',header_present=False)
        self.assertEqual(rows[0].columns,['column_1','column_2'])
        self.assertEqual(rows[0].values,['café','a\tb'])

    def test_headerless_utf8_preserves_leading_data_bom_unless_sig_codec_selected(self):
        data='\ufeff\\N,value\n'.encode('utf-8')
        self.assertEqual(self.records(data,header_present=False)[0].values,['\ufeff\\N','value'])
        self.assertEqual(self.records(data,header_present=False,encoding='utf-8-sig')[0].values,[None,'value'])

    def test_quote_doubling_and_explicit_escape(self):
        self.assertEqual(self.records(b'a,b\n1,"say ""hello"""\n')[0].values,['1','say "hello"'])
        self.assertEqual(self.records(b'a,b\n1,"say ""hello"""\n',escape_character='"')[0].values,['1','say "hello"'])
        self.assertEqual(self.records(b'a,b\n1,"say \\"hello\\""\n',escape_character='\\')[0].values,['1','say "hello"'])

    def test_empty_data_with_header_and_headerless_empty(self):
        self.assertEqual(self.records(b'a,b\n'),[])
        with self.assertRaises(self.reader.DelimitedError) as error:self.records(b'',header_present=False)
        self.assertEqual(error.exception.code,'EMPTY_FILE')

    def test_malformed_records_have_real_position_without_raw_values(self):
        fixtures=[b'a,a\n1,2\n',b'a,\n1,2\n',b'a,b\n1\n',b'a,b\n1,"private-value\n',b'a,b\n1,"private-value"trailing\n',b'a,b\n1,\xff\n']
        for data in fixtures:
            with self.subTest(data_sha_prefix=__import__('hashlib').sha256(data).hexdigest()[:8]):
                with self.assertRaises(self.reader.DelimitedError) as error:self.records(data)
                self.assertGreaterEqual(error.exception.line,1);self.assertGreaterEqual(error.exception.record,0)
                self.assertNotIn('private-value',str(error.exception));self.assertNotIn('private-value',error.exception.code)

    def test_record_limit_is_enforced_before_materializing_oversized_row(self):
        class Bounded(io.BytesIO):
            def read(self,size=-1):
                if size<0 or size>8192:raise AssertionError('Reader requested an unbounded buffer')
                return super().read(size)
        source=Bounded(b'a\n"'+b'x'*(1024*1024)+b'"\n')
        with self.assertRaises(self.reader.DelimitedError) as error:list(self.reader.read(source,self.config()))
        self.assertEqual(error.exception.code,'RECORD_TOO_LARGE')
        self.assertLessEqual(source.tell(),1024*1024+8192)

    def test_preview_stops_at_requested_rows_without_validating_the_rest(self):
        data=b'a,b\n'+b'1,2\n'*101+b'bad-row\n'
        result=self.reader.preview(io.BytesIO(data),self.config(),max_rows=100)
        self.assertEqual(len(result['rows']),100);self.assertTrue(result['limited'])
        with self.assertRaises(self.reader.DelimitedError):list(self.reader.read(io.BytesIO(data),self.config()))
        headers=self.reader.preview(io.BytesIO(b'a,b\n1,2\n'),self.config(),max_rows=0)
        self.assertEqual(headers['columns'],['a','b']);self.assertEqual(headers['rows'],[])

    def test_parser_config_rejects_ambiguous_and_non_text_grammar(self):
        for changes in ({'delimiter':'::'},{'delimiter':'\n'},{'quote_character':','},{'encoding':'not-a-codec'},{'escape_character':'xx'}):
            config=dict(encoding='utf-8',delimiter=',',header_present=True,quote_character='"',escape_character=None,null_representation=r'\N');config.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.reader.ParserConfig(**config)
