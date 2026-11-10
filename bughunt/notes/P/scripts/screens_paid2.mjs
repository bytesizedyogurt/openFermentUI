// Hunt P, second pass on the built app: pages the paid rows name, each opened and read for its words and for console
// errors. Rows 13 (a runbook kept with no note and no progress), 20 (a library run read as a pureOS train), 21 (the
// Studies run card naming a kinetics configuration by its title), 36 (the record a gold-label decision decided).
//   ORIGIN=http://127.0.0.1:8950 node bughunt/notes/P/scripts/screens_paid2.mjs
import { chromium } from 'playwright';

const ORIGIN = process.env.ORIGIN ?? 'http://127.0.0.1:8950';
const RUN = process.env.LIBRARY_RUN ?? 'bfda026530692adc';
const KIN = process.env.KINETICS_RUN ?? 'dd56ace8dfbe8cca';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
page.setDefaultTimeout(30000);
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(`${page.url()} :: ${m.text()}`); });
page.on('pageerror', (e) => errors.push(`${page.url()} :: ${e.message}`));
const words = async () => (await page.locator('#of-main').innerText().catch(() => '')).replace(/\s+/g, ' ');
const open = async (path, wait = 3000) => { await page.goto(`${ORIGIN}/#/p/pa${path}`); await page.waitForTimeout(wait); return words(); };

const show = (name, text, re) => {
  const m = re ? text.match(re) : null;
  console.log(`${name}: ${m ? m.slice(0, 4).join(' / ') : text.slice(0, 400)}`);
};

show('row 13 runbook rb-p9', await open('/runbooks/rb-p9'), /[^.]*(note|progress|draft)[^.]*\./gi);
show('row 20 train page of the library run', await open(`/pureos/train/${RUN}`, 5000), /[^.]*(Studies|scenario|library|cornstover)[^.]*\./gi);
show('row 21 kinetics run page', await open(`/proforma/runs/${KIN}`, 4000), /[^.]*(kinetics|batch_v1|measured|reading)[^.]*\./gi);
show('row 21 studies card', await open('/proforma/studies', 4000), /[^.]*(simulation, kept|vessel)[^.]*/gi);
show('row 36 intake records', await open('/intake', 4000), /[^.]*(gold|verified)[^.]*/gi);
console.log(`console errors: ${errors.length}`);
for (const e of errors.slice(0, 8)) console.log('  ', e.slice(0, 300));
await browser.close();
