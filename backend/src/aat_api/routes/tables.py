"""Creation commands and durable job history."""
from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Header,Query
from aat_api.schemas.common import UTCDateTime
from aat_api.schemas.definitions import TableCreateRequest
from aat_api.routes.operations import get_operation,OperationResponse
from aat_api.services import table_history as service

router=APIRouter()


@router.post('/table-creation-jobs',status_code=202,response_model=OperationResponse,response_model_exclude_none=True)
def create_tables(value:TableCreateRequest,idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    return get_operation(service.create(value,idempotency_key))


@router.get('/table-creation-jobs')
def list_jobs(upload_id:UUID|None=None,target_connection_id:UUID|None=None,
              state:Literal['QUEUED','RUNNING','SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION']|None=None,
              from_:Annotated[UTCDateTime|None,Query(alias='from')]=None,to:UTCDateTime|None=None,
              limit:Annotated[int,Query(ge=1,le=200)]=50,offset:Annotated[int,Query(ge=0)]=0):
    return service.jobs(upload_id,target_connection_id,state,from_,to,limit,offset)


@router.get('/table-creation-jobs/{id}')
def get_job(id:UUID):return service.detail_job(id)
