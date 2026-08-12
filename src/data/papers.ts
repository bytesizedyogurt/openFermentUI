// Corpus assembly (OF-COR-001). Threads are authored separately and
// concatenated here in entry-id order.
// The collection itself now comes from the adapter; this module keeps only
// the derived views built on top of it.
import { PAPERS } from '@/data/source';

export { PAPERS };

import type { Paper } from './types';

/** Sort by thread letter then numeric index, so H2 precedes H10. */
function byEntryId(a: Paper, b: Paper): number {
  const pa = a.id.match(/^([A-O])(\d+)(\w*)$/);
  const pb = b.id.match(/^([A-O])(\d+)(\w*)$/);
  if (!pa || !pb) return a.id.localeCompare(b.id);
  if (pa[1] !== pb[1]) return pa[1].localeCompare(pb[1]);
  if (Number(pa[2]) !== Number(pb[2])) return Number(pa[2]) - Number(pb[2]);
  return pa[3].localeCompare(pb[3]);
}


export const PAPERS_BY_ID: Record<string, Paper> = Object.fromEntries(
  PAPERS.map((p) => [p.id, p]),
);

/** Nothing is on a demo shelf any more — the corpus is real and catalogued. */
export const DEMO_SHELF: Paper[] = PAPERS.filter((p) => p.ingest === 'shelf');

/** Entries whose full text has been ingested and can be searched properly. */
export const FULL_TEXT: Paper[] = PAPERS.filter((p) => p.textSource === 'full-text');

/** The searchable corpus — catalogued entries are searchable via their notes. */
export const CORPUS: Paper[] = PAPERS.filter((p) => p.ingest !== 'shelf');
