import type { components } from '../../lib/api.generated';
type Dashboard = components['schemas']['Dashboard'];
export const count = (value: number | null | undefined) => value == null ? 'Not available' : value.toLocaleString();

export function Metrics({ data }: { data: Dashboard }) {
  const cards = [['Total DAGs', data.inventory.total], ['Active DAGs', data.inventory.active], ['Paused DAGs', data.inventory.paused],
    ['Total DAG Runs', data.run_metrics.total], ['Successful Runs', data.run_metrics.successful], ['Failed Runs', data.run_metrics.failed], ['Running Runs', data.run_metrics.running]] as const;
  return <section aria-label="Dashboard metrics"><h2>Workflow inventory and selected-period runs</h2><div className="dashboard-metrics">{cards.map(([label, value]) => <article className="connection-panel" key={label}><h3>{label}</h3><strong>{count(value)}</strong></article>)}<article className="connection-panel"><h3>Success Rate</h3><strong>{data.run_metrics.success_rate == null ? 'Not available' : `${data.run_metrics.success_rate.toFixed(1)}%`}</strong><p>Successful / (successful + failed)</p></article></div><p>Queued: {count(data.run_metrics.queued)} · Other states: {count(data.run_metrics.other)}</p></section>;
}

export function RunChart({ data }: { data: Dashboard }) {
  const rows = data.time_series ?? [];
  const max = Math.max(1, ...rows.flatMap(row => [row.metrics?.successful ?? 0, row.metrics?.failed ?? 0]));
  return <section className="connection-panel" aria-label="Run outcomes over time"><h2>Run outcomes over time</h2><p>Successful (blue) and failed (red) runs in the selected timezone.</p>
    {rows.length ? <><svg viewBox={`0 0 ${Math.max(300, rows.length * 24)} 160`} role="img" aria-label="Daily successful and failed run counts"><title>Daily successful and failed runs; exact values follow in the table</title>{rows.map((row, i) => <g key={row.date}><rect x={i * 24 + 2} y={140 - (row.metrics?.successful ?? 0) / max * 130} width={9} height={(row.metrics?.successful ?? 0) / max * 130} fill="#2563a5" /><rect x={i * 24 + 12} y={140 - (row.metrics?.failed ?? 0) / max * 130} width={9} height={(row.metrics?.failed ?? 0) / max * 130} fill="#ae3545" /></g>)}</svg><details><summary>View daily counts</summary><div className="table-scroll" tabIndex={0}><table><thead><tr><th>Date</th><th>Successful</th><th>Failed</th></tr></thead><tbody>{rows.map(row => <tr key={row.date}><td>{row.date}</td><td>{count(row.metrics?.successful)}</td><td>{count(row.metrics?.failed)}</td></tr>)}</tbody></table></div></details></> : <p>Not available</p>}</section>;
}
