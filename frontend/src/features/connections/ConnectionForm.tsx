import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import type { Connection, ConnectionCreate } from '../../lib/api';

type Values = { code: string; name: string; database_type: 'POSTGRESQL' | 'MYSQL'; host: string; port: number;
  database_name: string; schema_name: string; username: string; password: string; description: string };
type Props = { connection?: Connection; busy: boolean; onSave: (value: ConnectionCreate) => Promise<void>; onCancel: () => void };

export function ConnectionForm({ connection, busy, onSave, onCancel }: Props) {
  const { register, handleSubmit, watch, setValue, setFocus, resetField, formState: { errors } } = useForm<Values>({
    defaultValues: { code: connection?.code ?? '', name: connection?.name ?? '', database_type: connection?.database_type ?? 'POSTGRESQL',
      host: connection?.host ?? 'postgres', port: connection?.port ?? 5432, database_name: connection?.database_name ?? 'etl_test',
      schema_name: connection?.schema_name ?? 'public', username: connection?.username ?? '', password: '', description: connection?.description ?? '' },
  });
  useEffect(() => { setFocus(connection?.dependencies.length ? 'name' : 'code'); }, [setFocus, connection]);
  const type = watch('database_type');
  const required = { required: 'This field is required.', validate: (value: string) => value.trim().length > 0 || 'Enter a non-empty value.' };
  const submit = handleSubmit(async (values) => {
    try {
      await onSave({ ...values, code: values.code.trim(), name: values.name.trim(),
        schema_name: values.database_type === 'MYSQL' ? null : values.schema_name.trim() || null,
        description: values.description.trim() || null });
    } finally { resetField('password'); }
  });
  const error = (field: keyof Values) => errors[field] && <span className="field-error">{errors[field]?.message}</span>;

  return <section className="connection-panel" aria-labelledby="connection-form-title">
    <h2 id="connection-form-title">{connection ? 'Edit connection' : 'Add connection'}</h2>
    {connection && <p className="muted">Leave the password blank to keep the current credential.</p>}
    {!!connection?.dependencies.length && <p className="connection-warning">This connection is referenced by other resources. Its code cannot change. Changing connection details requires dependent workflows to be validated again.</p>}
    <form onSubmit={submit} aria-labelledby="connection-form-title">
      <fieldset disabled={busy} className="connection-fields">
        <label>Connection code<input autoComplete="off" readOnly={!!connection?.dependencies.length} aria-invalid={!!errors.code} {...register('code', { ...required, maxLength: { value: 64, message: 'Use at most 64 characters.' } })} />{error('code')}</label>
        <label>Connection name<input autoComplete="off" aria-invalid={!!errors.name} {...register('name', required)} />{error('name')}</label>
        <label>Database type<select {...register('database_type')} onChange={(event) => {
          const next = event.target.value;
          if (next !== 'MYSQL' && next !== 'POSTGRESQL') return;
          setValue('database_type', next); setValue('port', next === 'MYSQL' ? 3306 : 5432);
          setValue('host', next === 'MYSQL' ? 'mysql' : 'postgres'); setValue('schema_name', next === 'MYSQL' ? '' : 'public');
        }}><option value="POSTGRESQL">PostgreSQL</option><option value="MYSQL">MySQL</option></select></label>
        <label>Host<input autoComplete="off" aria-invalid={!!errors.host} {...register('host', required)} />{error('host')}</label>
        <label>Port<input type="number" min={1} max={65535} aria-invalid={!!errors.port} {...register('port', { valueAsNumber: true, required: 'A port is required.', min: { value: 1, message: 'Use a port from 1 to 65535.' }, max: { value: 65535, message: 'Use a port from 1 to 65535.' } })} />{error('port')}</label>
        <label>Database name<input autoComplete="off" aria-invalid={!!errors.database_name} {...register('database_name', required)} />{error('database_name')}</label>
        {type === 'POSTGRESQL' && <label>Schema<input autoComplete="off" {...register('schema_name')} /></label>}
        <label>Username<input autoComplete="off" aria-invalid={!!errors.username} {...register('username', required)} />{error('username')}</label>
        <label>Password<input type="password" autoComplete="new-password" placeholder={connection ? 'Leave blank to keep current password' : 'Database password'} {...register('password')} /></label>
        <label className="full-width">Description<textarea rows={3} {...register('description')} /></label>
        {Object.keys(errors).length > 0 && <p className="field-error full-width" role="alert">Check the highlighted fields before saving.</p>}
        <div className="connection-actions full-width"><button className="primary-button" type="submit">{busy ? 'Saving…' : 'Save connection'}</button><button type="button" onClick={onCancel}>Cancel</button></div>
      </fieldset>
    </form>
  </section>;
}
