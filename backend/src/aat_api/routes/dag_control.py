"""Managed manual trigger commands return acceptance, not ETL completion."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Header
from aat_api.schemas.dag_control import TriggerRequest,DagStateRequest
from aat_api.routes.connections import expected_revision
from aat_api.routes.operations import get_operation,OperationResponse
from aat_api.services import dag_control as service

router=APIRouter()


@router.post('/dags/{dag_id}/trigger',status_code=202,response_model=OperationResponse,
             response_model_exclude_none=True,operation_id='post_dags_dag_id_trigger')
def trigger_dag(dag_id:str,value:TriggerRequest,idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    return get_operation(service.trigger(dag_id,value,idempotency_key))


@router.patch('/dags/{dag_id}/state',status_code=202,response_model=OperationResponse,
              response_model_exclude_none=True,operation_id='patch_dags_dag_id_state')
def state_dag(dag_id:str,value:DagStateRequest,if_match:Annotated[str,Header(alias='If-Match')],
              idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    from aat_api.services.dag_activation import request
    return get_operation(request(dag_id,value,expected_revision(if_match),idempotency_key))
