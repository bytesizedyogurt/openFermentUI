// H4-02: the composite run's page in Chromium (the built app in dist/): its cost card's rows, the closing row,
// the base-case line and the price note, written to <outdir>/screen.json with a screenshot of the card.
//   node screen.mjs <origin> <project> <outdir> <run id>
import { writeFileSync } from 'node:fs';
import { chromium } from '/home/user/openFermentUI/node_modules/playwright/index.mjs';

const [origin, project, outdir, id] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage();
await page.goto(`${origin}/#/p/${project}/proforma/runs/${id}`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="waterfall"]', { timeout: 60000 }).then(() => page.waitForTimeout(1500)).catch(() => null);
const rows = await page.$$eval('[data-testid="waterfall-row"], [data-testid="waterfall-total"]', (gs) =>
  gs.map((g) => Array.from(g.querySelectorAll('text')).map((t) => t.textContent.trim()).filter(Boolean).join(' ')));
const card = await page.$eval('[data-testid="cost-breakdown"]', (e) => e.innerText).catch(() => '');
const base = await page.$eval('[data-testid="base-case"]', (e) => e.innerText).catch(() => null);
const note = card.split('\n').find((l) => /set price/.test(l)) || null;
const out = { composite: { runId: id, rows, base: base && base.replace(/\s+/g, ' ').trim(), note: note && note.trim() } };
// The card itself (the page scrolls inside its own frame, so a full-page shot holds the first screen alone).
await page.locator('[data-testid="cost-breakdown"]').screenshot({ path: `${outdir}/composite.png` })
  .catch(() => page.screenshot({ path: `${outdir}/composite.png`, fullPage: true }));
writeFileSync(`${outdir}/screen.json`, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out.composite.rows));
await browser.close();
