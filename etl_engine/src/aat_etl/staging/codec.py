"""Exact typed JSON scalar encoding, with no implicit conversions."""
from datetime import date,datetime
from decimal import Decimal
import re
from ..contracts.config import parse_timestamp


def scalar(value,column,*,decode=False):
    logical=column['logical_type']
    if value is None:
        if not column.get('nullable',True):raise ValueError('NULL is not allowed for this staging column.')
        return None
    try:
        if logical in ('integer','bigint'):
            bits=32 if logical=='integer' else 64
            if type(value) is not int or not -(2**(bits-1))<=value<2**(bits-1):raise ValueError()
            return value
        if logical=='boolean':
            if type(value) is not bool:raise ValueError()
            return value
        if logical in ('varchar','text'):
            if type(value) is not str or '\0' in value:raise ValueError()
            value.encode('utf-8')
            if logical=='varchar' and column.get('length') is not None and len(value)>column['length']:raise ValueError()
            return value
        if logical=='decimal':
            if decode:
                if type(value) is not str or not re.fullmatch(r'-?\d+(?:\.\d+)?',value):raise ValueError()
                value=Decimal(value)
            if not isinstance(value,Decimal) or not value.is_finite():raise ValueError()
            precision=column['precision'];scale=column['scale']
            if type(precision) is not int or type(scale) is not int or not 1<=precision<=38 or not 0<=scale<=precision:raise ValueError()
            if value==0:encoded='0'
            else:
                _,digits,exponent=value.as_tuple();digits=list(digits)
                while digits[-1]==0:digits.pop();exponent+=1
                if max(len(digits)+exponent,0)>precision-scale or max(-exponent,0)>scale:raise ValueError()
                encoded=format(value,'f')
                if '.' in encoded:encoded=encoded.rstrip('0').rstrip('.')
            return value if decode else encoded
        if logical=='date':
            if decode:
                if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError()
                value=date.fromisoformat(value)
            if type(value) is not date:raise ValueError()
            return value if decode else value.isoformat()
        if logical=='timestamp':
            if decode:
                if type(value) is not str:raise ValueError()
                value=parse_timestamp(value)
            if not isinstance(value,datetime):raise ValueError()
            semantics=column.get('timezone_semantics','naive')
            if semantics not in ('naive','aware') or (value.utcoffset() is not None)!=(semantics=='aware'):raise ValueError()
            precision=column.get('precision',6)
            if precision is None:precision=6
            if type(precision) is not int or not 0<=precision<=6 or value.microsecond%10**(6-precision):raise ValueError()
            return value if decode else value.isoformat()
    except (ValueError,TypeError,KeyError,ArithmeticError,UnicodeError):
        raise ValueError('Staging value does not match its declared lossless type.') from None
    raise ValueError('Unsupported staging logical type.')


def row(values,columns,*,decode=False):
    if type(values) not in (list,tuple) or len(values)!=len(columns):raise ValueError('Staging row does not match its ordered schema.')
    return [scalar(value,column,decode=decode) for value,column in zip(values,columns)]
