// Full copy: export a study package from Studies (the download), ask Postdoc a question with no key, open Primer, a
// lesson, Guild's matrix and people, BioRepo's Artifacts and Witness, and Flowsheets.
//   node full9.mjs ORIGIN PROJECT
import { open, shot, go, text, drain } from './lib.mjs';
import { mkdirSync } from 'node:fs';

const [origin, project] = process.argv.slice(2);
const { browser, context, page, log } = await open(origin);
await go(page, origin, '/settings/corpus');
await page.fill('#reviewer-name', 'Hunt Fourteen');
await page.keyboard.press('Tab');

// Export
await go(page, origin, `/p/${project}/proforma/studies`);
await page.waitForTimeout(2000);
const dl = page.waitForEvent('download', { timeout: 120000 }).catch((e) => null);
await page.click('[data-testid="studies-export"]');
const d = await dl;
if (d) {
  const dir = '/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H14/export';
  mkdirSync(dir, { recursive: true });
  const p = `${dir}/${d.suggestedFilename()}`;
  await d.saveAs(p);
  console.log('== export saved', p);
} else {
  console.log('== no download; page says:\n' + (await text(page)).slice(0, 800));
}
console.log(drain(log).join('\n'));

// Postdoc with no key
await go(page, origin, `/p/${project}/postdoc`);
await page.waitForTimeout(2000);
const nokey = page.locator('[data-testid="postdoc-no-key"]');
console.log('== postdoc no-key card: ' + ((await nokey.count()) ? (await nokey.innerText()).slice(0, 500) : '(none)'));
const box = page.locator('[aria-label="Ask a question"]');
console.log('ask box enabled:', await box.isEnabled().catch(() => 'n/a'));
await page.click('button:has-text("New conversation")').catch(() => {});
await page.waitForTimeout(800);
await box.fill('Which documents report an ethanol titre above 80 g/L?');
await page.keyboard.press('Enter');
await page.waitForTimeout(8000);
await shot(page, 'full9-postdoc-ask');
console.log('== postdoc after ask\n' + (await text(page)).slice(0, 3000));
console.log(drain(log).join('\n'));

for (const p of ['/primer', '/primer/path', '/primer/practice', '/guild/matrix', '/guild/people', '/guild/checks', '/biorepo/artifacts', '/biorepo/witness', '/biorepo/compare', '/flowsheets', '/runbooks/ledger', '/fermos/simulate', '/fermos/vessel', '/fermos/forecast', '/pureos/build', '/geneos?view=model', '/settings/architecture', '/settings/about']) {
  await go(page, origin, `/p/${project}${p}`);
  await page.waitForTimeout(1800);
  await shot(page, `full9${p.replace(/[/?=]/g, '-')}`);
  const t = await text(page);
  console.log(`\n== ${p}\n` + t.slice(0, 1400));
  console.log(drain(log).join('\n'));
}
await browser.close();
