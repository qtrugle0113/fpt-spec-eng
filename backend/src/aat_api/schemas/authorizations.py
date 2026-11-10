"""Explicit replacement consent; selecting a load strategy grants no authority."""
from typing import Literal
from datetime import datetime
from uuid import UUID
from pydantic import Field, StrictBool, model_validator
from .common import APIModel


class AuthorizationRequest(APIModel):
    revision_id: UUID
    physical_target_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    scope: Literal['ONCE','SCHEDULED']
    allow_empty: StrictBool
    allow_empty_acknowledged: StrictBool = False
    acknowledged: StrictBool
    confirmation_token: str = Field(min_length=1,max_length=16384)

    @model_validator(mode='after')
    def consent(self):
        if self.acknowledged is not True or self.allow_empty and self.allow_empty_acknowledged is not True:
            raise ValueError('Explicit replacement and separate empty-data acknowledgment are required.')
        return self


class AuthorizationPublic(APIModel):
    id: UUID
    revision_id: UUID
    dag_id: str
    physical_target_id: str
    scope: Literal['ONCE','SCHEDULED']
    scope_sha256: str
    schedule_sha256: str | None
    allow_empty: bool
    acknowledged_at: datetime
    allow_empty_acknowledged_at: datetime | None
    state: Literal['GRANTED','RESERVED','CONSUMED','CLOSED','REVOKED','INVALIDATED']
    revision: int
    reserved_intent_id: UUID | None
    reserved_run_id: str | None
    consumed_at: datetime | None
    closed_at: datetime | None
    revoked_at: datetime | None
    invalidated_at: datetime | None
    replacement_in_progress: bool | None


class RevokeAuthorizationRequest(APIModel):
    acknowledged: StrictBool

    @model_validator(mode='after')
    def consent(self):
        if self.acknowledged is not True:raise ValueError('Acknowledge that revocation does not cancel an admitted transaction.')
        return self
