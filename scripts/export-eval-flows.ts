/**
 * Export the scripted flows as Audit's seed eval corpus.
 *
 *   pnpm capture:eval-flows          write packages/assay/fixtures/flows.json
 *   pnpm check:evals                 assert the committed file is current
 *
 * The restructuring brief's Phase 4 names the second life of `src/data/flows.ts`:
 * each ChatFlow is a question with an expected retrieval set and an expected
 * answer, authored as a demo script and usable as an eval case without
 * modification. When a real agent answers behind Postdoc, these are what its
 * answers are scored against — which makes this file the eval-side sibling of
 * `fixtures/answer-shapes.json` (the formatter contract; shape, not prose).
 * This one keeps the prose, because an eval needs the expected ANSWER.
 *
 * They land in `packages/assay/fixtures/` rather than the brief's
 * `packages/evals/` because `packages/assay` IS the Audit package here — the
 * Inspect AI scorer already lives in it, and a second eval home would split
 * the thing the fixtures exist to feed. Recorded in MIGRATION.md.
 *
 * Every flow is validated through the Pydantic `ChatFlow` model on the way out
 * and must round-trip unchanged — the same discipline as `export-corpus.ts`,
 * and the first time the flows have been held to the schema at all. Where a
 * real flow fails, the MODEL is wrong, never the flow.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import { FLOWS } from '../src/data/flows';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'packages', 'assay', 'fixtures', 'flows.json');

const PY = `
import json, sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "packages" / "core"))
sys.path.insert(0, str(ROOT / "packages" / "core" / "scripts"))

from pydantic import ValidationError

from openferment_core.schema import ChatFlow
from validate_fixtures import diff_summary, prune_none

flows = json.load(sys.stdin)
failures = []
dumped = []
for raw in flows:
    ident = raw.get("id", "?")
    try:
        parsed = ChatFlow.model_validate(raw)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(flow)"
            failures.append(f"{ident}: {loc} - {err['msg']}")
        continue
    emitted = parsed.model_dump(by_alias=True, exclude_none=True, mode="json")
    drift = diff_summary(prune_none(raw), emitted)
    if drift:
        failures.append(f"{ident}: ChatFlow altered the flow - {drift}")
        continue
    dumped.append(emitted)

if failures:
    json.dump({"ok": False, "failures": failures}, sys.stdout, ensure_ascii=False)
else:
    text = json.dumps(dumped, ensure_ascii=False, indent=2) + "\\n"
    json.dump({"ok": True, "count": len(dumped), "text": text}, sys.stdout, ensure_ascii=False)
`;

const report = JSON.parse(
  execFileSync('python3', ['-c', PY, ROOT], {
    input: JSON.stringify(FLOWS),
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  }),
);

console.log('openFerment eval-flow export');
console.log('────────────────────────────');

if (!report.ok) {
  console.error(`✗ ${report.failures.length} flow(s) failed the ChatFlow model. The MODEL is wrong,`);
  console.error('  not the flows — they are the authored demo scripts. Report before changing:');
  for (const f of report.failures) console.error(`  - ${f}`);
  console.error('\nNothing was written.');
  process.exit(1);
}

if (FLOWS.length === 0 || report.count !== FLOWS.length) {
  console.error(`✗ expected ${FLOWS.length} flows, ${report.count} survived — refusing a partial export.`);
  process.exit(1);
}

if (process.argv.includes('--check')) {
  const committed = existsSync(OUT) ? readFileSync(OUT, 'utf8') : '';
  if (committed !== report.text) {
    console.error(`✗ ${relative(ROOT, OUT)} no longer matches src/data/flows.ts.`);
    console.error(`  committed ${committed.length} bytes, the flows imply ${report.text.length}.`);
    console.error('  Run `pnpm capture:eval-flows` and read the diff before committing it —');
    console.error('  this file is what the real agent will be SCORED against, so a change');
    console.error('  here is a change to what counts as a right answer.');
    process.exit(1);
  }
  console.log(`  packages/assay/fixtures/flows.json   ${report.count} flows, up to date`);
  process.exit(0);
}

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, report.text, 'utf8');
console.log(`  ${relative(ROOT, OUT)}   ${report.count} flows · ${(report.text.length / 1024).toFixed(0)} KB`);
console.log('\n✓ every flow parsed and round-tripped unchanged through ChatFlow.\n');
