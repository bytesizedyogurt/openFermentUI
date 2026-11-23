// P-03: Guild's review strip filter (src/screens/Guild.tsx:208-216), computed with the tree's own paperHeld
// (src/lib/review.ts:215) over the project's overlay, plus one record the project does not hold whose paper
// carries a DOI. Prints each waiting record, its paper's identifiers, and whether the strip hides it.
// usage: node_modules/.bin/tsx bughunt/repro/P-03/filter.ts OVERLAY.json
import { readFileSync } from 'node:fs';
import { paperHeld, type Paper } from '@/lib/review';

const overlay = JSON.parse(readFileSync(process.argv[2], 'utf8'));
// The store's papers: the overlay's entries under their ids (review.ts:45).
const papers: Paper[] = Object.entries(overlay.papers as Record<string, Paper>).map(([id, p]) => ({
  ...p,
  id,
  title: p.title ?? id,
}));
const decided = new Set(Object.keys(overlay.records ?? {}));
type Rec = { id: string; paperId: string; status: string };
const records: Rec[] = (overlay.candidates ?? []).map((c: { id: string; paperId: string }) => ({
  id: c.id,
  paperId: c.paperId,
  status: decided.has(c.id) ? 'decided' : 'unverified',
}));
// A record on a paper the project does not hold, as a Durable snapshot from an earlier load could keep it.
records.push({ id: 'cl1-PMC0000001-0123abcd', paperId: 'PMC0000001', status: 'unverified' });
const ids: Record<string, string> = { PMC0000001: 'doi=10.1000/held-nowhere pmcid=PMC0000001 (not in this project)' };

const keepable = (r: Rec) => paperHeld(papers.find((p) => p.id === r.paperId));
const waiting = records.filter((r) => r.status === 'unverified');
const hidden = waiting.filter((r) => !keepable(r));
for (const r of waiting) {
  const p = papers.find((x) => x.id === r.paperId);
  const who = p ? `doi=${JSON.stringify(p.doi)} pmcid=${JSON.stringify(p.pmcid)} (held)` : ids[r.paperId];
  console.log(`WAITING: ${r.id} on ${r.paperId} ${who} -> ${keepable(r) ? 'shown' : 'HIDDEN'}`);
}
const noIdShown = waiting.filter((r) => {
  const p = papers.find((x) => x.id === r.paperId);
  return keepable(r) && p && !p.doi && !p.pmcid;
}).length;
const idHidden = hidden.filter((r) => !papers.find((x) => x.id === r.paperId) && ids[r.paperId]?.startsWith('doi=10.')).length;
console.log(`FILTER: hiddenByFilter=${hidden.length}; shown with no PMCID or DOI=${noIdShown}; hidden though it has a DOI and PMCID=${idHidden}`);
