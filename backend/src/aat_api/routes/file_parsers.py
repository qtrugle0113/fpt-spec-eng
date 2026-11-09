"""Explicit parser confirmation with a strong File ETag."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Header,Response
from aat_api.schemas.files import PublicParser,FilePublic
from aat_api.routes.connections import expected_revision
from aat_api.routes.files import etag
from aat_api.services.file_parsers import patch

router=APIRouter()


@router.patch('/files/{id}/parser',response_model=FilePublic)
def patch_parser(id:UUID,value:PublicParser,response:Response,if_match:Annotated[str,Header(alias='If-Match')]):
    return etag(response,patch(id,expected_revision(if_match),value))
