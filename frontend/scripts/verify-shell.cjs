const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '../..');
fs.mkdirSync(path.join(root, '.tools'), { recursive: true });
const baseURL = process.env.AAT_SHELL_BASE_URL ?? 'http://127.0.0.1:4173';
const server = process.env.AAT_SHELL_BASE_URL ? null : spawn(process.execPath, [path.join(root, 'frontend/node_modules/vite/bin/vite.js'), 'preview', '--host', '127.0.0.1', '--port', '4173', '--strictPort'], {
  cwd: path.join(root, 'frontend'), windowsHide: true, stdio: 'ignore',
});

(async () => {
  let browser;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 50; attempt++) {
      if (server && server.exitCode !== null) throw Error('Owned preview exited before validation');
      try { ready = (await fetch(baseURL)).ok; } catch {}
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(ready, 'Preview must become ready');
    browser = await chromium.launch({ headless: true });
    const results = [];
    for (const width of [1440, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      for (const [route, title] of [['/', 'Dashboard'], ['/connections', 'Connections'], ['/tables', 'Table Management'], ['/dag-builder', 'DAG Builder'], ['/monitoring', 'DAG Monitoring'], ['/settings', 'Settings']]) {
        await page.goto(`${baseURL}${route}`);
        await page.getByRole('heading', { name: title, exact: true }).waitFor();
        assert.ok(await page.getByRole('status').isVisible());
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        results.push({ width, route, heading: title, noHorizontalOverflow: true });
      }
      if (width === 390) await page.getByRole('button', { name: 'Open menu' }).click();
      await page.getByRole('searchbox', { name: 'Find a page' }).fill('connections');
      assert.equal(await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link').count(), 1);
      await page.getByRole('link', { name: 'Connections', exact: true }).click();
      await page.getByRole('heading', { name: 'Connections', exact: true }).waitFor();
      if (width === 390) assert.equal(await page.getByRole('button', { name: 'Open menu' }).getAttribute('aria-expanded'), 'false');
      assert.deepEqual(errors, []);
      await page.screenshot({ path: path.join(root, `.tools/shell-${width}.png`), fullPage: true });
      await page.close();
    }
    const version = browser.version();
    fs.writeFileSync(path.join(root, '.tools/shell-validation.json'), JSON.stringify({ browser: version, results }, null, 2));
    console.log(JSON.stringify({ status: 'PASS', browser: version, routesAndViewports: results.length, navigationSearch: true, mobileMenu: true, pageErrors: 0 }));
  } finally {
    if (browser) await browser.close();
    server?.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
