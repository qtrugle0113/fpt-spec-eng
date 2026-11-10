import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { requestJSON } from '../lib/api';
import type { components } from '../lib/api.generated';
import { Metrics, RunChart, count } from '../features/dashboard/Metrics';
type Schema = components['schemas'];

export function Dashboard() {
  const [filters, setFilters] = useState({ from: '', to: '', timezone: '', scope: 'ALL' });
  const [auto, setAuto] = useState(false);
  const settings = useQuery({ queryKey: ['settings'], queryFn: ({ signal }) => requestJSON<Schema['Settings']>('/settings', { signal }) });
  const query = useQuery({ queryKey: ['dashboard', filters], queryFn: ({ signal }) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
    return requestJSON<Schema['Dashboard']>('/dashboard?' + params, { signal });
  }, refetchInterval: auto ? (settings.data?.data.dashboard_refresh_interval ?? 30) * 1000 : false });
  const [refreshError, setRefreshError] = useState('');
  const [manualBusy, setManualBusy] = useState(false);
  const data = query.data?.data;
  return <div className="connections-page"><header className="page-heading"><div><p className="eyebrow">Workspace overview</p><h1>Dashboard</h1><p>Workflow inventory and actual executions from Airflow.</p></div><button disabled={manualBusy || query.isFetching} onClick={async () => {
    setManualBusy(true); setRefreshError('');
    try {
      // Force refresh is a server-side cache bypass, not just a browser refetch.
      const params = new URLSearchParams({ ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value)), force_refresh: 'true' });
      await requestJSON<Schema['Dashboard']>('/dashboard?' + params);
      await query.refetch();
      await settings.refetch();
    } catch (error) { setRefreshError(error instanceof Error ? error.message : 'Refresh failed.'); }
    finally { setManualBusy(false); }
  }}>Refresh dashboard</button></header>
    <section className="connection-panel" aria-label="Dashboard filters"><h2>Execution period</h2><div className="monitoring-filters"><label>From date<input type="date" value={filters.from} onChange={event => setFilters({ ...filters, from: event.target.value })} /></label><label>To date<input type="date" value={filters.to} onChange={event => setFilters({ ...filters, to: event.target.value })} /></label><label>Timezone<input placeholder={settings.data?.data.default_timezone ?? 'UTC'} value={filters.timezone} onChange={event => setFilters({ ...filters, timezone: event.target.value })} /></label><label>Ownership scope<select value={filters.scope} onChange={event => setFilters({ ...filters, scope: event.target.value })}><option value="ALL">All workflows</option><option value="MANAGED">Managed</option><option value="EXTERNAL">External</option></select></label></div><label><input type="checkbox" checked={auto} onChange={event => setAuto(event.target.checked)} />Auto Refresh</label><p>Refresh interval: {settings.data?.data.dashboard_refresh_interval ?? 30} seconds.</p></section>
    {query.isPending && <p role="status">Loading dashboard…</p>}{(query.error || refreshError) && <p role="alert">{refreshError || 'Dashboard is unavailable. Previously displayed values may be stale.'}</p>}
    {data && <><p role="status">{data.stale || query.error ? 'Stale data' : data.completeness === 'COMPLETE' ? 'Complete data' : data.completeness === 'INCOMPLETE' ? 'Incomplete data' : 'Not available'} · Last update: {data.fetched_at ?? 'Not available'} · Timezone: {data.timezone}</p>{data.unavailable_fields.length > 0 && <p>Unavailable fields: {data.unavailable_fields.join(', ')}</p>}<p>Selected execution period: {data.from} – {data.to}. Inventory describes the current workflows.</p><Metrics data={data} /><RunChart data={data} />
      <section className="connection-panel"><h2>Schedule groups</h2><p>DAG counts describe current schedules. Run counts describe historical schedules for the selected period.</p><div className="table-scroll" tabIndex={0}><table><thead><tr><th>Schedule</th><th>DAG count</th><th>Run count</th></tr></thead><tbody>{data.schedule_groups?.map(row => <tr key={row.group}><td>{row.group}</td><td>{count(row.dag_count)}</td><td>{count(row.run_count)}</td></tr>)}</tbody></table></div></section>
      <section className="connection-panel"><h2>Lifetime history</h2><p>Independent of the selected execution period, within the current ownership scope.</p><p>Total runs: {count(data.lifetime_metrics?.total)} · Successful: {count(data.lifetime_metrics?.successful)} · Failed: {count(data.lifetime_metrics?.failed)}</p><p>Last successful run: {data.last_successful_run ? <a href={data.last_successful_run.airflow_url} target="_blank" rel="noreferrer">{data.last_successful_run.run_id}</a> : data.last_successful_run_availability === 'AVAILABLE' ? 'No successful run reported' : 'Not available'}</p></section>
      <section className="connection-panel"><h2>Next scheduled runs</h2><p>Airflow forecasts; paused workflows require explicit activation.</p>{data.next_scheduled_runs?.length ? <ul>{data.next_scheduled_runs.map(run => <li key={run.dag_id}><a href={run.airflow_url} target="_blank" rel="noreferrer">{run.dag_id}</a>: {run.scheduled_time} / {run.is_paused ? 'Paused' : 'Unpaused'}</li>)}</ul> : <p>No next scheduled run reported.</p>}</section><section className="connection-panel"><h2>Recent runs</h2><div className="table-scroll" tabIndex={0}><table><thead><tr><th>DAG</th><th>Run ID</th><th>Status</th><th>Start</th><th>End</th><th>Duration (seconds)</th><th>Details</th></tr></thead><tbody>{data.recent_runs?.map(run => <tr key={run.dag_id + run.run_id}><td>{run.dag_id}</td><td>{run.run_id}</td><td>{run.state}</td><td>{run.start_time ?? 'Not available'}</td><td>{run.end_time ?? 'Not available'}</td><td>{run.duration_ms == null ? 'Not available' : count(run.duration_ms / 1000)}</td><td><a href={`/monitoring?${new URLSearchParams({ dag: run.dag_id, run: run.run_id })}`}>View run details</a></td></tr>)}</tbody></table></div>{data.recent_runs?.length === 0 && <p>No runs in this period.</p>}</section>
    </>}
  </div>;
}
