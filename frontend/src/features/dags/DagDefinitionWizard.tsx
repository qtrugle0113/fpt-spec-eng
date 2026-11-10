import { useEffect, useRef, useState } from 'react';
import { newIdempotencyKey, pollOperation, requestJSON } from '../../lib/api';
import { ColumnList } from '../tables/TableWizard';
import { failure, isETLItem } from './types';
import type { DagReview, ETLItem, Schema } from './types';

function MappingReview({ item }: { item: ETLItem }) {
  const config = item.config;
  return <article className="dag-review-card"><h4>{config.dag_id}</h4>
    <dl className="dag-facts"><dt>Source</dt><dd>{config.source.type === 'DB' ? `${config.source.schema}.${config.source.table}` : `${config.source.type} file ${config.source.file_id} · parser revision ${config.source.parser_revision}`}</dd><dt>Target</dt><dd>{item.target}</dd></dl>
    {item.columns && <ColumnList columns={item.columns} />}
    <p>Primary key: {item.primary_key?.join(', ') || 'None'}</p>
    {config.mappings.filter(mapping => mapping.enabled).length === 0 ? <p>Implicit mapping: match exact column names and compatible types.</p> : <div className="table-scroll" tabIndex={0} aria-label={'Column mappings for ' + config.dag_id}><table><thead><tr><th>Source column</th><th>Target column</th><th>Transformation</th><th>Typed default</th><th>Enabled</th></tr></thead><tbody>
      {config.mappings.map((mapping, index) => <tr key={index}><td>{mapping.source_column ?? 'Constant'}</td><td>{mapping.target_column}</td><td>{mapping.transformation}</td><td>{mapping.default_literal ? `${mapping.default_literal.logical_type}: ${JSON.stringify(mapping.default_literal.value)}` : '—'}</td><td>{mapping.enabled ? 'Yes' : 'No'}</td></tr>)}
    </tbody></table></div>}
    {config.filter && <details><summary>Validated source filter</summary><pre>{JSON.stringify(config.filter, null, 2)}</pre></details>}
  </article>;
}

export function DagDefinitionWizard({ upload, onChange, onReview, locked = false }: { upload: Schema['DefinitionUpload'] | null; onChange: (value: Schema['DefinitionUpload']) => void; onReview: (review: DagReview | null) => void; locked?: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Schema['DefinitionPreview'] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [step, setStep] = useState(1);
  const [issues, setIssues] = useState<Schema['IssuePage'] | null>(null);
  const [issueOffset, setIssueOffset] = useState(0);
  const [operation, setOperation] = useState<Schema['Operation'] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const abort = useRef<AbortController | null>(null);
  const keys = useRef(new Map<string, string>());
  const key = (scope: string) => { let value = keys.current.get(scope); if (!value) { value = newIdempotencyKey(); keys.current.set(scope, value); } return value; };
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => { abort.current?.abort(); setBusy(false); setPreview(null); setSelected([]); setIssues(null); setOperation(null); setStep(1); setError(''); setNotice(''); onReview(null); }, [upload?.id]);
  useEffect(() => {
    onReview(upload && preview ? { upload, preview, items: preview.items.filter(isETLItem), selected, ready: step === 3 } : null);
  }, [upload, preview, selected, step, onReview]);

  async function run(action: (signal: AbortSignal) => Promise<void>) {
    const controller = new AbortController(); abort.current = controller; setBusy(true); setError(''); setNotice('');
    try { await action(controller.signal); }
    catch (error) { if (!controller.signal.aborted) setError(failure(error)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function loadIssues(offset: number, signal?: AbortSignal) {
    if (!upload) return;
    setIssues((await requestJSON<Schema['IssuePage']>(`/definition-uploads/${upload.id}/issues?limit=200&offset=${offset}`, { signal })).data); setIssueOffset(offset);
  }
  async function loadPreview(signal?: AbortSignal) {
    if (!upload) return;
    const current = (await requestJSON<Schema['DefinitionPreview']>(`/definition-uploads/${upload.id}/etl-preview`, { signal })).data;
    setPreview(current); setSelected(current.items.filter(isETLItem).map(item => item.config.dag_id)); setStep(2);
  }
  const items = preview?.items.filter(isETLItem) ?? [];
  return <section className="connection-panel" aria-labelledby="dag-definition-title">
    <fieldset disabled={locked} className="dag-workspace"><legend>ETL workbook</legend>
    <h2 id="dag-definition-title">Define your workflows</h2>
    <p>Use an Excel Definition workbook to set sources, mappings, schedules and load policies. Edit the workbook and upload a new revision to change these values.</p>
    <a href="/api/v1/templates/etl-definition" download>Download ETL Definition template</a>
    <nav className="connection-actions dag-steps" aria-label="Workflow definition steps">{['Upload and validate', 'Sources and mappings', 'Schedules and load'].map((label, index) => <button key={label} type="button" aria-current={step === index + 1 ? 'step' : undefined} disabled={busy || index > 0 && !preview} onClick={() => setStep(index + 1)}>{index + 1}. {label}</button>)}</nav>
    {error && <p role="alert" className="error-message">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {step === 1 && <>
      <form onSubmit={event => { event.preventDefault(); void run(async signal => {
        if (!file) return;
        const form = new FormData(); form.set('kind', 'ETL'); form.set('file', file);
        const result = await requestJSON<Schema['DefinitionUpload']>('/definition-uploads', { method: 'POST', form, signal });
        onChange(result.data); setNotice('Workbook uploaded. Validate it before reviewing the workflows.');
      }); }}><label>ETL Definition workbook<input type="file" accept=".xlsx" required disabled={busy} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label><button disabled={busy || !file}>Upload ETL workbook</button></form>
      {upload && <><p>Workbook status: <strong>{upload.status}</strong></p><details><summary>Workbook reference</summary><code>{upload.id}</code><p>SHA-256: <code>{upload.sha256}</code></p></details>
        <div className="connection-actions"><button disabled={busy || !['UPLOADED', 'INVALID'].includes(upload.status)} onClick={() => void run(async signal => {
          setPreview(null); setSelected([]); onReview(null);
          const scope = `validate:${upload.id}:${upload.sha256}`;
          const started = (await requestJSON<Schema['Operation']>(`/definition-uploads/${upload.id}/validate`, { method: 'POST', key: key(scope), body: { expected_sha256: upload.sha256 }, signal })).data;
          setOperation(started); const result = await pollOperation(started.id, signal); setOperation(result);
          if (result.state === 'SUCCEEDED' || result.state === 'FAILED') keys.current.delete(scope);
          onChange((await requestJSON<Schema['DefinitionUpload']>(`/definition-uploads/${upload.id}`, { signal })).data);
          if (result.state === 'SUCCEEDED') { await loadPreview(signal); setIssues(null); }
          else { await loadIssues(0, signal); setError(`Validation ${result.state.toLowerCase()}. Review the workbook issues before continuing.`); }
        })}>Validate ETL workbook</button>
          <button disabled={busy} onClick={() => void run(async signal => onChange((await requestJSON<Schema['DefinitionUpload']>(`/definition-uploads/${upload.id}`, { signal })).data))}>Refresh workbook status</button>
          <button disabled={busy || upload.status !== 'VALIDATED'} onClick={() => void run(loadPreview)}>Review validated workbook</button>
          <button disabled={busy} onClick={() => void run(signal => loadIssues(0, signal))}>View ETL validation issues</button></div>
      </>}
    </>}
    {operation && <p role="status">Validation operation: {operation.state}</p>}
    {issues && <section aria-label="ETL validation issues"><h3>Workbook issues ({issues.total ?? 'unknown total'})</h3>
      {issues.items.length === 0 && <p>No validation issues.</p>}<ul>{issues.items.map((issue, index) => <li key={index}><strong>{issue.code}</strong>: {issue.message}{issue.sheet && ` — ${issue.sheet}, row ${issue.row ?? '—'}, column ${issue.column ?? '—'}`}</li>)}</ul>
      <div className="connection-actions"><button disabled={busy || issueOffset === 0} onClick={() => void run(signal => loadIssues(Math.max(0, issueOffset - 200), signal))}>Previous ETL issues</button><button disabled={busy || issues.next_offset === null} onClick={() => void run(signal => loadIssues(issues.next_offset ?? 0, signal))}>Next ETL issues</button></div>
    </section>}
    {preview && step > 1 && <>
      <p>Review expires at {new Date(preview.expires_at).toLocaleString()}. Refresh the preview after any dependency changes.</p>
      <fieldset disabled={busy}><legend>Select workflows to deploy ({selected.length}/{items.length})</legend>{items.map(item => <label className="file-header-check" key={item.id}><input type="checkbox" checked={selected.includes(item.config.dag_id)} onChange={event => setSelected(previous => event.target.checked ? [...previous, item.config.dag_id] : previous.filter(dag => dag !== item.config.dag_id))} />{item.config.dag_id}</label>)}</fieldset>
      {items.filter(item => selected.includes(item.config.dag_id)).map(item => step === 2 ? <MappingReview key={item.id} item={item} /> : <article className="dag-review-card" key={item.id}><h3>{item.config.dag_id}</h3>
        <dl className="dag-facts"><dt>Schedule</dt><dd>{item.config.schedule}</dd><dt>Timezone</dt><dd>{item.config.timezone}</dd><dt>Start date</dt><dd>{item.config.start_date ?? 'Not scheduled'}</dd><dt>Catchup</dt><dd>{item.config.catchup ? 'Enabled — past intervals may run' : 'Disabled'}</dd><dt>Load policy</dt><dd>{item.config.load_strategy}</dd><dt>Conflict keys</dt><dd>{item.config.conflict_keys.join(', ') || 'None'}</dd><dt>Batch size</dt><dd>{item.config.batch_size}</dd><dt>Retries</dt><dd>{item.config.retry_count}, delay {item.config.retry_delay} seconds</dd><dt>Initial state</dt><dd>Paused until activation is confirmed</dd></dl>
        {item.warnings.map(warning => <p key={warning} className="dag-warning">{warning}</p>)}
      </article>)}
      <div className="connection-actions"><button disabled={busy} onClick={() => void run(loadPreview)}>Refresh ETL preview</button>{step === 2 && <button disabled={selected.length === 0} onClick={() => setStep(3)}>Review schedules and load policies</button>}</div>
    </>}
    {busy && <p role="status">Processing workbook…</p>}
    </fieldset>
  </section>;
}
