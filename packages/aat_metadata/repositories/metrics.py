"""Idempotent app projection only; target marker queries belong to the engine."""
from datetime import datetime,timezone
from uuid import uuid4,UUID
from sqlalchemy.dialects.postgresql import insert
from ..models.registry import Base


def project(connection,binding_id,snapshot):
    # Accept a public structural snapshot, without importing the ETL package
    # into shared metadata or creating any dependency on writer callbacks.
    table=Base.metadata.tables['execution_metrics']
    values=dict(binding_id=UUID(str(binding_id)),extracted_rows=snapshot.extracted_rows,validated_rows=snapshot.validated_rows,
        loaded_rows=snapshot.loaded_rows,failed_rows_nullable=snapshot.failed_rows,staging_bytes_current=snapshot.staging_bytes,
        staging_bytes_peak=snapshot.staging_bytes,duration_ms=snapshot.duration_ms,phase=snapshot.phase,
        metric_updated_at=datetime.now(timezone.utc))
    statement=insert(table).values(id=uuid4(),**values)
    update={k:v for k,v in values.items() if k!='binding_id'}
    from sqlalchemy import func
    update['staging_bytes_peak']=func.greatest(table.c.staging_bytes_peak,snapshot.staging_bytes)
    connection.execute(statement.on_conflict_do_update(index_elements=['binding_id'],set_=update))
