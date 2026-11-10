"""Revision-bound DAG commands; manual runs never inherit scheduled authority."""
from uuid import UUID
from pydantic import Field,StrictBool
from .common import APIModel


class TriggerRequest(APIModel):
    expected_revision: UUID
    confirmation_token: str = Field(min_length=1,max_length=16384)
    authorization_id: UUID | None = None


class DagStateRequest(TriggerRequest):
    is_paused: StrictBool
