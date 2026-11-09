"""Common contract types; no dependency checks or business-side effects."""

from datetime import datetime, timezone
import re
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import (
    AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field,
    PlainSerializer, StrictBool, StrictInt, field_validator,
)

ResourceID = UUID


def _rfc3339_input(value):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value
    ):
        raise ValueError('Expected timezone-aware RFC3339 datetime')
    return value


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Timezone is required')
    return value.astimezone(timezone.utc)


UTCDateTime = Annotated[
    datetime, BeforeValidator(_rfc3339_input), AfterValidator(_utc),
    PlainSerializer(lambda value: value.isoformat().replace('+00:00', 'Z'), return_type=str, when_used='json'),
]


class APIModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class PageQuery(APIModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @field_validator('limit', 'offset', mode='before')
    @classmethod
    def integer_query(cls, value):
        if isinstance(value, bool) or not (
            isinstance(value, int) or isinstance(value, str) and re.fullmatch(r'[0-9]+', value)
        ):
            raise ValueError('Expected integer')
        return value


T = TypeVar('T')


class Page(APIModel, Generic[T]):
    items: list[T]
    total: Annotated[StrictInt, Field(ge=0)] | None
    next_offset: Annotated[StrictInt, Field(ge=0)] | None


class Issue(APIModel):
    scope: Literal['workbook', 'sheet', 'cell', 'resource']
    code: str
    message: str
    sheet: str | None = None
    row: Annotated[StrictInt, Field(ge=1)] | None = None
    column: Annotated[StrictInt, Field(ge=1)] | None = None
    column_name: str | None = None


class ErrorBody(APIModel):
    code: str
    message: str
    request_id: ResourceID
    retryable: StrictBool
    operation_id: str | None = None
    details: list[Issue] = Field(default_factory=list)


class ErrorResponse(APIModel):
    error: ErrorBody


class Health(APIModel):
    status: Literal['ALIVE', 'READY', 'NOT_READY']
    dependencies: dict[str, Literal['HEALTHY', 'UNHEALTHY', 'UNKNOWN']] = Field(default_factory=dict)
