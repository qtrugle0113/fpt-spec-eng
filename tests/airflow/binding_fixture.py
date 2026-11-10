"""Fixed metadata identities for an isolated real-TI binding contract fixture."""
DAG_ID='aat_binding_contract'
REVISION_ID='33333333-3333-4333-8333-333333333333'
CONNECTION_REVISION_ID='44444444-4444-4444-8444-444444444444'


def configuration():
    return dict(dag_id=DAG_ID,source=dict(type='DB',connection_revision_id=CONNECTION_REVISION_ID,schema='public',table='fixture_source'),
        target=dict(connection_revision_id=CONNECTION_REVISION_ID,schema='public',table='fixture_target',physical_target_id='a'*64),
        schedule='Manual',timezone='UTC',catchup=False,is_paused=True,load_strategy='APPEND',conflict_keys=[],
        batch_size=1000,retry_count=0,retry_delay=60,mappings=[])
