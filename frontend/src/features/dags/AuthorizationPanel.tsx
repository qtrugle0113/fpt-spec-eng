import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { newIdempotencyKey, requestJSON } from '../../lib/api';
import { failure } from './types';
import type { ETLItem, Schema } from './types';

export function AuthorizationPanel({ item, confirmationToken, disabled = false, onSelect, onBusy }: { item: ETLItem; confirmationToken: string; disabled?: boolean; onSelect: (authority: Schema['Authorization']) => void; onBusy: (busy: boolean) => void }) {
  const cache = useQueryClient();
  const [scope, setScope] = useState<'ONCE' | 'SCHEDULED'>('ONCE');
  const [allowEmpty, setAllowEmpty] = useState(false);
  const [emptyAck, setEmptyAck] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [revokeAck, setRevokeAck] = useState('');
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [detail, setDetail] = useState<Schema['Authorization'] | null>(null);
  const keys = useRef(new Map<string, string>());
  useEffect(() => { setConfirmed(false); setEmptyAck(false); setRevokeAck(''); }, [confirmationToken, item.id]);
  const key = (identity: string) => { let value = keys.current.get(identity); if (!value) { value = newIdempotencyKey(); keys.current.set(identity, value); } return value; };
  const history = useQuery({ queryKey: ['replacement-authorizations', item.definition_id, offset], enabled: Boolean(item.definition_id), queryFn: async ({ signal }) =>
    (await requestJSON<Schema['AuthorizationPage']>(`/etl-definitions/${item.definition_id}/replacement-authorizations?limit=20&offset=${offset}`, { signal })).data, refetchInterval: 5000 });
  useEffect(() => { history.data?.items.filter(authority => authority.state !== 'GRANTED').forEach(onSelect); }, [history.data, onSelect]);
  async function run(action: () => Promise<void>) {
    setBusy(true); onBusy(true); setError(''); setNotice('');
    try { await action(); }
    catch (error) { setError(failure(error)); }
    finally { setBusy(false); onBusy(false); }
  }
  const locked = disabled || busy;
  const refresh = () => cache.invalidateQueries({ queryKey: ['replacement-authorizations', item.definition_id] });
  if (item.config.load_strategy !== 'FULL_REFRESH') return null;
  return <section className="dag-authorization" aria-label={'Replacement authorization for ' + item.config.dag_id}>
    <h3>Replacement authority · {item.config.dag_id}</h3>
    <p>Target: <strong>{item.target}</strong>. FULL_REFRESH replaces every row in this table. Deploying a DAG does not grant replacement authority.</p>
    <p className="dag-warning">Revocation blocks new admissions. It does not cancel a transaction that has already been admitted, and recovery evidence is retained.</p>
    {!item.definition_id && <p role="alert">Refresh the preview before managing replacement authority.</p>}
    {error && <p role="alert" className="error-message">{error}</p>}{notice && <p role="status">{notice}</p>}
    <fieldset disabled={locked || !item.definition_id}><legend>Grant replacement authority</legend>
      <label>Authority scope<select value={scope} onChange={event => { setScope(event.target.value as 'ONCE' | 'SCHEDULED'); setConfirmed(false); }}><option value="ONCE">ONCE — next manual run only</option><option value="SCHEDULED" disabled={item.config.schedule === 'Manual'}>SCHEDULED — matching recurring schedule only</option></select></label>
      <p>{scope === 'ONCE' ? 'The first accepted manual trigger reserves this authority exclusively. Retry keeps that run; a new run requires a new authority.' : `Only Airflow scheduled runs for ${item.config.schedule} (${item.config.timezone}) may use this authority. Manual runs and backfills are excluded.`}</p>
      <label><input type="checkbox" checked={allowEmpty} onChange={event => { setAllowEmpty(event.target.checked); setEmptyAck(false); setConfirmed(false); }} />Allow a valid empty dataset to empty the target</label>
      {allowEmpty && <label><input type="checkbox" checked={emptyAck} onChange={event => setEmptyAck(event.target.checked)} />I separately authorize emptying every row in {item.target} when the validated source contains zero rows. Source errors are not empty data.</label>}
      <label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />I authorize replacing all rows in {item.target} for this exact revision and {scope === 'ONCE' ? 'one manual run' : 'the displayed schedule'}.</label>
      <button disabled={!confirmed || allowEmpty && !emptyAck} onClick={() => void run(async () => {
        const identity = `grant:${item.id}:${scope}:${allowEmpty}:${confirmationToken}`;
        const body: Schema['AuthorizationRequest'] = { revision_id: item.id, physical_target_id: item.config.target.physical_target_id, scope, allow_empty: allowEmpty, allow_empty_acknowledged: emptyAck, acknowledged: true, confirmation_token: confirmationToken };
        const result = await requestJSON<Schema['Authorization']>(`/etl-definitions/${item.definition_id}/replacement-authorizations`, { method: 'POST', body, key: key(identity) });
        keys.current.delete(identity); setConfirmed(false); setEmptyAck(false); await refresh();
        if (result.data.state === 'GRANTED') onSelect(result.data);
        setNotice(`Authority saved: ${result.data.state}. ${result.data.state === 'GRANTED' ? 'It can now be selected for its matching scope.' : 'Review its saved state before granting another authority.'}`);
      })}>Grant {scope} authority</button>
    </fieldset>
    <h4>Saved authority</h4>
    {history.isPending && item.definition_id && <p role="status">Loading authority history…</p>}{history.error && <p role="alert">{failure(history.error)}</p>}
    {history.data && <><div className="table-scroll" tabIndex={0} aria-label={'Authority history for ' + item.config.dag_id}><table><thead><tr><th>Scope</th><th>State</th><th>Empty target allowed</th><th>Reserved run</th><th>Replacement in progress</th><th>Actions</th></tr></thead><tbody>
      {history.data.items.map(authority => <tr key={authority.id}><td>{authority.scope}</td><td>{authority.state}</td><td>{authority.allow_empty ? 'Yes' : 'No'}</td><td>{authority.reserved_run_id ?? 'Not reserved'}</td><td>{authority.replacement_in_progress === null ? 'Unknown — reconciliation may be required' : authority.replacement_in_progress ? 'Yes' : 'No unresolved admission recorded'}</td><td>
        <div className="connection-actions"><button disabled={locked} onClick={() => void run(async () => setDetail((await requestJSON<Schema['Authorization']>('/replacement-authorizations/' + authority.id)).data))}>View authority details</button>
          <button disabled={locked || authority.state !== 'GRANTED' || authority.revision_id !== item.id || authority.physical_target_id !== item.config.target.physical_target_id} onClick={() => { onSelect(authority); setNotice(`${authority.scope} authority selected.`); }}>Use for {authority.scope === 'ONCE' ? 'manual run' : 'schedule activation'}</button></div>
        {['GRANTED', 'RESERVED'].includes(authority.state) && <><label><input type="checkbox" checked={revokeAck === authority.id} disabled={locked} onChange={event => setRevokeAck(event.target.checked ? authority.id : '')} />I understand revocation does not cancel an admitted transaction.</label>
          <button disabled={locked || revokeAck !== authority.id} onClick={() => void run(async () => {
            const identity = `revoke:${authority.id}:${authority.revision}`;
            const revoked = await requestJSON<Schema['Authorization']>(`/replacement-authorizations/${authority.id}/revoke`, { method: 'POST', body: { acknowledged: true }, etag: `"${authority.revision}"`, key: key(identity) });
            onSelect(revoked.data);
            keys.current.delete(identity); setRevokeAck(''); await refresh(); setNotice('Revocation saved. Existing admitted transactions may still finish.');
          })}>Revoke authority</button></>}
      </td></tr>)}
    </tbody></table></div>{history.data.items.length === 0 && <p>No replacement authority has been granted.</p>}
      <div className="connection-actions"><button disabled={locked || offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous authorities</button><button disabled={locked || history.data.next_offset === null} onClick={() => setOffset(history.data?.next_offset ?? 0)}>Next authorities</button><button disabled={locked} onClick={() => void history.refetch()}>Refresh authorities</button></div></>}
    {detail && <details open><summary>Authority details</summary><dl className="dag-facts"><dt>Reference</dt><dd>{detail.id}</dd><dt>Target identity</dt><dd><code>{detail.physical_target_id}</code></dd><dt>Revision</dt><dd>{detail.revision_id}</dd><dt>State</dt><dd>{detail.state}</dd><dt>Scope hash</dt><dd><code>{detail.scope_sha256}</code></dd><dt>Empty-data acknowledgment</dt><dd>{detail.allow_empty_acknowledged_at ?? 'Not granted'}</dd><dt>Reserved run</dt><dd>{detail.reserved_run_id ?? 'Not reserved'}</dd></dl><button onClick={() => setDetail(null)}>Close authority details</button></details>}
  </section>;
}
