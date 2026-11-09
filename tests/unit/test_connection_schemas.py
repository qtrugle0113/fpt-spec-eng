"""T040 schema boundaries independent of remote database availability."""
import unittest
from pydantic import ValidationError
from aat_api.schemas.connections import ConnectionCreate,ConnectionPatch


class ConnectionSchemaTests(unittest.TestCase):
    def value(self,**changes):
        data=dict(code=' example ',name=' Example ',database_type='POSTGRESQL',host='postgres',port=5432,
                  database_name='etl_test',username='aat_etl',password='synthetic-password')
        data.update(changes)
        return data

    def test_required_values_trim_and_password_is_not_in_repr(self):
        model=ConnectionCreate(**self.value())
        self.assertEqual(model.code,'example');self.assertEqual(model.name,'Example')
        self.assertTrue('synthetic-password' not in repr(model))

    def test_bad_types_ranges_fields_and_hosts_rejected(self):
        for changes in [{'port':True},{'port':'5432'},{'port':0},{'port':65536},{'name':' '},
                        {'username':''},{'code':' '},{'database_type':'OTHER'},
                        {'host':'http://postgres'},{'host':'127.0.0.1'},{'unknown':'value'}]:
            with self.subTest(fields=tuple(changes)),self.assertRaises(ValidationError):
                ConnectionCreate(**self.value(**changes))

    def test_patch_distinguishes_omitted_nullable_and_empty_password(self):
        self.assertEqual(ConnectionPatch().model_dump(exclude_unset=True),{})
        self.assertEqual(ConnectionPatch(password='').model_dump(exclude_unset=True),{'password':''})
        self.assertEqual(ConnectionPatch(schema_name=None).model_dump(exclude_unset=True),{'schema_name':None})
        for value in [{'password':None},{'port':None},{'database_type':None},{'name':None},{'host':None}]:
            with self.subTest(fields=tuple(value)),self.assertRaises(ValidationError):ConnectionPatch(**value)
