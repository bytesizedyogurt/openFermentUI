/**
 * Golden-path interaction test (OF-DES-001 §19). Rendering without errors is
 * not the same as working, so this drives the ten-minute demo script's actual
 * interactions and asserts the behaviors the design lists as acceptance
 * criteria.
 *
 *   pnpm build && node scripts/golden-path.mjs
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, extname } from 'node:path';

const DIST = join(process.cwd(), 'dist');
const PORT = 4321;
const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.svg': 'image/svg+xml',
};

const server = createServer(async (req, res) => {
  try {
    const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
    let file = join(DIST, url === '/' ? 'index.html' : url);
    try {
      if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
    } catch {
      file = join(DIST, 'index.html');
    }
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] ?? 'application/octet-stream' });
    res.end(await readFile(file));
  } catch {
    res.writeHead(404).end('nf');
  }
});

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`);
};

async function main() {
  await new Promise((r) => server.listen(PORT, r));
  const exe = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
  const browser = await chromium.launch(existsSync(exe) ? { executablePath: exe } : {});
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

  const consoleErrors = [];
  page.on('console', (m) => {
    if (m.type() === 'error' && !/DevTools|favicon/i.test(m.text())) consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => consoleErrors.push(`UNCAUGHT: ${e.message}`));

  const go = async (hash) => {
    await page.goto(`http://localhost:${PORT}/#${hash}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
  };

  // Run at instant sim speed so scripted timings don't dominate the test.
  await go('/settings/appearance');
  const instant = page.locator('label', { hasText: /^Instant/ }).first();
  let speedSet = false;
  if (await instant.count()) {
    await instant.click();
    await page.waitForTimeout(300);
    // The top bar shows a speed badge whenever the multiplier is not 1×.
    speedSet = /instant\s+speed/i.test(await page.locator('header').first().innerText());
  }
  check('Sim speed control responds', speedSet);

  // ── 1. Home vitals reflect seed data ────────────────────────────────
  await go('/');
  const homeText = await page.locator('body').innerText();
  check(
    'Home shows live corpus vitals',
    /1[23]\d/.test(homeText),
    homeText.match(/\b1[23]\d\b/g)?.slice(0, 3).join(', ') ?? '',
  );

  // ── 2. Postdoc: a scripted flow plays and produces chips ────────────────
  await go('/postdoc');
  const suggested = page.locator('button', { hasText: /titers have been achieved/i }).first();
  await suggested.click();
  await page.waitForTimeout(2500);
  const askText = await page.locator('body').innerText();
  check('Postdoc plays a flow and renders an answer', /500 mg\/L|15–18|1\.45/.test(askText));
  const chips = page.locator('button', { hasText: /^\[[A-O]\d+[a-z]?\]$|^\[r-[A-Z0-9]+-\d+\]$/ });
  const chipCount = await chips.count();
  check('Answer carries working citation chips', chipCount > 0, `${chipCount} chips`);

  // Inspector reproduces the retrieval
  const inspectorTab = page.getByRole('button', { name: /^retrieval$/i }).first();
  if (await inspectorTab.count()) {
    await inspectorTab.click();
    await page.waitForTimeout(300);
    const inspectorText = await page.locator('aside').last().innerText();
    check('Inspector shows retrieved passages', inspectorText.length > 80);
  } else {
    check('Inspector shows retrieved passages', false, 'tab not found');
  }

  // ── 3. Chip → reader, anchored on the span ──────────────────────────
  await go('/biorepo/papers/H4?span=r-H4-1');
  await page.waitForTimeout(700);
  const marks = await page.locator('mark').count();
  const activeMark = await page.locator('mark.span-active').count();
  check('Reader highlights extraction spans', marks > 0, `${marks} spans`);
  check('Deep link anchors the requested span', activeMark > 0);

  // ── 4. Guild: keyboard triage mutates a record ─────────────────────
  await go('/guild');
  await page.waitForTimeout(600);
  const beforeReview = await page.locator('body').innerText();
  const progressBefore = beforeReview.match(/(\d+)\s*\/\s*(\d+)/)?.[1];
  await page.keyboard.press('a');
  await page.waitForTimeout(500);
  const afterReview = await page.locator('body').innerText();
  const progressAfter = afterReview.match(/(\d+)\s*\/\s*(\d+)/)?.[1];
  check(
    'Guild accepts by keyboard and advances',
    progressBefore !== progressAfter,
    `${progressBefore} → ${progressAfter}`,
  );

  // Undo restores position
  await page.keyboard.press('u');
  await page.waitForTimeout(400);
  const afterUndo = (await page.locator('body').innerText()).match(/(\d+)\s*\/\s*(\d+)/)?.[1];
  check('Undo restores queue position', afterUndo === progressBefore, `back to ${afterUndo}`);

  // ── 5. Witness states the gap honestly ───────────────────────────
  await go('/witness');
  await page.waitForTimeout(600);
  const valText = await page.locator('body').innerText();
  check(
    'Witness refuses to show metrics it has not earned',
    /no extractor has been run/i.test(valText) && !/\bF1\s*0\.\d/.test(valText),
  );
  check('Witness shows the gold-set plan instead', /gold set — planned|0 of \d+ annotated/i.test(valText));
  check(
    'Witness surfaces values the ontology cannot hold',
    /cannot hold/i.test(valText) && /Would need/i.test(valText),
  );

  // ── 6. Protocol scaling recomputes materials ────────────────────────
  await go('/protocols/PR-TAP-01');
  await page.waitForTimeout(600);
  const before = await page.locator('body').innerText();
  const x5 = page.locator('button', { hasText: /^(×5|5×|5x)$/i }).first();
  let scaled = false;
  if (await x5.count()) {
    await x5.click();
    await page.waitForTimeout(500);
    const after = await page.locator('body').innerText();
    scaled = before !== after && /12\.1|5 L|5\.0 L/.test(after);
    check('Scaling 1 L → 5 L recomputes bound quantities', scaled);
    // reversible
    const x1 = page.locator('button', { hasText: /^(1×|1x|×1)$/i }).first();
    if (await x1.count()) {
      await x1.click();
      await page.waitForTimeout(400);
      const back = await page.locator('body').innerText();
      check('Scaling is reversible', back.includes('2.42') || back === before);
    }
  } else {
    check('Scaling 1 L → 5 L recomputes bound quantities', false, 'scale chip not found');
  }

  // ── 7. Deposition: start a run, complete a step, run a timer ──────────
  const startRun = page.locator('button', { hasText: /start run/i }).first();
  if (await startRun.count()) {
    await startRun.click();
    await page.waitForTimeout(900);
    const inRun = page.url().includes('/run/');
    check('Start run enters Deposition', inRun, page.url().split('#')[1] ?? '');
    if (inRun) {
      const runBefore = await page.locator('body').innerText();
      await page.keyboard.press(' ');
      await page.waitForTimeout(500);
      const runAfter = await page.locator('body').innerText();
      check('Space completes a step and advances', runBefore !== runAfter);

      // Walk to a timed step and start its timer
      let timerStarted = false;
      for (let i = 0; i < 14; i++) {
        const timerBtn = page.locator('button', { hasText: /start timer/i }).first();
        if (await timerBtn.count()) {
          await timerBtn.click();
          await page.waitForTimeout(600);
          timerStarted = (await page.locator('svg text').count()) > 0;
          break;
        }
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(150);
      }
      check('A timed step starts a countdown timer', timerStarted);

      // Deviation note
      const noteBtn = page.locator('button', { hasText: /deviation note/i }).first();
      if (await noteBtn.count()) {
        await noteBtn.click();
        await page.waitForTimeout(300);
        await page.locator('textarea').first().fill('pH drifted to 7.6 before adjustment.');
        await page.locator('button', { hasText: /^Record$/ }).first().click();
        await page.waitForTimeout(400);
        const withNote = await page.locator('body').innerText();
        check('Deviation is logged verbatim', withNote.includes('pH drifted to 7.6'));
      } else {
        check('Deviation is logged verbatim', false, 'note button not found');
      }
    }
  } else {
    check('Start run enters Deposition', false, 'start-run button not found');
  }

  // ── 8. Proforma: slider moves MSP; waterfall agrees with headline ───
  await go('/proforma/sc-s2');
  await page.waitForTimeout(800);
  const mspBefore = (await page.locator('body').innerText()).match(/\$([\d.]+)/)?.[1];
  const slider = page.locator('input[type=range]').first();
  await slider.evaluate((el) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, String(Number(el.max) * 0.85));
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForTimeout(1200);
  const mspAfter = (await page.locator('body').innerText()).match(/\$([\d.]+)/)?.[1];
  check(
    'Moving a sweep slider changes the MSP',
    mspBefore !== mspAfter,
    `$${mspBefore} → $${mspAfter}`,
  );

  // Waterfall lines must sum to the headline
  const sums = await page.evaluate(() => {
    const details = [...document.querySelectorAll('details')];
    for (const d of details) {
      d.open = true;
    }
    const tables = [...document.querySelectorAll('table')];
    for (const t of tables) {
      const rows = [...t.querySelectorAll('tbody tr')];
      const labels = rows.map((r) => r.cells[0]?.textContent ?? '');
      if (labels.some((l) => /Minimum selling price/i.test(l))) {
        let sum = 0;
        let total = 0;
        for (const r of rows) {
          const label = r.cells[0]?.textContent ?? '';
          const v = parseFloat((r.cells[1]?.textContent ?? '').replace(/[^\d.-]/g, ''));
          if (isNaN(v)) continue;
          if (/Minimum selling price/i.test(label)) total = v;
          else sum += v;
        }
        return { sum, total };
      }
    }
    return null;
  });
  check(
    'Cost lines sum to the headline MSP',
    sums !== null && Math.abs(sums.sum - sums.total) < 0.05,
    sums ? `Σ${sums.sum.toFixed(2)} vs $${sums.total.toFixed(2)}` : 'table not found',
  );

  // ── 9. Primer: unit-aware numeric checkpoint grading ─────────────────
  await go('/primer/m0/l0-2');
  await page.waitForTimeout(600);
  const numInput = page.locator('input[placeholder*="e.g."]').first();
  if (await numInput.count()) {
    // 3.6 d⁻¹ is the same quantity as the expected 0.15 h⁻¹.
    await numInput.fill('3.6 d⁻¹');
    await page.locator('button', { hasText: /check answer/i }).first().click();
    await page.waitForTimeout(500);
    const graded = await page.locator('body').innerText();
    check('Numeric checkpoint accepts a unit-equivalent answer', /Correct/i.test(graded));
  } else {
    check('Numeric checkpoint accepts a unit-equivalent answer', false, 'input not found');
  }

  // ── 10. Agent declines an out-of-corpus question ────────────────────
  await go('/postdoc');
  await page.waitForTimeout(400);
  const composer = page.locator('textarea').first();
  await composer.fill('What is the optimal sous-vide temperature for brisket?');
  await composer.press('Enter');
  // Wait for streaming to settle rather than guessing a duration.
  await page
    .locator('text=/outside this demo corpus/i')
    .first()
    .waitFor({ timeout: 20000 })
    .catch(() => {});
  const declineText = await page.locator('body').innerText();
  check(
    'Out-of-corpus question gets an honest decline',
    /outside this|corpus does not|does not cover/i.test(declineText),
  );

  // The algal-casein question is NOT a decline — the corpus answers it with a
  // substantive "no", which is the demo's whole point (OF-COR-001 §21 F6).
  await go('/postdoc');
  await page.waitForTimeout(400);
  const c2 = page.locator('textarea').first();
  await c2.fill('Has anyone expressed a casein in an alga?');
  await c2.press('Enter');
  await page
    .locator('text=/no algal|never been|no.{0,12}alga/i')
    .first()
    .waitFor({ timeout: 25000 })
    .catch(() => {});
  const f6 = await page.locator('body').innerText();
  check(
    'The algal-casein absence is answered substantively, not declined',
    /17 bacterial|Kiverdi|no algal/i.test(f6),
  );

  // ── 11. Command palette navigates ───────────────────────────────────
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(400);
  const paletteOpen = (await page.locator('input[aria-label="Command palette"]').count()) > 0;
  check('Command palette opens', paletteOpen);
  if (paletteOpen) {
    // Typed as the OLD word on purpose. People reached for "validation" for
    // months after the rename, and Witness has since moved again — under
    // BioRepo — so the palette has to carry them across both moves.
    await page.locator('input[aria-label="Command palette"]').fill('validation');
    await page.waitForTimeout(400);
    const options = await page.locator('[role="option"]').allInnerTexts();
    check(
      'Palette resolves an old word to the surfaces that own it',
      /BioRepo/.test(options[0] ?? '') && options.slice(0, 3).some((o) => /Witness/.test(o)),
      (options[0] ?? '(nothing)').split('\n')[0],
    );
    // Clicked rather than Entered. Enter runs whichever row `sel` points at,
    // and `sel` follows the mouse — a pointer left over the overlay by an
    // earlier step silently changes what this asserts.
    await page.locator('[role="option"]', { hasText: /^Witness/ }).first().click();
    await page.waitForTimeout(700);
    check(
      'Palette navigates to the moved screen',
      (page.url().split('#')[1] ?? '') === '/biorepo/witness',
      page.url().split('#')[1] ?? '',
    );
  }

  await browser.close();
  server.close();

  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} golden-path checks passed`);
  if (consoleErrors.length) {
    console.log(`\n${consoleErrors.length} console error(s) during the walk:`);
    for (const e of [...new Set(consoleErrors)].slice(0, 8)) console.log(`  - ${e.slice(0, 200)}`);
  }
  if (failed.length || consoleErrors.length) process.exit(1);
}

main();
