"""MySQL UPDATE JOIN then INSERT missing chosen keys; no ambiguous upsert."""
from .batches import write_batches


def execute(dataset,session,ledger,*,conflict_keys,batch_rows=1000):
    if session.connection.dialect.name!='mysql':raise ValueError('MySQL target required.')
    return write_batches(dataset,session,ledger,strategy='UPSERT',batch_rows=batch_rows,conflict_keys=conflict_keys)
