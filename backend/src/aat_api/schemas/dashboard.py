"""Dashboard counts preserve unknown values and explicit completeness."""
from datetime import datetime,date
from typing import Literal
from pydantic import Field
from .common import APIModel
from .monitoring import RunPublic,RunReference


class RunMetrics(APIModel):
    total:int|None=None
    successful:int|None=None
    failed:int|None=None
    running:int|None=None
    queued:int|None=None
    other:int|None=None
    success_rate:float|None=None


class Inventory(APIModel):
    total:int|None=None
    active:int|None=None
    paused:int|None=None
    other:int|None=None


class ScheduleGroup(APIModel):
    group:Literal['Hourly','Daily','Weekly','Monthly','Custom','Manual','Unknown']
    dag_count:int|None=None
    run_count:int|None=None


class DailyMetrics(APIModel):
    date:date
    metrics:RunMetrics


class NextRun(APIModel):
    dag_id:str
    scheduled_time:datetime
    is_paused:bool
    airflow_url:str


class DashboardPublic(APIModel):
    inventory:Inventory
    run_metrics:RunMetrics
    lifetime_metrics:RunMetrics
    schedule_groups:list[ScheduleGroup]
    time_series:list[DailyMetrics]
    recent_runs:list[RunPublic]
    next_scheduled_runs:list[NextRun]=Field(default_factory=list)
    last_successful_run:RunReference|None
    last_successful_run_availability:Literal['AVAILABLE','UNAVAILABLE','UNKNOWN']
    timezone:str
    scope:Literal['ALL','MANAGED','EXTERNAL']='ALL'
    from_:datetime=Field(alias='from')
    to:datetime
    completeness:Literal['COMPLETE','INCOMPLETE','UNAVAILABLE']
    unavailable_fields:list[str]
    fetched_at:datetime|None
    stale:bool
