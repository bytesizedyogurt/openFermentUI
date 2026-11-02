/**
 * The stage 1 smoke: the app starts and every rail entry opens (execution
 * prompt §10, stage 1 gate), and so do the screens beyond the rail that an
 * empty project opens too (`ALSO`: the studies of stage 5).
 *
 * It runs the real service on loopback with dist/ mounted, so the page and its
 * /api calls share one origin the way the host serves them, and opens each
 * entry of RAIL (src/data/nav.ts) in Chromium. An entry fails on a console
 * error, an uncaught exception, the screen boundary's card, the not-found page,
 * a near-empty render, or a 500 from the service. The service writes into a
 * fresh temporary data directory and a database of the smoke's own, made on
 * the server OPENFERMENT_TEST_DATABASE_URL names (the tests' server) and
 * dropped at the end, so a smoke run never touches core/data/ or another
 * database. A project is made through the API first, and every screen must
 * open inside it.
 *
 *   pnpm build && pnpm smoke
 */
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { randomBytes } from 'node:crypto';
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
/** The server the smoke makes its database on: the tests' (core/tests/conftest.py). */
const SERVER = process.env.OPENFERMENT_TEST_DATABASE_URL?.trim() || 'postgresql://openferment:openferment@127.0.0.1:5432/openferment_test';
const PROJECT = { name: 'Smoke', by: 'Smoke Test' };
/** Screens beyond the rail that open on an empty project (execution prompt §9.1 step 5), each with the test id its screen draws. */
const ALSO = [{ label: 'Studies', to: '/proforma/studies', testid: 'proforma-studies' }];
const SCREENS: { label: string; to: string; testid?: string }[] = [...RAIL.map((e) => ({ label: e.label, to: e.to })), ...ALSO];

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
 * The project's Python, with `args`. Its environment is called directly when
 * it exists: `uv run` would sync it first, and that re-points the editable
 * install when the environment is shared with another checkout.
 */
function python(args: string[]): [string, string[]] {
  const own = join(CORE, '.venv', 'bin', 'python');
  return existsSync(own) ? [own, args] : ['uv', ['run', '--all-extras', 'python', ...args]];
}

/** `address` naming database `name` on the same server. */
function onServer(address: string, name: string): string {
  const url = new URL(address);
  url.pathname = `/${name}`;
  return url.toString();
}

/** Run one database command (`python -m openferment_core.migrations`) against SERVER. */
function dbCommand(args: string[]): void {
  const [command, argv] = python(['-m', 'openferment_core.migrations', ...args]);
  const done = spawnSync(command, argv, { cwd: CORE, env: { ...process.env, OPENFERMENT_DATABASE_URL: SERVER }, encoding: 'utf8' });
  if (done.status !== 0) throw new Error(`db ${args.join(' ')} failed: ${(done.stderr || done.stdout).trim()}`);
}

function startService(port: number, dataDir: string, database: string, log: string[]): ChildProcess {
  const [command, argv] = python(['-m', 'uvicorn', 'openferment_core.api:app', '--host', HOST, '--port', String(port), '--log-level', 'warning']);
  const child = spawn(command, argv, {
    cwd: CORE,
    env: {
      ...process.env,
      OPENFERMENT_DIST_DIR: DIST,
      OPENFERMENT_DATA_DIR: dataDir,
      OPENFERMENT_DATABASE_URL: onServer(SERVER, database),
    },
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
  const database = `openferment_smoke_${randomBytes(4).toString('hex')}`;
  try {
    dbCommand(['reset', database]);
  } catch (e) {
    console.error(`✗ ${String(e)}\n  Start PostgreSQL (\`pnpm db:up\`), or set OPENFERMENT_TEST_DATABASE_URL.`);
    rmSync(dataDir, { recursive: true, force: true });
    return 1;
  }
  const serviceLog: string[] = [];
  const service = startService(port, dataDir, database, serviceLog);
  const failures: string[] = [];

  try {
    await waitForHealth(origin, service);
    console.log(`✓ the service answers at ${origin}, serving dist/, on database ${database}`);
    const made = await fetch(`${origin}/api/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(PROJECT),
    });
    if (made.status !== 201) throw new Error(`making the project answered ${made.status}: ${await made.text()}`);
    console.log(`✓ project ${((await made.json()) as { id: string }).id} made through the API`);

    // The environment's installed Chromium, when the repository's Playwright
    // expects a different build of it.
    const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium';
    const browser = await chromium.launch(existsSync(executablePath) ? { executablePath } : {});
    try {
      for (const entry of SCREENS) {
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
          // The one project the service holds opens by itself, and the top bar names it.
          if (await page.locator('[data-testid="project-needed"]').count()) problems.push('no project is open');
          const open = (await page.locator('[data-testid="project-switch"]').innerText().catch(() => '')).trim();
          if (open !== PROJECT.name) problems.push(`the top bar names the project ${JSON.stringify(open)}, not ${PROJECT.name}`);
          if (/Route not found/i.test(text)) problems.push('the path opened the not-found page');
          if (entry.testid && !(await page.locator(`[data-testid="${entry.testid}"]`).count())) problems.push(`the path drew no ${entry.testid} screen`);
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
    if (service.exitCode === null && service.signalCode === null) {
      const exited = new Promise((r) => service.once('exit', r));
      service.kill('SIGTERM');
      await exited;
    }
    rmSync(dataDir, { recursive: true, force: true });
    try {
      dbCommand(['drop', database]);
    } catch (e) {
      console.log(`  (the smoke's database ${database} was left behind: ${String(e)})`);
    }
  }

  console.log(
    failures.length
      ? `\n${failures.length} failed of ${SCREENS.length} screens`
      : `\nall ${SCREENS.length} screens open: ${RAIL.length} rail entries and ${ALSO.length} more`,
  );
  return failures.length ? 1 : 0;
}

process.exit(await main());
