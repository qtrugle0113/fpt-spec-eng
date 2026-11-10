import { useCallback, useEffect, useRef, useState } from 'react';
import { newIdempotencyKey, pollOperation, requestJSON } from '../../lib/api';
import { AuthorizationPanel } from './AuthorizationPanel';
import { failure } from './types';
import type { DagReview, Schema } from './types';

type Result = { data: Schema['Deployment']; etag: string | null };
type Choice = { once?: string; scheduled?: string };

export function DeploymentPanel({ review, onBusy, locked = false }: { review: DagReview | null; onBusy: (busy: boolean) => void; locked?: boolean }) {
  const [confirmed, setConfirmed] = useState(false);
  const [supportAck, setSupportAck] = useState(false);
  const [active, setBusy] = useState(false);
  const busy = active || locked;
  const [operation, setOperation] = useState<Schema['Operation'] | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [controlPreview, setControlPreview] = useState<Schema['DefinitionPreview'] | null>(null);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const selectAuthority = useCallback((authority: Schema['Authorization']) => setChoices(previous => {
    const field = authority.scope === 'ONCE' ? 'once' : 'scheduled';
    const current = previous[authority.revision_id] ?? {};
    if (authority.state !== 'GRANTED' && current[field] !== authority.id) return previous;
    const value = authority.state === 'GRANTED' ? authority.id : undefined;
    if (current[field] === value) return previous;
    return { ...previous, [authority.revision_id]: { ...current, [field]: value } };
  }), []);
  const [stateAck, setStateAck] = useState<Record<string, boolean>>({});
  const [runAck, setRunAck] = useState<Record<string, boolean>>({});
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const keys = useRef(new Map<string, string>());
  const abort = useRef<AbortController | null>(null);
  const lastOperation = useRef<Schema['Operation'] | null>(null);
  const key = (scope: string) => { let value = keys.current.get(scope); if (!value) { value = newIdempotencyKey(); keys.current.set(scope, value); } return value; };
  const remember = (value: Schema['Operation']) => { setOperation(value); lastOperation.current = value; };
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => { setConfirmed(false); setSupportAck(false); setControlPreview(null); setChoices({}); setStateAck({}); setRunAck({}); }, [review?.preview.confirmation_token]);
  useEffect(() => { setResults([]); setOperation(null); lastOperation.current = null; setError(''); setNotice(''); }, [review?.upload.id]);
  const items = review?.items.filter(item => review.selected.includes(item.config.dag_id)) ?? [];
  const preview = controlPreview ?? review?.preview;
  const expired = !preview || Date.parse(preview.expires_at) <= Date.now();
  const deployExpired = !review || Date.parse(review.preview.expires_at) <= Date.now();
  const pending = operation && ['QUEUED', 'RUNNING', 'NEEDS_RECONCILIATION'].includes(operation.state);
  const supportNeeded = items.some(item => item.support_ddl.length > 0);
  async function loadResults(links: string[], signal?: AbortSignal) {
    const paths = links.filter(link => link.startsWith('/api/v1/dag-deployments/'));
    if (paths.length) setResults(await Promise.all(paths.map(link => requestJSON<Schema['Deployment']>(link.slice('/api/v1'.length), { signal }))));
  }
  async function refreshResults(signal?: AbortSignal) {
    if (results.length) await loadResults(results.map(result => '/api/v1/dag-deployments/' + result.data.id), signal);
  }
  async function refreshControls(signal?: AbortSignal) {
    if (!review) return;
    setControlPreview((await requestJSON<Schema['DefinitionPreview']>(`/definition-uploads/${review.upload.id}/etl-preview`, { signal })).data);
  }
  async function complete(started: Schema['Operation'], signal: AbortSignal) {
    remember(started);
    try {
      const finished = await pollOperation(started.id, signal); remember(finished);
      await loadResults(finished.result_links ?? [], signal); return finished;
    } catch (error) { await loadResults(started.result_links ?? [], signal); throw error; }
  }
  async function run(action: (signal: AbortSignal) => Promise<void>) {
    const controller = new AbortController(); abort.current = controller;
    setBusy(true); onBusy(true); setError(''); setNotice('');
    try { await action(controller.signal); }
    catch (error) { if (!controller.signal.aborted) setError(failure(error)); }
    finally { if (!controller.signal.aborted) { setBusy(false); onBusy(false); } }
  }
  const currentToken = preview?.confirmation_token;
  return <section className="connection-panel" aria-labelledby="deployment-title"><h2 id="deployment-title">Confirm and deploy</h2>
    <p>Registration in Airflow is verified before deployment succeeds. New workflows remain paused until activation is confirmed. FULL_REFRESH authority is managed separately.</p>
    <p>A manual trigger does not unpause a workflow. A run submitted while paused remains queued until unpause is separately confirmed.</p>
    {error && <p role="alert" className="error-message">{error}</p>}{notice && <p role="status">{notice}</p>}
    {!review && <p>Upload and validate an ETL workbook to review a deployment.</p>}
    {review && <><p>Selected workflows: {items.map(item => item.config.dag_id).join(', ') || 'None'}</p>
      {!review.ready && <p>Complete the schedules and load review before confirming deployment.</p>}
      {items.map(item => <details key={item.id}><summary>{item.config.dag_id} · {item.target} · {item.config.load_strategy}</summary>{item.warnings.map(warning => <p key={warning}>{warning}</p>)}{item.support_ddl.length > 0 && <><h3>Support object SQL</h3><pre>{item.support_ddl.join('\n\n')}</pre></>}</details>)}
      <fieldset disabled={busy || Boolean(pending) || !review.ready || items.length === 0}>
        <legend>Deployment confirmation</legend>
        {supportNeeded && <label><input type="checkbox" checked={supportAck} onChange={event => setSupportAck(event.target.checked)} />I reviewed and authorize creating the displayed support objects in the target database.</label>}
        <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />I reviewed every selected source, target, mapping, schedule and load policy. Deploy these exact revisions.</label>
        <button disabled={!confirmed || supportNeeded && !supportAck || deployExpired} onClick={() => void run(async signal => {
          const scope = `deploy:${review.upload.id}:${[...review.selected].sort().join(',')}:${review.preview.confirmation_token}:${supportAck}`;
          const body: Schema['DeployRequest'] = { upload_id: review.upload.id, dag_ids: review.selected, confirmation_token: review.preview.confirmation_token, support_objects_acknowledged: supportAck };
          const started = (await requestJSON<Schema['Operation']>('/dag-deployments', { method: 'POST', body, key: key(scope), signal })).data;
          const finished = await complete(started, signal); setConfirmed(false); setSupportAck(false);
          if (finished.state !== 'NEEDS_RECONCILIATION') keys.current.delete(scope);
          setNotice(`Deployment ${finished.state.toLowerCase()}. Review each workflow result below.`);
          if (finished.state === 'SUCCEEDED' || finished.state === 'PARTIALLY_SUCCEEDED') await refreshControls(signal);
        })}>Confirm and deploy workflows</button>
      </fieldset>
      {expired && <p role="alert">The review has expired. Refresh the ETL preview before confirming a new action.</p>}
      {items.map(item => <AuthorizationPanel key={item.id} item={item} confirmationToken={currentToken ?? ''} disabled={busy || expired} onBusy={onBusy} onSelect={selectAuthority} />)}
    </>}
    {operation && <div className="dag-operation" role="status"><p>{operation.kind}: <strong>{operation.state}</strong>{operation.progress?.total ? ` · ${operation.progress.completed ?? 0}/${operation.progress.total} processed` : ''}</p>
      <p>Command completion does not mean the ETL run has completed.</p><a href={`/api/v1/operations/${operation.id}`} target="_blank" rel="noreferrer">View saved operation status</a>
      <button disabled={busy} onClick={() => void run(async signal => { if (!lastOperation.current) return; await complete(lastOperation.current, signal); await refreshResults(signal); })}>Refresh saved operation</button>
    </div>}
    {results.map(result => {
      const deployed = result.data;
      const item = review?.items.find(item => item.id === deployed.revision && item.config.dag_id === deployed.dag_id);
      const canControl = deployed.state === 'DEPLOYED' && !deployed.reconcile_required && Boolean(item) && !expired && Boolean(result.etag);
      const full = item?.config.load_strategy === 'FULL_REFRESH';
      const needsScheduleAuthority = full && item?.config.schedule !== 'Manual';
      const selected = choices[deployed.revision] ?? {};
      async function control(isPaused: boolean, signal: AbortSignal) {
        if (!item || !currentToken || !result.etag) return;
        const scope = `state:${deployed.id}:${result.etag}:${isPaused}:${currentToken}`;
        const body: Schema['DagStateRequest'] = { expected_revision: deployed.revision, confirmation_token: currentToken, is_paused: isPaused, ...(!isPaused && needsScheduleAuthority ? { authorization_id: selected.scheduled } : {}) };
        const started = (await requestJSON<Schema['Operation']>(`/dags/${encodeURIComponent(deployed.dag_id)}/state`, { method: 'PATCH', body, etag: result.etag, key: key(scope), signal })).data;
        const finished = await complete(started, signal); setStateAck(previous => ({ ...previous, [deployed.id]: false }));
        if (finished.state !== 'NEEDS_RECONCILIATION') keys.current.delete(scope);
        await refreshResults(signal); setNotice(`State command ${finished.state.toLowerCase()}. Pause does not cancel an active run.`);
      }
      return <article className="dag-result" key={deployed.id} aria-label={'Deployment result for ' + deployed.dag_id}><h3>{deployed.dag_id}</h3><p>Registration: <strong>{deployed.state}</strong>{deployed.reconcile_required ? ' · reconciliation required' : ''}</p>
        {deployed.error_summary && <p role="alert">{deployed.error_summary}</p>}
        <details><summary>Deployment evidence</summary><p>Revision: <code>{deployed.revision}</code></p><p>Airflow version: {deployed.airflow_version_id ?? 'Not verified'}</p><p>Last verified: {deployed.last_verified_at ? new Date(deployed.last_verified_at).toLocaleString() : 'Not verified'}</p></details>
        {deployed.state === 'DEPLOYED' && deployed.airflow_url && <a href={deployed.airflow_url} target="_blank" rel="noreferrer">Open Airflow</a>}
        <div className="connection-actions"><button disabled={busy} onClick={() => void run(refreshResults)}>Refresh deployment results</button><button disabled={busy || !review} onClick={() => void run(refreshControls)}>Refresh action review</button>
          {deployed.reconcile_required && <button disabled={busy} onClick={() => void run(async signal => {
            const scope = 'reconcile:' + deployed.id;
            const started = (await requestJSON<Schema['Operation']>(`/dag-deployments/${deployed.id}/reconcile`, { method: 'POST', key: key(scope), signal })).data;
            await complete(started, signal); keys.current.delete(scope); await refreshResults(signal);
          })}>Reconcile this deployment</button>}</div>
        {deployed.state === 'PARSE_ERROR' || deployed.state === 'DEPLOYMENT_FAILED' ? <p>Review the error, correct or revalidate the workbook, then explicitly confirm a new deployment. A failed deployment is not automatically retried.</p> : null}
        {deployed.state === 'DEPLOYED' && <fieldset disabled={busy || !canControl || Boolean(pending)}><legend>Workflow commands</legend>
          {full && <p>Selected ONCE authority: {selected.once ?? 'None'}. Selected SCHEDULED authority: {selected.scheduled ?? 'None'}.</p>}
          <label><input type="checkbox" checked={stateAck[deployed.id] ?? false} onChange={event => setStateAck(previous => ({ ...previous, [deployed.id]: event.target.checked }))} />I confirm the schedule state change for {deployed.dag_id}. Pausing only stops future scheduling; it does not cancel runs or revoke authority.</label>
          <div className="connection-actions"><button disabled={!stateAck[deployed.id] || Boolean(needsScheduleAuthority && !selected.scheduled)} onClick={() => void run(signal => control(false, signal))}>{item?.config.schedule === 'Manual' ? 'Enable manual execution' : 'Activate schedule'}</button><button disabled={!stateAck[deployed.id]} onClick={() => void run(signal => control(true, signal))}>Pause future scheduling</button></div>
          <label><input type="checkbox" checked={runAck[deployed.id] ?? false} onChange={event => setRunAck(previous => ({ ...previous, [deployed.id]: event.target.checked }))} />I confirm a new manual run for {deployed.dag_id}.{item?.config.load_strategy === 'APPEND' ? ' APPEND can add duplicate records on a new run.' : full ? ` This will replace all rows in ${item?.target} using a new ONCE reservation.` : ' Existing keys may be updated.'}</label>
          <button disabled={!runAck[deployed.id] || Boolean(full && !selected.once)} onClick={() => void run(async signal => {
            if (!currentToken) return;
            const scope = `trigger:${deployed.id}:${currentToken}:${selected.once ?? 'none'}`;
            const body: Schema['TriggerRequest'] = { expected_revision: deployed.revision, confirmation_token: currentToken, ...(full ? { authorization_id: selected.once } : {}) };
            const started = (await requestJSON<Schema['Operation']>(`/dags/${encodeURIComponent(deployed.dag_id)}/trigger`, { method: 'POST', body, key: key(scope), signal })).data;
            const finished = await complete(started, signal); setRunAck(previous => ({ ...previous, [deployed.id]: false }));
            if (finished.state !== 'NEEDS_RECONCILIATION') keys.current.delete(scope);
            setNotice(`Manual trigger ${finished.state.toLowerCase()}. Inspect the actual run in Airflow or Monitoring; this command status is not the ETL result.`);
          })}>Run workflow now</button>
        </fieldset>}
      </article>;
    })}
    {busy && <p role="status">Waiting for the server-confirmed outcome…</p>}
  </section>;
}
