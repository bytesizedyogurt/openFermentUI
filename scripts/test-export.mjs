/**
 * The decision merge reaches the corpus, and a wrong merge fails the guard
 * (OF-BLD-012.1 F4).
 *
 *   pnpm test:export
 *
 * `export-corpus.ts` MERGES biorepo.json into the projection the service
 * reads: a corrected value becomes the record's value, a gold decision
 * becomes the record's provenance, a promotion's re-anchored quote replaces
 * the seed's, and an accepted candidate is appended as a new record. Until
 * this stage none of that was exercised by `pnpm verify`, because the
 * committed biorepo.json is empty — the code ran over nothing and passed.
 *
 * So the demo's fixture, which HAS decisions, is exported into a temp
 * directory and read back. Then the same fixture is copied with one value
 * changed behind the exporter's back, and `check:biorepo` is pointed at it:
 * a corpus that does not reflect a decision has to fail, or the guard is
 * decoration.
 */
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const FIXTURE = 'core/tests/fixtures/demo';
const SHELL = process.platform === 'win32';

let fails = 0;
const check = (label, ok, extra = '') => {
  console.log(`${ok ? '✓' : '✗'} ${label}${extra === '' ? '' : `  ${JSON.stringify(extra)}`}`);
  if (!ok) fails++;
};

const tmp = mkdtempSync(join(tmpdir(), 'of-export-'));
const out = join(tmp, 'corpus.json');

const exported = spawnSync('pnpm', ['export:corpus'], {
  encoding: 'utf-8',
  shell: SHELL,
  env: { ...process.env, OPENFERMENT_DATA_DIR: FIXTURE, OPENFERMENT_CORPUS_OUT: out },
});
if (exported.status !== 0) {
  console.error(exported.stderr || exported.stdout);
  console.error('✗ the export did not run');
  process.exit(1);
}

const corpus = JSON.parse(readFileSync(out, 'utf8'));
const repo = JSON.parse(readFileSync(join(FIXTURE, 'biorepo.json'), 'utf8'));
const byId = new Map(corpus.records.map((r) => [r.id, r]));
const decisions = Object.entries(repo.decisions);

// ── a correction becomes the record's value ────────────────────────────
const corrected = decisions.find(([, d]) => d.corrected);
check('the fixture carries a corrected decision to test with', !!corrected);
if (corrected) {
  const [id, d] = corrected;
  const rec = byId.get(id);
  check(`${id} reached the corpus at all`, !!rec);
  if (rec) {
    check(
      'the corrected value is the record’s value',
      rec.value === d.corrected.value && rec.unit === d.corrected.unit,
      { exported: `${rec.value} ${rec.unit}`, decided: `${d.corrected.value} ${d.corrected.unit}` },
    );
    check('the SI twin was recomputed from it', typeof rec.si?.value === 'number' && rec.si.value > 0, rec.si);
    check('the sentence the decision anchored on came with it', rec.quote === d.quote, rec.quote);
    check('and an accepted candidate is appended as a record', rec.source === 'biorepo' && rec.status === 'verified', {
      source: rec.source,
      status: rec.status,
    });
  }
}

// ── a gold decision becomes the record's provenance ────────────────────
const golden = decisions.find(([, d]) => d.provenance === 'gold' || d.gold != null);
check('the fixture carries a gold decision to test with', !!golden);
if (golden) {
  const [id] = golden;
  const rec = byId.get(id);
  check('a gold decision reaches the corpus as gold provenance', rec?.provenance === 'gold', rec?.provenance);
}

// ── a rejection keeps a candidate out ──────────────────────────────────
const rejected = decisions.find(([, d]) => d.status === 'rejected');
check('the fixture carries a rejection to test with', !!rejected);
if (rejected) {
  check('a rejected candidate is not appended to the corpus', !byId.has(rejected[0]), rejected[0]);
}

// ── and a merge that did not happen fails the guard ────────────────────
const sabotaged = join(tmp, 'sabotaged');
mkdirSync(sabotaged, { recursive: true });
const bent = JSON.parse(JSON.stringify(repo));
const [bentId, bentDecision] = corrected ?? [];
if (bentDecision) {
  // A value no export would produce: the guard has to notice the corpus and
  // the decision disagree.
  bentDecision.corrected = { value: bentDecision.corrected.value * 3 + 1, unit: bentDecision.corrected.unit };
  bent.decisions[bentId] = bentDecision;
}
writeFileSync(join(sabotaged, 'biorepo.json'), JSON.stringify(bent, null, 2));

// Checked against the corpus exported BEFORE the value was bent. The guard
// makes its own projection by default, and a guard that builds the corpus it
// is about to check can only ever find them in agreement — so rule 4 is
// pointed at the one made a moment ago, which is what a stale or hand-edited
// projection looks like.
const guard = spawnSync('node', ['scripts/check-biorepo.mjs'], {
  encoding: 'utf-8',
  shell: SHELL,
  env: { ...process.env, OPENFERMENT_DATA_DIR: sabotaged, OPENFERMENT_CORPUS_IN: out },
});
const said = `${guard.stdout}${guard.stderr}`;
check('check:biorepo fails when the corpus does not reflect a decision', guard.status !== 0, guard.status);
check('and says which record and what it expected', /corrected it to/.test(said), said.split('\n').filter((l) => l.includes('-')).slice(0, 2));

// The unsabotaged fixture must still pass, or the failure above proves nothing.
const honest = spawnSync('node', ['scripts/check-biorepo.mjs'], {
  encoding: 'utf-8',
  shell: SHELL,
  env: { ...process.env, OPENFERMENT_DATA_DIR: FIXTURE },
});
check('and passes on the fixture it was built from', honest.status === 0, `${honest.stdout}${honest.stderr}`.slice(-300));

console.log(fails === 0 ? '\nTHE MERGE IS TESTED' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
