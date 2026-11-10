// Full copy: from a run's page, make a scenario whose parameter rests on a deposited reading, run it, and read the
// new run's page (its provenance, the reading's origin and its link).
//   node full7.mjs ORIGIN PROJECT RUN FINDWORDS
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project, run, words = 'cornstover flow'] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await go(page, origin, `/p/${project}/proforma/runs/${run}`);
await page.waitForTimeout(3000);
await page.click('button:has-text("New scenario from this run")');
await page.waitForTimeout(1500);
await page.fill('[data-testid="scenario-find"]', words);
await page.waitForTimeout(800);
console.log('== found\n' + (await page.locator('[data-testid="scenario-found"]').innerText().catch(() => '(none)')));
await page.locator('[data-testid="scenario-found-row"] button').first().click();
await page.waitForTimeout(500);
await page.click('[data-testid="scenario-source-reading"]');
await page.waitForTimeout(2500);
console.log('== readings\n' + (await page.locator('[data-testid="scenario-readings"]').innerText()));
await shot(page, 'full7-dialog');
const choice = page.locator('[data-testid="scenario-reading"] input');
if (await choice.count()) await choice.first().check();
else await page.locator('[data-testid="scenario-reading"]').first().click();
await page.fill('input[aria-label="The scenario\'s title"]', 'Feed at the bench reading, H14');
await page.fill('input[aria-label="What the scenario rests on"]', 'a placeholder pairing by unit');
await page.click('[data-testid="run-make-scenario-go"]');
for (let i = 0; i < 300; i++) {
  await page.waitForTimeout(1000);
  if (!page.url().includes(`/runs/${run}`)) break;
  if (await page.locator('[data-testid="run-make-scenario-problem"]').count()) break;
}
await page.waitForTimeout(3000);
console.log('== address', page.url());
const prob = page.locator('[data-testid="run-make-scenario-problem"]');
if (await prob.count()) console.log('PROBLEM: ' + (await prob.innerText()));
await shot(page, 'full7-new-run');
console.log((await text(page)).slice(0, 5000));
console.log(drain(log).join('\n'));
await browser.close();
