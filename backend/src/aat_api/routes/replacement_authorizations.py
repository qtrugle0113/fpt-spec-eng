"""Explicit replacement grant/history/revoke; readback does not cancel execution."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Header,Query,Response
from aat_api.routes.connections import expected_revision,etag
from aat_api.schemas.common import Page,ErrorResponse
from aat_api.schemas.authorizations import AuthorizationRequest,AuthorizationPublic,RevokeAuthorizationRequest
from aat_api.services import replacement_authorizations as service

router=APIRouter()
errors={'default':{'model':ErrorResponse}}


@router.post('/etl-definitions/{id}/replacement-authorizations',status_code=201,
             response_model=AuthorizationPublic,operation_id='post_etl_definitions_id_replacement_authorizations',responses=errors)
def grant_authorization(id:UUID,value:AuthorizationRequest,response:Response,
                        idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    result=service.grant(id,value,idempotency_key)
    response.headers['Location']='/api/v1/replacement-authorizations/'+str(result['id'])
    return etag(response,result)


@router.get('/etl-definitions/{id}/replacement-authorizations',response_model=Page[AuthorizationPublic],
            operation_id='get_etl_definitions_id_replacement_authorizations',responses=errors)
def list_authorizations(id:UUID,limit:Annotated[int,Query(ge=1,le=200)]=50,
                        offset:Annotated[int,Query(ge=0)]=0):
    return service.listing(id,limit,offset)


@router.get('/replacement-authorizations/{id}',response_model=AuthorizationPublic,
            operation_id='get_replacement_authorizations_id',responses=errors)
def get_authorization(id:UUID,response:Response):return etag(response,service.detail(id))


@router.post('/replacement-authorizations/{id}/revoke',response_model=AuthorizationPublic,
             operation_id='post_replacement_authorizations_id_revoke',responses=errors)
def revoke_authorization(id:UUID,value:RevokeAuthorizationRequest,response:Response,if_match:Annotated[str,Header(alias='If-Match')],
                         idempotency_key:Annotated[UUID,Header(alias='Idempotency-Key')]):
    return etag(response,service.revoke(id,expected_revision(if_match),idempotency_key))
