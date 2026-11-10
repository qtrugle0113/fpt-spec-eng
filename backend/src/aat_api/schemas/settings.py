"""Settings PATCH boundary; connectivity and version remain read-only."""
from typing import Annotated,Literal
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from pydantic import Field,StrictInt,StrictStr,field_validator
from .common import APIModel


class SettingsPatch(APIModel):
    default_batch_size:Annotated[StrictInt,Field(ge=1,le=10000)]|None=None
    dashboard_refresh_interval:Annotated[StrictInt,Field(ge=5,le=3600)]|None=None
    default_timezone:StrictStr|None=None
    staging_retention_days:Annotated[StrictInt,Field(ge=1,le=365)]|None=None

    @field_validator('*',mode='before')
    @classmethod
    def no_explicit_null(cls,value):
        if value is None:raise ValueError('Null setting is not supported')
        return value


    @field_validator('default_timezone')
    @classmethod
    def timezone_name(cls,value):
        try:ZoneInfo(value)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('Expected IANA timezone') from None
        return value


class SettingsPublic(APIModel):
    default_batch_size:int
    dashboard_refresh_interval:int
    default_timezone:str
    staging_retention_days:int
    revision:int
    airflow_connectivity_status:Literal['AVAILABLE','UNAVAILABLE','UNKNOWN']
    application_version:str
