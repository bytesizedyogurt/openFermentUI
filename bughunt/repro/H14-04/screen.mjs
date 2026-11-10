// H14-04: open the Witness screen of a project in headless Chromium and print what its callout and its
// precision tile say. Prints one JSON object: the callout's words, the precision tile's text and tick class,
// and the "tp · fp · fn" line under the headline. No screenshot, no write outside stdout.
//   node screen.mjs ORIGIN PROJECT
import { chromium } from 'playwright';

const [origin, project] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
await page.goto(`${origin}/#/p/${project}/biorepo/witness`);
await page.waitForLoadState('networkidle').catch(() => {});
await page.getByText('Precision', { exact: true }).first().waitFor({ timeout: 30000 }).catch(() => {});
await page.waitForTimeout(1500);
const out = await page.evaluate(() => {
  const main = document.querySelector('#of-main') ?? document.body;
  const lines = main.innerText.split('\n').map((l) => l.trim()).filter(Boolean);
  const tiles = [...main.querySelectorAll('div.tick')].filter((d) =>
    /^(Precision|Recall)$/i.test((d.querySelector('div.text-caption')?.textContent ?? '').trim()),
  );
  const tile = (name) => {
    const t = tiles.find((d) => (d.querySelector('div.text-caption')?.textContent ?? '').trim().toLowerCase() === name);
    if (!t) return null;
    return {
      value: (t.querySelector('span.font-num')?.textContent ?? '').trim(),
      tickClass: [...t.classList].filter((c) => c.startsWith('tick-')).join(' '),
      label: (t.querySelector('span.sr-only')?.textContent ?? '').trim(),
    };
  };
  return {
    callout: lines.filter((l) => /No gold annotations yet|undefined without a gold set/.test(l)),
    counts: lines.filter((l) => /^tp \d+ · fp \d+ · fn \d+/.test(l)),
    precision: tile('precision'),
    recall: tile('recall'),
  };
});
console.log(JSON.stringify(out));
await browser.close();
