"""Private binding handshake and direct metadata-driven execution, without FastAPI."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
from uuid import UUID
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
import psycopg
from sqlalchemy import text
from aat_metadata.repositories.base import create_app_engine
from .contracts.config import ETLConfig
from .engine import execute_database,execute_file,PreparationPins
from .readers.file_source import FileReference,FilePins
from .readers.schema import inspect_table
from .staging.quota import QuotaManager
from .loaders.replacement_admission import AdmissionAdapter
from .recovery.coordinator import NeedsReconciliation
from .runtime_state import RuntimeState
from .runtime_connections import revision_engine


class RuntimeUnavailable(RuntimeError):pass
class RuntimeRejected(ValueError):pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def bind_context(*,dag_id,run_id,task_id,expected_revision,transport=None):
    url=os.environ.get('AAT_RUNTIME_BIND_URL','http://backend:8000/internal/runtime/bind');parsed=urlsplit(url)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.path!='/internal/runtime/bind' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeRejected('Runtime bind requires the canonical private endpoint.')
    try:token=Path(os.environ.get('AAT_RUNTIME_TOKEN_FILE','/secrets/runtime/runtime_token')).read_text().strip()
    except OSError:raise RuntimeUnavailable('Runtime authentication file is unavailable.') from None
    if not re.fullmatch(r'[0-9a-f]{64}',token):raise RuntimeUnavailable('Runtime authentication file is invalid.')
    payload=dict(dag_id=dag_id,run_id=run_id,task_id=task_id,expected_revision=str(expected_revision))
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'}
    try:
        if transport is not None:
            # Optional transport exists only for isolated fault tests. Production
            # uses the standard library and adds no engine dependency baseline.
            import httpx
            with httpx.Client(transport=transport,trust_env=False,follow_redirects=False,timeout=10) as client:
                response=client.post(url,json=payload,headers=headers);status=response.status_code;data=response.content
        else:
            opener=build_opener(ProxyHandler({}),_NoRedirect())
            try:
                with opener.open(Request(url,data=json.dumps(payload).encode(),headers=headers,method='POST'),timeout=10) as response:
                    status=response.status;data=response.read(65537)
            except HTTPError as error:status=error.code;data=b'';error.close()
    except (URLError,OSError,TimeoutError):raise RuntimeUnavailable('Runtime binding could not be confirmed. Retry the same identity.') from None
    if status!=200:
        if status>=500 or status==429:raise RuntimeUnavailable('Runtime binding dependencies are unavailable.')
        raise RuntimeRejected('Runtime binding was rejected; no engine execution is permitted.')
    try:
        if len(data)>65536:raise ValueError()
        value=json.loads(data)
        required={'binding_id','config_revision_id','target_revision_id','run_intent_id','run_uuid'}
        if not isinstance(value,dict) or not required<=set(value) or set(value)-required-{'source_revision_id','authorization_id','dataset_id'}:raise ValueError()
        for name,identity in value.items():
            if identity is not None:UUID(identity)
        if UUID(value['config_revision_id'])!=UUID(str(expected_revision)):raise ValueError()
        return value
    except (ValueError,KeyError,TypeError,AttributeError):raise RuntimeRejected('Runtime binding returned an invalid immutable identity.') from None


def _connect(metadata):
    url=metadata.url
    return psycopg.connect(host=url.host,port=url.port or 5432,dbname=url.database,user=url.username,password=url.password,
        connect_timeout=3,options='-c timezone=UTC -c statement_timeout=10000 -c lock_timeout=3000')


def run_binding(binding_id,*,root=None,metadata_engine=None,journal_path=None):
    metadata=metadata_engine or create_app_engine(runtime=True)
    state=RuntimeState(metadata,binding_id,root or os.environ.get('AAT_STAGING_ROOT','/data/staging'))
    try:
        with metadata.connect().execution_options(isolation_level='AUTOCOMMIT') as ownership:
            acquired=ownership.scalar(text('SELECT pg_try_advisory_lock(718423104,hashtext(:binding))'),{'binding':str(binding_id)})
            if not acquired:raise NeedsReconciliation('Another runtime attempt still owns this binding.')
            try:
                binding=state.load();config=ETLConfig.model_validate(binding['config_json']);state.claim()
                if config.source.connection_revision_id!=binding['source_revision_id'] or config.target.connection_revision_id!=binding['target_revision_id']:
                    raise RuntimeRejected('Binding connection revisions differ from its immutable config.')
                if journal_path is not None:
                    from .runtime_journal import AttemptJournal,JournalQuota
                    quota=JournalQuota(metadata,state.root,AttemptJournal(journal_path,state.binding_id,state.owner))
                else:quota=QuotaManager(metadata,state.root)
                with ExitStack() as owned:
                    target=owned.enter_context(revision_engine(metadata,config.target.connection_revision_id))
                    prepared=state.restore(config,target)
                    dataset_id=state.dataset['id'] if prepared is not None else state.begin_dataset(config)
                    authority=AdmissionAdapter(lambda:_connect(metadata),authorization_id=binding['authorization_id'],run_intent_id=binding['run_intent_id'],
                        binding_id=state.binding_id,scope_sha256=binding['scope_sha256']) if config.load_strategy=='FULL_REFRESH' else None
                    options=dict(root=state.root,quota=quota,run_uuid=binding['run_uuid'],dataset_id=dataset_id,binding_sha256=binding['binding_hash'],
                        support_consent=False,admission=authority,project=state.project,on_prepared=state.prepared,prepared=prepared,
                        old_session_id=state.old_session_id,on_writer_owned=state.writer_owned,retry_count_override=0)
                    if config.source.type=='DB':
                        source=owned.enter_context(revision_engine(metadata,config.source.connection_revision_id)) if prepared is None else None
                        if source is not None:
                            from .engine import inspect_inputs
                            source_profile,_=inspect_inputs(config,source,target)
                            source_identity=source_profile.physical_identity
                        else:source_identity='unused-after-durable-preparation'
                        pins=PreparationPins(source_identity,binding['schema_fingerprint_source'],config.target.physical_target_id,binding['schema_fingerprint_target'])
                        return execute_database(config,source,target,pins=pins,**options)
                    with metadata.connect() as c:
                        file=c.execute(text("""SELECT f.id,f.safe_storage_key,f.bytes,p.revision,p.encoding,p.delimiter,p.header_present,p.quote_char,p.escape_char,p.null_token
                            FROM file_parser_revisions p JOIN uploaded_files f ON f.id=p.file_id WHERE p.id=:id"""),{'id':binding['file_parser_revision']}).mappings().one()
                    if not re.fullmatch(r'[0-9a-f]{32}',file['safe_storage_key']):raise RuntimeRejected('Invalid opaque source storage key.')
                    parser=dict(encoding=file['encoding'],delimiter=file['delimiter'],header_present=file['header_present'],quote_character=file['quote_char'],escape_character=file['escape_char'],null_representation=file['null_token'])
                    reference=FileReference(file['id'],file['revision'],config.source.file_sha256,file['bytes'],Path(os.environ.get('AAT_UPLOADS_ROOT','/data/uploads'))/file['safe_storage_key'],parser)
                    return execute_file(config,reference,target,pins=FilePins(binding['schema_fingerprint_source'],config.target.physical_target_id,binding['schema_fingerprint_target']),**options)
            finally:
                try:ownership.execute(text('SELECT pg_advisory_unlock(718423104,hashtext(:binding))'),{'binding':str(binding_id)})
                except Exception:ownership.invalidate()
    finally:
        if metadata_engine is None:metadata.dispose()
