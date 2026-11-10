// Full copy: keep catalogue entries (a strain with aliases, a product, a skill with a policy), edit the strain, and
// read each back on its own screen: geneOS's Hosts and the strain's page, pureOS's products, Guild's skills; then
// reload and read the catalogue again.
//   node full8.mjs ORIGIN PROJECT
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');

async function keep(kind, fields, selects = {}) {
  await go(page, origin, `/p/${project}/catalogues${kind === 'strain' ? '' : '/' + kind + 's'}`);
  await page.waitForTimeout(1500);
  await page.click('[data-testid="catalogue-add"]');
  await page.waitForTimeout(500);
  for (const [k, v] of Object.entries(fields)) await page.fill(`[data-testid="catalogue-field-${k}"]`, v);
  for (const [k, v] of Object.entries(selects)) await page.selectOption(`[data-testid="catalogue-field-${k}"]`, v);
  await page.click('[data-testid="catalogue-keep"]');
  await page.waitForTimeout(2500);
  const prob = page.locator('[data-testid="catalogue-problem"]');
  const kept = page.locator('[data-testid="catalogue-kept"]');
  console.log(`== keep ${kind} ${fields.id}: ` + ((await prob.count()) ? 'PROBLEM ' + (await prob.innerText()) : (await kept.count()) ? await kept.innerText() : '(no kept line)'));
  console.log(drain(log).join('\n'));
}
await keep('strain', { id: 'h14-ethanol-red', name: 'Ethanol Red (H14)', species: 'Saccharomyces cerevisiae', program: 'yeast', aliases: 'Ethanol Red\nS. cerevisiae Ethanol Red', summary: 'An industrial yeast the project reads about.', source: 'the project documents' });
await keep('product', { id: 'h14-ethanol', name: 'Ethanol (H14)', summary: 'Fuel ethanol', source: 'the project' }, { category: '', location: 'secreted' }).catch((e) => console.log('product keep failed', e.message));
await keep('skill', { id: 'h14-hplc', name: 'HPLC for ethanol (H14)', recencyDays: '180', supervisedRuns: '2', mastery: 'Calibrates the column\nReads the ethanol peak', summary: 'Measuring ethanol by HPLC', source: 'the lab' }, { criticality: 'critical' }).catch((e) => console.log('skill keep failed', e.message));
await shot(page, 'full8-skills');

// geneOS hosts and the strain page
await go(page, origin, `/p/${project}/geneos`);
await page.waitForTimeout(2000);
const g = await text(page);
console.log('== geneOS\n' + g.slice(0, 1200));
await shot(page, 'full8-geneos');
await go(page, origin, `/p/${project}/geneos/hosts/h14-ethanol-red`);
await page.waitForTimeout(2500);
await shot(page, 'full8-strain');
console.log('== strain page\n' + (await text(page)).slice(0, 3000));
console.log(drain(log).join('\n'));

// Home tile and palette find the strain by its alias
await go(page, origin, `/p/${project}`);
await page.keyboard.press('Control+k');
await page.waitForTimeout(400);
await page.keyboard.type('Ethanol Red');
await page.waitForTimeout(800);
console.log('== palette "Ethanol Red"\n' + (await page.locator('[role=listbox]').innerText()).slice(0, 1500));
await page.keyboard.press('Escape');
await go(page, origin, '/');
await page.waitForTimeout(1500);
const home = await text(page);
console.log('== home geneOS tile: ' + (home.match(/geneOS\n[^\n]*\n[^\n]*/) || ['?'])[0]);

// Guild skills
await go(page, origin, `/p/${project}/guild/skills`);
await page.waitForTimeout(2000);
await shot(page, 'full8-guild-skills');
console.log('== guild skills\n' + (await text(page)).slice(0, 2500));
console.log(drain(log).join('\n'));
await browser.close();
