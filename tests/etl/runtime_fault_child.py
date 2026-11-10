"""Isolated fault injection: die during source extraction, without finally."""
import os
import signal
import sys
from unittest.mock import patch
from aat_etl.readers.postgres import SnapshotReader
from aat_etl.runtime import run_binding
from aat_etl.runtime_child import parent_guard

parent_guard(int(sys.argv[3]))
original=SnapshotReader.rows
def interrupted(reader):
    for row in original(reader):
        yield row
        os.kill(os.getpid(),signal.SIGKILL)
with patch.object(SnapshotReader,'rows',interrupted):
    if len(sys.argv)>4 and sys.argv[4]=='publication':
        from aat_etl.runtime_state import RuntimeState
        with patch.object(SnapshotReader,'rows',original),patch.object(RuntimeState,'prepared',side_effect=lambda _:os.kill(os.getpid(),signal.SIGKILL)):
            run_binding(sys.argv[1],journal_path=sys.argv[2])
    else:run_binding(sys.argv[1],journal_path=sys.argv[2])
