"""APPEND entry point; a new logical run may duplicate source rows."""
from .batches import write_batches


def execute(dataset,session,ledger,*,batch_rows=1000):
    return write_batches(dataset,session,ledger,strategy='APPEND',batch_rows=batch_rows)
