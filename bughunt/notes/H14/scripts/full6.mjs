// Full copy: lock a runbook, start a deposition with the readings alone, record a reading and read it back, reload
// between each step, close it, then open a run's New scenario dialog and see whether the reading is offered.
//   node full6.mjs ORIGIN PROJECT RUNBOOK LINE [RUN]
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project, runbook, line, run] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await go(page, origin, `/p/${project}/runbooks/${runbook}`);
await page.waitForTimeout(2500);
await page.click('button:has-text("Lock predictions")');
await page.waitForTimeout(2500);
console.log('== after lock: ' + (await page.locator('text=Frozen').first().innerText().catch(() => '(no Frozen line)')));
console.log(drain(log).join('\n'));
await page.reload();
await page.waitForTimeout(4000);
console.log('== after reload: ' + (await page.locator('text=Frozen').first().innerText().catch(() => '(no Frozen line after reload)')));
await shot(page, 'full6-locked');

await page.click('button:has-text("Start a deposition")');
await page.waitForTimeout(800);
await page.click('[data-testid="deposition-readings-alone"]');
await page.waitForTimeout(2500);
console.log('== bench at', page.url());
await shot(page, 'full6-bench-staged');
console.log((await page.locator('[data-testid="deposition-bench"]').innerText()).slice(0, 1500));
await page.click('[data-testid="deposition-bench-begin"]');
await page.waitForTimeout(1500);
await page.fill('textarea[aria-label="Describe what you observed"]', line);
await page.waitForTimeout(500);
console.log('== preview: ' + (await page.locator('section[aria-label="Record what happened"]').innerText()).slice(0, 600));
await page.keyboard.press('Enter');
await page.waitForTimeout(1500);
await shot(page, 'full6-bench-recorded');
console.log('== recorded\n' + (await page.locator('[data-testid="deposition-bench"]').innerText()).slice(0, 2000));
const dep = await page.locator('[data-testid="deposition-bench"]').getAttribute('data-deposition');
console.log('deposition', dep);
await page.click('button:has-text("That is right")');
await page.waitForTimeout(3000);
console.log(drain(log).join('\n'));
await page.reload();
await page.waitForTimeout(5000);
console.log('== after reload at bench\n' + (await page.locator('[data-testid="deposition-bench"]').innerText().catch(() => '(no bench)')).slice(0, 1500));
await shot(page, 'full6-bench-after-reload');
console.log(drain(log).join('\n'));
await browser.close();
