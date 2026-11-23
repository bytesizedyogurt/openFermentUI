// H7: src/screens/Deposition.tsx at 810x1080 (CLAUDE.md R line: 810 px portrait, 44 px targets, 7:1 step-text
// contrast, no hover affordance). Each view of the takeover is opened in Chromium and measured:
//   targets: every visible a, button, input, textarea, select, summary and [role=button] under 44x44 css px;
//   contrast: the contrast of every visible text element against its effective background, the step text named;
//   hover:   every stylesheet rule with :hover whose selector, :hover taken off, matches an element in the view,
//            with the properties it changes, and every [title] (a tooltip shows on hover alone).
//   node deposition_a11y.mjs <origin> <project> <runbook> <protocol> <out.json>
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, protocol, out] = process.argv.slice(2);
const PERSON = 'H7 Hunter';
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 810, height: 1080 }, hasTouch: true });
const views = {};

async function measure(name) {
  await page.waitForTimeout(600);
  views[name] = await page.evaluate(() => {
    const parse = (c) => {
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    };
    const lum = ({ r, g, b }) => {
      const f = (v) => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const blend = (top, under) => ({
      r: top.r * top.a + under.r * (1 - top.a),
      g: top.g * top.a + under.g * (1 - top.a),
      b: top.b * top.a + under.b * (1 - top.a),
      a: 1,
    });
    const background = (el) => {
      const layers = [];
      for (let e = el; e; e = e.parentElement) {
        const c = parse(getComputedStyle(e).backgroundColor);
        if (c && c.a > 0) {
          layers.push(c);
          if (c.a >= 1) break;
        }
      }
      let bg = { r: 255, g: 255, b: 255, a: 1 };
      for (const l of layers.reverse()) bg = blend(l, bg);
      return bg;
    };
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !el.closest('.sr-only');
    };
    const label = (el) => (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || el.tagName).replace(/\s+/g, ' ').trim().slice(0, 60);
    const targets = [];
    for (const el of document.querySelectorAll('a[href], button, input, textarea, select, summary, [role="button"]')) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 44 || r.height < 44)
        targets.push({ tag: el.tagName.toLowerCase(), type: el.getAttribute('type'), label: label(el), w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 });
    }
    const texts = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.textContent.trim()) continue;
      const el = n.parentElement;
      if (!el || seen.has(el) || !visible(el)) continue;
      seen.add(el);
      const fg = parse(getComputedStyle(el).color);
      if (!fg) continue;
      const bg = background(el);
      const f = fg.a < 1 ? blend(fg, bg) : fg;
      const L1 = lum(f), L2 = lum(bg);
      const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      texts.push({ text: el.textContent.replace(/\s+/g, ' ').trim().slice(0, 70), ratio: Math.round(ratio * 100) / 100, cls: (el.className && el.className.baseVal === undefined ? el.className : '').slice(0, 80), size: getComputedStyle(el).fontSize });
    }
    const hover = [];
    for (const sheet of document.styleSheets) {
      let rules;
      try {
        rules = sheet.cssRules;
      } catch {
        continue;
      }
      for (const rule of rules) {
        if (!rule.selectorText || !rule.selectorText.includes(':hover')) continue;
        const bare = rule.selectorText.replace(/:hover/g, '');
        let hits;
        try {
          hits = [...document.querySelectorAll(bare)].filter(visible);
        } catch {
          continue;
        }
        if (!hits.length) continue;
        const props = [...rule.style].join(',');
        hover.push({ selector: rule.selectorText.slice(0, 90), props, count: hits.length, first: label(hits[0]) });
      }
    }
    const titles = [...document.querySelectorAll('[title]')].filter(visible).map((el) => ({ tag: el.tagName.toLowerCase(), title: el.getAttribute('title').slice(0, 80), label: label(el) }));
    const step = document.querySelector('p.text-ink.font-medium');
    const stepText = step ? texts.find((t) => t.text === step.textContent.replace(/\s+/g, ' ').trim().slice(0, 70)) : null;
    return { address: location.hash, width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, stepText, small: targets, lowContrast: texts.filter((t) => t.ratio < 7), hover, titles };
  });
  const v = views[name];
  console.log(`${name}: ${v.address} small=${v.small.length} lowContrast=${v.lowContrast.length} hoverRules=${v.hover.length} titles=${v.titles.length} step=${v.stepText ? v.stepText.ratio : '-'} scrollWidth=${v.scrollWidth}`);
}

try {
  await at(page, '/settings/corpus');
  await page.locator('#reviewer-name').fill(PERSON);
  await page.waitForTimeout(800);
  // A protocol's run against the runbook.
  await at(page, `/runbooks/${runbook}`);
  await page.getByRole('button', { name: /Start a deposition/ }).click();
  await page.getByRole('button', { name: new RegExp(protocol) }).click();
  await page.waitForURL(/\/run\//);
  await measure('protocol-staged');
  await page.getByRole('button', { name: /Begin/ }).first().click();
  await page.waitForTimeout(800);
  await measure('protocol-step-1');
  await page.getByLabel('Describe what you observed').fill('it came in at 1.5 USD/kg');
  await measure('protocol-step-1-preview');
  await page.getByLabel('Describe what you observed').press('Enter');
  await measure('protocol-step-1-readback');
  const yes = page.getByRole('button', { name: 'That is right' });
  if (await yes.count()) await yes.first().click();
  await page.getByLabel('Next step').click();
  await measure('protocol-step-2-timer');
  await page.getByRole('button', { name: /Start timer/ }).click();
  await measure('protocol-step-2-timer-running');
  await page.getByLabel('Toggle step list').click();
  await measure('protocol-step-list');
  await page.getByLabel('Toggle step list').click();
  const skip = page.getByRole('button', { name: /Skip/ }).first();
  if (await skip.count()) {
    await skip.click();
    await measure('protocol-skip-modal');
    await page.keyboard.press('Escape');
  }
  // The readings alone.
  await at(page, `/runbooks/${runbook}`);
  await page.getByRole('button', { name: /Start a deposition/ }).click();
  await page.getByTestId('deposition-readings-alone').click();
  await page.locator('[data-testid="deposition-bench"][data-state="staged"]').waitFor();
  await measure('bench-staged');
  await page.getByTestId('deposition-bench-begin').click();
  await page.locator('[data-testid="deposition-bench"][data-state="running"]').waitFor();
  await measure('bench-running');
  await page.getByLabel('Describe what you observed').fill('foam on the second impeller');
  await measure('bench-preview-observation');
  await page.getByLabel('Describe what you observed').fill('came in at 2.5 USD/kg');
  await page.getByLabel('Describe what you observed').press('Enter');
  await measure('bench-readback');
  await page.getByTestId('deposition-bench-close').click();
  await measure('bench-close-modal');
} catch (e) {
  console.log('stopped:', String(e).slice(0, 300));
}
writeFileSync(out, JSON.stringify(views, null, 1));
await browser.close();
