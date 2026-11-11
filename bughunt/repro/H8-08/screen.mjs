// H8-08's screen half: BioRepo Search, a question, the Answer with citations button, with no key.
// Prints the words the screen shows in its alert and saves a screenshot.
//   node screen.mjs ORIGIN PROJECT QUESTION SHOT
import { chromium } from 'playwright';

const [origin, project, question, shotPath] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
try {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
  await page.goto(`${origin}/#/p/${project}/biorepo/search`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.fill('input[aria-label="Question"]', question);
  await page.getByRole('button', { name: /Answer with citations/ }).click();
  const alert = page.locator('[role="alert"]').filter({ hasText: /\S/ }).first();
  await alert.waitFor({ timeout: 90000 });
  await page.screenshot({ path: shotPath, fullPage: true });
  console.log(`SCREEN: ${(await alert.innerText()).replace(/\s+/g, ' ').trim()}`);
} catch (e) {
  console.log(`SCREEN-FAILED: ${String(e && e.message ? e.message : e).split('\n')[0]}`);
} finally {
  await browser.close();
}
