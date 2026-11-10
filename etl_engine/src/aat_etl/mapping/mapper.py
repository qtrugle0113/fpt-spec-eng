"""Exact-name or explicitly enabled mappings, with safe row/column diagnostics."""
from ..contracts.config import ETLMapping, TypedLiteral
from ..readers.database import literal_value
from .types import convert_value, direct_value
from ..staging.codec import scalar


class MappingError(ValueError):
    def __init__(self, row_number, column):
        self.row_number = row_number
        self.column = column
        super().__init__(f'Invalid mapped value at row {row_number}, column {column}.')


def map_row(row, *, source_schema, target_schema, mappings, row_number=1):
    sources = {c['name']:c for c in source_schema}
    targets = {c['name']:c for c in target_schema}
    if len(sources) != len(source_schema) or len(targets) != len(target_schema):
        raise ValueError('Schema column names must be unique.')
    enabled = [m if isinstance(m, ETLMapping) else ETLMapping.model_validate(m) for m in mappings]
    enabled = [m for m in enabled if m.enabled]
    if not enabled:
        enabled = [ETLMapping(source_column=name, target_column=name, transformation='DIRECT', enabled=True)
                   for name in targets if name in sources]
    result = {}
    for mapping in enabled:
        name = mapping.target_column
        try:
            if name in result:raise ValueError('Duplicate target mapping.')
            target = targets[name]
            if target.get('generated'):raise ValueError('Generated targets cannot be mapped.')
            if mapping.transformation == 'CONSTANT':
                literal = mapping.default_literal
                value = direct_value(literal_value(literal), literal_schema(literal, target), target)
            else:
                source = sources[mapping.source_column]
                value = row[mapping.source_column]
                if mapping.transformation == 'NULL_HANDLING' and value is None:
                    literal = mapping.default_literal
                    value = direct_value(literal_value(literal), literal_schema(literal, target), target)
                elif mapping.transformation == 'TYPE_CONVERSION':
                    scalar(value, source)
                    limits = {k:v for k,v in target.items() if k not in {'name','logical_type'}}
                    value = convert_value(value, source_type=source['logical_type'], target_type=target['logical_type'], **limits)
                else:value = direct_value(value, source, target)
            result[name] = value
        except (ValueError, KeyError, TypeError, ArithmeticError):
            raise MappingError(row_number, name) from None
    if not result:raise ValueError('At least one target column must be mapped.')
    for name, target in targets.items():
        if name not in result and not target.get('nullable', True) and not target.get('has_default') and not target.get('generated'):
            raise MappingError(row_number, name)
    return result


def literal_schema(literal: TypedLiteral, target):
    # TypedLiteral has already validated the scalar; target validation supplies
    # precision/length/timezone limits without inventing source constraints.
    return dict(target, logical_type=literal.logical_type, nullable=True)
