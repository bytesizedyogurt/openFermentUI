// Full copy: compare two runs from Studies, open the comparison's page, then each run's page, and set the price the
// comparison shows beside the price each run's page shows.
//   node full4.mjs ORIGIN PROJECT RUN_A RUN_B TITLE
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project, a, b, title = 'Dilute acid against hot water, IB'] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await go(page, origin, `/p/${project}/proforma/studies`);
await page.waitForTimeout(2000);
await page.check(`input[aria-label="Compare run ${a}"]`);
await page.check(`input[aria-label="Compare run ${b}"]`);
await page.fill('input[aria-label="The comparison\'s title"]', title);
await page.click('[data-testid="studies-compare"]');
await page.waitForTimeout(6000);
console.log('== address', page.url());
await shot(page, 'full4-comparison');
const cmp = await text(page);
console.log(cmp.slice(0, 6000));
console.log(drain(log).join('\n'));
for (const id of [a, b]) {
  await go(page, origin, `/p/${project}/proforma/runs/${id}`);
  await page.waitForTimeout(3000);
  await shot(page, `full4-run-${id}`);
  console.log(`== run ${id}\n` + (await text(page)).slice(0, 3500));
  console.log(drain(log).join('\n'));
}
await browser.close();
