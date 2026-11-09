"""Liveness is independent of DB/Airflow; foundation readiness is T034."""

from uuid import uuid4
from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse

from aat_api.schemas.common import ErrorBody, ErrorResponse, Health

router = APIRouter()
ERROR_RESPONSES = {'default': {'model': ErrorResponse}}


@router.get('/health/live', response_model=Health, response_model_exclude_unset=True,
            operation_id='get_health_live', responses=ERROR_RESPONSES)
def live() -> Health:
    return Health(status='ALIVE')


@router.get('/health/ready', response_model=Health, operation_id='get_health_ready',
            responses={503: {'model': ErrorResponse}, **ERROR_RESPONSES})
def ready(request:Request) -> JSONResponse:
    from aat_api.services.health import probe
    from aat_api.errors import response
    result=probe()
    if result['ready']:return JSONResponse(status_code=200,content={'status':'READY','dependencies':result['dependencies']})
    return response(request,'FOUNDATION_NOT_READY','Application foundation is not ready.',503,True)
