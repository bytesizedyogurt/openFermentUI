// Proposals a model made at a gate (OF-BLD-015 §7.4), read and answered
// through the service. Nothing here decides anything: a person presses the
// button, and their reviewer name goes on the proposal and the audit log.
import type { Proposal } from '@/data/types';

export async function listProposals(signal?: AbortSignal): Promise<Proposal[]> {
  const response = await fetch('/api/proposals?state=proposed', { signal });
  if (!response.ok) throw new Error(`GET /api/proposals → ${response.status}`);
  return (await response.json()) as Proposal[];
}

async function act(id: string, verb: 'carry-out' | 'dismiss', person: string, reason = ''): Promise<Proposal> {
  const response = await fetch(`/api/proposals/${encodeURIComponent(id)}/${verb}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ person, reason }),
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

export const carryOut = (id: string, person: string) => act(id, 'carry-out', person);
export const dismiss = (id: string, person: string, reason: string) => act(id, 'dismiss', person, reason);
