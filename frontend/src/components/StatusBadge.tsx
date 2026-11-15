export function StatusBadge({ value = 'Not available' }: { value?: string }) {
  const state = value.toLowerCase();
  const tone = ['success', 'succeeded', 'validated', 'valid', 'deployed'].includes(state) ? 'success'
    : ['failed', 'invalid', 'parse_error', 'deployment_failed', 'partially_succeeded'].includes(state) ? 'failed'
    : ['running', 'queued', 'validating', 'deployment_pending', 'needs_reconciliation'].includes(state) ? 'running' : '';
  return <span className={`connection-badge ${tone}`}>{value}</span>;
}
