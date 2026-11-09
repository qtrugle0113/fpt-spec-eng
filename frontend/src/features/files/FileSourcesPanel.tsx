import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import type { UseFormReturn } from 'react-hook-form';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { components } from '../../lib/api.generated';
import { newIdempotencyKey, pollOperation, requestJSON } from '../../lib/api';
import { defaultParser, getSourceFile, listSourceFiles, normalizedParser, parserSignature, patchSourceParser, previewSourceFile, uploadSourceFile } from '../../lib/files';
import type { Parser, SourceFile, SourcePreview } from '../../lib/files';

type Operation = components['schemas']['Operation'];
type Detail = Awaited<ReturnType<typeof getSourceFile>>;
const failure = (error: unknown) => error instanceof Error ? error.message : 'The request could not be completed.';
const oneCharacter = (value: string) => Array.from(value).length === 1 || 'Enter exactly one character.';
const terminal = (operation: Operation) => !['QUEUED', 'RUNNING'].includes(operation.state);

function ParserFields({ form, prefix, disabled }: { form: UseFormReturn<Parser>; prefix: string; disabled: boolean }) {
  const { register, watch, setValue, formState: { errors } } = form;
  const delimiter = watch('delimiter');
  const presets = [',', ';', '|', '\t'];
  return <fieldset disabled={disabled} className="connection-fields">
    <legend>Parser settings</legend>
    <label>Encoding<input autoComplete="off" list={prefix + '-encodings'} {...register('encoding', { required: 'Choose a text encoding.', maxLength: 64 })} />
      <datalist id={prefix + '-encodings'}>{['utf-8','utf-8-sig','utf-16','cp1252','latin-1'].map(value => <option key={value} value={value} />)}</datalist>{errors.encoding && <span className="field-error">Choose a supported text encoding.</span>}</label>
    <label>Delimiter preset<select value={presets.includes(delimiter) ? delimiter : '__custom__'} onChange={event => setValue('delimiter', event.target.value === '__custom__' ? '' : event.target.value, { shouldValidate: true, shouldDirty: true })}>
      <option value=",">Comma</option><option value=";">Semicolon</option><option value="|">Pipe</option><option value={'\t'}>Tab</option><option value="__custom__">Custom</option>
    </select></label>
    <label>Delimiter character<input autoComplete="off" maxLength={2} {...register('delimiter', { required: 'Enter a delimiter.', validate: oneCharacter })} />{errors.delimiter && <span className="field-error">{errors.delimiter.message}</span>}</label>
    <label>Quote character<input autoComplete="off" maxLength={2} {...register('quote_character', { required: 'Enter a quote character.', validate: value => oneCharacter(value) === true && value !== delimiter || 'Quote and delimiter must be different single characters.' })} />{errors.quote_character && <span className="field-error">{errors.quote_character.message}</span>}</label>
    <label>Escape character (optional)<input autoComplete="off" maxLength={2} {...register('escape_character', { validate: value => !value || Array.from(value).length === 1 && value !== delimiter || 'Enter a single escape character different from the delimiter.' })} />{errors.escape_character && <span className="field-error">{errors.escape_character.message}</span>}</label>
    <label>NULL marker<input autoComplete="off" maxLength={255} {...register('null_representation')} /></label>
    <label className="file-header-check"><input type="checkbox" {...register('header_present')} />First record contains column headers</label>
  </fieldset>;
}

function UploadSource({ busy, onUpload }: { busy: boolean; onUpload: (file: File, parser: Parser) => Promise<void> }) {
  const form = useForm<Parser>({ defaultValues: { ...defaultParser, escape_character: '' } });
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  return <form noValidate aria-label="Upload source file" onSubmit={form.handleSubmit(async values => {
    if (!file) { setError('Choose a CSV or TXT file.'); return; }
    if (!/\.(csv|txt)$/i.test(file.name)) { setError('Choose a CSV or TXT file.'); return; }
    if (file.size > 256 * 1024 * 1024) { setError('Source files must be at most 256 MiB.'); return; }
    setError(''); await onUpload(file, normalizedParser(values));
  })}>
    <h3>Upload source file</h3>
    <label>Source file<input type="file" accept=".csv,.txt" disabled={busy} onChange={event => { setFile(event.target.files?.[0] ?? null); setError(''); }} /></label>
    <p>Confirm the parser settings for this upload. Quoted NULL markers remain text; an empty NULL marker applies only to unquoted empty values.</p>
    <ParserFields form={form} prefix="upload-source" disabled={busy} />
    {error && <p role="alert">{error}</p>}
    <button disabled={busy || !file}>Upload source file</button>
  </form>;
}

function ParserEditor({ file, busy, previewSignature, canSave, onPreview, onSave, onDirtyChange }: {
  file: SourceFile; busy: boolean; previewSignature: string | null; canSave: boolean;
  onPreview: (parser: Parser) => Promise<void>; onSave: (parser: Parser) => Promise<void>;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const form = useForm<Parser>({ defaultValues: { ...file.parser, escape_character: file.parser.escape_character ?? '' } });
  const values = form.watch(); const signature = parserSignature(values);
  const changed = signature !== parserSignature(file.parser);
  useEffect(() => onDirtyChange(changed), [changed, onDirtyChange]);
  return <form noValidate aria-label="Source parser configuration" onSubmit={form.handleSubmit(async value => onPreview(normalizedParser(value)))}>
    <h3>Source parser configuration</h3><ParserFields form={form} prefix={'edit-source-' + file.id} disabled={busy} />
    <p>Preview these settings before confirming a change. Changing the parser requires full validation again; saved run settings remain unchanged.</p>
    {previewSignature && previewSignature !== signature && <p role="status">Settings changed after this preview. Preview again before confirming.</p>}
    <div className="connection-actions"><button disabled={busy}>Preview with these settings</button>
      <button type="button" disabled={busy || !changed || !canSave || previewSignature !== signature} onClick={form.handleSubmit(async value => onSave(normalizedParser(value)))}>Confirm parser change</button>
      <button type="button" disabled={busy || !changed} onClick={() => form.reset({ ...file.parser, escape_character: file.parser.escape_character ?? '' })}>Discard parser changes</button></div>
  </form>;
}

export function FileSourcesPanel({ selected, onSelect }: { selected: SourceFile | null; onSelect: (file: SourceFile | null) => void }) {
  const cache = useQueryClient(); const [offset, setOffset] = useState(0);
  const listing = useQuery({ queryKey: ['source-files', offset], queryFn: ({ signal }) => listSourceFiles(offset, signal) });
  const [detail, setDetail] = useState<Detail | null>(null);
  const [preview, setPreview] = useState<{ value: SourcePreview; signature: string } | null>(null);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [parserDirty, setParserDirty] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const controller = useRef<AbortController | null>(null);
  const validationKeys = useRef(new Map<string, { key: string; terminal: boolean }>());
  useEffect(() => () => controller.current?.abort(), []);
  const refreshList = () => cache.invalidateQueries({ queryKey: ['source-files'] });
  function keepSelectionConsistent(file: SourceFile) {
    if (selected?.id === file.id && (selected.parser_revision !== file.parser_revision || selected.sha256 !== file.sha256 || file.needs_revalidation)) onSelect(null);
  }
  async function run(action: (signal: AbortSignal) => Promise<void>) {
    setBusy(true); setError(''); setNotice(''); const abort = new AbortController(); controller.current = abort;
    try { await action(abort.signal); } catch (error) { if (!abort.signal.aborted) setError(failure(error)); }
    finally { if (!abort.signal.aborted) setBusy(false); }
  }
  async function openFile(id: string, signal: AbortSignal) {
    const result = await getSourceFile(id, signal); setDetail(result); setPreview(null); setOperation(null); keepSelectionConsistent(result.data);
  }
  async function complete(started: Operation, signal: AbortSignal) {
    setOperation(started);
    const result = terminal(started) ? started : await pollOperation(started.id, signal); setOperation(result);
    if (detail) {
      const latest = await getSourceFile(detail.data.id, signal); setDetail(latest); keepSelectionConsistent(latest.data);
      const scope = `${detail.data.id}:${detail.data.sha256}:${detail.data.parser_revision}`;
      const entry = validationKeys.current.get(scope); if (entry) entry.terminal = terminal(result);
    }
    await refreshList();
    setNotice(result.state === 'SUCCEEDED' ? 'Full file validation succeeded. You can select this source.' : `Validation ${result.state.toLowerCase()}. Review the error and validate the current parser before selecting this source.`);
  }
  const file = detail?.data;
  const isExpired = !!file?.expires_at && Date.parse(file.expires_at) <= Date.now();
  const validating = !!operation && !terminal(operation);
  return <section className="connection-panel file-sources-panel" aria-labelledby="file-sources-title">
    <h2 id="file-sources-title">File Sources</h2>
    <p>Upload CSV or TXT files, confirm their parser, then validate the full file before choosing a source.</p>
    {error && <p role="alert" className="error-message">{error}</p>}{notice && <p role="status">{notice}</p>}
    <UploadSource busy={busy} onUpload={async (source, parser) => run(async signal => {
      const result = await uploadSourceFile(source, parser, signal); setDetail(result); setPreview(null); setOperation(null);
      setNotice('Source uploaded. Preview and validate the file before selecting it.'); await refreshList();
    })} />
    <h3>Uploaded files</h3>
    {listing.isPending && <p role="status">Loading source files…</p>}{listing.error && <p role="alert">{failure(listing.error)}</p>}
    {listing.data && <>
      <div className="table-scroll" tabIndex={0} aria-label="Uploaded source files"><table><thead><tr><th>File</th><th>Reference</th><th>Size</th><th>Validation</th><th>Actions</th></tr></thead><tbody>
        {listing.data.items.map(item => <tr key={item.id}><td>{item.file_name}<small>{item.file_type} · parser revision {item.parser_revision}</small></td><td><code>{item.id}</code></td><td>{item.size.toLocaleString()} bytes</td><td>{item.validation_status ?? 'UNKNOWN'}</td><td><button disabled={busy} aria-label={`Open file ${item.file_name} ${item.id}`} onClick={() => void run(signal => openFile(item.id, signal))}>Open file</button></td></tr>)}
      </tbody></table></div>{listing.data.items.length === 0 && <p>No source files have been uploaded.</p>}
      <p>Files: {listing.data.total ?? 'Unknown'}</p><div className="connection-actions"><button disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous files</button><button disabled={busy || listing.data.next_offset === null} onClick={() => setOffset(listing.data?.next_offset ?? 0)}>Next files</button><button disabled={busy} onClick={() => void listing.refetch()}>Refresh files</button></div>
    </>}
    {file && <section aria-label="Source file details">
      <h3>{file.file_name}</h3><p>Reference: <code>{file.id}</code></p><p>SHA-256: <code>{file.sha256}</code></p>
      <p>Parser revision {file.parser_revision} · validation {file.validation_status ?? 'UNKNOWN'} · {file.needs_revalidation ? 'Validation required' : 'Current validation available'}</p>
      <p>Expiry: {file.expires_at ? new Date(file.expires_at).toLocaleString() : 'No expiry'}. Referenced source files are retained during workflow and recovery use.</p>
      <button disabled={busy} onClick={() => void run(signal => openFile(file.id, signal))}>Refresh source details</button>
      <ParserEditor key={`${file.id}:${file.parser_revision}`} file={file} busy={busy} canSave={!!detail?.etag} previewSignature={preview?.signature ?? null}
        onDirtyChange={setParserDirty}
        onPreview={async parser => run(async signal => setPreview({ value: await previewSourceFile(file.id, parser, signal), signature: parserSignature(parser) }))}
        onSave={async parser => run(async signal => {
          if (!detail?.etag) throw new Error('Refresh the selected file before changing its parser.');
          const result = await patchSourceParser(file.id, detail.etag, parser, signal); setDetail(result); setPreview(null); setOperation(null);
          keepSelectionConsistent(result.data); setNotice(result.data.parser_revision === file.parser_revision ? 'Parser configuration is unchanged.' : 'Parser configuration confirmed. Validate the full file before selecting this source.'); await refreshList();
        })} />
      {preview && <section aria-label="Source data preview"><h4>Data preview ({preview.value.rows.length} rows)</h4>
        <p>{preview.value.limited ? 'Preview is limited. Full validation checks the complete file.' : 'This preview does not replace full validation.'}</p>
        <div className="table-scroll" tabIndex={0} aria-label="Source preview rows"><table><thead><tr>{preview.value.columns.map(column => <th key={column.name}>{column.name}</th>)}</tr></thead><tbody>
          {preview.value.rows.map((row, index) => <tr key={index}>{row.map((value, column) => <td key={column} className="file-preview-value">{value === null ? <span className="file-null" aria-label="SQL NULL">NULL</span> : value === '' ? <span aria-label="Empty string">""</span> : String(value)}</td>)}</tr>)}
        </tbody></table></div>{preview.value.rows.length === 0 && <p>No data rows in this preview.</p>}
      </section>}
      {parserDirty && <p role="status">Confirm or discard parser changes before validating or selecting this source.</p>}
      <div className="connection-actions"><button disabled={busy || validating || isExpired || parserDirty} onClick={() => void run(async signal => {
        const scope = `${file.id}:${file.sha256}:${file.parser_revision}`; let entry = validationKeys.current.get(scope);
        if (!entry || entry.terminal) { entry = { key: newIdempotencyKey(), terminal: false }; validationKeys.current.set(scope, entry); }
        const started = (await requestJSON<Operation>(`/files/${file.id}/validate`, { method: 'POST', body: { expected_sha256: file.sha256, parser_revision: file.parser_revision }, key: entry.key, signal })).data;
        if (selected?.id === file.id) onSelect(null); await complete(started, signal);
      })}>Validate full file</button>
        <button disabled={busy || parserDirty || file.needs_revalidation || file.validation_status !== 'VALID' || isExpired} onClick={() => { onSelect(file); setNotice('Validated source selected for this workflow.'); }}>Select as ETL source</button>
      </div>
      {operation && <section aria-label="File validation operation"><h4>Validation: {operation.state}</h4><p>Operation reference: <code>{operation.id}</code></p>
        {operation.error && <div role="alert"><p>{operation.error.error.message}</p><ul>{operation.error.error.details?.map((issue, index) => <li key={index}>{issue.message}{issue.row ? ` Line ${issue.row}.` : ''}{issue.column ? ` Column ${issue.column}.` : ''}</li>)}</ul></div>}
        <button disabled={busy} onClick={() => void run(async signal => complete((await requestJSON<Operation>('/operations/' + operation.id, { signal })).data, signal))}>Refresh validation status</button>
      </section>}
    </section>}
    {busy && <p role="status">Processing source file…</p>}
  </section>;
}
