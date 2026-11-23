// Full copy: on a run's page, read the numbers a runbook can predict, choose two, make the runbook, open it, lock it.
//   node full5.mjs ORIGIN PROJECT RUN [OUTPUT,OUTPUT]
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project, run, outs = ''] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await go(page, origin, `/p/${project}/proforma/runs/${run}`);
await page.waitForTimeout(3000);
const card = page.locator('[data-testid="run-make-runbook"]');
console.log('== runbook card\n' + (await card.innerText()));
const want = outs ? outs.split(',') : [];
const boxes = card.locator('li');
const n = await boxes.count();
let picked = 0;
for (let i = 0; i < n; i++) {
  const li = boxes.nth(i);
  const name = (await li.locator('span.font-num').first().innerText()).trim();
  if ((want.length && want.includes(name)) || (!want.length && picked < 2)) {
    await li.locator('input[type=checkbox]').check();
    picked++;
  }
}
await page.fill('input[aria-label="The runbook\'s title"]', 'Corn plant at the bench, H14');
await page.click('[data-testid="run-make-runbook-go"]');
await page.waitForTimeout(4000);
console.log('== address', page.url());
await shot(page, 'full5-runbook-draft');
console.log((await text(page)).slice(0, 5000));
console.log(drain(log).join('\n'));
await browser.close();
