/**
 * Do the two implementations of the aggregation gate still agree?
 *
 *   pnpm check:aggregation   (→ tsx scripts/check-aggregation-parity.mjs)
 *
 * `isAggregatable` is the single gate deciding which records may enter an
 * aggregate (CLAUDE.md invariant 3). It exists twice: in
 * `src/engine/aggregation.ts`, because the Ledger recomputes as a reviewer
 * corrects a record, and on `ExtractionRecord` in
 * `packages/core/openferment_core/schema/records.py`, because the gate has to
 * travel with the model into Postgres and the extraction pipeline.
 *
 * There is no captured fixture for it — Phase 0 pinned the unit engine, the
 * scaler and the metrics, not this — so instead of a pin, this runs BOTH
 * implementations over the REAL CORPUS in `data/corpus/records.json` and
 * compares every answer. 134 records, and the answers must agree exactly:
 * whether the record is aggregatable, and which exclusion is reported, since
 * the reason string is displayed and a multiply-excluded record reporting a
 * different reason on each side is a visible disagreement.
 *
 * `provenanceOf` is deliberately NOT compared: it is display logic that decides
 * which tick a record renders with, it was never ported, and it has no Python
 * counterpart to disagree with.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { aggregateExclusion, isAggregatable } from '../src/engine/aggregation.ts';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const RECORDS = join(ROOT, 'data', 'corpus', 'records.json');

const PY = `
import json, sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "packages" / "core"))

from openferment_core.schema import ExtractionRecord

def answer(raw):
    r = ExtractionRecord.model_validate(raw)
    excl = r.aggregateExclusion()
    return {
        "id": r.id,
        "aggregatable": r.isAggregatable(),
        "exclusion": None if excl is None else excl.value,
    }


payload = json.load(sys.stdin)
json.dump(
    {
        "corpus": [answer(raw) for raw in payload["corpus"]],
        "probes": [answer(raw) for raw in payload["probes"]],
    },
    sys.stdout,
    ensure_ascii=False,
)
`;

const records = JSON.parse(readFileSync(RECORDS, 'utf8'));
if (records.length === 0) {
  console.error('✗ data/corpus/records.json is empty — nothing was compared.');
  process.exit(1);
}

// Synthetic probes, because the corpus cannot exercise the whole gate. All 134
// seeded records are `unverified` with an explicit boolean `isPrimary`, so the
// REJECTED clause — the first one, and the one that keeps a reviewer's explicit
// "no" out of a median — is never reached, and neither is the clause ORDER nor
// the `=== false` test. `status: 'rejected'` is produced at runtime by the
// Review screen, so the app manufactures records on a path the corpus half of
// this check had never compared: removing the rejected clause from either
// implementation used to leave this gate green.
const base = records.find((r) => r.provenance !== 'industry-estimate' && r.isPrimary !== false);
if (!base) {
  console.error('✗ no ordinary record in the corpus to build probes from.');
  process.exit(1);
}
// Not probed, deliberately: `r.isPrimary === false` versus `!r.isPrimary`.
// `isPrimary` is a REQUIRED boolean in both languages — `is_primary: bool` with
// no default in Pydantic, non-optional in the generated TypeScript — so it is
// only ever `true` or `false` and the two spellings cannot disagree. Rewriting
// one into the other leaves this gate green because the mutation is a semantic
// no-op on every value the type admits, not because the gate cannot see it.
// The `is False` spelling stays as documentation of intent.
const PROBES = [
  { ...base, id: 'probe:rejected', status: 'rejected' },
  { ...base, id: 'probe:rejected+industry', status: 'rejected', provenance: 'industry-estimate' },
  { ...base, id: 'probe:rejected+not-primary', status: 'rejected', isPrimary: false },
  // All three at once. WHICH reason is reported is a visible behaviour, because
  // the string is displayed, so the two must agree on precedence and not merely
  // on the verdict.
  {
    ...base,
    id: 'probe:all-three',
    status: 'rejected',
    provenance: 'industry-estimate',
    isPrimary: false,
  },
  { ...base, id: 'probe:industry+not-primary', provenance: 'industry-estimate', isPrimary: false },
  { ...base, id: 'probe:verified', status: 'verified' },
  { ...base, id: 'probe:demo', provenance: 'demo' },
  { ...base, id: 'probe:gold', provenance: 'gold' },
  { ...base, id: 'probe:primary-true', isPrimary: true },
];

let pyOut;
try {
  pyOut = execFileSync('python3', ['-c', PY, ROOT], {
    encoding: 'utf8',
    input: JSON.stringify({ corpus: records, probes: PROBES }),
    maxBuffer: 32 * 1024 * 1024,
  });
} catch (e) {
  console.error('✗ the Python side could not be run:\n' + (e.stderr || e.message));
  process.exit(1);
}
const parsed = JSON.parse(pyOut);
const fromPython = new Map(parsed.corpus.map((r) => [r.id, r]));
const probesFromPython = new Map(parsed.probes.map((r) => [r.id, r]));

console.log('openFerment aggregation parity — src/engine/aggregation.ts vs openferment_core.schema');
console.log('──────────────────────────────────────────────────────────────────────────────────────');

const failures = [];
for (const raw of records) {
  const theirs = fromPython.get(raw.id);
  if (!theirs) {
    failures.push(`${raw.id}: Python returned no answer for this record`);
    continue;
  }
  const ours = { aggregatable: isAggregatable(raw), exclusion: aggregateExclusion(raw) ?? null };
  if (ours.aggregatable !== theirs.aggregatable) {
    failures.push(
      `${raw.id}: aggregatable — TypeScript ${ours.aggregatable}, Python ${theirs.aggregatable}`,
    );
  } else if (ours.exclusion !== theirs.exclusion) {
    failures.push(
      `${raw.id}: exclusion — TypeScript ${JSON.stringify(ours.exclusion)}, ` +
        `Python ${JSON.stringify(theirs.exclusion)}`,
    );
  }
}

for (const probe of PROBES) {
  const theirs = probesFromPython.get(probe.id);
  const ours = { aggregatable: isAggregatable(probe), exclusion: aggregateExclusion(probe) ?? null };
  if (!theirs) {
    failures.push(`${probe.id}: Python returned no answer`);
  } else if (ours.aggregatable !== theirs.aggregatable) {
    failures.push(
      `${probe.id}: aggregatable — TypeScript ${ours.aggregatable}, Python ${theirs.aggregatable}`,
    );
  } else if (ours.exclusion !== theirs.exclusion) {
    failures.push(
      `${probe.id}: exclusion — TypeScript ${JSON.stringify(ours.exclusion)}, ` +
        `Python ${JSON.stringify(theirs.exclusion)}`,
    );
  }
}

const excluded = records.filter((r) => !isAggregatable(r)).length;
console.log(`  records compared  ${String(records.length).padStart(6)}   ${failures.length === 0 ? '✓' : `✗ ${failures.length}`}`);
console.log(`  of which excluded ${String(excluded).padStart(6)}`);
console.log(`  synthetic probes  ${String(PROBES.length).padStart(6)}   ${failures.length === 0 ? '✓' : ''}`);

if (failures.length) {
  console.error('\n✗ the two aggregation gates disagree about the real corpus:');
  for (const f of failures.slice(0, 40)) console.error(`  - ${f}`);
  if (failures.length > 40) console.error(`  … and ${failures.length - 40} more.`);
  console.error(
    '\nThis decides which records enter an aggregate (CLAUDE.md invariant 3). Python is\n' +
      'canonical; fix it there first, then the mirror.',
  );
  process.exit(1);
}

console.log('\n✓ both gates agree on every record, including which exclusion they report.\n');
