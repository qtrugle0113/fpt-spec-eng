"""Typed public monitoring projections; missing metrics remain nullable."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field
from .common import APIModel


class RunReference(APIModel):
    dag_id:str
    run_id:str
    start_time:datetime|None=None
    end_time:datetime|None=None
    airflow_url:str|None=None


class DAGPublic(APIModel):
    dag_id:str
    description:str|None=None
    ownership:Literal['MANAGED','EXTERNAL']
    is_paused:bool
    is_active:bool|None=None
    schedule:str|None=None
    timezone:str|None=None
    definition_id:UUID|None=None
    revision_id:UUID|None=None
    upload_id:UUID|None=None
    deployment_id:UUID|None=None
    latest_run_status:str|None=None
    next_scheduled_run:datetime|None=None
    airflow_url:str
    last_successful_run:RunReference|None
    last_successful_run_availability:Literal['AVAILABLE','UNAVAILABLE','UNKNOWN']


class TaskStatus(APIModel):
    task_id:str
    map_index:int=-1
    state:str|None
    try_number:int|None=None
    start_time:datetime|None=None
    end_time:datetime|None=None
    duration_ms:int|None=None
    error_summary:str|None=None


class ETLMetrics(APIModel):
    extracted_rows:int|None=None
    validated_rows:int|None=None
    loaded_rows:int|None=None
    failed_rows:int|None=None
    staging_bytes:int|None=None
    duration_ms:int|None=None
    phase:str|None=None
    protected_bytes:int|None=None
    recovery_summary:str|None=None


class RunPublic(APIModel):
    dag_id:str
    run_id:str
    revision_id:UUID|None=None
    state:str
    run_type:Literal['backfill','scheduled','manual','operator_triggered','asset_triggered','asset_materialization']
    error_summary:str|None=None
    start_time:datetime|None=None
    queued_time:datetime|None=None
    end_time:datetime|None=None
    duration_ms:int|None=None
    tasks:list[TaskStatus]=Field(default_factory=list)
    metrics:ETLMetrics|None=None


class LogPage(APIModel):
    content:list[str]
    continuation_token:str|None=None
    available:bool
    truncated:bool
    unavailable_reason:str|None=None
