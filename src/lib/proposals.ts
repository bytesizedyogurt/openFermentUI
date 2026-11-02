// Proposals a model made at a gate (OF-BLD-015 §7.4), read and answered
// through the service. Nothing here decides anything: a person presses the
// button, and their reviewer name goes on the proposal and the audit log.
import type { GuildPerson, Proposal, ProposalAction } from '@/data/types';
import { mayQueue } from '@/engine/checks';
import type { StatusMap } from '@/engine/competence';
import { apiFetch } from './project';

export async function listProposals(signal?: AbortSignal): Promise<Proposal[]> {
  const response = await apiFetch('/api/proposals?state=proposed', { signal });
  if (!response.ok) throw new Error(`GET /api/proposals → ${response.status}`);
  return (await response.json()) as Proposal[];
}

/**
 * The open proposals Home shows to whoever is acting (OF-BLD-016 §1.R
 * finding 9). A Guild proposal is about a person, so the check rules in
 * src/engine/checks.ts decide who sees it: the queue is for the lead and
 * assessors (`mayQueue`), and a check never shows to the person it names
 * until it is run (`shownTo`, held here on the proposal's `personId`; a
 * listed proposal has not run). Every other proposal shows to everyone.
 * (The in-browser sample team this once also excluded left the screens in
 * OF-BLD-016 §3.2.)
 */
export function shownProposals(
  items: Proposal[],
  acting: GuildPerson | null,
  status: StatusMap,
): Proposal[] {
  const queue = mayQueue(acting, status);
  return items.filter((p) => p.module !== 'guild' || (queue && acting !== null && p.fields.personId !== acting.id));
}

/** Whether carrying a proposal out asks Guild for something in a person's name, which needs who is acting. */
export const needsActing = (p: Pick<Proposal, 'module' | 'action'>): boolean =>
  p.module === 'guild' && p.action === 'propose_check';

async function act(id: string, verb: 'carry-out' | 'dismiss', body: ProposalAction): Promise<Proposal> {
  const response = await apiFetch(`/api/proposals/${encodeURIComponent(id)}/${verb}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      detail = String(((await response.json()) as { detail?: string }).detail ?? detail);
    } catch {
      /* the status is the message */
    }
    throw new Error(detail);
  }
  return (await response.json()) as Proposal;
}

/**
 * Carry a proposal out as `person`. `actingId` is the Guild person the browser
 * is acting as: Guild knows people by id, so a check is asked for by them
 * (OF-BLD-016 §1.R finding 11), and the reviewer name goes on the proposal.
 */
export const carryOut = (id: string, person: string, actingId: string | null = null) =>
  act(id, 'carry-out', { person, reason: '', actingId });
export const dismiss = (id: string, person: string, reason: string) => act(id, 'dismiss', { person, reason });
