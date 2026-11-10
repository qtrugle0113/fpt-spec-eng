"""Read-only monitoring; mutation continues through the existing guarded primitives."""
from typing import Literal
from fastapi import APIRouter,Query,Response
from aat_api.airflow_client.client import AirflowError
from aat_api.errors import APIError
from aat_api.schemas.common import Page,UTCDateTime
from aat_api.schemas.monitoring import DAGPublic,RunPublic,LogPage
from aat_api.services import monitoring as service

router=APIRouter()


def call(function,*args,**kwargs):
    try:return function(*args,**kwargs)
    except AirflowError as error:
        if error.status==404:raise APIError('AIRFLOW_RESOURCE_NOT_FOUND','Airflow resource not found.',404) from None
        raise APIError('AIRFLOW_UNAVAILABLE','Airflow monitoring is unavailable. Retry after connectivity is restored.',503,True) from None


@router.get('/dags',response_model=Page[DAGPublic],operation_id='get_dags')
def dags(search:str|None=None,ownership:Literal['MANAGED','EXTERNAL']|None=None,paused:Literal['true','false']|None=None,
         latest_status:Literal['success','failed','running','queued']|None=None,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0)):
    return call(service.inventory,search=search,ownership=ownership,paused=None if paused is None else paused=='true',
        latest_status=latest_status,limit=limit,offset=offset)


@router.get('/dags/{dag_id}',response_model=DAGPublic,operation_id='get_dags_dag_id')
def dag(dag_id:str,response:Response):
    result,etag=call(service.detail,dag_id)
    if etag is not None:response.headers['ETag']='"'+etag+'"'
    return result


@router.get('/dags/{dag_id}/runs',response_model=Page[RunPublic],operation_id='get_dags_dag_id_runs')
def runs(dag_id:str,from_:UTCDateTime|None=Query(None,alias='from'),to:UTCDateTime|None=None,state:str|None=None,
         limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0)):
    return call(service.runs,dag_id,from_=from_,to=to,state=state,limit=limit,offset=offset)


@router.get('/dags/{dag_id}/runs/{run_id}',response_model=RunPublic,operation_id='get_dags_dag_id_runs_run_id')
def run(dag_id:str,run_id:str):return call(service.run_detail,dag_id,run_id)


@router.get('/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs',response_model=LogPage,
            operation_id='get_dags_dag_id_runs_run_id_tasks_task_id_logs')
def logs(dag_id:str,run_id:str,task_id:str,attempt:int=Query(1,ge=0),map_index:int=Query(-1,ge=-1),token:str|None=Query(None,max_length=16384)):
    return call(service.log_page,dag_id,run_id,task_id,attempt=attempt,map_index=map_index,token=token)
