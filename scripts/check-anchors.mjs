/**
 * How many curated records can be promoted to gold (OF-BLD-012.1 F1).
 *
 *   pnpm check:anchors
 *
 * Runs the SERVICE's anchoring — `anchor_candidate`, through
 * `openferment_core.anchor_report` — over every numeric seed record, against
 * a section that says exactly what that record's quote says. A record that
 * anchors is one a reviewer can promote without editing it first.
 *
 * The numbers below are committed on purpose. F1 exists because 34 of the 104
 * numeric curated records could not be promoted: the curator recorded the
 * midpoint of a range, or a zero for a measured absence, or a value the paper
 * wrote in another unit, and rule 3 compared bare numbers. THE COUNT MAY NOT
 * GO DOWN. A change that lets more through is a change to these numbers and a
 * sentence saying why.
 */
import { spawnSync } from 'node:child_process';

/**
 * Of the 104 numeric curated records, how many anchor. Measured: 63 before
 * F1, 93 after. The 30 F1 added are the curators' recorded structure being
 * read at last — 19 a range, 7 a measured absence, 3 a number the paper
 * wrote in words, 1 a unit it spelled differently. (34 records failed rule 3
 * before; 4 of them still refuse, for reasons below that are not rule 3's.)
 */
const FLOOR = 93;

/**
 * The eleven that do not, and why each is not a rule-3 problem. Two of these
 * are what F1 set out to leave refused; the other nine never were about the
 * quote at all.
 *
 * Derived — the sentence does not state the number, and no recorded
 * structure licenses the arithmetic. Refusing is the point:
 *   r-E2-1  140 nm read off "radius ~70 nm"
 *   r-H4-4  100 % read off "the same degree of phosphorylation as"
 *
 * Outside the FIELD's own ontology range (rule 5). No anchoring change
 * reaches these; widening a range is a curation call, and if one is made
 * the record moves into the anchoring set and FLOOR goes up:
 *   r-A2-1  0 % TSP, below expression_pct_tsp's floor of 0.001
 *   r-E1-3  80 % TSP, above its ceiling of 40
 *   r-O8-1  1e6 USD/kg, above minimum_selling_price's ceiling of 100000
 *
 * Unit family (rule 4): the engine refuses to convert a currency without an
 * exchange rate and a date, which is a refusal the project wants:
 *   r-O4-1, r-O4-2, r-O5-1, r-O5-2, r-O6-1, r-O7-1 — all EUR/kg
 */
const EXPECTED_REFUSALS = [
  'r-E2-1', 'r-H4-4',
  'r-A2-1', 'r-E1-3', 'r-O8-1',
  'r-O4-1', 'r-O4-2', 'r-O5-1', 'r-O5-2', 'r-O6-1', 'r-O7-1',
];

const fail = (m) => {
  console.error(`✗ ${m}`);
  process.exitCode = 1;
};

const run = spawnSync('uv', ['run', 'python', '-m', 'openferment_core.anchor_report'], {
  cwd: 'core',
  encoding: 'utf-8',
  maxBuffer: 32 * 1024 * 1024,
  shell: process.platform === 'win32',
});
if (run.status !== 0) {
  console.error(run.stderr || run.stdout);
  fail('the anchoring report did not run — is `uv` on PATH and core/ installed?');
  process.exit(1);
}

let report;
try {
  report = JSON.parse(run.stdout);
} catch {
  console.error(run.stdout.slice(0, 500));
  fail('the anchoring report did not print JSON');
  process.exit(1);
}

const rows = report.records ?? [];
const anchored = rows.filter((r) => r.anchors);
const refused = rows.filter((r) => !r.anchors);

const byBasis = {};
for (const r of anchored) byBasis[r.basis] = (byBasis[r.basis] ?? 0) + 1;

console.log(`  anchoring   ${anchored.length} of ${rows.length} numeric curated records can be promoted`);
for (const [basis, n] of Object.entries(byBasis).sort()) {
  console.log(`              ${String(n).padStart(3)} ${basis}`);
}
for (const r of refused) {
  console.log(`              refused ${r.id} on rule '${r.rule}'`);
}

if (rows.length === 0) fail('the report is empty — has `pnpm export:corpus` run?');
if (anchored.length < FLOOR) {
  fail(
    `${anchored.length} records anchor; the committed floor is ${FLOOR}. ` +
      'Something that used to anchor no longer does — find it before lowering this number.',
  );
}

const unexpected = refused.map((r) => r.id).filter((id) => !EXPECTED_REFUSALS.includes(id));
if (unexpected.length) {
  fail(`records refused that the guard does not account for: ${unexpected.join(', ')}`);
}

if (!process.exitCode) {
  console.log(`✓ ${anchored.length} curated records anchor; the ${refused.length} that do not are the ones on record`);
}
