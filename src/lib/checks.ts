// The browser's side of Guild's checks (OF-BLD-013 §5.4).
//
// The rules live in `core/openferment_core/checks.py`; a refusal comes back
// as the rule and the reason, and nothing here repeats them. The ranking is
// src/engine/checks.ts's, which the service's nightly job mirrors
// (checks.py), the competence fixture holding the two equal.
//
// Every shape here is the service's own, generated from its models into
// src/api/types.gen.ts (ADR-007).
import type { components } from '@/api/types.gen';
import { IntakeDown } from './intake';
import { apiFetch } from './project';
import { detailWords } from './http';

type S = components['schemas'];

/** `GET /api/guild/checks`: every check proposed, asked for, run or dismissed. */
export type Checks = S['Checks'];
/** One witnessed check: who it is for, on which skills and why, and where it stands. */
export type Check = S['Check'];
/** Why a check is proposed, written by fixed rules from the ledger. */
export type CheckReason = S['CheckReason'];
/** What the model suggests the assessor watch for: references and questions with no number. */
export type CheckBrief = S['CheckBrief'];
/** One of a skill's mastery criteria, by its place in the skill's list. */
export type CheckCriterion = S['CheckCriterion'];
/** The assessor's call on one criterion, with their own words. */
export type CheckResult = S['CheckResult'];
/** The assessor's own words on one skill, kept verbatim as the entry's raw. */
export type CheckNote = S['CheckNote'];
/** `POST /api/guild/checks/request`: a check asked for by name, for a person on the skills named. */
export type CheckRequest = S['CheckRequest'];
/** `POST /api/guild/checks/{id}/schedule`: the day the assessor picked, which the person is not told. */
export type CheckSchedule = S['CheckSchedule'];
/** `POST /api/guild/checks/{id}/dismiss`: who dismissed a check, and why. */
export type CheckDismiss = S['CheckDismiss'];
/** `POST /api/guild/checks/{id}/record`: the assessor's calls and words at the bench. */
export type CheckRecord = S['CheckRecord'];

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
    response = await apiFetch(
      path,
      body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
    );
  } catch {
    throw new IntakeDown('The service is not running.');
  }
  let detail = '';
  if (!response.ok) {
    try {
      detail = detailWords(((await response.json()) as { detail?: unknown }).detail);
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
