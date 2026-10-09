// The browser's side of Guild's checks (OF-BLD-013 §5.4).
//
// The rules live in `core/openferment_core/checks.py`; a refusal comes back
// as the rule and the reason, and nothing here repeats them. With the sample
// team shown, the store runs the same ranking (src/engine/checks.ts) in this
// browser and keeps the sample's checks in memory: nothing about the sample
// reaches the service.
import type { Check, CheckDismiss, CheckRecord, CheckRequest, Checks, CheckSchedule } from '@/data/types';
import { IntakeDown } from './intake';

export class CheckRefused extends Error {
  constructor(
    readonly rule: string,
    readonly why: string,
  ) {
    super(why);
    this.name = 'CheckRefused';
  }
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(
      path,
      body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
    );
  } catch {
    throw new IntakeDown('The service is not running.');
  }
  let detail = '';
  if (!response.ok) {
    try {
      detail = String(((await response.json()) as { detail?: string }).detail ?? '');
    } catch {
      /* the status is the message */
    }
  }
  if (response.status === 422) {
    const m = /^([a-z]+): (.*)$/s.exec(detail);
    throw new CheckRefused(m ? m[1] : 'unknown', m ? m[2] : detail || 'refused without a reason');
  }
  if (!response.ok) throw new IntakeDown(detail || `The service answered ${response.status}.`);
  return (await response.json()) as T;
}

/** Every check, or null when there is no service to ask. */
export async function loadChecks(): Promise<Checks | null> {
  try {
    const got = await call<Checks>('/api/guild/checks');
    // Anything without a list of checks is no answer about checks.
    return got && Array.isArray(got.checks) ? got : null;
  } catch {
    return null;
  }
}

export const postPropose = (by: string) => call<Check[]>('/api/guild/checks/propose', { by });
export const postRequest = (r: CheckRequest) => call<Check>('/api/guild/checks/request', r);
export const postSchedule = (id: string, r: CheckSchedule) => call<Check>(`/api/guild/checks/${id}/schedule`, r);
export const postDismiss = (id: string, r: CheckDismiss) => call<Check>(`/api/guild/checks/${id}/dismiss`, r);
export const postRecord = (id: string, r: CheckRecord) => call<Check>(`/api/guild/checks/${id}/record`, r);
export const postBrief = (id: string, by: string) => call<Check>(`/api/guild/checks/${id}/brief`, { by });

/** A refusal or an outage in words a screen can show. */
export function whyNot(e: unknown): string {
  if (e instanceof CheckRefused) return `${e.why} (${e.rule})`;
  if (e instanceof IntakeDown) return e.message;
  return String(e);
}

export const OPEN_STATES: Check['state'][] = ['proposed', 'scheduled'];
