// Hunt P, row 36: the Intake screen's records table, a row a line, as a fresh browser reads project pa.
//   ORIGIN=http://127.0.0.1:8950 PROJECT=pa node bughunt/notes/P/scripts/intake_rows.mjs
import { chromium } from 'playwright';
const ORIGIN = process.env.ORIGIN ?? 'http://127.0.0.1:8950';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
await page.goto(`${ORIGIN}/#/p/${process.env.PROJECT ?? 'pa'}/intake`);
await page.waitForTimeout(4000);
const head = await page.locator('table thead tr').first().innerText().catch(() => '');
console.log('HEAD:', head.replace(/\s+/g, ' | '));
for (const row of await page.locator('table tbody tr').all()) console.log('ROW:', (await row.innerText()).replace(/\s+/g, ' | ').slice(0, 300));
await browser.close();
