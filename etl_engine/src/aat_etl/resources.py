"""Linux RSS supervision for an ETL child; never invoke a shell or retain output."""
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import time
from collections.abc import Sequence

MEMORY_BUDGET_BYTES = 512 * 1024**2


@dataclass(frozen=True)
class SupervisionResult:
    pid: int
    exit_code: int
    reason: str
    peak_rss_bytes: int
    memory_budget_bytes: int = MEMORY_BUDGET_BYTES


def run_supervised(command: Sequence[str]) -> SupervisionResult:
    """Stop at 480 MiB, leaving headroom for sampling and interpreter cleanup.

    This is a sampled budget, not a hard allocation limit. The scheduler cgroup
    remains the final backstop. Output inherits the caller's bounded logging.
    """
    if not Path('/proc/self/statm').exists():
        raise RuntimeError('ETL RSS supervision requires Linux procfs.')
    if not command or isinstance(command, (str, bytes)):
        raise ValueError('A nonempty argument sequence is required.')
    process = subprocess.Popen(command, start_new_session=True)
    peak = 0
    reason = 'COMPLETED'
    try:
        while process.poll() is None:
            try:
                pages = int(Path(f'/proc/{process.pid}/statm').read_text().split()[1])
            except FileNotFoundError:
                break
            peak = max(peak, pages * os.sysconf('SC_PAGE_SIZE'))
            if peak >= MEMORY_BUDGET_BYTES - 32 * 1024**2:
                reason = 'MEMORY_BUDGET_EXCEEDED'
                os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(.005)
        exit_code = process.wait()
        if reason == 'COMPLETED' and exit_code:
            reason = 'PROCESS_FAILED'
        return SupervisionResult(process.pid, exit_code, reason, peak)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
