// H3-03: what DepositionDetail draws for dep1's released evidence after repro.py ran.
//   node screen.cjs ORIGIN SHOT.png
const { chromium } = require('/home/user/openFermentUI/node_modules/playwright');
const origin = process.argv[2];
const shot = process.argv[3];
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
  await page.goto(`${origin}/#/p/p1/runbooks/depositions/dep1`, { waitUntil: 'networkidle', timeout: 60000 });
  const band = page.locator('section[aria-labelledby="band-evidence"]');
  await band.waitFor({ timeout: 20000 }).catch(() => {});
  const text = (await band.innerText().catch(() => '(no evidence band)')).replace(/\s+/g, ' ');
  console.log('SCREEN_BAND:', text.slice(0, 160));
  if (shot) await page.screenshot({ path: shot, fullPage: true });
  await browser.close();
})().catch((e) => { console.log('SCREEN_ERROR:', String(e).slice(0, 200)); process.exit(0); });
