// H4-01: each run's page in Chromium (the built app in dist/), its cost card's rows, closing row and words.
//   node screen.mjs <origin> <project> <outdir> <label>=<run id> [<label>=<run id> ...]
import { chromium } from '/home/user/openFermentUI/node_modules/playwright/index.mjs';

const [origin, project, outdir, ...pairs] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage();
for (const pair of pairs) {
  const [label, id] = pair.split('=');
  await page.goto(`${origin}/#/p/${project}/proforma/runs/${id}`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="waterfall"]', { timeout: 60000 }).then(() => page.waitForTimeout(1500)).catch(() => null);
  const rows = await page.$$eval('[data-testid="waterfall-row"], [data-testid="waterfall-total"]', (gs) =>
    gs.map((g) => Array.from(g.querySelectorAll('text')).map((t) => t.textContent).join(' | ')));
  const card = await page.$eval('[data-testid="cost-breakdown"]', (e) => e.innerText).catch(() => '(no cost-breakdown card)');
  const base = await page.$eval('[data-testid="base-case"]', (e) => e.innerText).catch(() => '(no base-case line)');
  console.log(`[screen ${label}] base case: ${base.replace(/\s+/g, ' ').trim()}`);
  for (const r of rows) console.log(`[screen ${label}] row: ${r}`);
  const note = card.split('\n').find((l) => /set price/.test(l));
  console.log(`[screen ${label}] price note: ${note ? note.trim() : '(none)'}`);
  await page.screenshot({ path: `${outdir}/${label}.png`, fullPage: true });
}
await browser.close();
