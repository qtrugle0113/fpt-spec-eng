"""Private Linux child entry point: fixed exit codes, no exception/data output."""
import ctypes
import os
import signal
import sys
from uuid import UUID


def parent_guard(expected_parent):
    if sys.platform!='linux':raise RuntimeError('Runtime child requires Linux.')
    # Do this in the child interpreter, never preexec_fn in a threaded SDK.
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError(ctypes.get_errno(),'Parent guard unavailable')
    if os.getppid()!=expected_parent:raise RuntimeError('Supervisor already ended.')


def main():
    try:
        identity=str(UUID(sys.argv[1]));parent_guard(int(sys.argv[2]))
        from .runtime import run_binding,RuntimeUnavailable
        from .recovery.coordinator import NeedsReconciliation
        from .loaders.session import SessionLost,TargetBusy
        from .loaders.batches import CommitUncertain
        from .loaders.full_refresh import ProjectionPending
        from .readers.database import SourceReadError
        from sqlalchemy.exc import SQLAlchemyError
        import psycopg
        try:
            run_binding(identity,journal_path=sys.argv[3] if len(sys.argv)>3 else None)
            return 0
        except (RuntimeUnavailable,NeedsReconciliation,SessionLost,TargetBusy,CommitUncertain,ProjectionPending,SourceReadError,SQLAlchemyError,psycopg.Error,OSError):
            return 20
        except ValueError:
            return 21
    except Exception:
        # SQL/driver errors can contain credentials or source values. Never
        # forward traceback/str(error) to inherited Airflow logs.
        return 20


if __name__=='__main__':sys.exit(main())
