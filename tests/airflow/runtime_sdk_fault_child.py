"""Kill the first real SDK attempt during extraction; next attempt uses same binding."""
import os
from pathlib import Path
import signal
import sys
from unittest.mock import patch
from aat_etl.runtime_child import main
from aat_etl.readers.postgres import SnapshotReader

original=SnapshotReader.rows
def interrupted(reader):
    marker=Path('/tmp/aat-runtime-staging/sdk-extraction-fault-injected')
    for row in original(reader):
        yield row
        if not marker.exists():
            marker.write_text('injected')
            os.kill(os.getpid(),signal.SIGKILL)
with patch.object(SnapshotReader,'rows',interrupted):sys.exit(main())
