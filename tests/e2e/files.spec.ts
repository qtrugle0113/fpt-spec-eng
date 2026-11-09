import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const parser = { encoding: 'utf-8', delimiter: ',', header_present: true, quote_character: '"', escape_character: null, null_representation: '\\N' };
type RetainedFile = { id: string; sha256: string; parser_revision: number; file_name: string; first_row: (string | null)[] };
async function retain(file: RetainedFile) {
  const path = '/tmp/aat-file-e2e-references.json';
  let previous: RetainedFile[] = [];
  try { previous = JSON.parse(await readFile(path, 'utf8')); } catch { /* First public fixture. */ }
  await writeFile(path, JSON.stringify([...previous, file]));
}

test('Source upload above 1 MiB reaches the API through nginx', async ({ request }) => {
  const buffer = Buffer.from('a,b\n' + '1,2\n'.repeat(300_000));
  const response = await request.post('/api/v1/files', { multipart: { parser_json: JSON.stringify(parser), file: { name: 'large-public.csv', mimeType: 'text/csv', buffer } } });
  expect(response.status()).toBe(201); const file = await response.json();
  expect(file.size).toBe(buffer.length); expect(file.sha256).toBe(createHash('sha256').update(buffer).digest('hex'));
  expect(file.validation_status).toBe('PENDING');
});

test('CSV and headerless TXT retain typed NULL semantics and stable source references', async ({ page, request }, testInfo) => {
  await page.goto('/dag-builder');
  await expect(page.getByRole('heading', { name: 'File Sources', exact: true })).toBeVisible();
  const cases = [
    { name: 'same.csv', data: '\ufeffid,name,note\n1,"\\N",\\N\n2,"",\n3,"Nguyễn, An\nline two",0\n', delimiter: ',', header: true, first: ['1', '\\N', null] },
    { name: 'source.txt', data: '1|Nguyễn\n2|text\n', delimiter: '|', header: false, first: ['1', 'Nguyễn'] },
  ];
  for (const item of cases) {
    const form = page.getByRole('form', { name: 'Upload source file', exact: true });
    const buffer = Buffer.from(item.data);
    await form.getByLabel('Source file', { exact: true }).setInputFiles({ name: item.name, mimeType: 'text/plain', buffer });
    await form.getByLabel('Source file', { exact: true }).focus(); await page.keyboard.press('Tab');
    await expect(form.getByLabel('Encoding', { exact: true })).toBeFocused();
    await form.getByRole('combobox', { name: 'Delimiter preset', exact: true }).selectOption(item.delimiter);
    await form.getByRole('checkbox', { name: 'First record contains column headers', exact: true }).setChecked(item.header);
    const uploaded = page.waitForResponse(response => response.url().endsWith('/api/v1/files') && response.request().method() === 'POST');
    await form.getByRole('button', { name: 'Upload source file', exact: true }).click();
    const file = await (await uploaded).json();
    expect(file.sha256).toBe(createHash('sha256').update(buffer).digest('hex'));
    expect(file.parser.header_present).toBe(item.header);
    const details = page.getByRole('region', { name: 'Source file details', exact: true });
    await details.getByRole('button', { name: 'Preview with these settings', exact: true }).click();
    const preview = page.getByRole('region', { name: 'Source data preview', exact: true });
    await expect(preview).toBeVisible();
    if (item.header) {
      await expect(preview.getByLabel('SQL NULL', { exact: true })).toHaveCount(1);
      await expect(preview.getByLabel('Empty string', { exact: true })).toHaveCount(2);
      await expect(preview.getByText('\\N', { exact: true })).toBeVisible();
    } else await expect(preview.getByRole('columnheader', { name: 'column_1', exact: true })).toBeVisible();
    await details.getByRole('button', { name: 'Validate full file', exact: true }).click();
    await expect(details.getByRole('heading', { name: 'Validation: SUCCEEDED', exact: true })).toBeVisible({ timeout: 35000 });
    await details.getByRole('button', { name: 'Select as ETL source', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Selected ETL source', exact: true })).toContainText(file.id);
    const fresh = await (await request.get(`/api/v1/files/${file.id}`)).json();
    expect(fresh.validation_status).toBe('VALID'); expect(fresh.parser_revision).toBe(1);
    await retain({ id: file.id, sha256: file.sha256, parser_revision: 1, file_name: item.name, first_row: item.first });
    if (item.header) {
      const duplicate = await (await request.post('/api/v1/files', { multipart: { parser_json: JSON.stringify(parser), file: { name: item.name, mimeType: 'text/csv', buffer } } })).json();
      expect(duplicate.id).not.toBe(file.id); expect(duplicate.sha256).toBe(file.sha256);
      expect(duplicate.needs_revalidation).toBe(true);
    }
    await page.reload();
    await page.getByRole('button', { name: `Open file ${item.name} ${file.id}`, exact: true }).click();
    await expect(page.getByRole('region', { name: 'Source file details', exact: true })).toContainText(file.sha256);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await mkdir('/tmp/aat-e2e-artifacts', { recursive: true });
  await page.screenshot({ path: `/tmp/aat-e2e-artifacts/files-${testInfo.project.name}.png`, fullPage: true });
});

test('Candidate preview requires confirmation and stale parser edits fail safely', async ({ page, request }) => {
  await page.goto('/dag-builder'); const buffer = Buffer.from('a;b\n1;2\n');
  const form = page.getByRole('form', { name: 'Upload source file', exact: true });
  await form.getByLabel('Source file', { exact: true }).setInputFiles({ name: 'settings.txt', mimeType: 'text/plain', buffer });
  const uploaded = page.waitForResponse(response => response.url().endsWith('/api/v1/files') && response.request().method() === 'POST');
  await form.getByRole('button', { name: 'Upload source file', exact: true }).click(); const file = await (await uploaded).json();
  const details = page.getByRole('region', { name: 'Source file details', exact: true });
  await details.getByRole('button', { name: 'Validate full file', exact: true }).click();
  await expect(details.getByRole('heading', { name: 'Validation: SUCCEEDED', exact: true })).toBeVisible({ timeout: 35000 });
  await details.getByRole('button', { name: 'Select as ETL source', exact: true }).click();
  const editor = page.getByRole('form', { name: 'Source parser configuration', exact: true });
  await editor.getByLabel('Delimiter character', { exact: true }).fill(';');
  await expect(details.getByRole('button', { name: 'Validate full file', exact: true })).toBeDisabled();
  await expect(editor.getByRole('button', { name: 'Confirm parser change', exact: true })).toBeDisabled();
  await editor.getByRole('button', { name: 'Preview with these settings', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Source data preview', exact: true }).getByRole('columnheader', { name: 'a', exact: true })).toBeVisible();
  const old = await request.get(`/api/v1/files/${file.id}`);
  expect((await old.json()).parser.delimiter).toBe(',');
  const changedElsewhere = await request.patch(`/api/v1/files/${file.id}/parser`, { data: { ...parser, delimiter: '|' }, headers: { 'If-Match': old.headers()['etag'] } });
  expect(changedElsewhere.status()).toBe(200);
  await editor.getByRole('button', { name: 'Confirm parser change', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Resource revision changed.' })).toBeVisible();
  await details.getByRole('button', { name: 'Refresh source details', exact: true }).click();
  await expect(editor.getByLabel('Delimiter character', { exact: true })).toHaveValue('|');
  await expect(page.getByRole('region', { name: 'Selected ETL source', exact: true })).toHaveCount(0);
  await editor.getByLabel('Delimiter character', { exact: true }).fill(';');
  await editor.getByRole('button', { name: 'Preview with these settings', exact: true }).click();
  await editor.getByRole('button', { name: 'Confirm parser change', exact: true }).click();
  await expect(editor.getByLabel('Delimiter character', { exact: true })).toHaveValue(';');
  await expect(details).toContainText('Parser revision 3');
  await details.getByRole('button', { name: 'Validate full file', exact: true }).click();
  await expect(details.getByRole('heading', { name: 'Validation: SUCCEEDED', exact: true })).toBeVisible({ timeout: 35000 });
  const current = await (await request.get(`/api/v1/files/${file.id}`)).json();
  expect(current.sha256).toBe(file.sha256); expect(current.parser_revision).toBe(3);
  await retain({ id: file.id, sha256: file.sha256, parser_revision: 3, file_name: file.file_name, first_row: ['1', '2'] });
});

test('Full validation finds an invalid tail after a successful bounded preview', async ({ page }) => {
  await page.goto('/dag-builder');
  const form = page.getByRole('form', { name: 'Upload source file', exact: true });
  await form.getByLabel('Source file', { exact: true }).setInputFiles({ name: 'invalid-tail.csv', mimeType: 'text/csv', buffer: Buffer.from('a,b\n' + '1,2\n'.repeat(101) + 'private-bad-row\n') });
  await form.getByRole('button', { name: 'Upload source file', exact: true }).click();
  const details = page.getByRole('region', { name: 'Source file details', exact: true });
  await details.getByRole('button', { name: 'Preview with these settings', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Data preview (100 rows)', exact: true })).toBeVisible();
  await details.getByRole('button', { name: 'Validate full file', exact: true }).click();
  await expect(details.getByRole('heading', { name: 'Validation: FAILED', exact: true })).toBeVisible({ timeout: 35000 });
  await expect(details.getByRole('region', { name: 'File validation operation', exact: true })).toContainText('Line 103.');
  await expect(details.getByRole('button', { name: 'Select as ETL source', exact: true })).toBeDisabled();
  await expect(page.locator('body')).not.toContainText('private-bad-row');
});
