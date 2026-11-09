"""Stored table definitions and independent target verification."""
from uuid import UUID
from fastapi import APIRouter
from aat_api.services.table_history import table_detail

router=APIRouter()


@router.get('/table-definitions/{id}')
def get_table(id:UUID):return table_detail(id)
