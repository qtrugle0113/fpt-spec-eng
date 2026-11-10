"""Read verified target evidence independently of every writer implementation."""
from dataclasses import dataclass,asdict
from uuid import UUID
from sqlalchemy import select,func


@dataclass(frozen=True)
class MetricSnapshot:
    extracted_rows:int
    validated_rows:int
    loaded_rows:int
    failed_rows:int|None=None
    staging_bytes:int=0
    duration_ms:int=0
    phase:str='PENDING'
    protected_bytes:int=0
    recovery_summary:str|None=None

    def __post_init__(self):
        for name in ('extracted_rows','validated_rows','loaded_rows','staging_bytes','duration_ms','protected_bytes'):
            value=getattr(self,name)
            if type(value) is not int or value<0:raise ValueError('Metric counts must be nonnegative integers.')
        if not self.loaded_rows<=self.validated_rows<=self.extracted_rows:raise ValueError('Metric phase counts are inconsistent.')
        if self.failed_rows is not None and (type(self.failed_rows) is not int or self.failed_rows<0):raise ValueError('Invalid failed-row count.')

    def public_dict(self):return asdict(self)


def snapshot_from_ledger(session,ledger,*,target_identity,run_uuid,dataset_sha,binding_sha,extracted_rows,validated_rows,phase,
                         staging_bytes=0,protected_bytes=0,duration_ms=0,recovery_summary=None,failed_rows=None):
    session.require_owned()
    if session.physical_identity!=target_identity:raise ValueError('Projection target identity is not locked.')
    c=session.connection;run=UUID(str(run_uuid)) if c.dialect.name=='postgresql' else str(run_uuid)
    where=(ledger.batch.c.target_identity==target_identity,ledger.batch.c.run_uuid==run,ledger.batch.c.dataset_sha==dataset_sha)
    mismatches=c.scalar(select(func.count()).select_from(ledger.batch).where(*where,ledger.batch.c.binding_sha!=binding_sha))
    if mismatches:raise ValueError('Committed marker binding differs from the pinned execution.')
    loaded=int(c.scalar(select(func.coalesce(func.sum(ledger.batch.c.row_count),0)).where(*where)))
    final=c.execute(select(ledger.run).where(ledger.run.c.target_identity==target_identity,ledger.run.c.run_uuid==run)).mappings().first()
    if final:
        if final['dataset_sha']!=dataset_sha or final['binding_sha']!=binding_sha:raise ValueError('Final commit identity differs from the pinned execution.')
        loaded=final['total_loaded_rows']
    return MetricSnapshot(extracted_rows,validated_rows,loaded,failed_rows,staging_bytes,duration_ms,phase,protected_bytes,recovery_summary)
