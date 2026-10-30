/**
 * The stage 1 smoke: the app starts and every rail entry opens (execution
 * prompt §10, stage 1 gate).
 *
 * It runs the real service on loopback with dist/ mounted, so the page and its
 * /api calls share one origin the way the host serves them, and opens each
 * entry of RAIL (src/data/nav.ts) in Chromium. An entry fails on a console
 * error, an uncaught exception, the screen boundary's card, the not-found page,
 * a near-empty render, or a 500 from the service. The service writes into a
 * fresh temporary data directory, so a smoke run never touches core/data/.
 *
 *   pnpm build && pnpm smoke
 */
import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { chromium } from 'playwright';
import { RAIL } from '../src/data/nav';

const ROOT = resolve(import.meta.dirname, '..');
const CORE = join(ROOT, 'core');
const DIST = join(ROOT, 'dist');
/** The service binds loopback only (CLAUDE.md; guard.py). */
const HOST = '127.0.0.1';
/** Chromium's own noise, which says nothing about the app. */
const IGNORE = [/Download the React DevTools/i, /favicon/i];
/** Fewer characters than this on a screen means it drew nothing. */
const MIN_TEXT = 60;

function freePort(): Promise<number> {
  return new Promise((done, fail) => {
    const probe = createServer();
    probe.once('error', fail);
    probe.listen(0, HOST, () => {
      const address = probe.address();
      probe.close(() => (typeof address === 'object' && address ? done(address.port) : fail(new Error('no port'))));
    });
  });
}

/**
 * Start the service. The project's environment is called directly when it
 * exists: `uv run` would sync it first, and that re-points the editable
 * install when the environment is shared with another checkout.
 */
function startService(port: number, dataDir: string, log: string[]): ChildProcess {
  const python = join(CORE, '.venv', 'bin', 'python');
  const args = ['-m', 'uvicorn', 'openferment_core.api:app', '--host', HOST, '--port', String(port), '--log-level', 'warning'];
  const [command, argv] = existsSync(python) ? [python, args] : ['uv', ['run', '--all-extras', 'python', ...args]];
  const child = spawn(command, argv, {
    cwd: CORE,
    env: { ...process.env, OPENFERMENT_DIST_DIR: DIST, OPENFERMENT_DATA_DIR: dataDir },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout?.on('data', (b: Buffer) => log.push(b.toString()));
  child.stderr?.on('data', (b: Buffer) => log.push(b.toString()));
  return child;
}

async function waitForHealth(origin: string, child: ChildProcess, timeoutMs = 90_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`the service exited with code ${child.exitCode}`);
    try {
      const response = await fetch(`${origin}/api/health`);
      if (response.status === 200) return;
    } catch {
      /* not listening yet */
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`the service did not answer /api/health within ${timeoutMs / 1000} s`);
}

async function main(): Promise<number> {
  if (!existsSync(join(DIST, 'index.html'))) {
    console.error('✗ no build in dist/. Run `pnpm build` first.');
    return 1;
  }
  const port = await freePort();
  const origin = `http://${HOST}:${port}`;
  const dataDir = mkdtempSync(join(tmpdir(), 'openferment-smoke-'));
  const serviceLog: string[] = [];
  const service = startService(port, dataDir, serviceLog);
  const failures: string[] = [];

  try {
    await waitForHealth(origin, service);
    console.log(`✓ the service answers at ${origin}, serving dist/`);

    // The environment's installed Chromium, when the repository's Playwright
    // expects a different build of it.
    const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium';
    const browser = await chromium.launch(existsSync(executablePath) ? { executablePath } : {});
    try {
      for (const entry of RAIL) {
        const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
        const problems: string[] = [];
        page.on('console', (m) => {
          if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) problems.push(`console: ${m.text()}`);
        });
        page.on('pageerror', (e) => problems.push(`uncaught: ${e.message}`));
        page.on('response', (r) => {
          if (r.status() >= 500 && r.url().startsWith(`${origin}/api/`)) problems.push(`${r.status()} from ${r.url().slice(origin.length)}`);
        });
        const label = `${entry.label.padEnd(10)} #${entry.to}`;
        try {
          await page.goto(`${origin}/#${entry.to}`, { waitUntil: 'networkidle' });
          await page.waitForTimeout(500);
          if (await page.locator('[data-testid="screen-error"]').count()) {
            problems.push(`the screen could not be drawn: ${await page.locator('[data-testid="screen-error"]').innerText()}`);
          }
          const text = (await page.locator('#of-main').innerText().catch(() => '')).trim();
          if (text.length < MIN_TEXT) problems.push(`the main region drew ${text.length} characters`);
          if (/Route not found/i.test(text)) problems.push('the path opened the not-found page');
          if (problems.length) {
            failures.push(label);
            console.log(`✗ ${label}`);
            for (const p of problems.slice(0, 6)) console.log(`    ${p.slice(0, 240)}`);
          } else {
            console.log(`✓ ${label} (${text.length} characters)`);
          }
        } catch (e) {
          failures.push(label);
          console.log(`✗ ${label}\n    ${String(e).slice(0, 240)}`);
        }
        await page.close();
      }
    } finally {
      await browser.close();
    }
  } catch (e) {
    failures.push(String(e));
    console.log(`✗ ${String(e)}`);
    const tail = serviceLog.join('').trim().split('\n').slice(-20).join('\n');
    if (tail) console.log(`  the service said:\n${tail}`);
  } finally {
    service.kill('SIGTERM');
    rmSync(dataDir, { recursive: true, force: true });
  }

  console.log(failures.length ? `\n${failures.length} failed of ${RAIL.length} rail entries` : `\nall ${RAIL.length} rail entries open`);
  return failures.length ? 1 : 0;
}

process.exit(await main());
