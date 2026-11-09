"""Read durable operation state; no polling from Airflow metadata DB."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from fastapi import APIRouter
from sqlalchemy import text
from aat_api.schemas.common import APIModel,ErrorResponse
from aat_api.errors import APIError
from aat_metadata.repositories.base import create_app_engine


class OperationProgress(APIModel):
    phase:str|None=None
    completed:int|None=None
    total:int|None=None


class OperationResponse(APIModel):
    id:UUID
    kind:str
    state:Literal['QUEUED','RUNNING','SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION']
    progress:OperationProgress
    result_links:list[str]
    created_at:datetime
    deadline_at:str|None=None


router=APIRouter()


@router.get('/operations/{id}',operation_id='get_operation',response_model=OperationResponse,
            response_model_exclude_none=True,
            responses={'default':{'model':ErrorResponse}})
def get_operation(id:UUID):
    engine=create_app_engine()
    try:
        with engine.connect() as c:
            row=c.execute(text('SELECT id,kind,state,progress_json,result_ref,created_at,deadline_at FROM operations WHERE id=:id'),{'id':id}).mappings().first()
        if row is None:raise APIError('OPERATION_NOT_FOUND','Operation not found.',404)
        return OperationResponse(id=row['id'],kind=row['kind'],state=row['state'],
            progress=OperationProgress(**{k:v for k,v in row['progress_json'].items() if k in ('phase','completed','total')}),
            result_links=[row['result_ref']] if row['result_ref'] and row['result_ref'].startswith('/api/v1/') else [],
            created_at=row['created_at'],deadline_at=row['deadline_at'].isoformat() if row['deadline_at'] else None)
    finally:engine.dispose()
