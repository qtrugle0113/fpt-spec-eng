"""Canonical private runtime endpoint, deliberately outside the public API prefix."""
import hmac
import os
import re
from pathlib import Path
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Depends
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import Field,StrictStr
from aat_api.schemas.common import APIModel
from aat_api.errors import APIError

router=APIRouter()
bearer=HTTPBearer(auto_error=False)


def require_runtime(credentials:Annotated[HTTPAuthorizationCredentials|None,Depends(bearer)]):
    if credentials is None:raise APIError('RUNTIME_AUTH_REQUIRED','Runtime authentication required.',401)
    try:expected=Path(os.environ.get('AAT_RUNTIME_TOKEN_FILE','/secrets/backend/runtime_token')).read_text().strip()
    except OSError:raise APIError('RUNTIME_AUTH_UNAVAILABLE','Runtime authentication is unavailable.',503) from None
    if not re.fullmatch(r'[0-9a-f]{64}',expected):raise APIError('RUNTIME_AUTH_UNAVAILABLE','Runtime authentication is unavailable.',503)
    if not hmac.compare_digest(credentials.credentials.encode('utf-8'),expected.encode('ascii')):raise APIError('RUNTIME_AUTH_REJECTED','Runtime access denied.',403)


class BindRequest(APIModel):
    dag_id:StrictStr=Field(min_length=1,max_length=200)
    run_id:StrictStr=Field(min_length=1,max_length=255)
    task_id:StrictStr=Field(min_length=1,max_length=200)
    expected_revision:StrictStr=Field(min_length=1,max_length=64)
    dag_version_id:UUID|None=None


@router.post('/internal/runtime/bind',dependencies=[Depends(require_runtime)])
def bind_runtime(value:BindRequest):
    from aat_api.services.runtime_binding import bind
    return bind(value)
