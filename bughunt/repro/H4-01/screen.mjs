// H4-01: each run's page in Chromium (the built app in dist/): its cost card's rows, the closing row, the
// base-case line and the price note, written to <outdir>/screen.json with a screenshot each.
//   node screen.mjs <origin> <project> <outdir> <label>=<run id> [<label>=<run id> ...]
import { writeFileSync } from 'node:fs';
import { chromium } from '/home/user/openFermentUI/node_modules/playwright/index.mjs';

const [origin, project, outdir, ...pairs] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage();
const out = {};
for (const pair of pairs) {
  const [label, id] = pair.split('=');
  await page.goto(`${origin}/#/p/${project}/proforma/runs/${id}`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="waterfall"]', { timeout: 60000 }).then(() => page.waitForTimeout(1500)).catch(() => null);
  const rows = await page.$$eval('[data-testid="waterfall-row"], [data-testid="waterfall-total"]', (gs) =>
    gs.map((g) => Array.from(g.querySelectorAll('text')).map((t) => t.textContent.trim()).filter(Boolean).join(' ')));
  const card = await page.$eval('[data-testid="cost-breakdown"]', (e) => e.innerText).catch(() => '');
  const base = await page.$eval('[data-testid="base-case"]', (e) => e.innerText).catch(() => null);
  const note = card.split('\n').find((l) => /set price/.test(l)) || null;
  out[label] = { runId: id, rows, base: base && base.replace(/\s+/g, ' ').trim(), note: note && note.trim() };
  await page.screenshot({ path: `${outdir}/${label}.png`, fullPage: true });
}
writeFileSync(`${outdir}/screen.json`, JSON.stringify(out, null, 1));
await browser.close();
