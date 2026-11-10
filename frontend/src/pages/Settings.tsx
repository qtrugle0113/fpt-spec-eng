import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { APIError, requestJSON } from '../lib/api';
import type { components } from '../lib/api.generated';
import { Feedback } from '../components/Feedback';

type SettingsValue = components['schemas']['Settings'];
type Patch = components['schemas']['SettingsPatch'];

export function Settings() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ['settings'], queryFn: ({ signal }) => requestJSON<SettingsValue>('/settings', { signal }) });
  const [draft, setDraft] = useState<Patch>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [conflict, setConflict] = useState(false);
  useEffect(() => { if (query.data) setDraft({}); }, [query.data]);
  const value = { ...query.data?.data, ...draft };
  return <div className="connections-page"><header className="page-heading"><div><p className="eyebrow">Workspace preferences</p><h1>Settings</h1><p>Defaults apply to new work. Existing validated revisions and deployed workflows keep their configuration.</p></div></header>
    {query.isPending && <p role="status">Loading settings…</p>}
    {query.error && <p role="alert">Settings are unavailable. Reload before editing.</p>}
    {error && <Feedback kind="error">{error}</Feedback>}{notice && <Feedback kind="status">{notice}</Feedback>}
    <button disabled={busy || query.isFetching} onClick={async () => { const result = await query.refetch(); if (result.isSuccess) { setConflict(false); setError(''); setNotice('Settings reloaded.'); } }}>Reload settings</button>
    {query.data && <><form className="connection-panel settings-form" onSubmit={async event => {
      event.preventDefault(); setBusy(true); setError(''); setNotice('');
      try {
        if (!query.data.etag) throw new Error('Reload settings before saving.');
        const saved = await requestJSON<SettingsValue>('/settings', { method: 'PATCH', etag: query.data.etag, body: draft });
        client.setQueryData(['settings'], saved); setDraft({}); setNotice('Settings saved. Refresh interval changes apply on the next refresh cycle.');
      } catch (reason) {
        const stale = reason instanceof APIError && reason.status === 412;
        setConflict(stale); setError(stale ? 'Settings changed in another session. Reload and review before saving again.' : reason instanceof Error ? reason.message : 'Settings could not be saved. Reload to check the current values.');
      } finally { setBusy(false); }
    }}><fieldset disabled={busy || conflict || Boolean(query.error)}><legend>Default configuration</legend>
      <label>Default Batch Size (rows)<input required type="number" min={1} max={10000} step={1} value={value.default_batch_size ?? ''} onChange={event => setDraft({ ...draft, default_batch_size: event.target.valueAsNumber })} /></label>
      <p>1–10,000 rows. Applies when a new workbook leaves Batch Size blank; byte limits still apply.</p>
      <label>Dashboard Refresh Interval (seconds)<input required type="number" min={5} max={3600} step={1} value={value.dashboard_refresh_interval ?? ''} onChange={event => setDraft({ ...draft, dashboard_refresh_interval: event.target.valueAsNumber })} /></label>
      <label>Default Timezone<input required value={value.default_timezone ?? ''} onChange={event => setDraft({ ...draft, default_timezone: event.target.value })} placeholder="Asia/Seoul" /></label>
      <p>Use an IANA timezone. Workbook Timezone remains explicit; existing workflows do not change.</p>
      <label>Staging Retention (days)<input required type="number" min={1} max={365} step={1} value={value.staging_retention_days ?? ''} onChange={event => setDraft({ ...draft, staging_retention_days: event.target.valueAsNumber })} /></label>
      <p>1–365 days. Protected recovery artifacts are retained regardless of this setting.</p>
      <button type="submit" disabled={Object.keys(draft).length === 0}>{busy ? 'Saving…' : 'Save settings'}</button>
    </fieldset></form><section className="connection-panel" aria-label="Application information"><h2>Application information</h2><dl className="dag-facts"><dt>Airflow Connectivity Status</dt><dd>{query.data.data.airflow_connectivity_status ?? 'UNKNOWN'}</dd><dt>Application Version</dt><dd>{query.data.data.application_version}</dd><dt>Settings Revision</dt><dd>{query.data.data.revision}</dd></dl><p>Connectivity and application information are read-only.</p></section></>}
  </div>;
}
