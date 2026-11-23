// H4: render a run's page in Chromium and read its cost card (the waterfall rows, the total row,
// the notes and the base-case line), to set beside the service's own lines.
//   node costcard.mjs http://127.0.0.1:8840 h4p <artifact id> [<artifact id> ...]
import { chromium } from '/home/user/openFermentUI/node_modules/playwright/index.mjs';

const [origin, project, ...ids] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage();
const out = {};
for (const id of ids) {
  await page.goto(`${origin}/#/p/${project}/proforma/runs/${id}`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="waterfall"]', { timeout: 45000 }).then(() => page.waitForTimeout(1500)).catch(() => null);
  const rows = await page.$$eval('[data-testid="waterfall-row"], [data-testid="waterfall-total"]', (gs) =>
    gs.map((g) => ({ line: g.getAttribute('data-line'), texts: Array.from(g.querySelectorAll('text')).map((t) => t.textContent) })));
  const card = await page.$eval('[data-testid="cost-breakdown"]', (e) => e.innerText).catch(() => null);
  const base = await page.$eval('[data-testid="base-case"]', (e) => e.innerText).catch(() => null);
  const tables = await page.$$eval('table', (ts) => ts.map((t) => t.innerText.slice(0, 3000)));
  out[id] = { rows, card, base, tables: tables.filter((t) => /Per unit|Capital recovery/.test(t)) };
  await page.screenshot({ path: `/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H4/run-${id}.png`, fullPage: true });
}
console.log(JSON.stringify(out, null, 1));
await browser.close();
