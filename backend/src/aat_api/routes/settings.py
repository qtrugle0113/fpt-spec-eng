"""Settings use the same strong ETag contract as other mutable resources."""
from typing import Annotated
from fastapi import APIRouter,Header,Response
from aat_api.routes.connections import etag,expected_revision,errors
from aat_api.schemas.settings import SettingsPatch,SettingsPublic
from aat_api.services import settings as service

router=APIRouter()


@router.get('/settings',response_model=SettingsPublic,operation_id='get_settings',responses=errors)
def get_settings(response:Response):return etag(response,service.detail())


@router.patch('/settings',response_model=SettingsPublic,operation_id='patch_settings',responses=errors)
def patch_settings(value:SettingsPatch,response:Response,if_match:Annotated[str,Header(alias='If-Match')]):
    return etag(response,service.patch(expected_revision(if_match),value))
