// Full copy: flag a record for gold in the review queue, then read Home's tiles (Gold set beside the BioRepo
// destination's words) and Witness; make a Proforma scenario from New scenario, read its page, reload, read it again.
//   node full10.mjs ORIGIN PROJECT
import { open, shot, go, text, drain } from './lib.mjs';

const [origin, project] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');

await go(page, origin, `/p/${project}/guild`);
await page.waitForTimeout(3000);
const before = (await text(page)).match(/Record \d+ of \d+\.[^\n]*/)?.[0];
console.log('== gold on: ' + before);
await page.locator('body').click({ position: { x: 5, y: 5 } }).catch(() => {});
await page.keyboard.press('g');
await page.waitForTimeout(3000);
console.log(drain(log).join('\n'));
await go(page, origin, `/`);
await page.waitForTimeout(2500);
const home = await text(page);
console.log('== home GOLD SET tile: ' + (home.match(/GOLD SET\n[^\n]*\n[^\n]*/) || ['?'])[0].replace(/\n/g, ' | '));
console.log('== home BioRepo destination: ' + (home.match(/BioRepo\nrecords, artifacts, provenance\n[^\n]*/) || ['?'])[0].replace(/\n/g, ' | '));
console.log('== home Postdoc destination: ' + (home.match(/Postdoc\nask, plan, answer from records\n[^\n]*/) || ['?'])[0].replace(/\n/g, ' | '));
await shot(page, 'full10-home-after-gold');
await go(page, origin, `/p/${project}/biorepo/witness`);
await page.waitForTimeout(2500);
const w = await text(page);
console.log('== witness\n' + w.slice(w.indexOf('RUN'), w.indexOf('RUN') + 900));
await shot(page, 'full10-witness-after-gold');

// A Proforma scenario
await go(page, origin, `/p/${project}/proforma`);
await page.waitForTimeout(2000);
await page.click('button:has-text("New scenario")');
await page.waitForTimeout(1500);
await page.locator('[data-testid="new-scenario-flowsheet"][data-flowsheet="ethanol_glucose_v0"] input').check();
await page.fill('[data-testid="new-scenario-name"]', 'Glucose at the bench, H14');
await page.click('[data-testid="new-scenario-create"]');
await page.waitForTimeout(3000);
const url = page.url();
console.log('== scenario page at ' + url);
await shot(page, 'full10-scenario');
console.log((await text(page)).slice(0, 2500));
console.log(drain(log).join('\n'));
await page.waitForTimeout(3000);
await page.reload();
await page.waitForTimeout(5000);
console.log('== after reload at ' + page.url() + '\n' + (await text(page)).slice(0, 800));
console.log(drain(log).join('\n'));
await browser.close();
