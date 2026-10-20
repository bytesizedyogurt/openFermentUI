// What a kept Live conversation or a proposal names, held to the program
// switch (OF-BLD-016 §2.2, review 23). A conversation that cites a record,
// paper or passage of an archived program, or a proposal whose target is
// one, hides while archived programs are hidden. Nothing is deleted: turning
// the switch on shows it again.
import type { LiveConversation, Proposal } from '@/data/types';
import type { ProgramEntityKind } from '@/store';

type Shows = (kind: ProgramEntityKind, id: string) => boolean;

export function conversationShows(c: LiveConversation, shows: Shows): boolean {
  for (const t of c.turns) {
    const plan = t.plan;
    if (!plan) continue;
    for (const cl of plan.claims) {
      if (cl.recordIds.some((id) => !shows('record', id))) return false;
      if (cl.paperIds.some((id) => !shows('paper', id))) return false;
    }
    if ((plan.passages ?? []).some((p) => !shows('paper', p.paperId))) return false;
  }
  return true;
}

const TARGET_KINDS: ProgramEntityKind[] = ['record', 'paper', 'runbook', 'protocol', 'strain', 'product', 'scenario', 'deposition', 'lesson', 'module'];

/** A proposal's target is an id of some kind; it shows unless one kind resolves it to a hidden program. */
export function proposalShows(p: Proposal, shows: Shows): boolean {
  const target = p.target;
  return !target || TARGET_KINDS.every((k) => shows(k, target));
}

/**
 * The review queue once the switch brings records back. While no card of the
 * session has been passed, the queue takes the order a fresh session would
 * (`order`, the records' own); once one has, the returning records join at
 * the end, so nothing already in front of the reviewer moves.
 */
export function rejoinQueue(kept: string[], joining: string[], order: string[], untouched: boolean): string[] {
  if (!untouched || joining.length === 0) return [...kept, ...joining];
  const all = new Set([...kept, ...joining]);
  const placed = order.filter((id) => all.has(id));
  const placedSet = new Set(placed);
  return [...placed, ...kept.filter((id) => !placedSet.has(id))];
}
