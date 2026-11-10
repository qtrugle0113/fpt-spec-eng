"""Explicit invariant conversions followed by strict target validation."""
from datetime import date, datetime
from decimal import Decimal
import re
from ..contracts.config import parse_timestamp
from ..staging.codec import scalar

TEXT = {'text', 'varchar'}
INTEGER = {'integer', 'bigint'}
NUMERIC = INTEGER | {'decimal'}
SUPPORTED = TEXT | NUMERIC | {'date', 'timestamp', 'boolean'}


def convert_value(value, *, source_type, target_type, **constraints):
    if source_type not in SUPPORTED or target_type not in SUPPORTED:
        raise ValueError('Unsupported mapping type.')
    if value is None:
        return scalar(None, dict(constraints, logical_type=target_type))
    # Validate the source's Python representation before converting. In
    # particular bool is never accepted as an integer, nor float as decimal.
    valid = (type(value) is str if source_type in TEXT else
             type(value) is int if source_type in INTEGER else
             isinstance(value, Decimal) and value.is_finite() if source_type == 'decimal' else
             type(value) is bool if source_type == 'boolean' else
             type(value) is date if source_type == 'date' else
             isinstance(value, datetime))
    if not valid:
        raise ValueError('Source value has an invalid logical representation.')
    if source_type in INTEGER:
        scalar(value, dict(logical_type=source_type))
    try:
        if source_type == target_type or source_type in TEXT and target_type in TEXT:
            converted = value
        elif source_type in TEXT:
            if target_type in INTEGER:
                if not re.fullmatch(r'[+-]?\d{1,20}', value, flags=re.ASCII):raise ValueError()
                converted = int(value)
            elif target_type == 'decimal':
                if len(value) > 80 or not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', value, flags=re.ASCII):raise ValueError()
                converted = Decimal(value)
            elif target_type == 'date':
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value, flags=re.ASCII):raise ValueError()
                converted = date.fromisoformat(value)
            elif target_type == 'timestamp':converted = parse_timestamp(value)
            else:raise ValueError()
        elif source_type in INTEGER and target_type in NUMERIC:
            converted = Decimal(value) if target_type == 'decimal' else value
        elif source_type == 'decimal' and target_type in INTEGER:
            # Bound before int() to avoid expanding an unbounded exponent.
            if not -(2**63) <= value < 2**63 or value != value.to_integral_value():raise ValueError()
            converted = int(value)
        else:raise ValueError()
        column = dict(constraints, logical_type=target_type)
        scalar(converted, column)
        return converted
    except (ValueError, TypeError, ArithmeticError, UnicodeError, KeyError):
        raise ValueError('Value cannot be converted losslessly to the target type.') from None


def direct_value(value, source, target):
    source_type = source['logical_type'];target_type = target['logical_type']
    compatible = (source_type == target_type or source_type in TEXT and target_type in TEXT or
                  source_type == 'integer' and target_type in {'bigint', 'decimal'} or
                  source_type == 'bigint' and target_type == 'decimal')
    if not compatible:raise ValueError('An explicit type conversion is required.')
    if value is not None:scalar(value, source)
    limits = {k:v for k,v in target.items() if k not in {'name','logical_type'}}
    return convert_value(value, source_type=source_type, target_type=target_type, **limits)
