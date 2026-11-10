"""Calendar filters are inclusive local dates; data timestamps remain UTC."""
from typing import Literal
from fastapi import APIRouter,Query
from aat_api.schemas.dashboard import DashboardPublic
from aat_api.services import dashboard as service

router=APIRouter()


@router.get('/dashboard',response_model=DashboardPublic,operation_id='get_dashboard')
def dashboard(from_:str|None=Query(None,alias='from'),to:str|None=None,timezone:str|None=None,
              scope:Literal['ALL','MANAGED','EXTERNAL']='ALL',force_refresh:bool=False):
    return service.snapshot(from_=from_,to=to,zone=timezone,scope=scope,force_refresh=force_refresh)
