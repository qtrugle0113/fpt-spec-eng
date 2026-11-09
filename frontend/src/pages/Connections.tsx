import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ConnectionForm } from '../features/connections/ConnectionForm';
import { APIError, createConnection, deleteConnection, getConnection, listConnections, patchConnection, testConnection,
  type Connection, type ConnectionCreate } from '../lib/api';

const statusLabel = (status?: string) => ({ SUCCESS: 'Verified', FAILED: 'Failed', UNTESTED: 'Not tested' }[status ?? ''] ?? 'Not tested');
const failureMessage = (error: unknown) => error instanceof APIError
  ? error.status === 412 ? 'This connection changed. Close the form and refresh its details before saving again.' : error.message
  : 'The service could not complete the request. Try again.';

function DeleteConfirmation({ connection, busy, onCancel, onDelete }: { connection: Connection; busy: boolean; onCancel: () => void; onDelete: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} aria-labelledby="delete-connection-title" onCancel={(event) => { event.preventDefault(); if (!busy) onCancel(); }}>
    <h2 id="delete-connection-title">Delete connection</h2>
    <p>Remove <strong>{connection.code}</strong> from this workspace? Its saved configuration will no longer be available for new work.</p>
    <div className="connection-actions"><button type="button" autoFocus disabled={busy} onClick={onCancel}>Cancel</button><button type="button" className="danger-button" disabled={busy} onClick={onDelete}>{busy ? 'Deleting…' : 'Confirm delete'}</button></div>
  </dialog>;
}

export function Connections() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ search: '', database_type: '', status: '', offset: 0 });
  const query = useQuery({ queryKey: ['connections', filters], queryFn: ({ signal }) => listConnections(filters, signal) });
  const [selected, setSelected] = useState<{ data: Connection; etag: string | null } | null>(null);
  const [editor, setEditor] = useState<'create' | 'edit' | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const busy = pending !== null;
  const refreshList = () => queryClient.invalidateQueries({ queryKey: ['connections'] });

  async function select(id: string) {
    setPending('details'); setError(''); setNotice(''); setEditor(null);
    try { setSelected(await getConnection(id)); } catch (error) { setError(failureMessage(error)); }
    finally { setPending(null); }
  }
  async function save(value: ConnectionCreate) {
    setPending('save'); setError(''); setNotice('');
    try {
      const result = editor === 'edit' && selected
        ? await patchConnection(selected.data.id, selected.etag ?? '"' + selected.data.revision + '"', value)
        : await createConnection(value);
      setSelected(result); setEditor(null); setNotice('Connection saved.'); await refreshList();
    } catch (error) { setError(failureMessage(error)); }
    finally { setPending(null); }
  }
  async function test() {
    if (!selected) return;
    setPending('test'); setError(''); setNotice('');
    try {
      const result = await testConnection(selected.data.id);
      setSelected(await getConnection(selected.data.id)); await refreshList();
      if (result.data.status === 'SUCCESS') setNotice('Connection verified.');
      else setError(result.data.error?.message ?? 'Connection test failed.');
    } catch (error) { setError(failureMessage(error)); }
    finally { setPending(null); }
  }
  async function remove() {
    if (!selected) return;
    setPending('delete'); setError(''); setNotice('');
    try {
      await deleteConnection(selected.data.id, selected.etag ?? '"' + selected.data.revision + '"');
      setConfirmDelete(false); setSelected(null); setNotice('Connection deleted.'); await refreshList();
    } catch (error) { setConfirmDelete(false); setError(failureMessage(error)); }
    finally { setPending(null); }
  }

  return <section className="workspace-page" aria-labelledby="page-title">
    <p className="eyebrow">DATABASE CONNECTIONS</p>
    <div className="connection-heading"><div><h1 id="page-title">Connections</h1><p className="page-description">Manage and verify the databases your workflows use.</p></div>
      <button className="primary-button" disabled={busy} onClick={() => { setEditor('create'); setSelected(null); setError(''); setNotice(''); }}>Add connection</button></div>
    {error && <div className="connection-error" role="alert">{error}</div>}
    {notice && <p className="connection-notice" role="status">{notice}</p>}
    <section className="connection-panel" aria-label="Connection list">
      <div className="connection-filters"><label>Search connections<input type="search" placeholder="Code, name or host" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value, offset: 0 })} /></label>
        <label>Filter database type<select value={filters.database_type} onChange={(event) => setFilters({ ...filters, database_type: event.target.value, offset: 0 })}><option value="">All databases</option><option value="POSTGRESQL">PostgreSQL</option><option value="MYSQL">MySQL</option></select></label>
        <label>Filter connection status<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value, offset: 0 })}><option value="">All statuses</option><option value="UNTESTED">Not tested</option><option value="SUCCESS">Verified</option><option value="FAILED">Failed</option></select></label></div>
      <p className="muted" role="status">{query.isPending ? 'Loading connections…' : query.isError ? 'Connection service unavailable.' : `${query.data.total ?? 'Unknown number of'} connections`}</p>
      {query.isError && <div className="connection-error" role="alert">Unable to load connections. <button onClick={() => void query.refetch()}>Retry</button></div>}
      {query.data && <><div className="connection-table-scroll"><table><caption className="sr-only">Saved database connections</caption><thead><tr><th>Code and name</th><th>Database</th><th>Endpoint</th><th>Status</th><th>Last tested</th></tr></thead><tbody>
        {query.data.items.map((connection) => <tr key={connection.id}><td><button className="text-button" disabled={busy} aria-label={'View ' + connection.code} onClick={() => void select(connection.id)}>{connection.code}</button><small>{connection.name}</small></td><td>{connection.database_type === 'MYSQL' ? 'MySQL' : 'PostgreSQL'}</td><td>{connection.host}:{connection.port}<small>{connection.database_name}</small></td><td><span className={'connection-badge ' + (connection.test_status ?? 'UNTESTED').toLowerCase()}>{statusLabel(connection.test_status)}</span></td><td>{connection.tested_at ? new Date(connection.tested_at).toLocaleString() : 'Never'}</td></tr>)}
      </tbody></table></div>{query.data.items.length === 0 && <p className="connection-empty">No connections match these filters.</p>}
        <div className="connection-actions connection-pagination"><button disabled={busy || filters.offset === 0} onClick={() => setFilters({ ...filters, offset: Math.max(0, filters.offset - 50) })}>Previous</button><button disabled={busy || query.data.next_offset === null} onClick={() => setFilters({ ...filters, offset: query.data.next_offset ?? 0 })}>Next</button></div></>}
    </section>
    {editor && <ConnectionForm key={editor === 'edit' ? selected?.data.id + ':' + selected?.data.revision : 'create'} connection={editor === 'edit' ? selected?.data : undefined} busy={busy} onSave={save} onCancel={() => setEditor(null)} />}
    {selected && !editor && <section className="connection-panel" aria-labelledby="connection-detail-title"><div className="connection-heading"><h2 id="connection-detail-title">{selected.data.name ?? selected.data.code}</h2><button disabled={busy} onClick={() => void select(selected.data.id)}>Refresh details</button></div>
      <dl className="connection-facts"><div><dt>Connection code</dt><dd>{selected.data.code}</dd></div><div><dt>Username</dt><dd>{selected.data.username}</dd></div><div><dt>Schema</dt><dd>{selected.data.schema_name ?? 'Not applicable'}</dd></div><div><dt>Password</dt><dd>{selected.data.has_password ? 'Stored securely' : 'Not configured'}</dd></div><div><dt>Revision</dt><dd>{selected.data.revision}</dd></div><div><dt>Status</dt><dd>{statusLabel(selected.data.test_status)}</dd></div></dl>
      {selected.data.needs_revalidation && <p className="connection-warning">This revision needs to be tested before it is used in new work.</p>}
      {selected.data.description && <p>{selected.data.description}</p>}
      <h3>Dependencies</h3>{selected.data.dependencies.length ? <><p className="muted">Referenced connections cannot be deleted or have their code changed. Location changes are blocked during active or unreconciled runs.</p><ul>{selected.data.dependencies.map((dependency) => <li key={dependency.resource_type + dependency.resource_id + dependency.label}>{dependency.resource_type}: {dependency.label}</li>)}</ul></> : <p className="muted">No dependent resources.</p>}
      <div className="connection-actions"><button className="primary-button" disabled={busy} onClick={() => void test()}>{pending === 'test' ? 'Testing…' : 'Test connection'}</button><button disabled={busy} onClick={() => { setEditor('edit'); setError(''); setNotice(''); }}>Edit connection</button><button className="danger-button" disabled={busy || selected.data.dependencies.length > 0} onClick={() => setConfirmDelete(true)}>Delete connection</button></div>
    </section>}
    {confirmDelete && selected && <DeleteConfirmation connection={selected.data} busy={busy} onCancel={() => setConfirmDelete(false)} onDelete={() => void remove()} />}
  </section>;
}
