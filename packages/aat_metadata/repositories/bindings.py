"""Immutable binding from server-verified Airflow facts; caller commits transaction."""
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
from uuid import UUID,uuid4,uuid5,NAMESPACE_URL
from types import SimpleNamespace
from .replacement_runs import row
from .authorizations import AuthorizationRepository


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def schedule_hash(config):return digest({key:config.get(key) for key in ('schedule','timezone','start_date','catchup')})


def binding_config(value):
    # ETL semantic validation belongs to the engine/backend. Metadata needs only
    # immutable identity fields and must not depend on the engine package.
    try:
        source=value['source'];target=value['target'];strategy=value['load_strategy']
        if strategy not in ('APPEND','UPSERT','FULL_REFRESH') or source['type'] not in ('DB','CSV','TXT'):raise ValueError()
        database=source['type']=='DB'
        parsed_source=SimpleNamespace(type=source['type'],connection_revision_id=UUID(source['connection_revision_id']) if database else None,
            file_id=UUID(source['file_id']) if not database else None,parser_revision=source.get('parser_revision'),file_sha256=source.get('file_sha256'))
        parsed_target=SimpleNamespace(connection_revision_id=UUID(target['connection_revision_id']),physical_target_id=target['physical_target_id'])
        if not isinstance(parsed_target.physical_target_id,str) or len(parsed_target.physical_target_id)!=64:raise ValueError()
        if not database and (type(parsed_source.parser_revision) is not int or parsed_source.parser_revision<1 or not isinstance(parsed_source.file_sha256,str) or len(parsed_source.file_sha256)!=64):raise ValueError()
        return SimpleNamespace(source=parsed_source,target=parsed_target,load_strategy=strategy)
    except (ValueError,TypeError,KeyError,AttributeError):raise ValueError('BINDING_CONFIG_INVALID') from None


@dataclass(frozen=True)
class VerifiedRun:
    dag_id:str
    run_id:str
    task_id:str
    dag_version_id:UUID
    run_type:str
    expected_revision:UUID


class BindingRepository:
    def __init__(self,connection):self.connection=connection

    @staticmethod
    def public(binding,intent):
        return dict(binding_id=binding['id'],config_revision_id=binding['etl_revision_id'],source_revision_id=binding['source_revision_id'],
            target_revision_id=binding['target_revision_id'],run_intent_id=binding['run_intent_id'],run_uuid=intent['run_uuid'],
            authorization_id=binding['authorization_id'],dataset_id=binding['dataset_id'])

    def bind(self,facts):
        c=self.connection
        if not isinstance(facts,VerifiedRun) or facts.task_id!='execute_etl' or facts.run_type not in ('manual','scheduled'):
            raise ValueError('RUNTIME_IDENTITY_REJECTED')
        version=UUID(str(facts.dag_version_id));expected=UUID(str(facts.expected_revision))
        c.execute('SELECT pg_advisory_xact_lock(718423103,hashtext(%s))',(facts.dag_id+':'+facts.run_id,))
        revision=row(c,"""SELECT r.* FROM etl_definition_revisions r JOIN etl_definitions d ON d.id=r.definition_id
            WHERE r.id=%s AND d.dag_id=%s AND d.owner='aat'""",(expected,facts.dag_id))
        if revision is None:raise ValueError('ETL_REVISION_NOT_FOUND')
        config=binding_config(revision['config_json'])
        deployed=row(c,"""SELECT * FROM dag_deployments WHERE dag_id=%s AND etl_revision_id=%s
            AND airflow_version_id=%s AND state='DEPLOYED' AND NOT reconcile_required
            ORDER BY last_verified_at DESC NULLS LAST,created_at DESC LIMIT 1""",(facts.dag_id,expected,version))
        if not deployed or deployed['revision_sha256']!=revision['config_sha256'] or deployed['expected_owner_tag']!='aat':
            raise ValueError('REVISION_MISMATCH')
        existing=row(c,'SELECT * FROM execution_bindings WHERE dag_id=%s AND airflow_run_id=%s',(facts.dag_id,facts.run_id))
        if existing:
            if existing['etl_revision_id']!=expected or existing['airflow_dag_version_id']!=str(version) or existing['task_id']!=facts.task_id or existing['airflow_run_type']!=facts.run_type:
                raise ValueError('REVISION_MISMATCH')
            intent=row(c,'SELECT * FROM run_intents WHERE id=%s',(existing['run_intent_id'],))
            return self.public(existing,intent)
        gate=row(c,'SELECT * FROM dag_admission WHERE dag_id=%s FOR UPDATE',(facts.dag_id,))
        if not gate or gate['gate_state']!='OPEN' or gate['etl_revision_id']!=expected or gate['deployment_id']!=deployed['id']:
            raise ValueError('DAG_ADMISSION_BLOCKED')
        if revision['status'] not in ('VALIDATED','DEPLOYED'):raise ValueError('DEPENDENCY_CHANGED')
        for identity in (config.source.connection_revision_id,config.target.connection_revision_id):
            if identity:
                active=row(c,"""SELECT r.id FROM connection_revisions r JOIN connections p ON p.id=r.connection_id
                    WHERE r.id=%s AND p.current_revision_id=r.id AND p.deleted_at IS NULL AND r.test_status='SUCCESS'""",(identity,))
                if not active:raise ValueError('DEPENDENCY_CHANGED')
        parser=None
        if config.source.type!='DB':
            parser=row(c,"""SELECT p.id,f.sha256,f.extension,f.validation_status,f.expires_at,p.revision,f.parser_revision FROM file_parser_revisions p
                JOIN uploaded_files f ON f.id=p.file_id WHERE p.file_id=%s AND p.revision=%s""",(config.source.file_id,config.source.parser_revision))
            if not parser or parser['extension']!=('.csv' if config.source.type=='CSV' else '.txt') or parser['sha256']!=config.source.file_sha256 or parser['validation_status']!='VALID' or parser['revision']!=parser['parser_revision'] or parser['expires_at'] and parser['expires_at']<=datetime.now(timezone.utc):
                raise ValueError('DEPENDENCY_CHANGED')
        intent=row(c,'SELECT * FROM run_intents WHERE dag_id=%s AND airflow_run_id=%s',(facts.dag_id,facts.run_id))
        authority=None
        if config.load_strategy=='FULL_REFRESH':
            if facts.run_type=='manual':
                if not intent or not intent['authorization_id']:raise ValueError('ONCE_INTENT_REQUIRED')
                authority=AuthorizationRepository(c).authorization(intent['authorization_id'])
                if authority['scope']!='ONCE' or authority['state']!='RESERVED' or authority['reserved_intent_id']!=intent['id']:raise ValueError('AUTHORIZATION_UNAVAILABLE')
            else:
                authority=row(c,"""SELECT * FROM replacement_authorizations WHERE dag_id=%s AND etl_revision_id=%s
                    AND scope='SCHEDULED' AND state='GRANTED' AND schedule_sha256=%s AND physical_target_id=%s
                    AND revoked_at IS NULL AND invalidated_at IS NULL ORDER BY created_at DESC LIMIT 1 FOR UPDATE""",
                    (facts.dag_id,expected,schedule_hash(revision['config_json']),config.target.physical_target_id))
                if authority is None:raise ValueError('SCHEDULED_AUTHORIZATION_REQUIRED')
                if intent is None:
                    intent=AuthorizationRepository(c).schedule_intent(authorization_id=authority['id'],dag_id=facts.dag_id,etl_revision_id=expected,
                        physical_target_id=config.target.physical_target_id,scope_sha256=authority['scope_sha256'],schedule_sha256=authority['schedule_sha256'],
                        run_type='scheduled',idempotency_key=uuid5(NAMESPACE_URL,'aat-scheduled:'+facts.dag_id+':'+facts.run_id),
                        request_sha256=digest([facts.dag_id,facts.run_id,str(expected)]),run_uuid=uuid4(),airflow_run_id=facts.run_id)
                    c.execute("UPDATE operations SET state='RUNNING' WHERE id=%s AND state='QUEUED'",(intent['operation_id'],))
                    c.execute("UPDATE operations SET state='SUCCEEDED' WHERE id=%s AND state='RUNNING'",(intent['operation_id'],))
            if authority['etl_revision_id']!=expected or authority['dag_id']!=facts.dag_id or authority['physical_target_id']!=config.target.physical_target_id or authority['revoked_at'] or authority['invalidated_at']:
                raise ValueError('AUTHORIZATION_SCOPE_MISMATCH')
        if intent is None:
            operation_id=uuid4();run_uuid=uuid4();intent_id=uuid4();fingerprint=digest([facts.dag_id,facts.run_id,str(expected)])
            c.execute("INSERT INTO operations(id,kind,idempotency_key,request_sha256,state) VALUES(%s,'DAG_OBSERVE',%s,%s,'SUCCEEDED')",(operation_id,str(uuid5(NAMESPACE_URL,'aat-observe:'+facts.dag_id+':'+facts.run_id)),fingerprint))
            intent=row(c,"""INSERT INTO run_intents(id,operation_id,run_uuid,dag_id,airflow_run_id,run_type,etl_revision_id,authorization_id,request_sha256,state)
                VALUES(%s,%s,%s,%s,%s,%s,%s,NULL,%s,'CREATED') RETURNING *""",(intent_id,operation_id,run_uuid,facts.dag_id,facts.run_id,facts.run_type,expected,fingerprint))
        intent=row(c,'SELECT * FROM run_intents WHERE id=%s FOR UPDATE',(intent['id'],))
        if intent['etl_revision_id']!=expected or intent['run_type']!=facts.run_type or intent['authorization_id']!=(authority['id'] if authority else None) or intent['state']=='REJECTED':
            raise ValueError('RUN_INTENT_MISMATCH')
        binding_id=uuid4()
        fingerprint=digest(dict(format='aat-binding/1',dag_id=facts.dag_id,run_id=facts.run_id,task_id=facts.task_id,dag_version_id=str(version),
            revision_id=str(expected),config_sha256=revision['config_sha256'],run_uuid=str(intent['run_uuid']),intent_id=str(intent['id']),
            source_revision_id=str(config.source.connection_revision_id) if config.source.connection_revision_id else None,
            target_revision_id=str(config.target.connection_revision_id),file_parser_id=str(parser['id']) if parser else None,
            file_sha256=config.source.file_sha256,authorization_id=str(authority['id']) if authority else None))
        binding=row(c,"""INSERT INTO execution_bindings(id,dag_id,airflow_run_id,task_id,airflow_dag_version_id,etl_revision_id,
            source_revision_id,target_revision_id,file_parser_revision,source_file_sha256,authorization_id,run_intent_id,airflow_run_type,runtime_build,binding_hash,state)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'aat-etl-engine/0.1.0',%s,'BOUND') RETURNING *""",
            (binding_id,facts.dag_id,facts.run_id,facts.task_id,str(version),expected,config.source.connection_revision_id,config.target.connection_revision_id,
             parser['id'] if parser else None,config.source.file_sha256,authority['id'] if authority else None,intent['id'],facts.run_type,fingerprint))
        if intent['state']!='CREATED':c.execute("UPDATE run_intents SET state='CREATED',last_reconciled_at=now() WHERE id=%s",(intent['id'],))
        return self.public(binding,intent)
