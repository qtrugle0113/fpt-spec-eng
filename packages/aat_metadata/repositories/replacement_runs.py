"""Intent/admission state policy and row helpers; caller owns transaction."""
from psycopg.rows import dict_row


def row(connection,statement,params=()):
    with connection.cursor(row_factory=dict_row) as cursor:
        return cursor.execute(statement,params).fetchone()


def transition_run_intent(state,event):
    graph={('RESERVED','submit'):'SUBMITTING',('SUBMITTING','timeout'):'NEEDS_RECONCILIATION',
           ('SUBMITTING','created_verified'):'CREATED',('NEEDS_RECONCILIATION','created_verified'):'CREATED',
           ('SUBMITTING','rejection_verified'):'REJECTED',('NEEDS_RECONCILIATION','rejection_verified'):'REJECTED'}
    try:return graph[state,event]
    except KeyError:raise ValueError('Illegal intent transition') from None


def transition_admission(state,event):
    if state not in ('ADMITTED','NEEDS_RECONCILIATION'):raise ValueError('Admission cannot be reused')
    target={'commit_verified':'COMMIT_VERIFIED','rollback_verified':'ROLLBACK_VERIFIED'}
    if event=='unknown_outcome' and state=='ADMITTED':return 'NEEDS_RECONCILIATION'
    if event in target:return target[event]
    raise ValueError('Illegal admission transition')
