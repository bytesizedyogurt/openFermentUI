// H2-06: open a plant's reference page in headless Chromium before any run of it, and print what the page's
// header and its "Held to its package's own test" card say. One JSON object on stdout; no screenshot, no write.
//   node screen.mjs ORIGIN PROJECT PLANT
import { chromium } from 'playwright';

const [origin, project, plant] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
const asked = page
  .waitForResponse((r) => r.url().includes(`/api/library/${plant}/regression`), { timeout: 60000 })
  .then(async (r) => ({ status: r.status(), body: await r.text() }))
  .catch(() => null);
await page.goto(`${origin}/#/p/${project}/proforma/reference/${plant}`);
const regressionAnswer = await asked;
await page.waitForLoadState('networkidle').catch(() => {});
await page.locator('[data-testid="regression-table"]').first().waitFor({ timeout: 30000 }).catch(() => {});
await page.waitForTimeout(1500);
const out = await page.evaluate(() => {
  const text = (sel) => (document.querySelector(sel)?.textContent ?? '').replace(/\s+/g, ' ').trim() || null;
  return {
    heldTo: text('[data-testid="reference-package-test"]'),
    configuration: text('[data-testid="reference-configuration"]'),
    card: text('[data-testid="regression-table"] p.text-caption'),
  };
});
console.log(JSON.stringify({ regressionAnswer, ...out }));
await browser.close();
