/**
 * The UI walk (execution prompt §9.1 step 9; stage 7): a person's path through
 * the built app, in Chromium, against a real service that serves dist/ on
 * loopback and holds a project the proof has filled (scripts/prove.py step 9
 * starts it): Home → the project → a document pasted in and searched → a run's
 * report and its SFF graph → a scenario begun from the run → the plants Studies
 * offers to run → the project's SFF flowsheets → a conversation with its
 * labelled estimate → a runbook → a reading deposited at the bench on that
 * locked runbook, the readings alone, in the unit a scenario parameter of the
 * project is denominated in, the placeholder value the person types and reads
 * back → a scenario made from the run through NewScenarioDialog with that
 * reading chosen and nothing typed, and run → the run's page: its provenance
 * measured, the reading's origin in words with a link that opens its
 * deposition, the parameter's chip measured (alpha 2.2 C.5).
 *
 *   WALK_ORIGIN=http://127.0.0.1:PORT WALK_PROJECT=<id> WALK_RUN=<run id> \
 *   WALK_CONVERSATION=<id> WALK_RUNBOOK=<id> WALK_PERSON=<name> \
 *   WALK_READING=<placeholder> WALK_READING_UNIT=<unit> WALK_READING_PARAMETER=<key> \
 *   npx tsx scripts/walk.ts
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
// Who signs what follows: the proof's person, who deposits the reading and makes the scenario on it.
const PERSON = process.env.WALK_PERSON?.trim() || 'Walk Reviewer';
// The reading the bench takes: a placeholder the person types, in the unit of a parameter a scenario of the project
// sets (the unit the runbook's measure is in), and the parameter the scenario sets to it. The pairing is a
// placeholder chosen by unit: the service holds a reading's unit to the parameter's, and which measure stands for
// which parameter is the scenario maker's to choose.
const READING = env('WALK_READING');
const READING_UNIT = env('WALK_READING_UNIT');
const PARAMETER = env('WALK_READING_PARAMETER');
const TIMEOUT = 60_000;
// How long a scenario's run may take, BioSTEAM building its plant fresh in the warm worker.
const RUN_TIMEOUT = 600_000;
const IGNORE = [/Download the React DevTools/i, /favicon/i];

let failed = 0;
function check(ok: boolean, words: string): void {
  console.log(`  ${ok ? '✓' : '✗'} ${words}`);
  if (!ok) failed += 1;
}

let current: Page | null = null;

/** A reading as the service lists it (GET /api/depositions/readings). */
interface Reading {
  ref: string;
  value: number;
  unit: string;
  by: string;
  at: string;
}

/**
 * The reading `ref` as the service lists it among those a run takes in the walk's unit, asked until the bench's
 * write reaches it (the page sends each change as it is made).
 */
async function readingHeld(page: Page, ref: string): Promise<Reading> {
  const deadline = Date.now() + 30_000;
  for (;;) {
    const answered = await page.request.get(`${ORIGIN}/api/depositions/readings?unit=${encodeURIComponent(READING_UNIT)}`, {
      headers: { 'X-OpenFerment-Project': PROJECT },
    });
    if (answered.ok()) {
      const found = ((await answered.json()) as Reading[]).find((r) => r.ref === ref);
      if (found) return found;
    }
    if (Date.now() > deadline) throw new Error(`the service lists no reading ${ref} in ${READING_UNIT} 30 s after the bench kept it`);
    await page.waitForTimeout(500);
  }
}

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

  await step('A scenario from the run', async () => {
    // The run's page opens NewScenarioDialog over its parameters, to set as the person's assumptions or to
    // readings; the walk finds one by words, sets it, and leaves the dialog with nothing made.
    await page.getByTestId('run-make-scenario').waitFor();
    await page.getByTestId('run-make-scenario-open').click();
    const maker = page.getByTestId('run-make-scenario-dialog');
    await maker.getByTestId('scenario-find').fill('price');
    const found = maker.getByTestId('scenario-found-row');
    await found.first().waitFor();
    await found.first().getByRole('button').click();
    await maker.getByTestId('scenario-setting').first().waitFor();
    const n = await found.count();
    await maker.getByRole('button', { name: 'Cancel' }).click();
    await maker.waitFor({ state: 'detached' });
    return `NewScenarioDialog over the run's parameters found by words (${n} for "price"), one set to make a scenario of, nothing made`;
  });

  await step('Run a plant', async () => {
    await at(page, '/proforma/studies');
    const plants = page.getByTestId('run-plant-plant').locator('option');
    await plants.first().waitFor({ state: 'attached' });
    const n = await plants.count();
    return `Studies offers ${n} plant${n === 1 ? '' : 's'} the installed package built here, each in the configurations it built in`;
  });

  await step('Flowsheets', async () => {
    await at(page, '/flowsheets');
    await page.getByTestId('flowsheets-held').waitFor();
    const runs = await page.locator('[data-testid="flowsheets-record"][data-origin="run"]').count();
    if (runs === 0) throw new Error('no SFF record written by a run is listed');
    await page.getByTestId('flowsheets-import').waitFor();
    await page.getByTestId('flowsheets-library-file').first().waitFor();
    return `${runs} record${runs === 1 ? '' : 's'} written by runs listed, with an import and the toolkit's reference files`;
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

  // alpha 2.2 C.5: a reading deposited at the bench on the locked runbook, a scenario on it alone, its run measured.
  let deposition = '';
  let entry = '';
  let ref = '';
  await step('A reading at the bench', async () => {
    await at(page, `/runbooks/${RUNBOOK}`);
    await page.getByRole('button', { name: /Start a deposition/ }).click();
    await page.getByTestId('deposition-readings-alone').click();
    const staged = page.locator('[data-testid="deposition-bench"][data-state="staged"]');
    await staged.waitFor();
    deposition = (await staged.getAttribute('data-deposition')) ?? '';
    await page.getByTestId('deposition-bench-begin').click();
    await page.locator('[data-testid="deposition-bench"][data-state="running"]').waitFor();
    const box = page.getByLabel('Describe what you observed');
    const said = `came in at ${READING} ${READING_UNIT}`;
    await box.fill(said);
    await box.press('Enter');
    const readBack = page.getByRole('button', { name: 'That is right' });
    await readBack.click();
    await readBack.waitFor({ state: 'detached' });
    await page.getByTestId('deposition-bench-close').click();
    await page.getByTestId('deposition-bench-close-confirm').click();
    // The deposition's record, its reading confirmed.
    const kept = page.locator('[data-testid="deposition-entry"][data-confirmed="true"]');
    await kept.first().waitFor();
    if ((await kept.count()) !== 1) throw new Error(`the record holds ${await kept.count()} confirmed readings, and the bench took one`);
    entry = (await kept.first().getAttribute('data-entry')) ?? '';
    ref = `${deposition}/${entry}`;
    // The service holds it as a reading a run takes in the parameter's unit, deposited by the person.
    const held = await readingHeld(page, ref);
    if (held.by !== PERSON || held.value !== Number(READING) || held.unit !== READING_UNIT)
      throw new Error(`the service lists ${ref} as ${held.value} ${held.unit} by ${held.by}`);
    return `deposition ${deposition} on runbook ${RUNBOOK}, the readings alone: "${said}" typed by ${PERSON}, read back, kept as reading ${ref}, and listed by the service as one a run takes in ${READING_UNIT}`;
  });

  let measured = '';
  await step('A scenario on the reading', async () => {
    if (!ref) throw new Error('no reading was deposited to make the scenario on');
    await at(page, `/proforma/runs/${RUN}`);
    await page.getByTestId('run-make-scenario-open').click();
    const maker = page.getByTestId('run-make-scenario-dialog');
    await maker.getByTestId('scenario-find').fill(PARAMETER);
    await maker.locator(`[data-testid="scenario-found-row"][data-key="${PARAMETER}"]`).getByRole('button').click();
    const setting = maker.locator(`[data-testid="scenario-setting"][data-key="${PARAMETER}"]`);
    await setting.getByTestId('scenario-source-reading').click();
    const choice = setting.locator(`[data-testid="scenario-reading"][data-ref="${ref}"]`);
    await choice.waitFor();
    const offered = (await choice.innerText()).replace(/\s+/g, ' ').trim();
    await choice.locator('input[type="radio"]').check();
    if ((await maker.getByTestId('scenario-setting').count()) !== 1) throw new Error('the scenario sets more than the reading');
    await maker.getByLabel("The scenario's title").fill('On the bench’s reading');
    await maker.getByTestId('run-make-scenario-go').click();
    const opened = page.locator(`[data-testid="proforma-run"][data-status="done"]:not([data-run="${RUN}"])`);
    await opened.waitFor({ timeout: RUN_TIMEOUT });
    measured = (await opened.getAttribute('data-run')) ?? '';
    return `NewScenarioDialog: ${PARAMETER} set to reading ${ref} (${offered}), a placeholder pairing chosen by unit, nothing typed; the scenario made and run in ${PERSON}'s name as run ${measured}`;
  });

  await step('The measured run', async () => {
    if (!measured) throw new Error('no run was made on the reading');
    await page.locator('[data-testid="run-provenance"][data-provenance="measured"]').waitFor();
    const origins = await page.getByTestId('run-input').evaluateAll((rows) => rows.map((r) => r.getAttribute('data-origin') ?? ''));
    const beside = origins.filter((k) => !['measurement', 'library-default', 'convention'].includes(k));
    if (beside.length) throw new Error(`inputs beside the reading: ${beside.join(', ')}`);
    const input = page.locator('[data-testid="run-input"][data-origin="measurement"]');
    if ((await input.count()) !== 1) throw new Error(`${await input.count()} inputs are measurements, and the scenario set one`);
    const origin = input.getByTestId('measurement-origin');
    if ((await origin.getAttribute('data-ref')) !== ref) throw new Error(`the input names reading ${await origin.getAttribute('data-ref')}`);
    const words = (await origin.innerText()).replace(/\s+/g, ' ').trim();
    await page.locator(`[data-testid="param-row"][data-key="${PARAMETER}"] [data-testid="param-chip"][data-origin="measurement"]`).waitFor();
    await origin.getByTestId('measurement-deposition').click();
    await page.locator(`[data-testid="deposition-entry"][data-entry="${entry}"][data-confirmed="true"]`).waitFor();
    return `run ${measured}: measured; ${PARAMETER} reads "${words}", its parameter's chip measured, and its link opens deposition ${deposition} at reading ${entry}`;
  });

  check(errors.length === 0, errors.length ? `console: ${errors.slice(0, 3).join(' | ')}` : 'no console error on any page');
  await browser.close();
  process.exit(failed ? 1 : 0);
}

void main();
