// Fresh service, project already made (lignin-valorisation): collect more identifiers, paste a document, press
// Extract with no key, search the documents for a value, reload and read the board again.
//   node fresh3.mjs ORIGIN PROJECT
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');
await go(page, origin, `/p/${project}/intake/ingest`);
await page.waitForTimeout(1500);

async function collectOne(id) {
  await page.fill('input[aria-label="Identifier"]', id);
  await page.click('form[aria-label="Add a document"] button[type=submit]');
  for (let i = 0; i < 300; i++) {
    await page.waitForTimeout(500);
    const dis = await page.locator('form[aria-label="Add a document"] button[type=submit]').isDisabled();
    if (!dis) break;
    if ((await page.inputValue('input[aria-label="Identifier"]')) === '') break;
  }
  await page.waitForTimeout(1000);
  const card = await page.locator('form[aria-label="Add a document"]').locator('xpath=..').innerText();
  console.log(`== ${id}\n${card.slice(0, 1200)}`);
}
for (const id of ['PMC5574463', 'sgd:S000203483', '12345', 'doi:10.1016/j.biortech.2016.01.000']) await collectOne(id);

// Paste a document.
await page.click('[role=tablist] button:has-text("Paste")');
await page.fill('input[aria-label="Title"]', 'Bench note on ethanol titre');
await page.fill('textarea[aria-label="Text"]', 'In the 2 L batch the strain reached an ethanol titre of 41.7 g/L after 48 h at 30 °C, with a yield of 0.46 g/g on glucose. The biomass yield was 0.08 g/g.');
await page.click('form[aria-label="Add a document"] button[type=submit]');
await page.waitForTimeout(6000);
console.log('== paste\n' + (await text(page)).slice(0, 3000));
await shot(page, 'f3-after-paste');
console.log(drain(log).join('\n'));

// Extract on the pasted document.
const extract = page.locator('ul[aria-label="Documents the project holds"] li').filter({ hasText: 'Bench note' }).locator('button:has-text("Extract")');
if (await extract.count()) {
  await extract.first().click();
  await page.waitForTimeout(5000);
  console.log('== after Extract\n' + (await text(page)).slice(0, 3500));
  await shot(page, 'f3-after-extract');
}
console.log(drain(log).join('\n'));
await browser.close();
