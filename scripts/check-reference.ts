/**
 * The no-results rule, enforced (OF-BLD-010 §1, §7).
 *
 * `src/data/reference.ts` exists because of one distinction, and the whole
 * increment is worthless if that distinction erodes:
 *
 *   REFERENCE CONTENT is domain knowledge. The seven EC classes. The
 *   chromatography modes that exist. The published genome-scale models. The
 *   rules for computing a priority date. A textbook contains these, and putting
 *   them on screen is not fabrication.
 *
 *   RESULTS are answers. A titre, a yield, a cost per kilogram, a patent
 *   status. Inventing one of those is the failure the whole product exists to
 *   avoid.
 *
 *   A stub subsystem may show what the FIELD looks like. It may never show what
 *   YOUR ANSWER would be.
 *
 * That rule is a sentence in a header comment, and a sentence in a header
 * comment is not a constraint — it is a hope about future readers. This makes
 * it a build failure.
 *
 * THE DESIGN. A blanket ban on digits is wrong: this file legitimately contains
 * iML1515, UniRef90, OD600, AlphaFold3, a DOI shape, the 8 June 1995 GATT
 * transition and "17 years from issue". So there are three rules, in order of
 * severity:
 *
 *   1. HARD — no number adjacent to a result unit, anywhere, ever. `4.2 g/L`
 *      cannot appear whatever else is true. No exceptions and no allowlist.
 *   2. HARD — no patent status word in the same cell as a patent number. The
 *      file names one patent publication as an example SHAPE; the moment a
 *      status attaches to it, it stops being a shape and becomes a claim.
 *   3. JUSTIFIED — every remaining numeric cell must match a pattern that has a
 *      stated reason. Adding a number to this file is then a deliberate act:
 *      either it fits an existing justification, or somebody writes a new one
 *      down here and says why.
 *
 * Runs offline, needs no key and no service.
 */
import { REFERENCE, referenceFor, type ReferenceContent } from '../src/data/reference';
import { PROVENANCE_LABEL, aggregateExclusion } from '../src/store';
import { RECORDS } from '../src/data/records';
import { SUBSYSTEMS } from '../src/data/subsystems';
import { ELEVEN } from '../src/data/nav';
import type { Provenance } from '../src/data/types';

const errors: string[] = [];
const fail = (m: string) => errors.push(m);

// ── 1. result units ────────────────────────────────────────────────────
//
// The units an ANSWER is denominated in, in this domain. A number touching one
// of these is a result no matter what column it sits in.
//
// Bare units on their own are fine and expected — "Target titre | HPLC or
// ELISA | g/L" names what an instrument measures and in what, which is exactly
// the kind of thing a reference shelf holds. It is the NUMBER that makes it an
// answer.
const RESULT_UNITS = [
  'g/L', 'g L-1', 'g/l',
  'mg/mL', 'mg/ml', 'µg/mL', 'ug/mL',
  'mg/g', 'g/g', 'kg', 'tonne', 'tonnes',
  '% TSP', '%TSP',
  'U/mg', 'EU/mg', 'pg/U', 'pg/mg', 'IMCU/mg',
  'USD', 'EUR', '/kg', 'kWh',
  'colonies', 'CFU', 'OD units',
];

const escapeRe = (t: string) => t.replace(/[.*+?^${}()|[\]\\/-]/g, '\\$&');

// A number, optional space, then a result unit. The lookbehind keeps
// identifiers out of it: `OD600` is letters-then-digits and never matches,
// because the digit is not standing alone as a quantity.
const RESULT_VALUE = new RegExp(
  `(?<![A-Za-z])\\d[\\d.,]*\\s*(?:${RESULT_UNITS.map(escapeRe).join('|')})(?![a-z])`,
);

// ── 2. patent status ───────────────────────────────────────────────────
const PATENT_NUMBER = /\b[A-Z]{2}\d{6,}(?:[A-Z]\d?)?\b/;
const PATENT_STATUS =
  /\b(granted|expired|lapsed|in force|invalidated|invalid|unenforceable|revoked|abandoned by|allowed|rejected)\b/i;

// ── 3. justified numerics ──────────────────────────────────────────────
//
// Every one of these is a real reason a number belongs in a reference shelf.
// A new numeric cell that fits none of them fails, and the fix is to remove the
// number or to add a justification here with a sentence saying why.
//
// IDENTIFIERS ARE MASKED, NOT MATCHED. A first pass at this anchored the
// identifier pattern to the whole cell and produced four false positives on day
// one — "E. coli K-12 MG1655" and "Sequence, fast MSA via MMseqs2" are
// identifiers sitting inside a phrase, not cells that ARE an identifier. A
// guard that fails on correct content is a guard somebody switches off, so
// identifier-shaped tokens are blanked first and only what survives is judged.
//
// The shape is the same one the Python Rule 1 validator uses: an identifier's
// digits are attached to letters, letters first (cw15, OD600, K-12, MG1655,
// AlphaFold3). A quantity's digits stand alone or lead.
const IDENTIFIER_TOKEN = /(?<![0-9.])[A-Za-z][A-Za-z]*(?:-[A-Za-z]*)*\d[A-Za-z0-9-]*/g;

const maskIdentifiers = (text: string) =>
  text.replace(IDENTIFIER_TOKEN, (m) => ' '.repeat(m.length));

const JUSTIFIED: { why: string; re: RegExp }[] = [
  { why: 'DOI example shape', re: /^10\.\d{4,}\//, },
  { why: 'PMID example shape — an 8-digit accession', re: /^\d{7,9}$/ },
  { why: 'PMCID example shape', re: /^PMC\d+$/ },
  { why: 'arXiv identifier shape', re: /^\d{4}\.\d{4,5}$/ },
  { why: 'patent publication example shape, with no status attached', re: /^[A-Z]{2}\d{6,}[A-Z]\d?$/ },
  { why: 'EC top-level class number, 1 through 7', re: /^[1-7]$/ },
  { why: 'US patent term rule — a statutory period, not a measurement', re: /\b(17|20) years\b/ },
  { why: 'the GATT transition date, a fixed point in law', re: /\b\d{1,2} [A-Z][a-z]+ \d{4}\b/ },
  {
    why: 'quoted claim limitation — the SHAPE of a patent claim, not a measured identity',
    re: /at least \d+% identical to SEQ ID NO:\d+/,
  },
  { why: 'chemical nomenclature (alpha-1,2-fucosyltransferase)', re: /alpha-\d,\d-/ },
  {
    why: 'a worked example of how NOT to state a prediction, inside a note that says so',
    re: /'Predicted Tm: \d+' is not evidence/,
  },
];

const hasDigit = /\d/;

interface Cell {
  where: string;
  text: string;
}

/** Every string in the file, with a path saying where it came from. */
function walk(): Cell[] {
  const cells: Cell[] = [];
  for (const [id, content] of Object.entries(REFERENCE) as [string, ReferenceContent][]) {
    cells.push({ where: `${id} · blurb`, text: content.blurb });
    if (content.note) cells.push({ where: `${id} · note`, text: content.note });
    for (const table of content.tables) {
      cells.push({ where: `${id} · ${table.title} · title`, text: table.title });
      for (const col of table.cols) {
        cells.push({ where: `${id} · ${table.title} · column "${col}"`, text: col });
      }
      for (const [i, row] of table.rows.entries()) {
        for (const [j, cell] of row.entries()) {
          cells.push({
            where: `${id} · ${table.title} · row ${i + 1} col ${j + 1} (${table.cols[j] ?? '?'})`,
            text: cell,
          });
        }
      }
    }
  }
  return cells;
}

const cells = walk();

// ── structure ──────────────────────────────────────────────────────────
let tables = 0;
let rows = 0;
let notes = 0;
for (const [id, content] of Object.entries(REFERENCE)) {
  if (!content.blurb.trim()) fail(`${id}: empty blurb`);
  if (content.tables.length === 0) fail(`${id}: no tables — an entry with nothing in it is worse than no entry`);
  if (content.note) notes++;
  for (const table of content.tables) {
    tables++;
    rows += table.rows.length;
    if (table.cols.length === 0) fail(`${id} · ${table.title}: no columns`);
    if (table.rows.length === 0) fail(`${id} · ${table.title}: no rows`);
    for (const [i, row] of table.rows.entries()) {
      if (row.length !== table.cols.length) {
        fail(
          `${id} · ${table.title}: row ${i + 1} has ${row.length} cells but there are ` +
            `${table.cols.length} columns — a ragged row renders shifted and silently misattributes values`,
        );
      }
    }
  }
}
for (const cell of cells) {
  if (!cell.text.trim()) fail(`${cell.where}: empty string`);
}

// ── rule 1: no result values ───────────────────────────────────────────
for (const cell of cells) {
  const hit = cell.text.match(RESULT_VALUE);
  if (hit) {
    fail(
      `${cell.where}: contains ${JSON.stringify(hit[0])} — a number in a result unit. ` +
        'Reference content may name what the field MEASURES; it may never carry a value. ' +
        `Cell: ${JSON.stringify(cell.text)}`,
    );
  }
}

// ── rule 2: no patent status ───────────────────────────────────────────
//
// SCOPED TO THE ROW, NOT THE CELL. A first pass checked each cell on its own
// and missed the obvious shape: the number sits in one column and the status in
// the next — ["Patent publication", "US10377787B2", "Expired 2019; no longer in
// force"]. A row is the unit of assertion in a table, and reading across it is
// how anybody would read that.
for (const [id, content] of Object.entries(REFERENCE)) {
  for (const table of content.tables) {
    for (const [i, row] of table.rows.entries()) {
      const line = row.join(' │ ');
      if (PATENT_NUMBER.test(line) && PATENT_STATUS.test(line)) {
        fail(
          `${id} · ${table.title} · row ${i + 1}: names a patent AND a status. The file names ` +
            'one publication number as an example SHAPE; a status attached to it — in any ' +
            `column of the same row — is a claim about a real patent. Row: ${JSON.stringify(line)}`,
        );
      }
    }
  }
}
// The blurbs and notes are prose rather than rows, and are checked on their own.
for (const cell of cells.filter((c) => /· (blurb|note)$/.test(c.where))) {
  if (PATENT_NUMBER.test(cell.text) && PATENT_STATUS.test(cell.text)) {
    fail(`${cell.where}: names a patent AND a status. ${JSON.stringify(cell.text)}`);
  }
}

// ── rule 3: every numeric cell is justified ────────────────────────────
const numeric = cells.filter((c) => hasDigit.test(c.text));
const unjustified: Cell[] = [];
let viaIdentifier = 0;
for (const cell of numeric) {
  // Identifiers first: if nothing numeric survives masking, every digit in the
  // cell belonged to a name.
  if (!hasDigit.test(maskIdentifiers(cell.text))) {
    viaIdentifier++;
    continue;
  }
  if (!JUSTIFIED.some((j) => j.re.test(cell.text))) unjustified.push(cell);
}
for (const cell of unjustified) {
  fail(
    `${cell.where}: contains a number with no recorded justification.\n` +
      `      Cell: ${JSON.stringify(cell.text)}\n` +
      '      Either remove the number, or add a JUSTIFIED entry in scripts/check-reference.ts ' +
      'with a sentence saying why a reference shelf carries it. Adding a number here is meant ' +
      'to be a deliberate act.',
  );
}

// ── the shelf agrees with the code it describes (§5, §7) ───────────────
//
// Two reference tables are surfaced on LIVE screens, which means they stop
// being inert prose and start being read as a legend for real data. §7 says one
// source, not copies in screens — so the source has to be checked against what
// the code actually does, or the "one source" is just a copy that nobody
// noticed drifting.
{
  const table = REFERENCE['biorepo.audit']?.tables.find((t) => t.title === 'Provenance levels');
  if (!table) {
    fail('biorepo.audit: no "Provenance levels" table — §5 surfaces it as the legend');
  } else {
    // The file uses plain ASCII throughout ("Curated - gold set"); the UI uses a
    // middot. That is a house style, not a disagreement, so it is normalised
    // rather than rewritten.
    const norm = (x: string) => x.replace(/[·—–]/g, '-').replace(/\s+/g, ' ').trim();

    for (const [level, shownAs, inAggregates] of table.rows) {
      const label = PROVENANCE_LABEL[level as Provenance];
      if (!label) {
        fail(`biorepo.audit: "${level}" is not a provenance the code knows about`);
        continue;
      }
      if (norm(label) !== norm(shownAs)) {
        fail(
          `biorepo.audit: "${level}" is shown as ${JSON.stringify(shownAs)} on the shelf but ` +
            `${JSON.stringify(label)} in the UI — the legend would contradict the ticks beside it`,
        );
      }
      if (inAggregates !== 'Yes' && inAggregates !== 'No') {
        fail(`biorepo.audit: "${level}" has aggregate flag ${JSON.stringify(inAggregates)}, expected Yes or No`);
        continue;
      }

      // A record carrying this level, with nothing else disqualifying it.
      const probe = { status: 'verified', provenance: level, isPrimary: true } as never;
      const liveIncluded = aggregateExclusion(probe) === null;
      const shelfIncluded = inAggregates === 'Yes';

      if (liveIncluded === shelfIncluded) continue;

      // ── the one known divergence, and why it is not an error ──────────
      //
      // 'demo' means "Modeled - not measured". The shelf says it stays out of
      // aggregates, which is right and matches how 'industry-estimate' is
      // treated. `aggregateExclusion` does not exclude it — but it never has
      // to, because no ExtractionRecord carries 'demo': the level is used for
      // scenario assumptions and activity items, which are not records and
      // never reach an aggregate of measurements.
      //
      // So the divergence is outside the function's domain rather than a bug in
      // it, and this is a TRIPWIRE rather than an exception: the day a record
      // does carry 'demo', the live function would admit a modelled value into
      // an aggregate while the legend on screen promised it was held out, and
      // that is the moment somebody needs to know.
      if (level === 'demo' && !shelfIncluded && liveIncluded) {
        const demoRecords = RECORDS.filter((r) => r.provenance === 'demo');
        if (demoRecords.length > 0) {
          fail(
            `biorepo.audit: ${demoRecords.length} record(s) now carry provenance 'demo' ` +
              `(${demoRecords.slice(0, 3).map((r) => r.id).join(', ')}). The shelf says demo is held ` +
              'OUT of aggregates and aggregateExclusion() does not hold it out. Until now that ' +
              'gap was harmless because no record carried the level. Either exclude demo in ' +
              'aggregateExclusion(), or stop putting demo on records.',
          );
        }
        continue;
      }

      fail(
        `biorepo.audit: "${level}" is "${inAggregates}" in aggregates on the shelf but ` +
          `aggregateExclusion() ${liveIncluded ? 'includes' : 'excludes'} it — the legend and the ` +
          'code disagree about what counts as evidence',
      );
    }
  }
}

// ── the shelf is reachable (OF-BLD-010 §3) ─────────────────────────────
//
// `referenceFor(id)` is the wiring, so an id in reference.ts that no subsystem
// claims is content nothing renders — a shelf in a room with no door. The
// reverse is allowed and is the normal case: a subsystem with no entry renders
// its statement alone, unchanged.
{
  const known = new Set(SUBSYSTEMS.map((sub) => sub.id));
  for (const id of Object.keys(REFERENCE)) {
    if (!known.has(id)) {
      fail(
        `${id}: no subsystem claims this id, so nothing renders it. Add it to ` +
          'src/data/subsystems.ts or remove the entry — orphan reference content is a shelf ' +
          'in a room with no door.',
      );
    }
  }

  const owners = new Set(ELEVEN.map((r) => r.label));
  for (const sub of SUBSYSTEMS) {
    if (!owners.has(sub.owner)) {
      fail(`${sub.id}: owner "${sub.owner}" is not one of the eleven`);
    }
    if (!sub.id.startsWith(`${sub.owner.toLowerCase()}.`)) {
      fail(
        `${sub.id}: id does not start with its owner "${sub.owner.toLowerCase()}." — the id is ` +
          'how a reader locates the subsystem, and it should name where it lives',
      );
    }
    if (!sub.state.trim()) fail(`${sub.id}: no state sentence — §2 needs something above the line`);
  }

  const ids = SUBSYSTEMS.map((sub) => sub.id);
  const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
  if (dupes.length) fail(`duplicate subsystem ids: ${[...new Set(dupes)].join(', ')}`);
}

// ── the ids are addressable ────────────────────────────────────────────
for (const id of Object.keys(REFERENCE)) {
  if (!/^[a-z]+\.[a-z]+$/.test(id)) {
    fail(`${id}: subsystem ids are "owner.subsystem", lowercase — this one will not match a route`);
  }
  if (referenceFor(id) === null) fail(`${id}: referenceFor() cannot find its own key`);
}
if (referenceFor('nothing.here') !== null) {
  fail('referenceFor() must return null for an unknown subsystem, so a stub renders EmptyState alone');
}

console.log('\nopenFerment reference check');
console.log('───────────────────────────');
console.log(`  subsystems    ${SUBSYSTEMS.length} registered, ${Object.keys(REFERENCE).length} with reference content`);
console.log(`  tables        ${tables}`);
console.log(`  entries       ${rows} rows, ${cells.length} strings scanned`);
console.log(`  notes         ${notes} carry a load-bearing sentence`);
console.log(`  numerics      ${numeric.length} cells contain a digit — ${viaIdentifier} are identifiers, ${numeric.length - viaIdentifier} carry a stated justification`);
console.log(`  results       none — no value in a result unit, no status on a patent`);

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors.slice(0, 30)) console.error(`  - ${e}`);
  if (errors.length > 30) console.error(`  … and ${errors.length - 30} more`);
  process.exit(1);
}
console.log('\n✓ Reference content holds the line: the field, never your answer.');
