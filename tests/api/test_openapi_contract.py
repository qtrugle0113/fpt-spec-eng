"""T015: reusable OpenAPI 3.1 harness and negative controls; no product mocks.

Dependencies are test-only PyYAML 6.0.3/jsonschema 4.26.0, already present in
the approved Airflow candidate. Later story tests call assert_response/request
against real HTTP responses; passing this file does not certify story endpoints.
"""

from copy import deepcopy
from pathlib import Path
import unittest
from uuid import uuid4

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'specs/001-airflow-automation-tool/contracts/openapi.yaml'
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'}


class ContractHarness:
    def __init__(self, document):
        self.document = document
        self.operations = {
            (method, path): operation
            for path, path_item in document['paths'].items()
            for method, operation in path_item.items() if method in METHODS
        }

    def resolve(self, value):
        while '$ref' in value:
            ref = value['$ref']
            assert ref.startswith('#/'), 'External references require explicit review'
            value = self.document
            for part in ref[2:].split('/'):
                value = value[part.replace('~1', '/').replace('~0', '~')]
        return value

    def validate(self, schema, payload):
        # Keep components at the document root so nested local $refs resolve.
        root = dict(self.document)
        root.update(schema)
        errors = sorted(Draft202012Validator(
            root, format_checker=FormatChecker()).iter_errors(payload), key=str)
        assert not errors, '\n'.join(
            f'{list(error.absolute_path)}: {error.validator}' for error in errors)

    def _no_write_only(self, schema, payload):
        schema = self.resolve(schema)
        assert not schema.get('writeOnly'), 'write-only value in response'
        if isinstance(payload, dict):
            for name, value in payload.items():
                if name in schema.get('properties', {}):
                    self._no_write_only(schema['properties'][name], value)
        if isinstance(payload, list) and 'items' in schema:
            for value in payload:
                self._no_write_only(schema['items'], value)
        for keyword in ('allOf', 'anyOf', 'oneOf'):
            for branch in schema.get(keyword, []):
                # Apply response secrecy even when an alternative accepts the value.
                self._no_write_only(branch, payload)

    def operation(self, method, path):
        key = (method.lower(), path)
        assert key in self.operations, f'Missing operation: {key}'
        return self.operations[key]

    def assert_request(self, method, path, *, headers=None, payload=None):
        operation = self.operation(method, path)
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        parameters = self.document['paths'][path].get('parameters', []) + operation.get('parameters', [])
        for parameter in parameters:
            parameter = self.resolve(parameter)
            if parameter['in'] == 'header':
                name = parameter['name'].lower()
                assert not parameter.get('required') or name in headers, f'Missing header: {name}'
                if name in headers:
                    self.validate(parameter['schema'], headers[name])
        if 'requestBody' in operation:
            body = self.resolve(operation['requestBody'])
            assert payload is not None or not body.get('required'), 'Missing request body'
            if payload is not None and 'application/json' in body['content']:
                self.validate(body['content']['application/json']['schema'], payload)

    def assert_response(self, method, path, status, payload=None, *, headers=None):
        responses = self.operation(method, path)['responses']
        key = str(status)
        # A default error response must never silently accept a wrong success code.
        if key not in responses:
            wildcard = key[0] + 'XX'
            if wildcard in responses:
                key = wildcard
            else:
                assert status >= 400 and 'default' in responses, f'Unexpected status: {status}'
                key = 'default'
        response = self.resolve(responses[key])
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        for name, definition in response.get('headers', {}).items():
            definition = self.resolve(definition)
            if definition.get('required'):
                assert name.lower() in headers, f'Missing response header: {name}'
            if name.lower() in headers:
                self.validate(definition['schema'], headers[name.lower()])
        content = response.get('content', {})
        if not content:
            assert payload is None, 'Unexpected response body'
        elif 'application/json' in content:
            schema = content['application/json']['schema']
            self._no_write_only(schema, payload)
            self.validate(schema, payload)

    def assert_implementation(self, actual_document, selected=None):
        """Compare only a completed story's operations; full inventory is explicit."""
        actual = ContractHarness(actual_document)
        selected = set(self.operations if selected is None else selected)
        for method, path in selected:
            expected_op = self.operation(method, path)
            actual_op = actual.operation(method, path)
            assert expected_op['operationId'] == actual_op['operationId'], 'operationId drift'
            expected = self.resolve_tree(expected_op)
            observed = actual.resolve_tree(actual_op)
            # Documentation may differ, validation/status/security semantics may not.
            assert expected == observed, f'Contract drift: {method} {path}'

    def resolve_tree(self, value):
        if isinstance(value, list):
            return [self.resolve_tree(item) for item in value]
        if isinstance(value, dict):
            resolved = self.resolve(value)
            return {key: self.resolve_tree(item) for key, item in resolved.items()
                    if key not in {'description', 'summary', 'example', 'examples', 'title'}}
        return value


class OpenAPIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(CONTRACT.read_text(encoding='utf-8'))
        cls.harness = ContractHarness(cls.document)

    def error(self):
        return {'error': {'code': 'DEPENDENCY_UNAVAILABLE', 'message': 'Service unavailable',
                          'request_id': str(uuid4()), 'retryable': True}}

    def test_inventory_is_derived_and_operation_ids_unique(self):
        ids = [op['operationId'] for op in self.harness.operations.values()]
        self.assertTrue(ids)
        self.assertEqual(len(ids), len(set(ids)))
        for name, schema in self.document['components']['schemas'].items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_missing_operation_is_detected(self):
        changed = deepcopy(self.document)
        method, path = next(iter(self.harness.operations))
        del changed['paths'][path][method]
        with self.assertRaisesRegex(AssertionError, 'Missing operation'):
            self.harness.assert_implementation(changed)

    def test_required_field_and_extra_field_drift_are_detected(self):
        for mutate in ('required', 'extra'):
            body = self.error()
            if mutate == 'required':
                del body['error']['request_id']
            else:
                body['error']['unexpected'] = 'value'
            with self.subTest(mutate=mutate), self.assertRaises(AssertionError):
                self.harness.assert_response('get', '/connections', 503, body)

    def test_schema_drift_in_implementation_is_detected(self):
        changed = deepcopy(self.document)
        changed['components']['schemas']['ErrorResponse']['required'] = []
        with self.assertRaisesRegex(AssertionError, 'Contract drift'):
            self.harness.assert_implementation(changed, {('get', '/connections')})

    def test_write_only_secret_cannot_be_returned(self):
        # A dedicated mutation proves writeOnly protection independently of extra fields.
        changed = deepcopy(self.document)
        changed['components']['schemas']['ErrorResponse']['properties']['password'] = {
            'type': 'string', 'writeOnly': True}
        body = self.error()
        body['password'] = 'synthetic-sentinel'
        with self.assertRaisesRegex(AssertionError, 'write-only'):
            ContractHarness(changed).assert_response('get', '/connections', 503, body)

    def test_wrong_success_status_is_not_accepted_by_default_error(self):
        with self.assertRaisesRegex(AssertionError, 'Unexpected status'):
            self.harness.assert_response('post', '/connections', 200, self.error())

    def test_if_match_and_idempotency_are_required(self):
        seen = set()
        for (method, path), operation in self.harness.operations.items():
            parameters = [self.harness.resolve(p) for p in operation.get('parameters', [])]
            for p in parameters:
                if p['in'] == 'header' and p.get('required'):
                    seen.add(p['name'])
                    with self.subTest(operation=operation['operationId'], header=p['name']):
                        with self.assertRaisesRegex(AssertionError, 'Missing header'):
                            self.harness.assert_request(method, path)
        self.assertTrue({'If-Match', 'Idempotency-Key'} <= seen)
        changed = deepcopy(self.document)
        op = changed['paths']['/connections/{id}']['patch']
        op['parameters'] = [p for p in op['parameters'] if p.get('name') != 'If-Match']
        with self.assertRaisesRegex(AssertionError, 'Contract drift'):
            self.harness.assert_implementation(changed, {('patch', '/connections/{id}')})

    def test_uuid_idempotency_format_and_response_etag_drift(self):
        for (method, path), operation in self.harness.operations.items():
            parameters = [self.harness.resolve(p) for p in operation.get('parameters', [])]
            if any(p.get('name') == 'Idempotency-Key' and p['schema'].get('format') == 'uuid'
                   for p in parameters):
                headers = {p['name']: 'placeholder' for p in parameters if p['in'] == 'header'}
                headers['Idempotency-Key'] = 'not-a-uuid'
                with self.assertRaises(AssertionError):
                    self.harness.assert_request(method, path, headers=headers)
                break
        else:
            self.fail('Canonical contract must declare UUID idempotency')
        changed = deepcopy(self.document)
        op = changed['paths']['/templates/table-definition']['get']
        del op['responses']['200']['headers']['ETag']
        with self.assertRaisesRegex(AssertionError, 'Contract drift'):
            self.harness.assert_implementation(changed, {('get', '/templates/table-definition')})

    def test_safe_error_and_story_selection_positive_controls(self):
        self.harness.assert_response('get', '/connections', 503, self.error())
        self.harness.assert_implementation(self.document, {('get', '/health/ready')})


if __name__ == '__main__':
    unittest.main()
