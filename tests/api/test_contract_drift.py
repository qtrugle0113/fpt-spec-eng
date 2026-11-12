"""T148: derive route/request coverage from the current canonical contract."""
import re
import unittest
import yaml
from tests.api.test_openapi_contract import CONTRACT,METHODS


def normalized(path):return re.sub(r'\{[^}]+\}','{}',path)


def resolve(document,value):
    while '$ref' in value:
        pointer=value['$ref']
        if not pointer.startswith('#/'):raise AssertionError('External schema reference is not supported')
        value=document
        for part in pointer[2:].split('/'):value=value[part.replace('~1','/').replace('~0','~')]
    return value


def fields(document,schema):
    schema=resolve(document,schema)
    properties=set(schema.get('properties',{}))
    required=set(schema.get('required',[]))
    for branch in schema.get('allOf',[]):
        child_properties,child_required=fields(document,branch)
        properties.update(child_properties);required.update(child_required)
    return properties,required


class ContractDriftTests(unittest.TestCase):
    def test_every_canonical_operation_has_a_runtime_route_and_request_fields(self):
        from aat_api.main import app
        expected=yaml.safe_load(CONTRACT.read_text(encoding='utf-8'))
        actual=app.openapi()
        observed={(method,normalized(path)):operation
                  for path,item in actual['paths'].items()
                  for method,operation in item.items() if method in METHODS}
        wanted=set()
        for path,item in expected['paths'].items():
            runtime_path=path if path.startswith('/internal/') else '/api/v1'+path
            for method,operation in item.items():
                if method not in METHODS:continue
                key=(method,normalized(runtime_path));wanted.add(key)
                with self.subTest(method=method,path=path):
                    self.assertIn(key,observed,'Canonical operation is missing from the running application')
                    body=resolve(expected,operation.get('requestBody',{}))
                    schema=body.get('content',{}).get('application/json',{}).get('schema')
                    if schema:
                        runtime_body=resolve(actual,observed[key].get('requestBody',{}))
                        runtime_schema=runtime_body.get('content',{}).get('application/json',{}).get('schema')
                        self.assertIsNotNone(runtime_schema,'Runtime JSON request schema is missing')
                        expected_properties,expected_required=fields(expected,schema)
                        actual_properties,actual_required=fields(actual,runtime_schema)
                        self.assertTrue(expected_properties<=actual_properties,'Canonical request fields are absent from runtime schema')
                        self.assertTrue(expected_required<=actual_required,'Canonical required fields became optional at runtime')
        self.assertEqual(set(observed),wanted,'Runtime exposes operations outside the canonical contract')

    def test_inventory_comparison_does_not_depend_on_a_hardcoded_operation_count(self):
        first={('get',normalized('/files/{id}')),('post','/files')}
        second={('get',normalized('/files/{file_id}')),('post','/files')}
        self.assertEqual(first,second)
        self.assertNotEqual(first,second|{('delete',normalized('/files/{file_id}'))})
