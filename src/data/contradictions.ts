// Contradictions (OF-FE-003 §9).
//
// Derived, never authored. OF-FE-003 §12.5 forbids seeding a contradiction that
// does not fail its tolerance when computed — the system committing the exact
// error it exists to catch would be the worst available outcome. Running the
// referee over the records at load makes a staged contradiction structurally
// impossible rather than merely against the rules.
//
// Curator notes attach by id below, so a human explanation can survive without
// the finding itself being hand-written.
import { RECORDS } from './records';
import { refereeAll } from '@/engine/balance';
import type { Contradiction } from './types';

const NOTES: Record<string, { status: Contradiction['status']; note: string }> = {};

export const CONTRADICTIONS: Contradiction[] = refereeAll(RECORDS).map((c) => {
  const overlay = NOTES[c.id];
  return overlay ? { ...c, status: overlay.status, note: overlay.note } : c;
});
