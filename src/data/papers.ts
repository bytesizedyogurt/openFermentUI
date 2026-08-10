// Corpus assembly. Sets are authored separately (see BUILD-SPEC.md) and
// concatenated here in ID order.
import type { Paper } from './types';
import { PAPERS_A } from './corpus/setA';
import { PAPERS_B } from './corpus/setB';
import { PAPERS_C } from './corpus/setC';

export const PAPERS: Paper[] = [...PAPERS_A, ...PAPERS_B, ...PAPERS_C].sort((a, b) =>
  a.id.localeCompare(b.id),
);

export const PAPERS_BY_ID: Record<string, Paper> = Object.fromEntries(
  PAPERS.map((p) => [p.id, p]),
);

/** Papers held out of the seeded corpus for the ingest demo (§8.5). */
export const DEMO_SHELF: Paper[] = PAPERS.filter((p) => p.ingest === 'shelf');

/** The searchable/askable corpus — excludes shelf and parse-failed papers. */
export const CORPUS: Paper[] = PAPERS.filter(
  (p) => p.ingest !== 'shelf' && p.ingest !== 'failed:parse',
);
