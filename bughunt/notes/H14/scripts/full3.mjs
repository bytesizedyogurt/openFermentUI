// Full copy: run a library plant from Studies (cornstover, the plant a reference run already holds), wait for it,
// then choose it and the kept reference run and compare them; open the comparison's page.
//   node full3.mjs ORIGIN PROJECT [PLANT] [CONFIG]
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project, plant = 'cornstover', config] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await go(page, origin, `/p/${project}/proforma/studies`);
await page.waitForTimeout(2000);
await page.selectOption('[data-testid="run-plant-engine"]', 'biosteam');
await page.selectOption('[data-testid="run-plant-plant"]', plant);
await page.waitForTimeout(800);
if (config) await page.selectOption('[data-testid="run-plant-configuration"]', { label: config });
const t0 = Date.now();
await page.click('[data-testid="run-plant-go"]');
for (let i = 0; i < 600; i++) {
  await page.waitForTimeout(1000);
  if (await page.locator('[data-testid="run-plant-ran"], [data-testid="run-plant-failed"], [data-testid="run-plant-problem"]').count()) break;
}
console.log('waited', Math.round((Date.now() - t0) / 1000), 's');
const card = await page.locator('[data-testid="studies-run-plant"]').innerText();
console.log('== run card\n' + card);
await shot(page, `full3-ran-${plant}`);
const ran = page.locator('[data-testid="run-plant-ran"]');
const runId = (await ran.count()) ? await ran.getAttribute('data-run') : null;
console.log('run id', runId, 'status', (await ran.count()) ? await ran.getAttribute('data-status') : null);
console.log(drain(log).join('\n'));
await page.waitForTimeout(2000);
const runs = await page.locator('[data-testid="studies-runs"]').innerText();
console.log('== runs table\n' + runs.slice(0, 2500));
await browser.close();
