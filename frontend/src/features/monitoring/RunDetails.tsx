import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { requestJSON } from '../../lib/api';
import { failure } from '../dags/types';
import type { Schema } from '../dags/types';

const count = (value: number | null | undefined) => value == null ? 'Not available' : value.toLocaleString();
const time = (value: string | null | undefined) => value ? new Date(value).toISOString() : 'Not available';

export function RunDetails({ dagId, runId }: { dagId: string; runId: string }) {
  const [task, setTask] = useState<{ id: string; map: number } | null>(null);
  const [attempt, setAttempt] = useState(1);
  const [token, setToken] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  useEffect(() => { setTask(null); setToken(null); setShowLogs(false); }, [dagId, runId]);
  const base = `/dags/${encodeURIComponent(dagId)}/runs/${encodeURIComponent(runId)}`;
  const detail = useQuery({ queryKey: ['monitoring-run', dagId, runId], queryFn: async ({ signal }) =>
    (await requestJSON<Schema['DAGRun']>(base, { signal })).data, refetchInterval: 5000 });
  const logs = useQuery({ queryKey: ['monitoring-logs', dagId, runId, task, attempt, token], enabled: showLogs && Boolean(task), queryFn: async ({ signal }) => {
    const params = new URLSearchParams({ attempt: String(attempt), map_index: String(task?.map ?? -1) }); if (token) params.set('token', token);
    return (await requestJSON<Schema['LogPage']>(`${base}/tasks/${encodeURIComponent(task?.id ?? '')}/logs?${params}`, { signal })).data;
  }, retry: false });
  const run = detail.data;
  return <section className="connection-panel" aria-label="Run details"><h2>Run details</h2><p><code>{runId}</code></p>
    {detail.isPending && <p role="status">Loading the actual Airflow run…</p>}
    {detail.error && <p role="alert">{failure(detail.error)} Any previously displayed run data may be stale.</p>}
    {run && <><dl className="dag-facts"><dt>State</dt><dd>{run.state}</dd><dt>Run type</dt><dd>{run.run_type}</dd><dt>Bound revision</dt><dd>{run.revision_id ?? 'Not available'}</dd>
      <dt>Queued</dt><dd>{time(run.queued_time)}</dd><dt>Started</dt><dd>{time(run.start_time)}</dd><dt>Ended</dt><dd>{time(run.end_time)}</dd><dt>{run.state === 'running' ? 'Elapsed duration (ms)' : 'Duration (ms)'}</dt><dd>{count(run.duration_ms)}</dd></dl>
      {run.error_summary && <p role="alert">{run.error_summary}</p>}
      <h3>ETL evidence</h3>{run.metrics ? <dl className="dag-facts"><dt>Extracted rows</dt><dd>{count(run.metrics.extracted_rows)}</dd><dt>Validated rows</dt><dd>{count(run.metrics.validated_rows)}</dd><dt>Loaded rows</dt><dd>{count(run.metrics.loaded_rows)}</dd><dt>Failed rows</dt><dd>{count(run.metrics.failed_rows)}</dd><dt>Phase</dt><dd>{run.metrics.phase ?? 'Not available'}</dd><dt>Staging bytes</dt><dd>{count(run.metrics.staging_bytes)}</dd><dt>Protected bytes</dt><dd>{count(run.metrics.protected_bytes)}</dd><dt>Recovery</dt><dd>{run.metrics.recovery_summary ?? 'No unresolved commit reported'}</dd></dl> : <p>ETL metrics are not available for this run. External runs do not receive invented row counts.</p>}
      <h3>Task attempts</h3><div className="table-scroll" tabIndex={0} aria-label="Task attempts"><table><thead><tr><th>Task</th><th>Map index</th><th>State</th><th>Attempt</th><th>Duration (ms)</th><th>Action</th></tr></thead><tbody>
        {(run.tasks ?? []).map(item => <tr key={`${item.task_id}:${item.map_index ?? -1}`}><td>{item.task_id}</td><td>{item.map_index ?? -1}</td><td>{item.state ?? 'Not started'}</td><td>{item.try_number ?? 'Not available'}</td><td>{count(item.duration_ms)}</td><td><button onClick={() => { setTask({ id: item.task_id, map: item.map_index ?? -1 }); setAttempt(item.try_number ?? 1); setToken(null); setShowLogs(true); }}>View attempt logs</button></td></tr>)}
      </tbody></table></div>{run.tasks?.length === 0 && <p>No task instances have been reported.</p>}
    </>}
    <button onClick={() => void detail.refetch()}>Refresh run details</button>
    {task && <section aria-label="Attempt logs"><h3>Attempt logs · {task.id}</h3><label>Attempt number<input type="number" min="0" step="1" value={attempt} onChange={event => { const value = Number(event.target.value); if (Number.isInteger(value) && value >= 0) { setAttempt(value); setToken(null); } }} /></label>
      <p>Map index: {task.map}. Each displayed page is limited to 1 MiB and redacted by the server.</p>
      {logs.isFetching && <p role="status">Loading log page…</p>}{logs.error && <p role="alert">{failure(logs.error)}</p>}
      {logs.data && <>{!logs.data.available && <p>{logs.data.unavailable_reason ?? 'Logs are not available for this attempt.'}</p>}{logs.data.truncated && <p role="alert">This log page reached the display limit. Open Airflow for complete logs.</p>}
        <pre className="monitoring-logs">{logs.data.content.join('\n')}</pre><div className="connection-actions"><button disabled={logs.isFetching || !logs.data.continuation_token} onClick={() => setToken(logs.data?.continuation_token ?? null)}>Next log page</button><button disabled={logs.isFetching} onClick={() => { setToken(null); void logs.refetch(); }}>Reload first log page</button></div>
      </>}
    </section>}
  </section>;
}
