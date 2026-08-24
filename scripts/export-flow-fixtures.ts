/**
 * The authored flows become acceptance criteria (OF-BLD-007 §9).
 *
 * Thirteen scripted conversations were written by hand: a question, and an
 * answer citing the records that answer it. Under the scripted path they were
 * a parallel implementation — content that looked like the system working.
 * They are not deleted and they are not a fallback. They become the fixtures
 * the real pipeline is graded against, which is the payoff of the inversion:
 * the authored content stops competing with the real system and starts
 * measuring it.
 *
 * Emits core/tests/fixtures/flows.json — the question, and the record and
 * paper ids a human said were the right ones. Exact prose will differ every
 * run; the citations should not.
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { FLOWS } from '../src/data/flows';
import { RECORDS } from '../src/data/records';
import { PAPERS } from '../src/data/papers';

const OUT = 'core/tests/fixtures/flows.json';

const recordIds = new Set(RECORDS.map((r) => r.id));
const paperIds = new Set(PAPERS.map((p) => p.id));

/** Citation chips in an authored answer: [[H2]] for a paper, [[r-H4-1]] for a record. */
function citations(md: string): { records: string[]; papers: string[] } {
  const chips = [...md.matchAll(/\[\[([^\]]+)\]\]/g)].map((m) => m[1].trim());
  return {
    // Only ids that actually resolve. An authored answer that cites something
    // no longer in the corpus is a fixture bug, and grading the model against
    // it would fail the model for the fixture's mistake.
    records: [...new Set(chips.filter((c) => recordIds.has(c)))].sort(),
    papers: [...new Set(chips.filter((c) => paperIds.has(c)))].sort(),
  };
}

const fixtures = FLOWS.map((flow) => {
  const { records, papers } = citations(flow.answerMd);
  const unresolved = [...new Set([...flow.answerMd.matchAll(/\[\[([^\]]+)\]\]/g)].map((m) => m[1].trim()))]
    .filter((c) => !recordIds.has(c) && !paperIds.has(c));
  return {
    id: flow.id,
    // The first trigger is the canonical phrasing — the one the prompt chips
    // use verbatim.
    question: flow.triggers[0],
    /** Every phrasing a human wrote for this question, for diagnosis. */
    alternates: flow.triggers.slice(1),
    recordIds: records,
    paperIds: papers,
    /** Chips that resolve to neither a record nor a paper — flagged, not dropped silently. */
    unresolvedChips: unresolved,
  };
});

mkdirSync('core/tests/fixtures', { recursive: true });
writeFileSync(OUT, JSON.stringify(fixtures, null, 2) + '\n');

const withRecords = fixtures.filter((f) => f.recordIds.length > 0);
const dangling = fixtures.filter((f) => f.unresolvedChips.length > 0);

console.log('\nopenFerment flow fixtures');
console.log('─────────────────────────');
console.log(`  flows        ${fixtures.length}`);
console.log(`  gradable     ${withRecords.length} cite at least one resolvable record`);
console.log(
  `  citations    ${fixtures.reduce((n, f) => n + f.recordIds.length, 0)} records, ` +
    `${fixtures.reduce((n, f) => n + f.paperIds.length, 0)} papers`,
);
if (dangling.length) {
  console.log(`  unresolved   ${dangling.length} flow(s) cite a chip that is neither:`);
  for (const f of dangling) console.log(`      ${f.id}: ${f.unresolvedChips.join(', ')}`);
}
console.log(`\n✓ ${OUT}`);
