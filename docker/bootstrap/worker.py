"""Worker bootstrap heartbeat; không xử lý Operation trước Phase2/T033."""

import json
import os
from pathlib import Path
import time

path = Path('/tmp/aat-worker-heartbeat.json')
while True:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'stage': 'bootstrap', 'pid': os.getpid(), 'timestamp': time.time()}))
    temporary.replace(path)
    time.sleep(5)
