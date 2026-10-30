/**
 * The UI walk (execution prompt §9.1 step 9; stage 7): a person's path through
 * the built app, in Chromium, against a real service that serves dist/ on
 * loopback and holds a project the proof has filled (scripts/prove.py step 9
 * starts it): Home → the project → a document pasted in and searched → a run's
 * report and its SFF graph → a conversation with its labelled estimate → a
 * runbook.
 *
 *   WALK_ORIGIN=http://127.0.0.1:PORT WALK_PROJECT=<id> WALK_RUN=<run id> \
 *   WALK_CONVERSATION=<id> WALK_RUNBOOK=<id> npx tsx scripts/walk.ts
 *
 * One line a check, ✓ or ✗ with what it saw; exit 1 when one fails. A console
 * error or an uncaught exception on any page is a failed check.
 */
import { existsSync } from 'node:fs';
import { chromium, type Page } from 'playwright';

const env = (name: string): string => {
  const v = process.env[name]?.trim();
  if (!v) {
    console.error(`walk: ${name} is not set`);
    process.exit(2);
  }
  return v;
};

const ORIGIN = env('WALK_ORIGIN');
const PROJECT = env('WALK_PROJECT');
const RUN = env('WALK_RUN');
const CONVERSATION = env('WALK_CONVERSATION');
const RUNBOOK = env('WALK_RUNBOOK');
const PERSON = 'Walk Reviewer';
const TIMEOUT = 60_000;
const IGNORE = [/Download the React DevTools/i, /favicon/i];

let failed = 0;
function check(ok: boolean, words: string): void {
  console.log(`  ${ok ? '✓' : '✗'} ${words}`);
  if (!ok) failed += 1;
}

let current: Page | null = null;

async function step(name: string, body: () => Promise<string>): Promise<void> {
  try {
    check(true, `${name}: ${await body()}`);
  } catch (e) {
    // What the page said when the step stopped, so a failure names its screen's words.
    const said = current
      ? (await current.locator('#of-main').innerText({ timeout: 2000 }).catch(() => '')).replace(/\s+/g, ' ').slice(0, 300)
      : '';
    check(false, `${name}: ${e instanceof Error ? e.message.split('\n')[0] : String(e)}${said ? ` (the page: ${said})` : ''}`);
  }
}

const at = (page: Page, path: string) => page.goto(`${ORIGIN}/#/p/${encodeURIComponent(PROJECT)}${path}`);

async function main(): Promise<void> {
  // The pre-installed Chromium when there is one (as scripts/smoke.ts launches), else Playwright's own.
  const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium';
  const browser = await chromium.launch(existsSync(executablePath) ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  page.setDefaultTimeout(TIMEOUT);
  current = page;
  const errors: string[] = [];
  page.on('console', (m) => {
    if (m.type() === 'error' && !IGNORE.some((r) => r.test(m.text()))) errors.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(e.message));

  await step('Home', async () => {
    await page.goto(`${ORIGIN}/#/`);
    await page.getByTestId('home-start').waitFor();
    const card = page.getByTestId('home-project').first();
    await card.waitFor();
    const name = (await card.innerText()).split('\n')[0];
    await card.click();
    await page.getByTestId('project-home').waitFor();
    await page.locator('[data-testid="trace-cards"][data-open="true"]').waitFor();
    return `the projects listed; ${name} opened at its own address, its live trace open`;
  });

  await step('Your name', async () => {
    await at(page, '/settings/corpus');
    await page.locator('#reviewer-name').fill(PERSON);
    await page.waitForTimeout(500);
    return `set to ${PERSON}, who signs what follows`;
  });

  await step('Ingest', async () => {
    await at(page, '/intake/ingest');
    await page.getByRole('tab', { name: /Paste/ }).click();
    await page.getByLabel('Title').fill('A note the walk pasted');
    await page.getByLabel('Text', { exact: true }).fill(
      'Ethanol was recovered from the fermented broth by distillation, and the stillage was sent to the boiler.',
    );
    await page.getByRole('form', { name: 'Add a document' }).locator('button[type="submit"]').click();
    const held = page.getByRole('list', { name: 'Documents in this project' }).getByText('A note the walk pasted');
    await held.first().waitFor({ timeout: 180_000 });
    return 'a pasted document taken into the project, split into passages and embedded, and listed among its documents';
  });

  await step('Search', async () => {
    await at(page, '/biorepo/search');
    await page.getByLabel('Question').fill('how was the ethanol recovered');
    await page.getByRole('form', { name: 'Search the papers' }).locator('button[type="submit"]').click();
    const found = page.getByRole('list', { name: 'Passages found' }).locator('li');
    await found.first().waitFor();
    const n = await found.count();
    return `${n} passage${n === 1 ? '' : 's'} found for a question in words`;
  });

  await step('Run report', async () => {
    await at(page, `/proforma/runs/${RUN}`);
    await page.getByTestId('run-sff').waitFor();
    const graph = page.getByTestId('sff-graph');
    await graph.waitFor();
    const units = Number(await graph.getAttribute('data-units'));
    const drawn = await page.getByTestId('sff-unit').count();
    if (!(units > 0 && drawn === units)) throw new Error(`the graph names ${units} units and draws ${drawn}`);
    return `run ${RUN}'s report, its SFF file and its graph: ${units} units drawn`;
  });

  await step('Conversation', async () => {
    await at(page, `/postdoc/${CONVERSATION}`);
    await page.getByTestId('claim-values').first().waitFor();
    await page.getByText(/an estimate by/).first().waitFor();
    return `conversation ${CONVERSATION} read from the service, its estimate marked as one`;
  });

  await step('Runbook', async () => {
    await at(page, `/runbooks/${RUNBOOK}`);
    await page.getByTestId('prediction-artifact').first().waitFor();
    return `runbook ${RUNBOOK}, each prediction linked to the run it came from`;
  });

  check(errors.length === 0, errors.length ? `console: ${errors.slice(0, 3).join(' | ')}` : 'no console error on any page');
  await browser.close();
  process.exit(failed ? 1 : 0);
}

void main();
