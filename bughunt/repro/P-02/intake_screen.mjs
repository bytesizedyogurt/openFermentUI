// P-02's screen half: the Intake table as a fresh browser reads the project, and its gold-set count.
//   ORIGIN=http://127.0.0.1:10250 PROJECT=p02 RECORD=<id> node bughunt/repro/P-02/intake_screen.mjs
import { chromium } from 'playwright';
const ORIGIN = process.env.ORIGIN;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await page.goto(`${ORIGIN}/#/p/${process.env.PROJECT}/intake`);
await page.waitForTimeout(5000);
const tail = (process.env.RECORD ?? '').slice(-8);
for (const row of await page.locator('table tbody tr').all()) {
  const t = (await row.innerText()).split(/\t|\n/).map((c) => c.trim()).filter(Boolean).join(' | ');
  if (!tail || t.includes(tail)) console.log('SCREEN row:', t.slice(0, 300));
}
const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ');
const m = body.match(/(\d+)\s+in the gold set/);
console.log('SCREEN gold set:', m ? `${m[1]} in the gold set` : '(the words were not found)');
await browser.close();
