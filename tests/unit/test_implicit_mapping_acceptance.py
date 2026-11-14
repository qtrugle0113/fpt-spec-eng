"""AL/FR-044: implicit mapping chỉ theo tên chính xác và kiểu tương thích."""
import unittest
from aat_etl.mapping.mapper import map_row


class ImplicitMappingAcceptanceTests(unittest.TestCase):
    def test_empty_and_all_disabled_mapping_use_exact_names_and_keep_defaults(self):
        source=[{'name':'id','logical_type':'integer','nullable':False},
                {'name':'note','logical_type':'text','nullable':True}]
        target=[*source,{'name':'NOTE','logical_type':'text','nullable':True,'has_default':True}]
        for mappings in ([],[{'source_column':'note','target_column':'NOTE','transformation':'DIRECT','enabled':False}]):
            with self.subTest(mappings=mappings):
                actual=map_row({'id':7,'note':'Unicode ệ'},source_schema=source,target_schema=target,mappings=mappings)
                self.assertEqual(actual,{'id':7,'note':'Unicode ệ'})
                self.assertNotIn('NOTE',actual)

    def test_case_mismatch_never_guesses_a_required_target(self):
        with self.assertRaises(ValueError):
            map_row({'id':7},source_schema=[{'name':'id','logical_type':'integer','nullable':False}],
                    target_schema=[{'name':'ID','logical_type':'integer','nullable':False}],mappings=[])

    def test_implicit_mapping_never_coerces_numeric_text(self):
        with self.assertRaises(ValueError):
            map_row({'id':'7'},source_schema=[{'name':'id','logical_type':'text','nullable':False}],
                    target_schema=[{'name':'id','logical_type':'integer','nullable':False}],mappings=[])
