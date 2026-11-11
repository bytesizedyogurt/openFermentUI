// H14-09: in headless Chromium (no proxy), name the reviewer, open the project's Studies page, choose BioSTEAM's
// plant, press Run it, and print one JSON line: the seconds the answer took, the card's answer line with its run id
// and status, and the runs table's rows as the page then shows them.
//   node screen.mjs ORIGIN PROJECT PLANT REVIEWER [SHOT]
import { chromium } from 'playwright';

const [origin, project, plant, reviewer, shot] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
const go = async (path) => {
  await page.goto(`${origin}/#${path}`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(800);
};
const out = { reviewer };
try {
  await go('/settings/corpus');
  await page.fill('#reviewer-name', reviewer);
  await page.keyboard.press('Tab');
  await page.waitForTimeout(500);
  await go(`/p/${project}/proforma/studies`);
  // The engine chooser shows once a second engine is listed; the plant chooser once the shelf is read.
  await page.waitForSelector(`[data-testid="run-plant-plant"] option[value="${plant}"]`, { state: 'attached', timeout: 90000 }).catch(async () => {
    if (await page.locator('[data-testid="run-plant-engine"]').count()) await page.selectOption('[data-testid="run-plant-engine"]', 'biosteam');
    await page.waitForSelector(`[data-testid="run-plant-plant"] option[value="${plant}"]`, { state: 'attached', timeout: 90000 });
  });
  await page.selectOption('[data-testid="run-plant-plant"]', plant);
  await page.waitForTimeout(500);
  const t0 = Date.now();
  await page.click('[data-testid="run-plant-go"]');
  await page.waitForSelector('[data-testid="run-plant-ran"], [data-testid="run-plant-problem"]', { timeout: 900000 });
  out.seconds = Math.round((Date.now() - t0) / 100) / 10;
  const ran = page.locator('[data-testid="run-plant-ran"]');
  if (await ran.count()) {
    out.cardLine = (await ran.innerText()).replace(/\s+/g, ' ').trim();
    out.cardRun = await ran.getAttribute('data-run');
    out.cardStatus = await ran.getAttribute('data-status');
  } else {
    out.problem = (await page.locator('[data-testid="run-plant-problem"]').innerText()).trim();
  }
  await page.waitForTimeout(2500);
  out.tableRows = await page.locator('[data-testid="studies-run"]').evaluateAll((rows) =>
    rows.map((r) => Array.from(r.querySelectorAll('td')).map((td) => td.innerText.replace(/\s+/g, ' ').trim()).filter(Boolean).join(' | ')),
  );
  if (shot) await page.screenshot({ path: shot, fullPage: true });
} catch (e) {
  out.error = String(e && e.message ? e.message : e).split('\n')[0];
}
console.log(JSON.stringify(out));
await browser.close();
