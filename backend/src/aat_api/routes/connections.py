"""Connections REST contract; no stored credential fields in public models."""
import re
from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Header,Query,Response
from aat_api.errors import APIError
from aat_api.schemas.common import ErrorResponse,Page
from aat_api.schemas.connections import ConnectionCreate,ConnectionPatch,ConnectionPublic,TestResult
from aat_api.services.connections import service

router=APIRouter()
errors={'default':{'model':ErrorResponse}}


def expected_revision(value:str) -> int:
    if not re.fullmatch(r'"[1-9][0-9]*"',value):
        raise APIError('INVALID_ETAG','A valid strong If-Match header is required.',422)
    return int(value[1:-1])


def etag(response:Response,value:dict) -> dict:
    response.headers['ETag']='"'+str(value['revision'])+'"'
    return value


@router.get('/connections',response_model=Page[ConnectionPublic],
            operation_id='get_connections',responses=errors)
def list_connections(search:str|None=None,database_type:Literal['POSTGRESQL','MYSQL']|None=None,
                     status:Literal['UNTESTED','SUCCESS','FAILED']|None=None,
                     limit:Annotated[int,Query(ge=1,le=200)]=50,offset:Annotated[int,Query(ge=0)]=0):
    return service.listing(search=search,database_type=database_type,status=status,limit=limit,offset=offset)


@router.post('/connections',status_code=201,response_model=ConnectionPublic,response_model_exclude_none=True,
             operation_id='post_connections',responses=errors)
def create_connection(value:ConnectionCreate,response:Response):
    result=service.create(value);response.headers['Location']='/api/v1/connections/'+str(result['id'])
    return etag(response,result)


@router.get('/connections/{id}',response_model=ConnectionPublic,response_model_exclude_none=True,
            operation_id='get_connections_id',responses=errors)
def get_connection(id:UUID,response:Response):return etag(response,service.detail(id))


@router.patch('/connections/{id}',response_model=ConnectionPublic,response_model_exclude_none=True,
              operation_id='patch_connections_id',responses=errors)
def patch_connection(id:UUID,value:ConnectionPatch,response:Response,if_match:Annotated[str,Header(alias='If-Match')]):
    return etag(response,service.patch(id,expected_revision(if_match),value))


@router.delete('/connections/{id}',status_code=204,response_class=Response,operation_id='delete_connections_id',responses=errors)
def delete_connection(id:UUID,if_match:Annotated[str,Header(alias='If-Match')]):
    service.delete(id,expected_revision(if_match));return Response(status_code=204)


@router.post('/connections/{id}/test',response_model=TestResult,response_model_exclude_none=True,
             operation_id='post_connections_id_test',responses=errors)
def test_connection(id:UUID):return service.test(id)
