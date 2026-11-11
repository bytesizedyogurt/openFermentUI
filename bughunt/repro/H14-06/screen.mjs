// H14-06: open a project's Home and its Postdoc screen in headless Chromium (no proxy) and print, as one JSON line,
// the Postdoc card of Home's destinations band and Postdoc's own word on the key.   node screen.mjs ORIGIN PROJECT
import { chromium } from 'playwright';

const [origin, project] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
const go = async (path) => {
  await page.goto(`${origin}/#${path}`, { timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(2500);
};
const split = (t) => t.split('\n').map((l) => l.trim()).filter(Boolean);

// Home: open the project, then Home at /, and read the destinations band's Postdoc card.
await go(`/p/${project}`);
await go('/');
await page.waitForSelector('section[aria-labelledby="home-destinations"] a', { timeout: 30000 });
const cards = await page.$$eval('section[aria-labelledby="home-destinations"] a', (as) => as.map((a) => a.innerText));
const card = split(cards.find((t) => split(t)[0] === 'Postdoc') || '');

// Postdoc: the screen's own word on the key, once the health answer has come back.
await go(`/p/${project}/postdoc`);
await page.waitForSelector('[data-testid="postdoc-no-key"]', { timeout: 20000 }).catch(() => {});
const el = await page.$('[data-testid="postdoc-no-key"]');
const noKey = el ? split(await el.innerText())[0] : '';
const main = (await page.$('#of-main')) ? split(await page.innerText('#of-main')) : [];
const answersOn = main.find((l) => /The Postdoc service answers on/.test(l)) || '';
console.log(JSON.stringify({ homePostdocCard: card, postdocNoKey: noKey, postdocAnswersOn: answersOn }));
await browser.close();
