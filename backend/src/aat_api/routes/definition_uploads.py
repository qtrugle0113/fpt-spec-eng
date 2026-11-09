"""Definition upload, validation and issue history endpoints."""
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, File, Form, Header, Query, Response, UploadFile
from aat_api.schemas.common import Page, Issue, UTCDateTime
from aat_api.schemas.definitions import UploadPublic, ValidationRequest
from aat_api.routes.operations import get_operation, OperationResponse
from aat_api.services import definition_uploads as service

router = APIRouter()


@router.post('/definition-uploads', status_code=201, response_model=UploadPublic)
async def upload_definition(response:Response, file:Annotated[UploadFile, File()], kind:Annotated[Literal['TABLE', 'ETL'], Form()]):
    result = await service.store(file, kind)
    response.headers['Location'] = '/api/v1/definition-uploads/' + str(result['id'])
    return result


@router.get('/definition-uploads', response_model=Page[UploadPublic])
def list_uploads(kind:Literal['TABLE', 'ETL']|None=None, status:Literal['UPLOADED','VALIDATING','VALIDATED','INVALID']|None=None,
                from_:Annotated[UTCDateTime|None, Query(alias='from')]=None, to:UTCDateTime|None=None,
                limit:Annotated[int, Query(ge=1,le=200)]=50, offset:Annotated[int, Query(ge=0)]=0):
    return service.listing(kind,status,from_,to,limit,offset)


@router.get('/definition-uploads/{id}', response_model=UploadPublic)
def get_upload(id:UUID): return service.detail(id)


@router.post('/definition-uploads/{id}/validate', status_code=202, response_model=OperationResponse, response_model_exclude_none=True)
def validate_upload(id:UUID, value:ValidationRequest, idempotency_key:Annotated[UUID, Header(alias='Idempotency-Key')]):
    return get_operation(service.request_validation(id,value,idempotency_key))


@router.get('/definition-uploads/{id}/issues', response_model=Page[Issue], response_model_exclude_none=False)
def get_issues(id:UUID, limit:Annotated[int,Query(ge=1,le=200)]=50, offset:Annotated[int,Query(ge=0)]=0):
    return service.issues(id,limit,offset)


@router.get('/definition-uploads/{id}/table-preview')
@router.get('/definition-uploads/{id}/ddl-preview')
def get_table_preview(id:UUID):
    from aat_api.services.table_preview import preview
    return preview(id)
