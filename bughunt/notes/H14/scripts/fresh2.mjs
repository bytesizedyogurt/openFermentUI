// Fresh service: set a reviewer name, make a project from Home, collect two identifiers and paste a document on
// Intake's ingest, then reload and read the board again.
//   node fresh2.mjs ORIGIN
import { open, shot, go, text, drain } from './lib.mjs';

const [origin] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await page.waitForTimeout(500);
await go(page, origin, '/');
await page.fill('#new-project-name', 'Lignin valorisation');
await page.click('[data-testid="new-project"] button[type=submit]');
await page.waitForTimeout(2500);
console.log('== address after Make it:', page.url());
await shot(page, 'f2-project-made');
console.log((await text(page)).slice(0, 1500));
console.log(drain(log).join('\n'));

await go(page, origin, page.url().split('#')[1].replace(/\/$/, '') + '/intake/ingest');
console.log('== address', page.url());
await shot(page, 'f2-ingest-empty');
const ids = process.argv.slice(3).length ? process.argv.slice(3) : ['PMC4842200', 'osti:1013269'];
for (const id of ids) {
  await page.fill('input[aria-label="Identifier"]', id);
  await page.fill('input[aria-label="Why it belongs here"]', 'a new lab member tries Intake');
  await page.click('form[aria-label="Add a document"] button[type=submit]');
  // wait up to 120 s for the busy state to clear
  for (let i = 0; i < 240; i++) {
    await page.waitForTimeout(500);
    const dis = await page.locator('form[aria-label="Add a document"] button[type=submit]').isDisabled();
    const val = await page.inputValue('input[aria-label="Identifier"]');
    if (!dis || val === '') break;
  }
  await page.waitForTimeout(1500);
  console.log(`== after collecting ${id}`);
  console.log((await text(page)).slice(0, 4000));
  console.log(drain(log).join('\n'));
  await shot(page, `f2-after-${id.replace(/[^a-z0-9]/gi, '_')}`);
}
await browser.close();
