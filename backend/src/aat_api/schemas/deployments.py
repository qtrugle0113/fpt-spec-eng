"""Bounded workbook deployment selection and safe result projection."""
from datetime import datetime
from uuid import UUID
from pydantic import Field,StrictBool,field_validator
from .common import APIModel


class DeployRequest(APIModel):
    upload_id: UUID
    dag_ids: list[str] = Field(min_length=1,max_length=100)
    confirmation_token: str = Field(min_length=1,max_length=16384)
    support_objects_acknowledged: StrictBool

    @field_validator('dag_ids')
    @classmethod
    def unique(cls,value):
        import re
        if len(set(value))!=len(value) or any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}',item) for item in value):
            raise ValueError('Select unique validated DAG IDs.')
        return sorted(value)


class DeploymentPublic(APIModel):
    id: UUID
    dag_id: str
    revision: str
    state: str
    reconcile_required: bool
    airflow_version_id: str | None
    airflow_url: str
    error_summary: str | None
    last_verified_at: datetime | None
