// Full copy: find a value in the documents. BioRepo Search for a titre, open the first passage in the reader, then
// the top-bar search (command palette) for the same words, then the Answer button with no key.
//   node full1.mjs ORIGIN PROJECT
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');

await go(page, origin, `/p/${project}/biorepo/search`);
await page.fill('input[aria-label="Question"]', 'ethanol titre g/L at the end of fermentation');
await page.click('form[aria-label="Search the papers"] button[type=submit]');
await page.waitForTimeout(8000);
await shot(page, 'full1-search');
console.log('== search\n' + (await text(page)).slice(0, 5000));
console.log(drain(log).join('\n'));

// Open the first passage
const first = page.locator('ol[aria-label="Passages found"] a').first();
const link = await first.getAttribute('href');
console.log('first passage link', link);
await first.click();
await page.waitForTimeout(3000);
await shot(page, 'full1-reader');
console.log('== reader at ' + page.url() + '\n' + (await text(page)).slice(0, 3000));
console.log(drain(log).join('\n'));

// Answer with no key
await go(page, origin, `/p/${project}/biorepo/search`);
await page.fill('input[aria-label="Question"]', 'What ethanol titre did the NREL 2012 design reach?');
const answerBtn = page.locator('button:has-text("Answer")');
console.log('answer buttons', await answerBtn.count());
if (await answerBtn.count()) {
  await answerBtn.first().click();
  await page.waitForTimeout(5000);
  await shot(page, 'full1-answer-nokey');
  console.log('== answer\n' + (await text(page)).slice(0, 2000));
}
console.log(drain(log).join('\n'));

// Top bar search / palette
await page.keyboard.press('Control+k');
await page.waitForTimeout(500);
await page.keyboard.type('titre');
await page.waitForTimeout(1500);
await shot(page, 'full1-palette');
const dlg = page.locator('[role=dialog]');
console.log('== palette\n' + ((await dlg.count()) ? (await dlg.first().innerText()).slice(0, 3000) : '(no dialog)'));
console.log(drain(log).join('\n'));
await browser.close();
