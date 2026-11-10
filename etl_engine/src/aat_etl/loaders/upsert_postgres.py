"""PostgreSQL chosen-key ON CONFLICT entry point."""
from .batches import write_batches


def execute(dataset,session,ledger,*,conflict_keys,batch_rows=1000):
    if session.connection.dialect.name!='postgresql':raise ValueError('PostgreSQL target required.')
    return write_batches(dataset,session,ledger,strategy='UPSERT',batch_rows=batch_rows,conflict_keys=conflict_keys)
