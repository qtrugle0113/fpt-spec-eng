import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const parser = { encoding: 'utf-8', delimiter: ',', header_present: true,
  quote_character: '"', escape_character: null, null_representation: '\\N' };

test('A fresh browser reconstructs workbook history and typed table details', async ({ page, browser }, info) => {
  const references = JSON.parse(await readFile('/tmp/aat-e2e-artifacts/full-workflows.json', 'utf8'));
  const reference = references.find((item: { code: string }) => item.code.startsWith(`full_pg_${info.project.name}_`));
  expect(reference).toBeTruthy();
  await page.goto('/tables');
  const context = await browser.newContext({ viewport: page.viewportSize() ?? undefined });
  try {
    const fresh = await context.newPage();
    await fresh.goto(page.url());
    const row = fresh.getByRole('row').filter({ hasText: reference.table_job });
    await row.getByRole('button', { name: 'View results', exact: true }).click();
    const results = fresh.getByRole('region', { name: 'Job results', exact: true });
    await expect(results).toContainText(reference.table);
    await results.getByRole('button', { name: 'View table details', exact: true }).click();
    const details = fresh.getByRole('region', { name: 'Table details', exact: true });
    await expect(details.getByRole('heading', { name: 'Live database verification: VERIFIED', exact: true })).toBeVisible();
    await expect(details).toContainText('balance');
    await expect(details).toContainText(/decimal/i);
    await expect(details).toContainText('registered_at');
    await expect(details).toContainText(/timestamp/i);
    await fresh.goto(new URL('/dag-builder', fresh.url()).href);
    const history = fresh.getByRole('region', { name: 'ETL workbook history', exact: true });
    await history.getByRole('row').filter({ hasText: reference.etl_upload })
      .getByRole('button', { name: 'Open ETL workbook', exact: true }).click();
    await fresh.getByRole('button', { name: 'Review validated workbook', exact: true }).click();
    await expect(fresh.getByRole('button', { name: 'Review schedules and load policies', exact: true })).toBeVisible();
    expect(await fresh.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await fresh.locator('body').innerText()).not.toContain('Traceback');
  } finally { await context.close(); }
});

test('Parser candidate stays unsaved and a stale confirmation cannot replace a newer revision', async ({ page, request, browser }, info) => {
  const name = `t139_${info.project.name}_${Date.now()}.txt`;
  const uploaded = await request.post('/api/v1/files', { multipart: {
    parser_json: JSON.stringify(parser), file: { name, mimeType: 'text/plain', buffer: Buffer.from('a;b\n1;2\n') },
  } });
  expect(uploaded.status()).toBe(201);
  const file = await uploaded.json();
  await page.goto('/dag-builder');
  await page.getByRole('button', { name: `Open file ${name} ${file.id}`, exact: true }).click();
  const editor = page.getByRole('form', { name: 'Source parser configuration', exact: true });
  await editor.getByLabel('Delimiter character', { exact: true }).fill(';');
  await expect(editor.getByRole('button', { name: 'Confirm parser change', exact: true })).toBeDisabled();
  await editor.getByRole('button', { name: 'Preview with these settings', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Source data preview', exact: true })
    .getByRole('columnheader', { name: 'a', exact: true })).toBeVisible();
  const saved = await request.get(`/api/v1/files/${file.id}`);
  const original = await saved.json();
  expect(original.parser_revision).toBe(1);
  expect(original.parser.delimiter).toBe(',');
  const changed = await request.patch(`/api/v1/files/${file.id}/parser`, {
    headers: { 'If-Match': saved.headers()['etag'] }, data: { ...parser, delimiter: '|' },
  });
  expect(changed.status()).toBe(200);
  await editor.getByRole('button', { name: 'Confirm parser change', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Resource revision changed.' })).toBeVisible();
  const latest = await (await request.get(`/api/v1/files/${file.id}`)).json();
  expect(latest.parser_revision).toBe(2);
  expect(latest.parser.delimiter).toBe('|');
  const context = await browser.newContext({ viewport: page.viewportSize() ?? undefined });
  try {
    const fresh = await context.newPage();
    await fresh.goto(page.url());
    await fresh.getByRole('button', { name: `Open file ${name} ${file.id}`, exact: true }).click();
    await expect(fresh.getByRole('form', { name: 'Source parser configuration', exact: true })
      .getByLabel('Delimiter character', { exact: true })).toHaveValue('|');
  } finally { await context.close(); }
});
