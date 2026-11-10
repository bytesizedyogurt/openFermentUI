// Full copy: review candidates in the queue. Start a review session from Intake, accept one, reject one with a
// reason, skip one, accept another; then reload and read what the service kept, Home's vitals and BioRepo's counts.
//   node full2.mjs ORIGIN PROJECT
import { open, shot, go, text, drain } from './lib.mjs';
import { writeFileSync } from 'node:fs';

const [origin, project] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');

await go(page, origin, `/p/${project}/intake`);
await page.waitForTimeout(1500);
await page.click('button:has-text("Start review session")');
await page.waitForTimeout(3000);
console.log('== address', page.url());
await shot(page, 'full2-review-1');
const t1 = await text(page);
console.log(t1.slice(0, 3500));
console.log(drain(log).join('\n'));

const decisions = [];
async function cardSummary() {
  const t = await text(page);
  const m = t.match(/RECORD[\s\S]{0,400}/i);
  return t.slice(0, 600).replace(/\n/g, ' | ');
}
async function act(key, extra) {
  const before = await cardSummary();
  await page.locator('body').click({ position: { x: 5, y: 5 } }).catch(() => {});
  await page.keyboard.press(key);
  if (extra) {
    await page.waitForTimeout(300);
    await page.keyboard.press(extra);
  }
  await page.waitForTimeout(2500);
  decisions.push({ key, extra, before });
  console.log(`-- pressed ${key}${extra ? ' ' + extra : ''}`);
  console.log(drain(log).join('\n'));
}
await act('a');
await shot(page, 'full2-review-2');
await act('r', '1');
await shot(page, 'full2-review-3');
await act('s');
await act('a');
await shot(page, 'full2-review-4');
console.log('== after four decisions\n' + (await text(page)).slice(0, 3000));
writeFileSync('/home/user/openFermentUI/bughunt/notes/H14/shots/full2-decisions.json', JSON.stringify(decisions, null, 2));

// Reload and read back
await page.reload();
await page.waitForTimeout(4000);
console.log('== after reload at', page.url(), '\n' + (await text(page)).slice(0, 2500));
await shot(page, 'full2-after-reload');
await go(page, origin, `/p/${project}`);
await go(page, origin, `/`);
await page.waitForTimeout(2000);
const home = await text(page);
console.log('== home vitals\n' + home.slice(home.indexOf('Project vitals'), home.indexOf('Project vitals') + 600));
console.log(drain(log).join('\n'));
await browser.close();
