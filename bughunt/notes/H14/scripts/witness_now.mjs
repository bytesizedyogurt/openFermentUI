// Open Witness on its own and read its headline, to set beside GET /api/witness/runs.
import { open, shot, go, text, drain } from './lib.mjs';
const [origin, project] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, `/p/${project}/biorepo/witness`);
await page.waitForTimeout(4000);
const w = await text(page);
console.log(w.slice(w.indexOf('RUN'), w.indexOf('RUN') + 1400));
await shot(page, 'witness-now');
console.log(drain(log).join('\n'));
await browser.close();
