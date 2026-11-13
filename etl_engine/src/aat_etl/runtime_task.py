"""One SDK task owns one supervised ETL child; no dataset enters XCom."""
import json
import os
import re
import sys
from pathlib import Path
from uuid import UUID
from .resources import ProcessExitProof,run_supervised
from .runtime import bind_context,RuntimeRejected,RuntimeUnavailable


class RuntimeTaskFailed(ValueError):pass


def _journal_location(identity):
    root=Path(os.environ.get('AAT_STAGING_ROOT','/data/staging')).absolute()
    if root.is_symlink() or not root.is_dir():
        raise RuntimeUnavailable('Persistent staging is unavailable for attempt recovery.')
    directory=root/'.aat-runtime-journals'
    if directory.is_symlink():raise RuntimeTaskFailed('The private attempt journal directory is unsafe.')
    if directory.exists() and not directory.is_dir():
        raise RuntimeTaskFailed('The private attempt journal directory is unsafe.')
    try:directory.mkdir(mode=0o700,exist_ok=True)
    except OSError:raise RuntimeUnavailable('Persistent attempt journal storage is unavailable.') from None
    if not directory.is_dir() or (os.name=='posix' and directory.stat().st_mode & 0o077):
        raise RuntimeTaskFailed('The private attempt journal directory permissions are unsafe.')
    return root,directory,directory/(identity+'.json')


def _runtime_child_active(pid,identity):
    if not Path('/proc').is_dir():return True
    try:raw=Path('/proc',str(pid),'cmdline').read_bytes()
    except FileNotFoundError:return False
    except OSError:return True
    if not raw:return False
    arguments=raw.rstrip(b'\0').split(b'\0')
    return len(arguments)>=4 and arguments[1:4]==[
        b'-m',b'aat_etl.runtime_child',identity.encode()]


def _remove_journal(path):
    part=path.with_suffix('.part')
    for candidate in (path,part):
        if candidate.is_symlink():raise RuntimeTaskFailed('An attempt journal path became unsafe.')
        try:candidate.unlink()
        except FileNotFoundError:pass


def _recover_interrupted_attempt(identity,root,journal_path,metadata_engine=None):
    directory=root/'.aat-runtime-journals'
    if journal_path.parent!=directory or journal_path.name!=identity+'.json':
        raise RuntimeTaskFailed('The interrupted attempt journal path is not canonical.')
    part=journal_path.with_suffix('.part')
    if part.exists() or part.is_symlink():
        raise RuntimeTaskFailed('An interrupted attempt journal is incomplete and requires reconciliation.')
    if not journal_path.exists():return None
    if journal_path.is_symlink() or journal_path.parent.is_symlink() or not journal_path.is_file() \
            or journal_path.stat().st_size>8192:
        raise RuntimeTaskFailed('An interrupted attempt journal is unsafe.')
    if os.name=='posix' and journal_path.stat().st_mode & 0o077:
        raise RuntimeTaskFailed('The interrupted attempt journal permissions are unsafe.')
    try:journal=json.loads(journal_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):raise RuntimeTaskFailed('An interrupted attempt journal is unreadable.') from None
    pid=journal.get('pid') if isinstance(journal,dict) else None
    owner=journal.get('owner') if isinstance(journal,dict) else None
    if not isinstance(journal,dict) or journal.get('binding_id')!=identity or type(pid) is not int \
            or not isinstance(owner,str) or not re.fullmatch(str(pid)+r':[0-9a-f]{32}',owner) \
            or type(journal.get('terminal')) is not bool:
        raise RuntimeTaskFailed('An interrupted attempt journal identity is invalid.')
    if _runtime_child_active(pid,identity):
        raise RuntimeUnavailable('The previous ETL child is still active; retry is blocked.')
    exit_code=journal.get('exit_code')
    if exit_code is not None and (type(exit_code) is not int or exit_code not in (0,20,21)):
        raise RuntimeTaskFailed('The interrupted attempt journal exit classification is invalid.')
    from .runtime_lifecycle import finish_attempt
    terminal=journal['terminal'] or exit_code==21
    outcome=finish_attempt(identity,proof=ProcessExitProof(
        pid,exit_code if exit_code is not None else -9,'SUPERVISOR_PROCESS_EXITED'),
        journal_path=journal_path,root=root,metadata_engine=metadata_engine,terminal=terminal)
    if outcome in ('RETRY_READY','ROLLBACK_VERIFIED','RESUME_VERIFIED_DATASET'):
        _remove_journal(journal_path)
        return outcome
    if outcome=='COMMIT_VERIFIED':
        _remove_journal(journal_path)
        return outcome
    if outcome=='TERMINAL_VERIFIED':
        _remove_journal(journal_path)
        return outcome
    raise RuntimeUnavailable('The interrupted ETL attempt still requires reconciliation.')


def run_bound(binding_id,*,terminal=False):
    identity=str(UUID(str(binding_id)))
    root,_,journal=_journal_location(identity)
    recovered=_recover_interrupted_attempt(identity,root,journal)
    if recovered=='COMMIT_VERIFIED':return None
    if recovered=='TERMINAL_VERIFIED':
        raise RuntimeTaskFailed('The previous ETL attempt was terminally reconciled.')
    result=run_supervised([sys.executable,'-m','aat_etl.runtime_child',identity,
                           str(os.getpid()),str(journal),str(int(terminal))])
    if result.exit_code:
        from .runtime_lifecycle import finish_attempt
        outcome=finish_attempt(identity,proof=result,journal_path=journal,
            terminal=terminal or result.exit_code==21 or result.reason=='MEMORY_BUDGET_EXCEEDED')
        if outcome in ('RETRY_READY','ROLLBACK_VERIFIED','RESUME_VERIFIED_DATASET',
                       'COMMIT_VERIFIED','TERMINAL_VERIFIED'):
            _remove_journal(journal)
        if outcome=='COMMIT_VERIFIED':return None
    if result.reason=='MEMORY_BUDGET_EXCEEDED':
        raise RuntimeTaskFailed('ETL memory budget exceeded; protected staging is retained.')
    if result.exit_code==21:
        raise RuntimeTaskFailed('ETL validation or policy failed; inspect the recorded run status.')
    if result.exit_code:
        raise RuntimeUnavailable('ETL attempt interrupted or requires reconciliation; retry the same binding.')
    _remove_journal(journal)
    return None


def execute_task(*,expected_revision):
    from airflow.sdk import get_current_context
    from airflow.exceptions import AirflowFailException
    context=get_current_context();ti=context['ti']
    try:
        binding=bind_context(dag_id=ti.dag_id,run_id=ti.run_id,task_id=ti.task_id,expected_revision=expected_revision)
        retries=getattr(context.get('task'),'retries',None)
        terminal=type(retries) is int and type(ti.try_number) is int and ti.try_number>retries
        return run_bound(binding['binding_id'],terminal=terminal)
    except (RuntimeRejected,RuntimeTaskFailed) as error:
        # Business errors must not consume multiple SDK retries. Transient and
        # uncertain outcomes propagate for the finite retry policy on the DAG.
        raise AirflowFailException(str(error)) from None
