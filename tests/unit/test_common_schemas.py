"""T018 boundaries, written before common schemas; no database dependency."""

from datetime import datetime, timezone
import importlib
import unittest
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError


def common():
    try:
        return importlib.import_module('aat_api.schemas.common')
    except ModuleNotFoundError as exc:
        if exc.name not in {'aat_api.schemas', 'aat_api.schemas.common'}:
            raise
        raise AssertionError('T018 common schemas are not implemented') from None


class CommonSchemaTests(unittest.TestCase):
    def test_uuid_validates_and_serializes_canonically(self):
        adapter = TypeAdapter(common().ResourceID)
        value = uuid4()
        self.assertEqual(adapter.validate_python(str(value)), value)
        self.assertEqual(adapter.dump_python(value, mode='json'), str(value))
        for invalid in ('not-a-uuid', '', 12, True):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                adapter.validate_python(invalid)

    def test_datetime_normalizes_offsets_and_serializes_utc_z(self):
        adapter = TypeAdapter(common().UTCDateTime)
        value = adapter.validate_python('2026-11-09T18:30:01.123456+09:00')
        self.assertEqual(value, datetime(2026, 11, 9, 9, 30, 1, 123456, tzinfo=timezone.utc))
        self.assertEqual(adapter.dump_python(value, mode='json'), '2026-11-09T09:30:01.123456Z')

    def test_datetime_rejects_naive_date_epoch_and_invalid_values(self):
        adapter = TypeAdapter(common().UTCDateTime)
        for invalid in ('2026-11-09', '2026-11-09T12:00:00', '2026-11-09 12:00:00Z',
                        '2026-02-30T12:00:00Z', 0, True, datetime(2026, 11, 9)):
            with self.subTest(value=str(invalid)), self.assertRaises(ValidationError):
                adapter.validate_python(invalid)

    def test_pagination_defaults_limits_and_query_strings(self):
        model = common().PageQuery
        self.assertEqual(model().model_dump(), {'limit': 50, 'offset': 0})
        self.assertEqual(model(limit='200', offset='10').model_dump(), {'limit': 200, 'offset': 10})
        for values in ({'limit': 0}, {'limit': 201}, {'offset': -1}, {'limit': True},
                       {'limit': 1.5}, {'offset': '1.0'}, {'unexpected': 1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                model(**values)

    def test_unknown_total_is_null_not_zero_and_page_forbids_extra_fields(self):
        page = common().Page[str](items=['first'], total=None, next_offset=1)
        self.assertEqual(page.model_dump(mode='json'), {'items': ['first'], 'total': None, 'next_offset': 1})
        self.assertEqual(set(common().Page[str].model_json_schema()['required']), {'items', 'total', 'next_offset'})
        for values in ({'total': -1}, {'next_offset': -1}, {'unexpected': 2}):
            body = {'items': [], 'total': None, 'next_offset': None}
            body.update(values)
            with self.subTest(values=values), self.assertRaises(ValidationError):
                common().Page[str](**body)

    def test_error_envelope_required_uuid_fields_and_location(self):
        model = common().ErrorResponse
        body = {'error': {'code': 'INVALID_INPUT', 'message': 'Invalid request.',
                         'request_id': str(uuid4()), 'retryable': False,
                         'details': [{'scope': 'workbook', 'code': 'INVALID_WORKBOOK',
                                      'message': 'Invalid workbook.', 'row': None, 'column': None}]}}
        self.assertEqual(model.model_validate(body).model_dump(mode='json')['error']['details'][0]['row'], None)
        for field in ('code', 'message', 'request_id', 'retryable'):
            changed = dict(body['error']); changed.pop(field)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                model(error=changed)
        with self.assertRaises(ValidationError):
            model(error=dict(body['error'], request_id='invalid'))
        with self.assertRaises(ValidationError):
            model(error=dict(body['error'], password='synthetic'))


if __name__ == '__main__':
    unittest.main()
