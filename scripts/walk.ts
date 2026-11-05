/**
 * The UI walk (execution prompt §9.1 step 9; stage 7): a person's path through
 * the built app, in Chromium, against a real service that serves dist/ on
 * loopback and holds a project the proof has filled (scripts/prove.py step 9
 * starts it): Home → the project → a document pasted in and searched → a run's
 * report and its SFF graph → a scenario begun from the run → the plants Studies
 * offers to run → the project's SFF flowsheets → the catalogues screen, where
 * the person keeps a placeholder strain, edits it, takes in a file naming it
 * again and reads it back as their own (alpha 2.2 E.8) → a lesson taken in from a
 * file with its body and renamed on the form, its body read back whole; a skill
 * kept with no policy, which its Guild page says in words; and a protocol kept
 * after the page opened, found at its address, its editor opened by its address
 * on a fresh load showing the steps kept (alpha 2.2 E.gate) → geneOS's Hosts, where
 * that strain has its card, and its page with the other names its entry keeps
 * (alpha 2.2 E.9) → a conversation with
 * its labelled estimate → a runbook → a reading deposited at the bench on that
 * locked runbook, the readings alone, in the unit a scenario parameter of the
 * project is denominated in, the placeholder value the person types and reads
 * back → a scenario made from the run through NewScenarioDialog with that
 * reading chosen and nothing typed, and run → the run's page: its provenance
 * measured, the reading's origin in words with a link that opens its
 * deposition, the parameter's chip measured (alpha 2.2 C.5) → for each engine
 * WALK_ENGINES names (the proof's: those a package under examples/engines/
 * registers), its first thing run on its own defaults from the Runs screen,
 * the engine chosen on Studies' run card, and the run's page opened: its
 * provenance, its outputs and its diagnostics as the service keeps them
 * (alpha 2.2 D0.8). The walk names no engine of its own.
 *
 *   WALK_ORIGIN=http://127.0.0.1:PORT WALK_PROJECT=<id> WALK_RUN=<run id> \
 *   WALK_CONVERSATION=<id> WALK_RUNBOOK=<id> WALK_PERSON=<name> \
 *   WALK_READING=<placeholder> WALK_READING_UNIT=<unit> WALK_READING_PARAMETER=<key> \
 *   [WALK_STRAIN=<id>] [WALK_ENGINES=<name>,<name>] npx tsx scripts/walk.ts
 *
 * One line a check, ✓ or ✗ with what it saw; exit 1 when one fails. A console
 * error or an uncaught exception on any page is a failed check.
 */
import { existsSync } from 'node:fs';
import { chromium, type Page } from 'playwright';
import type { CatalogueEntry } from '../src/lib/catalogues';
import type { DepositionReading, RunReport } from '../src/lib/studies';
import type { Protocol } from '../src/lib/protocols';

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
// The placeholder strain the walk keeps on the catalogues screen: an id the proof names, a name and other names that
// stand for no strain (the repository ships software alone), and the file the screen takes in naming it again.
const STRAIN = process.env.WALK_STRAIN?.trim() || 'walk-placeholder-strain';
const STRAIN_NAME = 'A placeholder strain the walk keeps';
const STRAIN_ALIASES = ['WALK-1', 'WALK-2'];
const STRAIN_FILE = 'walk-strains.csv';
// The placeholder lesson, skill and protocol the walk keeps (alpha 2.2 E.gate): words and numbers a person writes, each
// standing for nothing (the repository ships software alone).
const LESSON = 'walk-placeholder-lesson';
const LESSON_FILE = 'walk-lessons.json';
const UNRATED_SKILL = 'walk-placeholder-skill';
const PROTOCOL = 'walk-placeholder-protocol';
// The engines whose first thing the walk runs from the Runs screen, comma-separated; none when unset.
const ENGINES = (process.env.WALK_ENGINES ?? '')
  .split(',')
  .map((name) => name.trim())
  .filter(Boolean);
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

// Each answer the walk reads back is the service's own model, generated from it (ADR-007): a run's report
// (GET /api/runs/{id}), a catalogue entry (GET /api/catalogues/{kind}/{id}) and a reading a run may take
// (GET /api/depositions/readings).
type HeldReport = RunReport;
type HeldEntry = CatalogueEntry;
type Reading = DepositionReading;

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
    await page.getByTestId('flowsheets-import-url').waitFor();
    await page.getByTestId('flowsheets-library-file').first().waitFor();
    return `${runs} record${runs === 1 ? '' : 's'} written by runs listed, with an import by file or by address and the toolkit's reference files`;
  });

  // alpha 2.2 E.8: the catalogues screen keeps a placeholder strain in the person's name, edits it, takes in a file
  // naming it again, and the service reads it back as the person's.
  await step('Catalogues', async () => {
    await at(page, '/catalogues');
    await page.locator('[data-testid="catalogues"][data-kind="strain"]').waitFor();
    await page.getByTestId('catalogue-add').click();
    const add = page.locator('[data-testid="catalogue-form"][data-mode="add"]');
    await add.getByTestId('catalogue-field-id').fill(STRAIN);
    await add.getByTestId('catalogue-field-name').fill(STRAIN_NAME);
    await add.getByTestId('catalogue-field-aliases').fill(STRAIN_ALIASES[0]);
    await add.getByTestId('catalogue-field-note').fill('A placeholder the walk keeps; it stands for no strain.');
    await add.getByTestId('catalogue-keep').click();
    const row = page.locator(`[data-testid="catalogue-entry"][data-entry="${STRAIN}"]`);
    await row.waitFor();
    await row.getByTestId('catalogue-edit').click();
    const edit = page.locator(`[data-testid="catalogue-form"][data-mode="edit"][data-entry="${STRAIN}"]`);
    await edit.getByTestId('catalogue-field-aliases').fill(STRAIN_ALIASES.join('\n'));
    await edit.getByTestId('catalogue-keep').click();
    await page.locator(`[data-testid="catalogue-kept"][data-entry="${STRAIN}"]`).waitFor();
    await row.getByText(STRAIN_ALIASES.join(', ')).waitFor();
    const csv = `id,name,aliases\n${STRAIN},${STRAIN_NAME},${STRAIN_ALIASES.join(';')}\n`;
    await page.getByTestId('catalogue-intake-file').setInputFiles({ name: STRAIN_FILE, mimeType: 'text/csv', buffer: Buffer.from(csv) });
    await page.getByTestId('catalogue-intake-go').click();
    await page.locator('[data-testid="catalogue-intake-result"][data-kept="1"][data-refused="0"]').waitFor();
    await row.getByText(`from the file ${STRAIN_FILE}`).waitFor();
    const answered = await page.request.get(`${ORIGIN}/api/catalogues/strain/${encodeURIComponent(STRAIN)}`, {
      headers: { 'X-OpenFerment-Project': PROJECT },
    });
    if (!answered.ok()) throw new Error(`GET /api/catalogues/strain/${STRAIN} answered ${answered.status()}`);
    const held = (await answered.json()) as HeldEntry;
    const aliases = (held.aliases ?? []).join(', ');
    if (held.by !== PERSON || held.agent !== 'person' || held.via != null || held.name !== STRAIN_NAME || aliases !== STRAIN_ALIASES.join(', ') || held.source !== `the file ${STRAIN_FILE}`)
      throw new Error(`the service keeps ${STRAIN} as "${held.name}" (${aliases}) by ${held.by} in the ${held.agent} lane from ${held.source}`);
    return `placeholder strain ${STRAIN} kept on the catalogues screen in ${PERSON}'s name, edited to the other names ${aliases}, taken in again from ${STRAIN_FILE} through the screen, and read back from the service as ${PERSON}'s keep from that file`;
  });

  // alpha 2.2 E.9: geneOS's hosts are the project's strain catalogue, which the store reads, so the strain the person
  // kept has its card on Hosts and its own page, named as its entry names it.
  // alpha 2.2 E.gate: a lesson taken in from a file with its body, then renamed on the form, keeps its body whole.
  await step('A lesson edited on the form', async () => {
    await at(page, '/catalogues/lessons');
    await page.locator('[data-testid="catalogues"][data-kind="lesson"]').waitFor();
    const lesson = {
      kind: 'lesson',
      id: LESSON,
      name: 'A placeholder lesson the walk keeps',
      minutes: 5,
      blocks: [{ kind: 'prose', md: 'A placeholder paragraph.' }, { kind: 'embed', embed: 'mini-queue' }],
      checkpoint: [{ id: 'q1', prompt: 'A placeholder choice?', kind: 'mc', options: ['One', 'Two'], answerIndex: 1 }],
    };
    await page.getByTestId('catalogue-intake-file').setInputFiles({ name: LESSON_FILE, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify([lesson])) });
    await page.getByTestId('catalogue-intake-go').click();
    await page.locator('[data-testid="catalogue-intake-result"][data-kept="1"][data-refused="0"]').waitFor();
    const row = page.locator(`[data-testid="catalogue-entry"][data-entry="${LESSON}"]`);
    await row.locator('[data-testid="catalogue-lesson-row-body"][data-blocks="2"][data-questions="1"]').waitFor();
    await row.getByTestId('catalogue-edit').click();
    const edit = page.locator(`[data-testid="catalogue-form"][data-mode="edit"][data-entry="${LESSON}"]`);
    await edit.getByTestId('catalogue-field-name').fill('A placeholder lesson the walk keeps, renamed');
    await edit.getByTestId('catalogue-keep').click();
    await page.locator(`[data-testid="catalogue-kept"][data-entry="${LESSON}"]`).waitFor();
    const answered = await page.request.get(`${ORIGIN}/api/catalogues/lesson/${encodeURIComponent(LESSON)}`, {
      headers: { 'X-OpenFerment-Project': PROJECT },
    });
    if (!answered.ok()) throw new Error(`GET /api/catalogues/lesson/${LESSON} answered ${answered.status()}`);
    const held = (await answered.json()) as HeldEntry;
    const blocks = (held.blocks ?? []).length;
    const questions = (held.checkpoint ?? []).length;
    if (held.name !== 'A placeholder lesson the walk keeps, renamed' || held.minutes !== 5 || blocks !== 2 || questions !== 1 || held.by !== PERSON)
      throw new Error(`the service keeps ${LESSON} as "${held.name}" by ${held.by} with ${held.minutes} min, ${blocks} blocks and ${questions} questions`);
    return `placeholder lesson ${LESSON} taken in from ${LESSON_FILE} with its body, renamed on the form in ${PERSON}'s name, and read back from the service with its ${held.minutes} min, ${blocks} blocks and ${questions} checkpoint question whole`;
  });

  // alpha 2.2 E.gate: a skill kept with no policy reads so in words on Guild's skill page.
  await step('A skill with no policy', async () => {
    await at(page, '/catalogues/skills');
    await page.locator('[data-testid="catalogues"][data-kind="skill"]').waitFor();
    await page.getByTestId('catalogue-add').click();
    const add = page.locator('[data-testid="catalogue-form"][data-mode="add"]');
    await add.getByTestId('catalogue-field-id').fill(UNRATED_SKILL);
    await add.getByTestId('catalogue-field-name').fill('A placeholder skill the walk keeps');
    await add.getByTestId('catalogue-keep').click();
    await page.locator(`[data-testid="catalogue-entry"][data-entry="${UNRATED_SKILL}"] [data-testid="catalogue-policy"][data-policy="none"]`).waitFor();
    await at(page, `/guild/skills/${UNRATED_SKILL}`);
    await page.getByTestId('guild-skill-no-policy').waitFor();
    await page.getByTestId('guild-skill-no-mastery').waitFor();
    return `placeholder skill ${UNRATED_SKILL} kept with no policy; its Guild page says it holds none and names no criterion, in words`;
  });

  // alpha 2.2 E.gate: a protocol kept after the page opened is found by its address, and its editor opened by its
  // address on a fresh load starts from the steps the service keeps.
  await step('A protocol opened by its address', async () => {
    const version = {
      version: '1.0',
      baseBatch: { value: 1, unit: 'placeholder-unit', label: 'a placeholder batch' },
      materials: [{ name: 'Placeholder material', amount: 1, unit: 'placeholder-unit', scaling: 'fixed', precision: 0 }],
      steps: [
        { id: 's1', text: 'Add {{qty:Placeholder material}}.' },
        { id: 's2', text: 'A placeholder second step.' },
      ],
      estMinutes: { active: 1, total: 2 },
    };
    const made = await page.request.post(`${ORIGIN}/api/protocols`, {
      headers: { 'X-OpenFerment-Project': PROJECT, 'Content-Type': 'application/json' },
      data: { protocol: { id: PROTOCOL, title: 'A placeholder protocol the walk keeps', category: 'sop', bsl: 1, versions: [version], currentVersion: '1.0' }, by: PERSON },
    });
    if (!made.ok()) throw new Error(`POST /api/protocols answered ${made.status()}: ${await made.text()}`);
    await at(page, `/runbooks/protocols/${PROTOCOL}`);
    await page.getByRole('heading', { name: 'A placeholder protocol the walk keeps' }).first().waitFor();
    await at(page, `/runbooks/protocols/${PROTOCOL}/edit`);
    await page.reload();
    await page.getByLabel('Step 2 instruction').waitFor();
    const boxes = await page.getByLabel(/^Step \d+ instruction$/).count();
    if (boxes !== 2) throw new Error(`the editor opened by its address shows ${boxes} steps of the 2 version 1.0 keeps`);
    return `placeholder protocol ${PROTOCOL} kept in ${PERSON}'s name after the page opened, found at its address, and its editor opened by its address on a fresh load showing the 2 steps version 1.0 keeps`;
  });

  // alpha 2.2 E.gate: a protocol begun on the protocols page, in the person's name, opens in its editor.
  await step('A protocol begun on the page', async () => {
    await at(page, '/runbooks/protocols');
    await page.getByTestId('begin-protocol-open').click();
    const form = page.getByTestId('begin-protocol');
    await form.getByTestId('begin-protocol-id').fill(`${PROTOCOL}-begun`);
    await form.getByTestId('begin-protocol-title').fill('A placeholder protocol the walk begins');
    await form.getByTestId('begin-protocol-batchValue').fill('1');
    await form.getByTestId('begin-protocol-batchUnit').fill('placeholder-unit');
    await form.getByTestId('begin-protocol-active').fill('1');
    await form.getByTestId('begin-protocol-total').fill('2');
    await form.getByTestId('begin-protocol-steps').fill('A placeholder first step.\nA placeholder second step.');
    await form.getByTestId('begin-protocol-keep').click();
    await page.getByLabel('Step 2 instruction').waitFor();
    const answered = await page.request.get(`${ORIGIN}/api/protocols/${encodeURIComponent(`${PROTOCOL}-begun`)}`, {
      headers: { 'X-OpenFerment-Project': PROJECT },
    });
    if (!answered.ok()) throw new Error(`GET /api/protocols/${PROTOCOL}-begun answered ${answered.status()}`);
    const held = (await answered.json()) as Protocol;
    const steps = held.versions[0]?.steps ?? [];
    if (held.currentVersion !== '1.0' || steps.length !== 2 || held.versions[0]?.by !== PERSON)
      throw new Error(`the service keeps ${held.id} at version ${held.currentVersion} with ${steps.length} steps, kept by ${held.versions[0]?.by}`);
    return `placeholder protocol ${held.id} begun on the protocols page in ${PERSON}'s name with version 1.0 and its 2 steps, and opened in its editor`;
  });

  await step('Hosts', async () => {
    await at(page, '/geneos/hosts');
    const card = page.locator(`[data-testid="strain-card"][data-strain="${STRAIN}"]`);
    await card.waitFor();
    await card.getByText(STRAIN_NAME, { exact: true }).waitFor();
    await card.getByRole('link', { name: /Open/ }).click();
    const held = page.locator(`[data-testid="strain-page"][data-strain="${STRAIN}"]`);
    await held.waitFor();
    await held.getByText(STRAIN_NAME, { exact: true }).first().waitFor();
    const aliases = (await held.getByTestId('strain-aliases').innerText()).trim();
    if (aliases !== STRAIN_ALIASES.join(', ')) throw new Error(`the strain's page names its other names as "${aliases}"`);
    return `geneOS → Hosts shows ${STRAIN}'s card from the project's strain catalogue, and its page names it with its other names ${aliases}`;
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

  // alpha 2.2 D0.8: each engine the walk is given, its first thing run on its own defaults from the Runs screen.
  for (const name of ENGINES) {
    await step(`The ${name} engine from the Runs screen`, async () => {
      await at(page, '/proforma/studies');
      const pick = page.getByTestId('run-plant-engine');
      await pick.waitFor();
      const offered = await pick.locator('option').evaluateAll((options) => options.map((o) => (o as HTMLOptionElement).value));
      if (!offered.includes(name)) throw new Error(`the run card offers ${offered.join(', ') || 'no engine'}, and no ${name}`);
      await pick.selectOption(name);
      const thing = page.getByTestId('run-engine-thing');
      await thing.waitFor();
      const first = await thing.inputValue();
      await page.getByTestId('run-engine-go').click();
      const ran = page.locator(`[data-testid="run-plant-ran"][data-engine="${name}"]`);
      // A thing that needs a value no default gives is refused on the card in the service's words: every thing of an
      // engine under examples/engines/ runs on its own defaults, with no value set (docs/api/engines.md).
      const refused = page.getByTestId('run-plant-problem');
      await ran.or(refused).first().waitFor({ timeout: RUN_TIMEOUT });
      if (await refused.count())
        throw new Error(
          `${first} on the ${name} engine's own defaults: ${((await refused.first().textContent()) ?? '').trim()}. ` +
            'Every thing of an engine under examples/engines/ runs on its own defaults, with no value set: give each of its parameters a default',
        );
      const id = (await ran.getAttribute('data-run')) ?? '';
      if ((await ran.getAttribute('data-status')) !== 'done') throw new Error(`run ${id} of ${first}: ${(await ran.innerText()).trim()}`);
      await ran.getByRole('link', { name: `Run ${id}` }).click();
      await page.locator(`[data-testid="proforma-run"][data-run="${id}"][data-status="done"]`).waitFor();
      const answered = await page.request.get(`${ORIGIN}/api/runs/${id}`, { headers: { 'X-OpenFerment-Project': PROJECT } });
      if (!answered.ok()) throw new Error(`GET /api/runs/${id} answered ${answered.status()}`);
      const held = ((await answered.json()) as HeldReport).run;
      const provenance = await page.getByTestId('run-provenance').getAttribute('data-provenance');
      if (held.engine !== name || held.plant !== first || provenance !== held.provenance)
        throw new Error(`the page reads ${provenance} for run ${id}, which the service keeps as ${held.engine}'s run of ${held.plant}, ${held.provenance}`);
      const outputs = Array.isArray(held.outputs?.values) ? held.outputs.values.length : 0;
      const drawn = await page.getByTestId('run-output').count();
      if (drawn !== outputs) throw new Error(`the page shows ${drawn} outputs of the ${outputs} the run keeps`);
      const reported = (held.diagnostics ?? []).length;
      const listed = await page.getByTestId('run-diagnostic').count();
      if (listed !== reported) throw new Error(`the page shows ${listed} diagnostics of the ${reported} the run keeps`);
      return `${first} run on the ${name} engine's own defaults from Studies' run card as run ${id}; its page reads it ${provenance}, with its ${outputs} output${outputs === 1 ? '' : 's'} and ${reported} diagnostic${reported === 1 ? '' : 's'} as the service keeps them`;
    });
  }

  check(errors.length === 0, errors.length ? `console: ${errors.slice(0, 3).join(' | ')}` : 'no console error on any page');
  await browser.close();
  process.exit(failed ? 1 : 0);
}

void main();
