"""Construct DDL solely from validated identifiers and typed literal values."""
from datetime import date, datetime
from decimal import Decimal
import re
from sqlalchemy import (MetaData, Table, Column, Integer, BigInteger, String, Text,
                        Numeric, Boolean, Date, DateTime, PrimaryKeyConstraint, literal)
from sqlalchemy.sql.elements import Grouping
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.exc import DBAPIError


class DDLOutcomeUnknown(RuntimeError):
    """DDL was dispatched but completion cannot be established safely."""


def build_table(spec, dialect_name):
    maximum = 63 if dialect_name == 'postgresql' else 64
    names = [spec.name, spec.target_schema, *(c.name for c in spec.columns)]
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) or len(name.encode()) > maximum for name in names):
        raise ValueError('Invalid SQL identifier.')
    columns = []
    for column in sorted(spec.columns, key=lambda c: c.ordinal):
        types = {'integer': Integer(), 'bigint': BigInteger(), 'varchar': String(column.length),
                 'text': Text(), 'decimal': Numeric(column.precision, column.scale),
                 'boolean': Boolean(), 'date': Date(),
                 'timestamp': DateTime(timezone=False) if dialect_name == 'postgresql' else mysql.DATETIME(fsp=6)}
        datatype = types[column.logical_type]
        default = None
        if column.has_default:
            value = column.default_literal['value']
            if value is not None:
                if column.logical_type == 'decimal': value = Decimal(value)
                elif column.logical_type == 'date': value = date.fromisoformat(value)
                elif column.logical_type == 'timestamp': value = datetime.fromisoformat(value)
            expression = literal(value, type_=datatype)
            # MySQL TEXT defaults require expression parentheses, including literals.
            default = Grouping(expression) if dialect_name == 'mysql' and column.logical_type == 'text' else expression
        columns.append(Column(column.name, datatype, nullable=column.nullable, server_default=default,
                              comment=column.description, quote=True, autoincrement=False))
    options = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'} if dialect_name == 'mysql' else {}
    return Table(spec.name, MetaData(), *columns, PrimaryKeyConstraint(*spec.primary_key),
                 schema=spec.target_schema, comment=spec.description, quote=True, quote_schema=True, **options)


def compile_table(spec, dialect_name):
    dialect = postgresql.dialect() if dialect_name == 'postgresql' else mysql.dialect()
    return str(CreateTable(build_table(spec, dialect_name)).compile(dialect=dialect, compile_kwargs={'literal_binds': True}))


def create(engine, spec, dialect_name):
    table = build_table(spec, dialect_name)
    # No checkfirst race or ALTER. The server is the authority on name collisions.
    with engine.connect() as connection:
        if dialect_name == 'mysql':
            connection.exec_driver_sql("SET SESSION sql_mode='STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'")
            connection.commit()
        try:
            connection.execute(CreateTable(table))
            connection.commit()
            return 'CREATED'
        except DBAPIError as error:
            original = error.orig
            if getattr(original, 'sqlstate', None) == '42P07' or (dialect_name == 'mysql' and original.args and original.args[0] == 1050):
                connection.rollback()
                return 'ALREADY_EXISTS'
            if error.connection_invalidated or (getattr(original, 'sqlstate', None) or '').startswith('08') or (dialect_name == 'mysql' and original.args and original.args[0] in (2006, 2013)):
                raise DDLOutcomeUnknown('Target connection lost after DDL dispatch; reconciliation required.') from None
            raise
        except (OSError, ConnectionError):
            raise DDLOutcomeUnknown('Target response lost after DDL dispatch; reconciliation required.') from None
