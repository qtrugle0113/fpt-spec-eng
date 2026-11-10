import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router';
import { newIdempotencyKey, pollOperation, requestJSON } from '../lib/api';
import { failure, isETLItem } from '../features/dags/types';
import type { ETLItem, Schema } from '../features/dags/types';
import { RunDetails } from '../features/monitoring/RunDetails';

export function Monitoring() {
  const cache = useQueryClient();
  const [params, setParams] = useSearchParams();
  const selected = params.get('dag') ?? ''; const selectedRun = params.get('run') ?? '';
  const [search, setSearch] = useState(''); const [ownership, setOwnership] = useState('');
  const [paused, setPaused] = useState(''); const [latest, setLatest] = useState(''); const [offset, setOffset] = useState(0);
  const [runOffset, setRunOffset] = useState(0); const [state, setState] = useState('');
  const [action, setAction] = useState<'trigger' | 'pause' | 'activate'>('trigger');
  const [review, setReview] = useState<{ item: ETLItem; token: string; expires: string } | null>(null);
  const [authority, setAuthority] = useState(''); const [ack, setAck] = useState(false); const [busy, setBusy] = useState(false);
  const [authorityOffset, setAuthorityOffset] = useState(0);
  const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [operation, setOperation] = useState<Schema['Operation'] | null>(null);
  const keys = useRef(new Map<string, string>());
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);
  const listing = useQuery({ queryKey: ['monitoring-inventory', search, ownership, paused, latest, offset], queryFn: async ({ signal }) => {
    const query = new URLSearchParams({ limit: '20', offset: String(offset) }); for (const [key, value] of Object.entries({ search, ownership, paused, latest_status: latest })) if (value) query.set(key, value);
    return (await requestJSON<Schema['DAGPage']>('/dags?' + query, { signal })).data;
  }, refetchInterval: 30000, retry: false });
  const detail = useQuery({ queryKey: ['monitoring-dag', selected], enabled: Boolean(selected), queryFn: ({ signal }) => requestJSON<Schema['DAG']>('/dags/' + encodeURIComponent(selected), { signal }), refetchInterval: 15000, retry: false });
  const runs = useQuery({ queryKey: ['monitoring-runs', selected, state, runOffset], enabled: Boolean(selected), queryFn: async ({ signal }) => {
    const query = new URLSearchParams({ limit: '20', offset: String(runOffset) }); if (state) query.set('state', state);
    return (await requestJSON<Schema['RunPage']>(`/dags/${encodeURIComponent(selected)}/runs?${query}`, { signal })).data;
  }, refetchInterval: 5000, retry: false });
  const dag = detail.data?.data;
  const authorities = useQuery({ queryKey: ['monitoring-authority', dag?.definition_id, authorityOffset], enabled: dag?.ownership === 'MANAGED' && Boolean(dag.definition_id) && review?.item.config.load_strategy === 'FULL_REFRESH', queryFn: async ({ signal }) =>
    (await requestJSON<Schema['AuthorizationPage']>(`/etl-definitions/${dag?.definition_id}/replacement-authorizations?limit=200&offset=${authorityOffset}`, { signal })).data, refetchInterval: 5000 });
  useEffect(() => { abort.current?.abort(); setBusy(false); setReview(null); setAuthority(''); setAuthorityOffset(0); setAck(false); setOperation(null); setError(''); setNotice(''); setRunOffset(0); }, [selected, dag?.revision_id]);
  useEffect(() => { setAck(false); setAuthority(''); setAuthorityOffset(0); }, [action]);
  const pending = Boolean(operation && ['QUEUED', 'RUNNING', 'NEEDS_RECONCILIATION'].includes(operation.state));
  const full = review?.item.config.load_strategy === 'FULL_REFRESH';
  const scope = action === 'activate' && review?.item.config.schedule !== 'Manual' ? 'SCHEDULED' : 'ONCE';
  const needsAuthority = full && (action === 'trigger' || action === 'activate' && review?.item.config.schedule !== 'Manual');
  const available = authorities.data?.items.filter(item => item.state === 'GRANTED' && item.revision_id === dag?.revision_id && item.scope === scope) ?? [];
  const selectedAuthority = available.find(item => item.id === authority);
  const expired = !review || Date.parse(review.expires) <= Date.now();
  async function refresh() { await cache.invalidateQueries({ queryKey: ['monitoring-inventory'] }); await cache.invalidateQueries({ queryKey: ['monitoring-dag', selected] }); await cache.invalidateQueries({ queryKey: ['monitoring-runs', selected] }); await cache.invalidateQueries({ queryKey: ['monitoring-authority'] }); }
  async function work(job: (signal: AbortSignal) => Promise<void>) { const controller = new AbortController(); abort.current = controller; setBusy(true); setError(''); setNotice(''); try { await job(controller.signal); } catch (error) { if (!controller.signal.aborted) setError(failure(error)); } finally { if (!controller.signal.aborted) setBusy(false); } }
  function select(dagId: string) { setParams({ dag: dagId }); }
  return <div className="connections-page"><header className="page-heading"><div><h1>DAG Monitoring</h1><p>Read actual Airflow runs, task attempts and ETL evidence. Times are shown in UTC.</p></div><button onClick={() => void refresh()}>Refresh monitoring</button></header>
    <section className="connection-panel" aria-label="Workflow inventory"><h2>Workflows</h2><div className="monitoring-filters">
      <label>Search DAG ID<input value={search} onChange={event => { setSearch(event.target.value); setOffset(0); }} /></label>
      <label>Ownership<select value={ownership} onChange={event => { setOwnership(event.target.value); setOffset(0); }}><option value="">All ownership</option><option>MANAGED</option><option>EXTERNAL</option></select></label>
      <label>Schedule state<select value={paused} onChange={event => { setPaused(event.target.value); setOffset(0); }}><option value="">All schedule states</option><option value="true">Paused</option><option value="false">Unpaused</option></select></label>
      <label>Latest run state<select value={latest} onChange={event => { setLatest(event.target.value); setOffset(0); }}><option value="">All latest states</option>{['success', 'failed', 'running', 'queued'].map(value => <option key={value}>{value}</option>)}</select></label>
    </div>{listing.isPending && <p role="status">Loading workflow inventory…</p>}{listing.error && <p role="alert">{failure(listing.error)} Previously displayed workflows may be stale.</p>}
    {listing.data && <><div className="table-scroll" tabIndex={0} aria-label="Workflow inventory"><table><thead><tr><th>DAG ID</th><th>Ownership</th><th>Schedule</th><th>Latest run</th><th>Actions</th></tr></thead><tbody>{listing.data.items.map(item => <tr key={item.dag_id}><td>{item.dag_id}</td><td>{item.ownership}</td><td>{item.is_paused ? 'Paused' : 'Unpaused'}</td><td>{item.latest_run_status ?? 'No reported run'}</td><td><div className="connection-actions"><button onClick={() => select(item.dag_id)}>View workflow</button><a href={item.airflow_url} target="_blank" rel="noreferrer">Open Airflow</a></div></td></tr>)}</tbody></table></div>
      {listing.data.items.length === 0 && <p>No workflows match these filters.</p>}<p>Workflows: {listing.data.total ?? 'Not available'}</p><div className="connection-actions"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous workflows</button><button disabled={listing.data.next_offset == null} onClick={() => setOffset(listing.data?.next_offset ?? 0)}>Next workflows</button></div></>}
    </section>
    {selected && <section className="connection-panel" aria-label="Workflow details"><h2>{selected}</h2>{detail.isPending && <p role="status">Loading workflow details…</p>}{detail.error && <p role="alert">{failure(detail.error)} Controls are unavailable until a fresh review succeeds.</p>}
      {dag && <><p>Ownership: <strong>{dag.ownership}</strong> · {dag.is_paused ? 'Paused' : 'Unpaused'}</p><p>Schedule: {dag.schedule ?? 'Not available'} · Timezone: {dag.timezone ?? 'Not available'}</p><p>Last successful run across all history: {dag.last_successful_run?.run_id ?? (dag.last_successful_run_availability === 'AVAILABLE' ? 'No successful run reported' : 'Not available')}</p><a href={dag.airflow_url} target="_blank" rel="noreferrer">Open workflow in Airflow</a>
        {dag.ownership === 'EXTERNAL' ? <p>This external workflow is read-only. Application ETL metrics and controls are not available.</p> : <section aria-label="Workflow controls"><h3>Workflow commands</h3>
          {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
          <fieldset disabled={busy || pending || Boolean(detail.error) || !detail.data?.etag}><label>Command<select value={action} onChange={event => setAction(event.target.value as typeof action)}><option value="trigger">Trigger manual run</option><option value="pause">Pause future scheduling</option><option value="activate">Unpause / activate schedule</option></select></label>
            <button onClick={() => void work(async signal => {
              if (!dag.upload_id) return;
              const data = (await requestJSON<Schema['DefinitionPreview']>(`/definition-uploads/${dag.upload_id}/etl-preview`, { signal })).data;
              const item = data.items.filter(isETLItem).find(item => item.id === dag.revision_id);
              if (!item || !data.confirmation_token) throw new Error('The current revision could not be reviewed. Revalidate it in DAG Builder.');
              setReview({ item, token: data.confirmation_token, expires: data.expires_at }); setAck(false);
            })}>Review workflow command</button>
            {review && <><p>Target: <strong>{review.item.target}</strong> · Load policy: {review.item.config.load_strategy} · Revision: <code>{review.item.id}</code></p>
              <p>Pausing stops future scheduling; it does not cancel an active run or revoke replacement authority. A manual trigger does not activate the recurring schedule.</p>
              {dag.is_paused && action === 'trigger' && <p className="dag-warning">This workflow is paused. The manual run will remain queued until you separately review and confirm unpause. A recurring FULL_REFRESH schedule still requires SCHEDULED authority.</p>}
              {review.item.config.load_strategy === 'APPEND' && <p>APPEND can add duplicate rows on a new run.</p>}
              {needsAuthority && <><label>Replacement authority<select value={authority} onChange={event => { setAuthority(event.target.value); setAck(false); }}><option value="">Select matching {scope} authority</option>{available.map(item => <option key={item.id} value={item.id}>{item.id} · {item.scope} · empty target {item.allow_empty ? 'allowed' : 'not allowed'}</option>)}</select></label><p>Grant or revoke authority in DAG Builder. ONCE cannot activate a recurring schedule.</p>{authorities.error && <p role="alert">{failure(authorities.error)}</p>}<div className="connection-actions"><button disabled={authorityOffset === 0} onClick={() => { setAuthorityOffset(Math.max(0, authorityOffset - 200)); setAuthority(''); setAck(false); }}>Previous authority page</button><button disabled={authorities.data?.next_offset == null} onClick={() => { setAuthorityOffset(authorities.data?.next_offset ?? 0); setAuthority(''); setAck(false); }}>Next authority page</button></div></>}
              <label><input type="checkbox" checked={ack} onChange={event => setAck(event.target.checked)} />I confirm this {action === 'trigger' ? 'new manual run' : action === 'pause' ? 'pause command' : 'schedule activation'} for {selected} and the displayed revision, target and load policy.</label>
              <button disabled={!ack || expired || Boolean(needsAuthority && !selectedAuthority)} onClick={() => void work(async signal => {
                if (!detail.data?.etag) return;
                const identity = JSON.stringify([selected, dag.revision_id, action, detail.data.etag, review.token, selectedAuthority?.id]);
                let key = keys.current.get(identity); if (!key) { key = newIdempotencyKey(); keys.current.set(identity, key); }
                const body = { expected_revision: review.item.id, confirmation_token: review.token, ...(needsAuthority ? { authorization_id: selectedAuthority?.id } : {}), ...(action === 'trigger' ? {} : { is_paused: action === 'pause' }) };
                const started = (await requestJSON<Schema['Operation']>(`/dags/${encodeURIComponent(selected)}/${action === 'trigger' ? 'trigger' : 'state'}`, { method: action === 'trigger' ? 'POST' : 'PATCH', body, key, signal, ...(action === 'trigger' ? {} : { etag: detail.data.etag }) })).data;
                setOperation(started); const finished = await pollOperation(started.id, signal); if (signal.aborted) return; setOperation(finished);
                if (finished.state !== 'NEEDS_RECONCILIATION') keys.current.delete(identity);
                setAck(false); await refresh(); setNotice(`Command ${finished.state.toLowerCase()}. Command completion does not mean the ETL run succeeded.`);
              })}>Confirm workflow command</button>{expired && <p role="alert">The review expired. Review the workflow command again.</p>}</>}
          </fieldset>
          {operation && <div role="status"><p>{operation.kind}: {operation.state}</p><button disabled={busy} onClick={() => void work(async () => { const current = (await requestJSON<Schema['Operation']>('/operations/' + operation.id)).data; setOperation(current); await refresh(); })}>Refresh command status</button></div>}
        </section>}
      </>}
      <h3>Run history</h3><label>Run state<select value={state} onChange={event => { setState(event.target.value); setRunOffset(0); }}><option value="">All run states</option>{['success', 'failed', 'running', 'queued'].map(value => <option key={value}>{value}</option>)}</select></label>
      {runs.isPending && <p role="status">Loading actual run history…</p>}{runs.error && <p role="alert">{failure(runs.error)} Previously displayed runs may be stale.</p>}
      {runs.data && <><div className="table-scroll" tabIndex={0} aria-label="Run history"><table><thead><tr><th>Run ID</th><th>Type</th><th>State</th><th>Loaded rows</th><th>Action</th></tr></thead><tbody>{runs.data.items.map(run => <tr key={run.run_id}><td><code>{run.run_id}</code></td><td>{run.run_type}</td><td>{run.state}</td><td>{run.metrics?.loaded_rows ?? 'Not available'}</td><td><button onClick={() => setParams({ dag: selected, run: run.run_id })}>View run details</button></td></tr>)}</tbody></table></div>
        {runs.data.items.length === 0 && <p>No runs match this filter.</p>}<div className="connection-actions"><button disabled={runOffset === 0} onClick={() => setRunOffset(Math.max(0, runOffset - 20))}>Previous runs</button><button disabled={runs.data.next_offset == null} onClick={() => setRunOffset(runs.data?.next_offset ?? 0)}>Next runs</button></div></>}
    </section>}
    {selected && selectedRun && <RunDetails dagId={selected} runId={selectedRun} />}
  </div>;
}
