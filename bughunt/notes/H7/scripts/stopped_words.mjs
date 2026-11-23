// H7: what each detail page says when the service does not answer (every /api request refused), against what it
// says with the service up. A page that says a thing the project keeps is "not found" while the service is away
// tells the person something false.
//   node stopped_words.mjs <origin> <project> <ids.json> <out.json>
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';

const [origin, project, idsFile, out] = process.argv.slice(2);
const ids = JSON.parse(readFileSync(idsFile, 'utf8'));
const PATHS = [
  `/runbooks/${ids.runbook}`,
  `/runbooks/protocols/${ids.protocol}`,
  `/runbooks/protocols/${ids.protocol}/edit`,
  `/geneos/hosts/${ids.strain}`,
  `/primer/${ids.lesson}`,
  `/guild/people/${ids.person}`,
  `/guild/skills/${ids.skill}`,
  `/postdoc/${ids.conversation}`,
  `/flowsheets/${ids.flowsheet}`,
  `/proforma/runs/${ids.run}`,
  `/proforma/comparisons/${ids.comparison}`,
  `/biorepo/paper/${ids.paper}`,
  `/biorepo/artifacts/${ids.artifact}`,
  `/pureos/train/${ids.train}`,
  `/runbooks/depositions/${ids.deposition ?? 'dep-missing'}`,
  `/runbooks/depositions/${ids.deposition ?? 'dep-missing'}/bench`,
  '/catalogues',
  '/',
];
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const results = {};
for (const state of ['up', 'stopped']) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  if (state === 'stopped') await context.route('**/api/**', (r) => r.abort('connectionrefused'));
  for (const path of PATHS) {
    const page = await context.newPage();
    await page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path === '/' ? '' : path}`, { waitUntil: 'load' });
    await page.waitForTimeout(3500);
    const main = await page.locator('#of-main').innerText().catch(async () => page.locator('body').innerText());
    (results[path] ??= {})[state] = main.replace(/\s+/g, ' ').trim().slice(0, 420);
    await page.close();
  }
  await context.close();
}
for (const [path, r] of Object.entries(results)) console.log(`\n${path}\n  up:      ${r.up.slice(0, 200)}\n  stopped: ${r.stopped.slice(0, 300)}`);
writeFileSync(out, JSON.stringify(results, null, 1));
await browser.close();
