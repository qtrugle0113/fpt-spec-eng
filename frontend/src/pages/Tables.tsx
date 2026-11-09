import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { requestJSON } from '../lib/api';
import type { components } from '../lib/api.generated';
import { ColumnList, TableWizard } from '../features/tables/TableWizard';

type S = components['schemas'];
const message = (error: unknown) => error instanceof Error ? error.message : 'The request could not be completed.';

export function Tables() {
  const [upload, setUpload] = useState<S['DefinitionUpload'] | null>(null);
  const [uploadOffset, setUploadOffset] = useState(0);
  const [jobOffset, setJobOffset] = useState(0);
  const [status, setStatus] = useState('');
  const [jobState, setJobState] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [job, setJob] = useState<S['TableCreationJob'] | null>(null);
  const [table, setTable] = useState<S['TableDetail'] | null>(null);
  const [error, setError] = useState('');
  const [loadingDetail, setLoadingDetail] = useState(false);
  const dates = () => {
    const params = new URLSearchParams();
    if (from) params.set('from', from + 'T00:00:00Z');
    if (to) params.set('to', to + 'T23:59:59.999999Z');
    return params;
  };
  const uploads = useQuery({ queryKey: ['table-uploads', status, uploadOffset, from, to], queryFn: async ({ signal }) => {
    const params = dates(); params.set('kind', 'TABLE'); params.set('limit', '20'); params.set('offset', String(uploadOffset));
    if (status) params.set('status', status);
    return (await requestJSON<S['DefinitionUploadPage']>('/definition-uploads?' + params, { signal })).data;
  } });
  const jobs = useQuery({ queryKey: ['table-jobs', jobState, jobOffset, from, to], queryFn: async ({ signal }) => {
    const params = dates(); params.set('limit', '20'); params.set('offset', String(jobOffset));
    if (jobState) params.set('state', jobState);
    return (await requestJSON<S['TableCreationJobPage']>('/table-creation-jobs?' + params, { signal })).data;
  }, refetchInterval: 5000 });
  async function detail(kind: 'job' | 'table', id: string) {
    setLoadingDetail(true); setError('');
    try {
      if (kind === 'job') setJob((await requestJSON<S['TableCreationJob']>('/table-creation-jobs/' + encodeURIComponent(id))).data);
      else setTable((await requestJSON<S['TableDetail']>('/table-definitions/' + encodeURIComponent(id))).data);
    } catch (error) { setError(message(error)); }
    finally { setLoadingDetail(false); }
  }
  return <div className="connections-page">
    <header className="page-heading"><div><h1>Table Management</h1><p>Create tables from reviewed Excel definitions and inspect their history.</p></div></header>
    <TableWizard upload={upload} onChange={setUpload} />
    {error && <p role="alert" className="error-message">{error}</p>}
    {loadingDetail && <p role="status">Loading details…</p>}
    <section className="connection-panel" aria-labelledby="table-history-title"><h2 id="table-history-title">History</h2>
      <div className="connection-filters">
        <label>From date (UTC)<input type="date" value={from} onChange={event => { setFrom(event.target.value); setUploadOffset(0); setJobOffset(0); }} /></label>
        <label>To date (UTC)<input type="date" value={to} onChange={event => { setTo(event.target.value); setUploadOffset(0); setJobOffset(0); }} /></label>
      </div>
      <h3>Workbook uploads</h3>
      <label>Upload status<select value={status} onChange={event => { setStatus(event.target.value); setUploadOffset(0); }}><option value="">All statuses</option>{['UPLOADED','VALIDATING','VALIDATED','INVALID'].map(value => <option key={value}>{value}</option>)}</select></label>
      {uploads.error && <p role="alert">{message(uploads.error)}</p>}
      {uploads.isPending && <p role="status">Loading uploads…</p>}
      {uploads.data && <>
        <div className="table-scroll" tabIndex={0} aria-label="Workbook upload history"><table><thead><tr><th>Uploaded</th><th>Upload</th><th>Status</th><th>Actions</th></tr></thead><tbody>
          {uploads.data.items.map(item => <tr key={item.id}><td>{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td><td><code>{item.id}</code></td><td>{item.status}</td><td><button onClick={() => setUpload(item)}>Open workbook</button></td></tr>)}
        </tbody></table></div>{uploads.data.items.length === 0 && <p>No workbook uploads match these filters.</p>}
        <p>Uploads: {uploads.data.total ?? 'Unknown'}</p><div className="connection-actions"><button disabled={uploadOffset === 0} onClick={() => setUploadOffset(Math.max(0, uploadOffset - 20))}>Previous uploads</button><button disabled={uploads.data.next_offset === null} onClick={() => setUploadOffset(uploads.data?.next_offset ?? 0)}>Next uploads</button><button onClick={() => void uploads.refetch()}>Refresh uploads</button></div>
      </>}
      <h3>Table creation jobs</h3>
      <label>Job state<select value={jobState} onChange={event => { setJobState(event.target.value); setJobOffset(0); }}><option value="">All states</option>{['QUEUED','RUNNING','SUCCEEDED','PARTIALLY_SUCCEEDED','FAILED','NEEDS_RECONCILIATION'].map(value => <option key={value}>{value}</option>)}</select></label>
      {jobs.error && <p role="alert">{message(jobs.error)}</p>}
      {jobs.isPending && <p role="status">Loading jobs…</p>}
      {jobs.data && <>
        <div className="table-scroll" tabIndex={0} aria-label="Table creation job history"><table><thead><tr><th>Created</th><th>Job</th><th>State</th><th>Actions</th></tr></thead><tbody>
          {jobs.data.items.map(item => <tr key={item.id}><td>{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td><td><code>{item.id}</code></td><td>{item.state}</td><td><button disabled={loadingDetail} onClick={() => void detail('job', item.id)}>View results</button></td></tr>)}
        </tbody></table></div>{jobs.data.items.length === 0 && <p>No table creation jobs match these filters.</p>}
        <p>Jobs: {jobs.data.total ?? 'Unknown'}</p><div className="connection-actions"><button disabled={jobOffset === 0} onClick={() => setJobOffset(Math.max(0, jobOffset - 20))}>Previous jobs</button><button disabled={jobs.data.next_offset === null} onClick={() => setJobOffset(jobs.data?.next_offset ?? 0)}>Next jobs</button><button onClick={() => void jobs.refetch()}>Refresh jobs</button></div>
      </>}
    </section>
    {job && <section className="connection-panel" aria-label="Job results"><h2>Job results</h2><p><code>{job.id}</code> · {job.state}</p>
      <button disabled={loadingDetail} onClick={() => void detail('job', job.id)}>Refresh job results</button>
      <p>Review each table result. UNKNOWN requires reconciliation before another attempt; a matching live schema does not establish who created it.</p>
      {job.results.map(result => <article key={result.table_id ?? result.table_name}><h3>{result.table_name}</h3><p>{result.state}</p>
        <p>Started: {result.started_at ?? '—'} · Finished: {result.finished_at ?? '—'}</p>
        {result.error && <p role="alert">{result.error.message}</p>}
        <details><summary>Executed SQL</summary><pre>{result.ddl ?? 'No SQL recorded.'}</pre></details>
        {result.table_id && <button disabled={loadingDetail} onClick={() => void detail('table', result.table_id!)}>View table details</button>}
      </article>)}
    </section>}
    {table && <section className="connection-panel" aria-label="Table details"><h2>{table.target_schema}.{table.table_name}</h2>
      <h3>Stored definition</h3><ColumnList columns={table.columns} /><p>Primary key: {table.primary_key.join(', ') || 'None'}</p>
      <h3>Live database verification: {table.verification_status}</h3><p>{table.unavailable_reason ?? (table.verified_at ? `Verified at ${new Date(table.verified_at).toLocaleString()}` : 'No live verification available.')}</p>
      {table.actual_columns && <ColumnList columns={table.actual_columns} />}
      <button disabled={loadingDetail} onClick={() => void detail('table', table.id)}>Verify table again</button>
    </section>}
  </div>;
}
