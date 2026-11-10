import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileSourcesPanel } from '../features/files/FileSourcesPanel';
import type { SourceFile } from '../lib/files';
import { requestJSON } from '../lib/api';
import { DagDefinitionWizard } from '../features/dags/DagDefinitionWizard';
import { DeploymentPanel } from '../features/dags/DeploymentPanel';
import { failure } from '../features/dags/types';
import type { DagReview, Schema } from '../features/dags/types';

export function DagBuilder() {
  const [source, setSource] = useState<SourceFile | null>(null);
  const [upload, setUpload] = useState<Schema['DefinitionUpload'] | null>(null);
  const [review, setReview] = useState<DagReview | null>(null);
  const [locked, setLocked] = useState(false);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState('');
  const history = useQuery({ queryKey: ['etl-upload-history', offset, status], queryFn: async ({ signal }) => {
    const params = new URLSearchParams({ kind: 'ETL', limit: '20', offset: String(offset) }); if (status) params.set('status', status);
    return (await requestJSON<Schema['DefinitionUploadPage']>('/definition-uploads?' + params, { signal })).data;
  }, refetchInterval: 5000 });
  return <div className="connections-page"><header className="page-heading"><div><h1>DAG Builder</h1><p>Build verified Airflow workflows from Excel definitions.</p></div></header>
    <DagDefinitionWizard upload={upload} onChange={setUpload} onReview={setReview} locked={locked} />
    <DeploymentPanel review={review} onBusy={setLocked} locked={locked} />
    <section className="connection-panel" aria-labelledby="etl-history-title"><h2 id="etl-history-title">ETL workbook history</h2>
      <label>Workbook status<select value={status} onChange={event => { setStatus(event.target.value); setOffset(0); }}><option value="">All statuses</option>{['UPLOADED', 'VALIDATING', 'VALIDATED', 'INVALID'].map(value => <option key={value}>{value}</option>)}</select></label>
      {history.isPending && <p role="status">Loading workbook history…</p>}{history.error && <p role="alert">{failure(history.error)}</p>}
      {history.data && <><div className="table-scroll" tabIndex={0} aria-label="ETL workbook history"><table><thead><tr><th>Uploaded</th><th>Workbook reference</th><th>Status</th><th>Action</th></tr></thead><tbody>{history.data.items.map(item => <tr key={item.id}><td>{item.created_at ? new Date(item.created_at).toLocaleString() : '—'}</td><td><code>{item.id}</code></td><td>{item.status}</td><td><button disabled={locked} onClick={() => setUpload(item)}>Open ETL workbook</button></td></tr>)}</tbody></table></div>
        {history.data.items.length === 0 && <p>No ETL workbooks match this filter.</p>}<div className="connection-actions"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous ETL workbooks</button><button disabled={history.data.next_offset === null} onClick={() => setOffset(history.data?.next_offset ?? 0)}>Next ETL workbooks</button><button onClick={() => void history.refetch()}>Refresh ETL history</button></div></>}
    </section>
    {source && <section className="connection-panel" aria-label="Selected ETL source"><h2>Selected ETL source</h2><p>{source.file_name} · parser revision {source.parser_revision}</p><p>Reference: <code>{source.id}</code></p><p>SHA-256: <code>{source.sha256}</code></p><button onClick={() => setSource(null)}>Clear source selection</button></section>}
    <fieldset disabled={locked} className="dag-workspace"><legend>Source file preparation</legend><FileSourcesPanel selected={source} onSelect={setSource} /></fieldset>
  </div>;
}
