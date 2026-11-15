// Kiểm chứng UI đọc dữ liệu thật; fixture chỉ cho trạng thái biên cô lập.
const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const output = path.join(root, '.tools/ui-refresh', process.env.AAT_UI_BASELINE ? 'baseline' : 'current');
const apiTarget = process.env.AAT_UI_API_TARGET ?? 'http://127.0.0.1:28000';
const fixturesOnly = process.env.AAT_UI_FIXTURES_ONLY === '1';
const routes = [['/', 'Dashboard'], ['/connections', 'Connections'], ['/tables', 'Table Management'], ['/dag-builder', 'DAG Builder'], ['/monitoring', 'DAG Monitoring'], ['/settings', 'Settings']];
const settings = { default_batch_size: 1000, dashboard_refresh_interval: 30, default_timezone: 'UTC', staging_retention_days: 7, revision: 1, application_version: 'isolated-test', airflow_connectivity_status: 'UNAVAILABLE' };
const emptyDashboard = { inventory: { total: 0, active: 0, paused: 0 }, run_metrics: { total: 0, successful: 0, failed: 0, running: 0, success_rate: null }, lifetime_metrics: {}, time_series: [], recent_runs: [], next_scheduled_runs: [], schedule_groups: [], last_successful_run: null, last_successful_run_availability: 'UNAVAILABLE', completeness: 'INCOMPLETE', unavailable_fields: ['test fixture'], fetched_at: null, stale: true, timezone: 'UTC', from: '2026-11-01', to: '2026-11-15' };
async function fixture(route) {
  const pathname = new URL(route.request().url()).pathname;
  const data = pathname.endsWith('/settings') ? settings : pathname.endsWith('/dashboard') ? emptyDashboard : pathname.endsWith('/health/live') ? { status: 'ALIVE' } : { items: [], total: 0, next_offset: null };
  await route.fulfill({ status: 200, contentType: 'application/json', headers: { etag: '"1"' }, body: JSON.stringify(data) });
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const { preview } = await import('vite');
  const server = await preview({ root: path.join(root, 'frontend'), configFile: false, preview: { host: '127.0.0.1', port: 4178, strictPort: true, proxy: { '/api': { target: apiTarget, changeOrigin: true } } } });
  let browser;
  const results = [], failures = [], downloads = [];
  async function check(name, work) {
    try { const detail = await work(); results.push({ name, status: 'PASS', detail }); }
    catch (error) { failures.push({ name, message: error.message }); }
  }
  try {
    if (!fixturesOnly) {
      const health = await fetch(apiTarget + '/api/v1/health/live');
      assert.equal(health.status, 200, 'Real backend must be available; use explicit fixtures-only mode for isolated checks');
    }
    browser = await chromium.launch({ headless: true });
    for (const viewport of [{ width: 1366, height: 768 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      if (fixturesOnly) await page.route('**/api/v1/**', fixture);
      for (const [route, title] of routes) {
        await check(`${viewport.width}:${title}`, async () => {
          await page.goto(`http://127.0.0.1:4178${route}`);
          await page.getByRole('heading', { name: title, exact: true }).waitFor();
          if (route === '/') await page.getByRole('heading', { name: 'Total DAGs', exact: true }).waitFor();
          else if (route === '/settings') await page.getByLabel('Default Batch Size (rows)').waitFor();
          else await page.waitForFunction(() => ![...document.querySelectorAll('main [role="status"]')].some(el => /^Loading /.test(el.textContent)));
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No full-page horizontal overflow');
          const firstControl = page.locator('main input, main select, main button, main a[download]').first();
          const bounds = await firstControl.boundingBox();
          assert.ok(bounds && bounds.y + bounds.height < viewport.height, 'First main control is in viewport');
          let firstRowBottom;
          if (viewport.width === 1366 && !fixturesOnly && route !== '/settings') {
            const row = page.locator('main tbody tr').first();
            if (await row.count()) {
              const rowBounds = await row.boundingBox(); firstRowBottom = rowBounds.y + rowBounds.height;
              assert.ok(firstRowBottom < viewport.height, 'First data row fully fits the desktop viewport');
            }
          }
          if (viewport.width === 1366 && route === '/') {
            const metrics = await page.locator('.dashboard-metrics').boundingBox();
            assert.ok(metrics && metrics.y + metrics.height < 640, 'All overview metrics fit compactly');
            const recent = await page.getByRole('heading', { name: 'Recent runs', exact: true }).boundingBox();
            assert.ok(recent && recent.y < 768, 'Recent runs is visible without scrolling past secondary panels');
          }
          await page.getByRole('link', { name: 'Skip to content' }).focus();
          await page.keyboard.press('Enter');
          assert.equal(await page.getByRole('main').evaluate(el => el === document.activeElement), true);
          await page.locator('h1').click();
          await page.keyboard.press('Tab');
          const focus = await page.evaluate(() => ({ tag: document.activeElement.tagName, outline: getComputedStyle(document.activeElement).outlineStyle }));
          assert.notEqual(focus.tag, 'BODY');
          assert.notEqual(focus.outline, 'none', 'Keyboard focus is visible');
          await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
          await page.screenshot({ path: path.join(output, `${viewport.width}-${title.toLowerCase().replaceAll(' ', '-')}.png`), fullPage: true });
          return { noOverflow: true, firstControlY: bounds.y, firstRowBottom, keyboard: true };
        });
      }
      await check(`${viewport.width}:navigation`, async () => {
        if (viewport.width === 390) await page.getByRole('button', { name: 'Open menu' }).click();
        const navigation = page.getByRole('navigation', { name: 'Main navigation' });
        assert.equal(await navigation.getByRole('link').count(), 6);
        await page.getByRole('searchbox', { name: 'Find a page' }).fill('connections');
        assert.equal(await navigation.getByRole('link').count(), 1);
        await navigation.getByRole('link', { name: 'Connections', exact: true }).click();
        if (viewport.width === 390) assert.equal(await page.getByRole('button', { name: 'Open menu' }).getAttribute('aria-expanded'), 'false');
        assert.deepEqual(errors, []);
      });
      await page.close();
    }
    const page = await browser.newPage();
    if (fixturesOnly) await page.route('**/api/v1/**', fixture);
    for (const [route, label] of [['/tables', 'Download Table Definition template'], ['/dag-builder', 'Download ETL Definition template']]) {
      await check(label, async () => {
        await page.goto('http://127.0.0.1:4178' + route);
        const link = page.getByRole('link', { name: label, exact: true });
        assert.equal(await link.evaluate(el => el.classList.contains('action-link')), true, 'Download has button appearance');
        const bounds = await link.boundingBox(); assert.ok(bounds.height >= 36);
        if (!fixturesOnly) {
          const downloadPromise = page.waitForEvent('download'); await link.click();
          const download = await downloadPromise; const file = path.join(output, download.suggestedFilename());
          await download.saveAs(file); assert.ok(fs.statSync(file).size > 1000);
          assert.equal(fs.readFileSync(file).subarray(0, 2).toString(), 'PK', 'Downloaded workbook is a ZIP-based XLSX');
          downloads.push({ name: download.suggestedFilename(), bytes: fs.statSync(file).size });
        }
      });
    }
    if (!fixturesOnly) await check('Airflow popup from real inventory', async () => {
      await page.goto('http://127.0.0.1:4178/monitoring');
      const link = page.getByRole('link', { name: 'Open Airflow', exact: true }).first(); await link.waitFor();
      const href = await link.getAttribute('href');
      assert.ok(await link.evaluate(el => el.classList.contains('action-link')));
      const popupPromise = page.waitForEvent('popup'); await link.click(); const popup = await popupPromise;
      await popup.waitForLoadState('domcontentloaded');
      assert.ok(popup.url().startsWith(new URL(href).origin), 'Popup reaches actual Airflow origin (login redirect allowed)');
      await popup.screenshot({ path: path.join(output, 'airflow-popup.png') }); await popup.close();
    });
    if (!fixturesOnly) await check('Read-only workflow and connection details', async () => {
      await page.goto('http://127.0.0.1:4178/connections');
      await page.getByRole('button', { name: 'Add connection', exact: true }).click();
      await page.getByRole('heading', { name: 'Add connection', exact: true }).waitFor();
      assert.ok(await page.getByLabel('Connection code', { exact: true }).isVisible());
      await page.getByRole('button', { name: 'Cancel', exact: true }).click();
      await page.goto('http://127.0.0.1:4178/monitoring');
      await page.getByRole('button', { name: 'View workflow', exact: true }).first().click();
      const link = page.getByRole('link', { name: 'Open workflow in Airflow', exact: true }); await link.waitFor();
      assert.ok(await link.evaluate(el => el.classList.contains('action-link')));
      const run = page.getByRole('button', { name: 'View run details', exact: true }).first();
      await run.waitFor(); await run.click();
      await page.getByRole('heading', { name: 'Run details', exact: true }).waitFor();
      await page.getByRole('heading', { name: 'Task attempts', exact: true }).waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: path.join(output, 'monitoring-details.png'), fullPage: true });
    });
    await check('isolated:long-identifiers', async () => {
      const isolated = await browser.newPage({ viewport: { width: 390, height: 844 } });
      try {
        await isolated.route('**/api/v1/**', async route => {
          if (!new URL(route.request().url()).pathname.endsWith('/dags')) return fixture(route);
          await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ items: [{ dag_id: 'long_workflow_'.repeat(25), ownership: 'EXTERNAL', is_paused: false, latest_run_status: 'running', airflow_url: 'http://127.0.0.1:28080/dags/long', last_successful_run: null, last_successful_run_availability: 'UNKNOWN' }], total: 1, next_offset: null }) });
        });
        await isolated.goto('http://127.0.0.1:4178/monitoring');
        await isolated.getByRole('button', { name: 'View workflow' }).waitFor();
        assert.ok(await isolated.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        const table = isolated.locator('.table-scroll');
        await table.focus(); await isolated.keyboard.press('ArrowRight');
        assert.ok(await table.evaluate(el => el.scrollWidth > el.clientWidth && el === document.activeElement));
        await isolated.screenshot({ path: path.join(output, 'isolated-long-identifiers.png'), fullPage: true });
      } finally { await isolated.close(); }
    });
    await check('isolated:settings-busy-conflict', async () => {
      const isolated = await browser.newPage({ viewport: { width: 1366, height: 768 } });
      try {
        await isolated.route('**/api/v1/**', async route => {
          if (route.request().method() !== 'PATCH') return fixture(route);
          await new Promise(resolve => setTimeout(resolve, 1200));
          await route.fulfill({ status: 412, contentType: 'application/json', body: JSON.stringify({ error: { code: 'TEST_STALE', message: 'Isolated stale revision.', request_id: 'isolated' } }) });
        });
        await isolated.goto('http://127.0.0.1:4178/settings');
        const save = isolated.getByRole('button', { name: 'Save settings', exact: true });
        await save.waitFor(); assert.equal(await save.isDisabled(), true);
        await isolated.getByLabel('Default Batch Size (rows)').fill('2048'); await save.click();
        const saving = isolated.getByRole('button', { name: 'Saving…', exact: true }); await saving.waitFor();
        assert.equal(await saving.isDisabled(), true);
        await isolated.getByRole('alert').waitFor();
        assert.equal(await save.isDisabled(), true);
        assert.ok((await isolated.getByRole('alert').textContent()).includes('Settings changed in another session'));
      } finally { await isolated.close(); }
    });
    // Các ca cô lập dưới đây không được tính là bằng chứng tích hợp backend.
    for (const mode of ['empty', 'error', 'loading']) {
      await check(`isolated:${mode}`, async () => {
        const isolated = await browser.newPage({ viewport: { width: 390, height: 844 } });
        try {
          await isolated.route('**/api/v1/**', async route => {
            if (!route.request().url().includes('/connections')) return fixture(route);
            if (mode === 'error') return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'TEST_UNAVAILABLE', message: 'Isolated connection failure.', request_id: 'isolated' } }) });
            if (mode === 'loading') await new Promise(resolve => setTimeout(resolve, 1500));
            return fixture(route);
          });
          await isolated.goto('http://127.0.0.1:4178/connections');
          if (mode === 'empty') await isolated.getByText('No connections match these filters.').waitFor();
          if (mode === 'error') await isolated.getByRole('alert').waitFor();
          if (mode === 'loading') await isolated.getByText('Loading connections…', { exact: true }).waitFor();
          assert.ok(await isolated.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
          await isolated.screenshot({ path: path.join(output, `isolated-${mode}.png`), fullPage: true });
        } finally { await isolated.close(); }
      });
    }
    await check('isolated:dashboard-stale', async () => {
      const isolated = await browser.newPage({ viewport: { width: 1366, height: 768 } });
      try {
        await isolated.route('**/api/v1/**', fixture);
        await isolated.goto('http://127.0.0.1:4178/');
        await isolated.getByRole('heading', { name: 'Total DAGs', exact: true }).waitFor();
        assert.ok((await isolated.getByRole('status').innerText()).includes('Stale data'));
        assert.equal(await isolated.locator('.metric-card').count(), 8);
        assert.equal(await isolated.locator('.metric-card').filter({ has: isolated.getByRole('heading', { name: 'Success Rate', exact: true }) }).locator('strong').innerText(), 'Not available');
        await isolated.getByText('No runs in this period.', { exact: true }).waitFor();
        await isolated.screenshot({ path: path.join(output, 'isolated-dashboard-stale.png'), fullPage: true });
      } finally { await isolated.close(); }
    });
    await check('Theme contrast and Airflow link inventory', async () => {
      const contrast = (fg, bg) => {
        const luminance = hex => {
          const rgb = hex.match(/\w\w/g).map(value => parseInt(value, 16) / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
          return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
        };
        const a = luminance(fg), b = luminance(bg); return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      };
      const textPairs = [['ffffff', '007f79'], ['586d79', 'ffffff'], ['006963', 'ffffff'], ['263d49', 'ffffff'], ['236544', 'e7f5ed'], ['992e2e', 'fff0f0'], ['795018', 'fff5df']];
      const ratios = textPairs.map(pair => ({ pair, ratio: contrast(...pair) }));
      for (const item of ratios) assert.ok(item.ratio >= 4.5, `Text contrast ${item.pair}`);
      assert.ok(contrast('005e59', 'ffffff') >= 3);
      if (!fixturesOnly) {
        for (const route of ['/', '/monitoring']) {
          await page.goto('http://127.0.0.1:4178' + route);
          if (route === '/') await page.getByRole('heading', { name: 'Lifetime history', exact: true }).waitFor();
          else await page.getByRole('button', { name: 'View workflow', exact: true }).first().waitFor();
          for (const link of await page.locator('main a[target="_blank"]').all()) {
            assert.ok(await link.evaluate(el => el.classList.contains('action-link')));
            assert.equal(await link.getAttribute('rel'), 'noreferrer');
          }
        }
      }
      return { textRatios: ratios, focusMinimum: 3 };
    });
    await page.close();
    const report = { mode: fixturesOnly ? 'isolated-fixtures-only' : 'real-api-read-only', node: process.version, browser: browser.version(), apiTarget, results, failures, downloads };
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    if (failures.length) process.exitCode = 1;
  } finally { await browser?.close(); await server.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
