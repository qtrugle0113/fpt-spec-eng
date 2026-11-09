"""Typed public File Sources contract; no disk path or storage key."""
from typing import Literal
from uuid import UUID
from pydantic import Field,StrictBool
from aat_etl.readers.delimited import ParserConfig
from .common import APIModel,UTCDateTime


class PublicParser(ParserConfig):
    encoding:str=Field(min_length=1,max_length=64)


class FilePublic(APIModel):
    id:UUID
    file_name:str
    file_type:Literal['CSV','TXT']
    size:int=Field(ge=0)
    sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    parser:PublicParser
    parser_revision:int=Field(ge=1)
    revision:int=Field(ge=1)
    needs_revalidation:StrictBool
    validation_status:Literal['PENDING','VALID','INVALID']
    uploaded_at:UTCDateTime
    expires_at:UTCDateTime|None=None


class FileColumn(APIModel):
    name:str
    logical_type:Literal['text']='text'
    nullable:Literal[True]=True
    ordinal:int=Field(ge=1)
    primary_key_ordinal:None=None
    has_default:Literal[False]=False


class FilePreview(APIModel):
    columns:list[FileColumn]
    rows:list[list[str|None]]
    limited:StrictBool
    parser:PublicParser
