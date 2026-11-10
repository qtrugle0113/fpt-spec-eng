"""One SDK task owns one supervised ETL child; no dataset enters XCom."""
import os
import sys
import tempfile
from pathlib import Path
from uuid import UUID
from .resources import run_supervised
from .runtime import bind_context,RuntimeRejected,RuntimeUnavailable


class RuntimeTaskFailed(ValueError):pass


def run_bound(binding_id,*,terminal=False):
    identity=str(UUID(str(binding_id)))
    with tempfile.TemporaryDirectory(prefix='aat-attempt-') as directory:
        journal=Path(directory)/'journal.json'
        result=run_supervised([sys.executable,'-m','aat_etl.runtime_child',identity,str(os.getpid()),str(journal)])
        if result.exit_code:
            from .runtime_lifecycle import finish_attempt
            outcome=finish_attempt(identity,proof=result,journal_path=journal,
                terminal=terminal or result.exit_code==21 or result.reason=='MEMORY_BUDGET_EXCEEDED')
            if outcome=='COMMIT_VERIFIED':return None
    if result.reason=='MEMORY_BUDGET_EXCEEDED':
        raise RuntimeTaskFailed('ETL memory budget exceeded; protected staging is retained.')
    if result.exit_code==21:
        raise RuntimeTaskFailed('ETL validation or policy failed; inspect the recorded run status.')
    if result.exit_code:
        raise RuntimeUnavailable('ETL attempt interrupted or requires reconciliation; retry the same binding.')
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
