// The browser's side of Guild's ledger (OF-BLD-013 §1.3).
//
// Five calls, no key: read the ledger, add or change a person, append an
// entry, ask whether an entry would be kept, withdraw an entry. The rules live
// in `core/openferment_core/guild.py` and the browser asks them; when the
// service is down, the store keeps what was made here in the Durable tier and
// posts it the next time the service answers.
//
// `offlineRefusal` below is the OFFLINE FALLBACK and says so: the few rules a
// screen needs to grey out a button it already knows the service would
// refuse. It is not a second copy of the rules, and it never decides what is
// stored. While the service is up, the sign-off sheet asks /api/guild/check.
//
// Every shape here is the service's own, generated from its models into
// src/api/types.gen.ts (ADR-007): the ledger, a person, an entry, a
// withdrawal and the lead's policy. The skills a level is computed on are the
// project's skill catalogue (lib/catalogues.ts, `Skill`).
import type { components } from '@/api/types.gen';
import { DEFAULT_POLICY } from '@/engine/competence';
import { IntakeDown } from './intake';
import { apiFetch } from './project';
import { detailWords } from './http';

type S = components['schemas'];

/** `GET /api/guild`: a project's ledger, the people on it and everything recorded about them, with the lead's policy. */
export type Guild = S['Guild'];
/** A person on the ledger; the browser chooses the id, so a person added offline keeps theirs. */
export type GuildPerson = S['GuildPerson'];
/** What a person may do on the ledger: a member holds skills, the lead designates assessors, an auditor reads. */
export type GuildRole = GuildPerson['role'];
/** One thing a person did that bears on one skill. Append-only. */
/** `POST /api/guild/check`: whether the service would keep an entry, and the rule of Guild's it would refuse it under. */
export type EvidenceCheck = S['EvidenceCheck'];
export type GuildEvidence = S['GuildEvidence'];
/** What an entry rests on: a sign-off, the lead, a run at the bench, a lesson, a practice session or a check. */
export type EvidenceSource = S['EvidenceSource'];
/** `POST /api/guild/withdraw`: an entry taken back, by whom, when and why; the entry stays on the ledger, marked. */
export type GuildWithdrawal = S['GuildWithdrawal'];
/**
 * The lead's choices for the team (OF-BLD-013 §5.1). In advise mode the
 * run-mode gate warns and records a deviation; in enforce mode it holds the
 * step until a cosigner is recorded, or someone qualified takes over.
 */
export type GuildPolicy = S['GuildPolicy'];
/** Whether the gate holds a step or only warns. */
export type GateMode = GuildPolicy['routineGate'];

/** The service stored nothing and said which rule held. Not an outage. */
export class GuildRefused extends Error {
  constructor(
    readonly rule: string,
    readonly why: string,
  ) {
    super(why);
    this.name = 'GuildRefused';
  }
}

/** A ledger with nobody on it, under the default policy, as the service answers one. */
export const EMPTY_GUILD: Guild = { version: 1, people: [], evidence: [], policy: DEFAULT_POLICY };

async function call<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await apiFetch(
      path,
      body === undefined
        ? { signal }
        : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal },
    );
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('The service is not running.');
  }
  if (response.status === 422) {
    let detail = '';
    try {
      detail = detailWords(((await response.json()) as { detail?: unknown }).detail);
    } catch {
      /* the status is the message */
    }
    const m = /^([a-z]+): (.*)$/s.exec(detail);
    throw new GuildRefused(m ? m[1] : 'unknown', m ? m[2] : detail || 'refused without a reason');
  }
  if (!response.ok) throw new IntakeDown(`The service answered ${response.status}.`, 'Check its log; it names what went wrong.');
  return (await response.json()) as T;
}

/** The whole ledger, or null when there is no service to ask. */
export async function loadGuild(signal?: AbortSignal): Promise<Guild | null> {
  try {
    return await call<Guild>('/api/guild', undefined, signal);
  } catch {
    return null;
  }
}

export const postPerson = (p: GuildPerson, signal?: AbortSignal) => call<GuildPerson>('/api/guild/people', p, signal);
export const postEvidence = (e: GuildEvidence, signal?: AbortSignal) => call<GuildEvidence>('/api/guild/evidence', e, signal);
export const postWithdrawal = (w: GuildWithdrawal, signal?: AbortSignal) =>
  call<GuildEvidence>('/api/guild/withdraw', w, signal);
export const checkEvidence = (e: GuildEvidence, signal?: AbortSignal) => call<EvidenceCheck>('/api/guild/check', e, signal);
export const postPolicy = (p: GuildPolicy) => call<GuildPolicy>('/api/guild/policy', p);

// ── ids ────────────────────────────────────────────────────────────────

/** `p-` and a slug of the name, made unique against the ledger. */
export function personIdFor(name: string, taken: Iterable<string>): string {
  const slug =
    name
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48) || 'person';
  const used = new Set(taken);
  let id = `p-${slug}`;
  for (let n = 2; used.has(id); n++) id = `p-${slug}-${n}`;
  return id;
}

/** `e-`, the time in base 36, and a random tail: unique without asking anyone. */
export function newEvidenceId(now: number = Date.now()): string {
  const tail = Math.random().toString(36).slice(2, 8).padEnd(6, '0');
  return `e-${now.toString(36)}-${tail}`;
}

// ── offline fallback ───────────────────────────────────────────────────

/**
 * OFFLINE FALLBACK. Whether the service would certainly refuse this entry,
 * judged from the ledger the browser holds: the rules a sign-off sheet needs
 * to say why its button is grey. The service's answer replaces this one
 * whenever the service is up.
 */
export function offlineRefusal(e: GuildEvidence, ledger: Guild): { rule: string; why: string } | null {
  const people = new Map(ledger.people.map((p) => [p.id, p]));
  const person = people.get(e.personId);
  if (!person || !person.active) return { rule: 'person', why: 'pick someone who is active on the ledger' };
  if (person.role === 'auditor') return { rule: 'role', why: `${person.name} is an auditor and holds no skills` };
  if (e.source.kind === 'lesson' || e.source.kind === 'scenario') {
    // Primer's own record of a lesson passed or a practice session closed;
    // which lessons count toward which skills, and which sessions closed, are
    // the service's questions.
    if (e.observerId) return { rule: 'observer', why: 'Primer records this with nobody watching, so it names no observer' };
    const again = ledger.evidence.some(
      (x) => x.id !== e.id && x.source.kind === 'scenario' && e.source.kind === 'scenario' && x.source.ref === e.source.ref && !x.withdrawnAt,
    );
    return again ? { rule: 'duplicate', why: 'this practice session already stands behind an entry' } : null;
  }
  if (e.source.kind === 'deposition' && (e.kind === 'independent' || e.kind === 'deviation')) {
    // The operator's own record of a run. Whether they hold the skill is the
    // service's question; the gate only writes `independent` when they do.
    return e.observerId ? { rule: 'observer', why: 'an operator\u2019s own record of a run names no observer' } : null;
  }
  const observer = people.get(e.observerId ?? '');
  if (!observer || !observer.active)
    return { rule: 'observer', why: 'choose who you are with Acting as; a sign-off needs a named observer' };
  if (observer.id === person.id) return { rule: 'observer', why: 'nobody signs off their own work' };
  if (observer.role === 'auditor') return { rule: 'authority', why: `${observer.name} is an auditor and signs nothing` };
  if (e.kind === 'designation') {
    if (observer.role !== 'lead') return { rule: 'authority', why: 'only the lead designates assessors' };
  } else if (e.source.kind === 'deposition') {
    // A cosigner: whether they hold the skill today is the service's question.
  } else {
    const designated = ledger.evidence.some(
      (x) =>
        x.personId === observer.id &&
        x.skillId === e.skillId &&
        x.kind === 'designation' &&
        x.outcome === 'pass' &&
        !x.withdrawnAt,
    );
    if (!designated)
      return { rule: 'authority', why: `${observer.name} holds no assessor designation on this skill` };
  }
  if (e.raw.trim().length < 2) return { rule: 'note', why: 'write what you saw; an empty note cannot be audited' };
  return null;
}
