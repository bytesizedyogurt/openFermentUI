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

out = []
for raw in json.load(open(ROOT / "data" / "corpus" / "records.json", encoding="utf-8")):
    r = ExtractionRecord.model_validate(raw)
    excl = r.aggregateExclusion()
    out.append({
        "id": r.id,
        "aggregatable": r.isAggregatable(),
        "exclusion": None if excl is None else excl.value,
    })
json.dump(out, sys.stdout, ensure_ascii=False)
`;

const records = JSON.parse(readFileSync(RECORDS, 'utf8'));
if (records.length === 0) {
  console.error('✗ data/corpus/records.json is empty — nothing was compared.');
  process.exit(1);
}

let pyOut;
try {
  pyOut = execFileSync('python3', ['-c', PY, ROOT], {
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
  });
} catch (e) {
  console.error('✗ the Python side could not be run:\n' + (e.stderr || e.message));
  process.exit(1);
}
const fromPython = new Map(JSON.parse(pyOut).map((r) => [r.id, r]));

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

const excluded = records.filter((r) => !isAggregatable(r)).length;
console.log(`  records compared  ${String(records.length).padStart(6)}   ${failures.length === 0 ? '✓' : `✗ ${failures.length}`}`);
console.log(`  of which excluded ${String(excluded).padStart(6)}`);

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
