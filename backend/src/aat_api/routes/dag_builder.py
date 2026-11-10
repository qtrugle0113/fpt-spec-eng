"""Workbook deployment commands and per-DAG durable results."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Header,Response
from aat_api.schemas.deployments import DeployRequest,DeploymentPublic
from aat_api.routes.operations import get_operation,OperationResponse
from aat_api.services import dag_builder as service

router=APIRouter()


@router.post('/dag-deployments',status_code=202,response_model=OperationResponse,response_model_exclude_none=True,
             operation_id='post_dag_deployments')
def deploy(value:DeployRequest,idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    return get_operation(service.create(value,idempotency_key))


@router.get('/dag-deployments/{id}',response_model=DeploymentPublic,operation_id='get_dag_deployments_id')
def deployment(id:UUID,response:Response):
    result,generation=service.detail(id)
    if generation is not None:response.headers['ETag']='"'+str(generation)+'"'
    return result


@router.post('/dag-deployments/{id}/reconcile',status_code=202,response_model=OperationResponse,
             response_model_exclude_none=True,operation_id='post_dag_deployments_id_reconcile')
def reconcile(id:UUID,idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    return get_operation(service.reconcile(id,idempotency_key))
