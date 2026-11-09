"""Definition upload requests and safe public projections."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field,StrictInt
from .common import APIModel


class UploadPublic(APIModel):
    id: UUID
    kind: Literal['TABLE', 'ETL']
    sha256: str
    template_version: str | None = None
    status: Literal['UPLOADED', 'VALIDATING', 'VALIDATED', 'INVALID']
    created_at: datetime


class ValidationRequest(APIModel):
    target_connection_id: UUID | None = None
    expected_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    parser_revision: StrictInt | None = Field(default=None, ge=1)


class TableCreateRequest(APIModel):
    upload_id: UUID
    confirmation_token: str = Field(max_length=16384)
