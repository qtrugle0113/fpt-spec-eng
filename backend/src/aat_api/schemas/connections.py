"""Strict public connection inputs; credentials remain write-only."""
from typing import Annotated, Literal
from pydantic import Field, StrictInt, StrictStr, field_validator,model_serializer
from .common import APIModel,Page,UTCDateTime,Issue,ResourceID
from aat_api.services.connections.policy import validate_host


class ConnectionCreate(APIModel):
    code: Annotated[StrictStr, Field(min_length=1,max_length=64)]
    name: Annotated[StrictStr, Field(min_length=1)]
    database_type: Literal['POSTGRESQL','MYSQL']
    host: Annotated[StrictStr, Field(min_length=1)]
    port: Annotated[StrictInt, Field(ge=1,le=65535)]
    database_name: Annotated[StrictStr, Field(min_length=1)]
    schema_name: StrictStr | None = None
    username: Annotated[StrictStr, Field(min_length=1)]
    password: StrictStr = Field(default='',repr=False,json_schema_extra={'writeOnly':True})
    description: StrictStr | None = None

    @field_validator('code','name','database_name','username',mode='before')
    @classmethod
    def required_text(cls,value):
        if not isinstance(value,str) or not value.strip():
            raise ValueError('A non-empty value is required')
        return value.strip()

    @field_validator('host')
    @classmethod
    def allowed_host(cls,value):return validate_host(value)


class ConnectionPatch(APIModel):
    code: Annotated[StrictStr, Field(min_length=1,max_length=64)] | None = None
    name: Annotated[StrictStr, Field(min_length=1)] | None = None
    database_type: Literal['POSTGRESQL','MYSQL'] | None = None
    host: Annotated[StrictStr, Field(min_length=1)] | None = None
    port: Annotated[StrictInt, Field(ge=1,le=65535)] | None = None
    database_name: Annotated[StrictStr, Field(min_length=1)] | None = None
    schema_name: StrictStr | None = None
    username: Annotated[StrictStr, Field(min_length=1)] | None = None
    password: StrictStr | None = Field(default=None,repr=False,json_schema_extra={'writeOnly':True})
    description: StrictStr | None = None

    @field_validator('code','name','database_name','username',mode='before')
    @classmethod
    def required_text(cls,value):return ConnectionCreate.required_text(value)

    @field_validator('host')
    @classmethod
    def allowed_host(cls,value):return validate_host(value)

    @field_validator('database_type','port','password',mode='before')
    @classmethod
    def not_null(cls,value):
        if value is None:raise ValueError('Null is not allowed for this field')
        return value


class DependencyRef(APIModel):
    resource_type: Literal['DEFINITION','DAG','RUN']
    resource_id: str
    label: str
    url: str | None = None

    @model_serializer(mode='wrap')
    def omit_missing_url(self,handler):
        value=handler(self)
        if value.get('url') is None:value.pop('url',None)
        return value


class ConnectionPublic(APIModel):
    id: ResourceID
    code: str
    name: str
    database_type: Literal['POSTGRESQL','MYSQL']
    host: str
    port: int
    database_name: str
    schema_name: str | None
    username: str
    description: str | None
    revision: int
    has_password: bool
    dependencies: list[DependencyRef]
    needs_revalidation: bool
    test_status: Literal['UNTESTED','SUCCESS','FAILED']
    tested_at: UTCDateTime | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class TestResult(APIModel):
    status: Literal['SUCCESS','FAILED']
    tested_at: UTCDateTime
    latency_ms: int
    error: Issue | None
