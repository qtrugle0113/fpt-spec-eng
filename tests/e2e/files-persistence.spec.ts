import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';

type RetainedFile = { id: string; sha256: string; parser_revision: number; file_name: string; first_row: (string | null)[] };
test('Real file bytes and parser references survive backend container recreation', async ({ request, page }) => {
  const files: RetainedFile[] = JSON.parse(await readFile('/tmp/aat-file-e2e-references.json', 'utf8'));
  expect(files.length).toBeGreaterThanOrEqual(6);
  for (const expected of files) {
    const before = await request.get(`/api/v1/files/${expected.id}`); expect(before.ok()).toBe(true);
    const file = await before.json(); expect(file.sha256).toBe(expected.sha256); expect(file.parser_revision).toBe(expected.parser_revision);
    const preview = await (await request.get(`/api/v1/files/${expected.id}/preview`)).json();
    expect(preview.rows[0]).toEqual(expected.first_row);
    const started = await request.post(`/api/v1/files/${expected.id}/validate`, { data: { expected_sha256: expected.sha256, parser_revision: expected.parser_revision }, headers: { 'Idempotency-Key': randomUUID() } });
    expect(started.status()).toBe(202); const operation = await started.json();
    await expect.poll(async () => (await (await request.get(`/api/v1/operations/${operation.id}`)).json()).state, { timeout: 35000 }).toBe('SUCCEEDED');
  }
  const file = files[0]; await page.goto('/dag-builder');
  await page.getByRole('button', { name: `Open file ${file.file_name} ${file.id}`, exact: true }).click();
  await expect(page.getByRole('region', { name: 'Source file details', exact: true })).toContainText(file.sha256);
});
