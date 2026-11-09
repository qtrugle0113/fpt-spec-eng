import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { listConnections, newIdempotencyKey, pollOperation, requestJSON } from '../../lib/api';
import type { components } from '../../lib/api.generated';

type S = components['schemas'];
type TableItem = Extract<S['DefinitionPreview']['items'][number], { table_name: string }>;
export const tableItem = (item: S['DefinitionPreview']['items'][number]): item is TableItem =>
  'table_name' in item && typeof item.table_name === 'string';
const message = (error: unknown) => error instanceof Error ? error.message : 'The request could not be completed.';

export function ColumnList({ columns }: { columns: S['Column'][] }) {
  return <div className="table-scroll" tabIndex={0} aria-label="Column definitions"><table><thead><tr>
    <th>Order</th><th>Column</th><th>Type</th><th>Nullable</th><th>Primary key</th><th>Default</th>
  </tr></thead><tbody>{columns.map(column => <tr key={column.name}>
    <td>{column.ordinal}</td><td>{column.name}</td><td>{column.logical_type}{column.length ? `(${column.length})` : column.precision ? `(${column.precision}, ${column.scale})` : ''}</td>
    <td>{column.nullable ? 'Yes' : 'No'}</td><td>{column.primary_key_ordinal ?? '—'}</td>
    <td>{column.has_default ? JSON.stringify(column.default_literal?.value) : 'No default'}</td>
  </tr>)}</tbody></table></div>;
}

export function TableWizard({ upload, onChange }: { upload: S['DefinitionUpload'] | null; onChange: (upload: S['DefinitionUpload']) => void }) {
  const cache = useQueryClient();
  const targets = useQuery({ queryKey: ['table-targets'], queryFn: ({ signal }) => listConnections({ search: '', database_type: '', status: 'SUCCESS', offset: 0 }, signal) });
  const [file, setFile] = useState<File | null>(null);
  const [target, setTarget] = useState('');
  const [preview, setPreview] = useState<S['DefinitionPreview'] | null>(null);
  const [issues, setIssues] = useState<S['IssuePage'] | null>(null);
  const [issueOffset, setIssueOffset] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [operation, setOperation] = useState<S['Operation'] | null>(null);
  const abort = useRef<AbortController | null>(null);
  const keys = useRef(new Map<string, string>());
  const idempotency = (scope: string) => {
    let key = keys.current.get(scope);
    if (!key) { key = newIdempotencyKey(); keys.current.set(scope, key); }
    return key;
  };
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => { setPreview(null); setIssues(null); setConfirmed(false); setOperation(null); setError(''); setNotice(''); setIssueOffset(0); }, [upload?.id]);

  async function run(action: (signal: AbortSignal) => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    const controller = new AbortController(); abort.current = controller;
    try { await action(controller.signal); }
    catch (error) { if (!controller.signal.aborted) setError(message(error)); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function loadIssues(offset: number) {
    if (!upload) return;
    setIssues((await requestJSON<S['IssuePage']>(`/definition-uploads/${upload.id}/issues?limit=200&offset=${offset}`)).data); setIssueOffset(offset);
  }
  async function getPreview() {
    if (!upload) return;
    setPreview((await requestJSON<S['DefinitionPreview']>(`/definition-uploads/${upload.id}/table-preview`)).data); setConfirmed(false);
  }
  async function refreshUpload() {
    if (upload) onChange((await requestJSON<S['DefinitionUpload']>(`/definition-uploads/${upload.id}`)).data);
    await cache.invalidateQueries({ queryKey: ['table-uploads'] });
    await cache.invalidateQueries({ queryKey: ['table-jobs'] });
  }
  async function complete(started: S['Operation'], signal: AbortSignal) {
    setOperation(started);
    const result = await pollOperation(started.id, signal); setOperation(result);
    await refreshUpload();
    return result;
  }
  return <section className="connection-panel" aria-labelledby="table-wizard-title">
    <h2 id="table-wizard-title">Define tables</h2>
    <p>Download the template, describe your tables, then review the generated SQL before creating them.</p>
    <a href="/api/v1/templates/table-definition" download>Download Table Definition template</a>
    {error && <p role="alert" className="error-message">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    <form onSubmit={event => { event.preventDefault(); void run(async signal => {
      if (!file) return;
      const form = new FormData(); form.set('kind', 'TABLE'); form.set('file', file);
      const result = await requestJSON<S['DefinitionUpload']>('/definition-uploads', { method: 'POST', form, signal });
      onChange(result.data); setNotice('Workbook uploaded. Select a target and validate it.'); await cache.invalidateQueries({ queryKey: ['table-uploads'] });
    }); }}>
      <label>Table Definition workbook<input type="file" accept=".xlsx" required disabled={busy} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <button disabled={busy || !file}>Upload workbook</button>
    </form>
    {upload && <>
      <p>Selected upload: <code>{upload.id}</code> · {upload.status}</p>
      <label>Target connection<select value={target} disabled={busy || upload.status !== 'UPLOADED' && upload.status !== 'INVALID'} onChange={event => { setTarget(event.target.value); setPreview(null); setConfirmed(false); }}>
        <option value="">Select a tested connection</option>{targets.data?.items.map(connection => <option key={connection.id} value={connection.id}>{connection.code} ({connection.database_type})</option>)}
      </select></label>
      {targets.error && <p role="alert">{message(targets.error)}</p>}
      <div className="connection-actions">
        <button disabled={busy || !target || upload.status !== 'UPLOADED' && upload.status !== 'INVALID'} onClick={() => void run(async signal => {
          setPreview(null); setConfirmed(false);
          const started = (await requestJSON<S['Operation']>(`/definition-uploads/${upload.id}/validate`, { method: 'POST', body: { target_connection_id: target, expected_sha256: upload.sha256 }, key: idempotency(`validate:${upload.id}:${target}`), signal })).data;
          const result = await complete(started, signal);
          if (result.state === 'SUCCEEDED') { await getPreview(); setNotice('Workbook validated. Review every table before confirming.'); }
          else { await loadIssues(0); setError(`Validation ${result.state.toLowerCase()}. Review the issues below.`); }
        })}>Validate workbook</button>
        <button disabled={busy || upload.status !== 'VALIDATED'} onClick={() => void run(async () => getPreview())}>Refresh preview</button>
        <button disabled={busy} onClick={() => void run(async () => loadIssues(0))}>View validation issues</button>
      </div>
      {operation && <div role="status"><p>Operation: {operation.state}</p><a href={`/api/v1/operations/${operation.id}`} target="_blank" rel="noreferrer">View current operation status</a></div>}
      {issues && <section aria-label="Validation issues"><h3>Validation issues ({issues.total ?? 'unknown total'})</h3>
        {issues.items.length === 0 && <p>No validation issues.</p>}
        <ul>{issues.items.map((issue, index) => <li key={index}><strong>{issue.code}</strong>: {issue.message} {issue.sheet && `(${issue.sheet}, row ${issue.row ?? '—'}, column ${issue.column ?? '—'})`}</li>)}</ul>
        <div className="connection-actions"><button disabled={busy || issueOffset === 0} onClick={() => void run(async () => loadIssues(Math.max(0, issueOffset - 200)))}>Previous issues</button><button disabled={busy || issues.next_offset === null} onClick={() => void run(async () => loadIssues(issues.next_offset ?? 0))}>Next issues</button></div>
      </section>}
      {preview && <section aria-label="Table preview"><h3>Review tables</h3>
        <p>Confirmation expires at {new Date(preview.expires_at).toLocaleString()}. Existing tables are preserved.</p>
        {preview.items.filter(tableItem).map(item => <article key={item.id}><h4>{item.target}</h4>
          {item.warnings.map(warning => <p key={warning}>{warning}</p>)}<ColumnList columns={item.columns} />
          <p>Primary key: {item.primary_key.join(', ') || 'None'}</p><details><summary>Generated SQL</summary><pre>{item.ddl}</pre></details>
        </article>)}
        <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />I reviewed the target tables and generated SQL.</label>
        <button disabled={busy || !confirmed || preview.items.length === 0 || Date.parse(preview.expires_at) <= Date.now()} onClick={() => void run(async signal => {
          const started = (await requestJSON<S['Operation']>('/table-creation-jobs', { method: 'POST', body: { upload_id: upload.id, confirmation_token: preview.confirmation_token }, key: idempotency(`create:${preview.confirmation_token}`), signal })).data;
          const result = await complete(started, signal); setConfirmed(false);
          setNotice(result.state === 'SUCCEEDED' ? 'Table creation finished. Open job history to review each table result.' : `Table creation ${result.state.toLowerCase()}. Review individual results before taking further action.`);
          setPreview(null);
        })}>Confirm and create tables</button>
      </section>}
    </>}
    {busy && <p role="status">Processing…</p>}
  </section>;
}
