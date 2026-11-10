// P-02's browser half: the client's provenanceOf (src/store.ts) on the decision the service's overlay serves,
// applied to a record the way the store's applyDecision applies it (status, provenance, gold, corrected).
// Run from the repository root: node_modules/.bin/tsx bughunt/repro/P-02/browser_rule.ts OUT_JSON
import { readFileSync } from 'node:fs';
(globalThis as any).localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
(globalThis as any).window = globalThis;
const { provenanceOf } = await import('../../../src/store');
const probe = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const d = probe.overlay ?? {};
const record = {
  id: probe.recordId, status: d.status, provenance: d.provenance, gold: d.gold ?? undefined,
  corrected: d.corrected ?? undefined, rejectReason: d.rejectReason ?? null, reviewer: d.reviewer, audit: [],
} as any;
console.log(`BROWSER provenanceOf(overlay decision: status ${d.status}, label ${d.provenance}, gold ${JSON.stringify(d.gold ?? null)}) = ${provenanceOf(record)}`);
console.log(`BROWSER gold-set count for it (Intake: rows with r.gold) = ${record.gold ? 1 : 0}`);
