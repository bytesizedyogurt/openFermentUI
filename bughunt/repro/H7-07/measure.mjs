// H7-07: the Deposition takeover at 810x1080 with touch. A protocol's run against a locked runbook is opened from the
// runbook's page; on the staged view the runbook link is measured and its underline read before and during a hover;
// after Begin recording, the footer's Next step button is measured on each step it shows on.
//
//   node measure.mjs <origin> <project> <runbook> <protocol title> <out.json>
//
// Writes the facts to <out.json> for run.sh to judge.
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, protocol, out] = process.argv.slice(2);
const PERSON = 'H7 Repro';
const facts = { staged: null, steps: [], footer: null, stopped: null };
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const box = async (loc) => {
  const b = await loc.boundingBox();
  return b ? { w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10 } : null;
};

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 810, height: 1080 }, hasTouch: true });
try {
  // A reading names the person who took it: the name goes in Settings first.
  await at(page, '/settings/corpus');
  await page.locator('#reviewer-name').fill(PERSON);
  await page.waitForTimeout(800);

  // The protocol's run against the runbook, from the runbook's page.
  await at(page, `/runbooks/${runbook}`);
  await page.getByRole('button', { name: /Start a deposition/ }).click();
  await page.getByRole('button', { name: new RegExp(protocol) }).click();
  await page.waitForURL(/\/run\//);
  await page.getByRole('button', { name: /Begin recording/ }).waitFor();
  await page.waitForTimeout(500);

  // Staged: the link to the runbook beside "against".
  const link = page.locator(`a[href$="/runbooks/${runbook}"]`).first();
  const rest = await link.evaluate((el) => {
    const hoverRules = [];
    for (const sheet of document.styleSheets) {
      let rules;
      try { rules = sheet.cssRules; } catch { continue; }
      for (const rule of rules) {
        if (!rule.selectorText || !rule.selectorText.includes(':hover')) continue;
        let hit = false;
        try { hit = el.matches(rule.selectorText.replace(/:hover/g, '')); } catch { continue; }
        if (hit) hoverRules.push(`${rule.selectorText} { ${rule.style.cssText} }`);
      }
    }
    const s = getComputedStyle(el);
    return { text: el.textContent.trim(), className: el.className, display: s.display, decoration: s.textDecorationLine, hoverRules };
  });
  const linkBox = await box(link);
  await link.hover();
  await page.waitForTimeout(300);
  const hovered = await link.evaluate((el) => getComputedStyle(el).textDecorationLine);
  await page.mouse.move(5, 1075);
  await page.waitForTimeout(300);
  facts.staged = { address: await page.evaluate(() => location.hash), link: { ...rest, box: linkBox, decorationOnHover: hovered } };
  facts.staged.begin = await box(page.getByRole('button', { name: /Begin recording/ }));

  // Running: the footer's Next step, step by step.
  await page.getByRole('button', { name: /Begin recording/ }).click();
  const next = page.getByLabel('Next step');
  await next.waitFor();
  await page.waitForTimeout(500);
  facts.footer = await page.evaluate(() => {
    const f = document.querySelector('footer');
    return f ? [...f.querySelectorAll('button')].map((b) => {
      const r = b.getBoundingClientRect();
      return { label: (b.getAttribute('aria-label') || b.textContent).replace(/\s+/g, ' ').trim().slice(0, 40), w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 };
    }) : [];
  });
  for (let i = 0; i < 3; i++) {
    const enabled = await next.isEnabled();
    facts.steps.push({ step: i + 1, nextStep: await box(next), enabled, minWidth: await next.evaluate((el) => getComputedStyle(el).minWidth) });
    if (!enabled) break;
    await next.click();
    await page.waitForTimeout(400);
  }
} catch (e) {
  facts.stopped = String(e).slice(0, 300);
}
writeFileSync(out, JSON.stringify(facts, null, 1));
await browser.close();
