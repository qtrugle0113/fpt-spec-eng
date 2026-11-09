"""File Sources upload, metadata, bounded candidate preview and validation."""
import json
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,File,Form,Header,Query,Request,Response,UploadFile
from aat_api.errors import APIError
from aat_api.schemas.common import Page
from aat_api.schemas.files import FilePublic,FilePreview
from aat_api.schemas.definitions import ValidationRequest
from aat_api.services import files as service
from aat_api.routes.operations import get_operation,OperationResponse
from aat_api.workers.files import request_validation

router=APIRouter()


def parse_json(value):
    try:return json.loads(value)
    except (ValueError,TypeError):raise APIError('INVALID_PARSER_JSON','Parser configuration must be valid JSON.',422) from None


def etag(response,value):
    response.headers['ETag']='"'+str(value['revision'])+'"'
    return value


@router.post('/files',status_code=201,response_model=FilePublic)
async def upload_file(response:Response,file:Annotated[UploadFile,File()],parser_json:Annotated[str,Form(max_length=8192)]):
    value=await service.store(file,parse_json(parser_json))
    response.headers['Location']='/api/v1/files/'+str(value['id'])
    return etag(response,value)


@router.get('/files',response_model=Page[FilePublic])
def list_files(limit:Annotated[int,Query(ge=0,le=200)]=50,offset:Annotated[int,Query(ge=0)]=0):
    return service.listing(limit,offset)


@router.get('/files/{id}',response_model=FilePublic)
def get_file(id:UUID,response:Response):return etag(response,service.detail(id))


@router.get('/files/{id}/preview',response_model=FilePreview)
def preview_file(id:UUID,max_rows:Annotated[int,Query(ge=0,le=100)]=100,
                 parser_json:Annotated[str|None,Query(max_length=8192)]=None):
    return service.preview(id,max_rows,parse_json(parser_json) if parser_json is not None else None)


@router.post('/files/{id}/validate',status_code=202,response_model=OperationResponse,response_model_exclude_none=True)
def validate_file(id:UUID,value:ValidationRequest,request:Request,idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    return get_operation(request_validation(id,value,idempotency_key),request=request)
