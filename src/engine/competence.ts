// Competence (OF-BLD-013 §1.3): a person's level on a skill, computed from the
// ledger by fixed rules. Pure, like `provenanceOf`: no store, no clock of its
// own (today is passed in), no model output anywhere near it. Nothing stores a
// level, so nothing can disagree with the entries it rests on.
//
// THE LADDER, per person and skill, over entries that are not withdrawn:
//
//   Assessor     the lead has designated them (and the designation stands)
//   Qualified    a passed witnessed check, at least `supervisedRuns`
//                supervised runs, knowledge signed off, prerequisites at
//                Supervised or above
//   Supervised   knowledge signed off and prerequisites at Supervised or above
//   Learning     anything at all on the ledger for this skill
//   Not started  nothing
//
// "Knowledge signed off" means a training sign-off by an assessor. A lesson
// passed in Primer is a knowledge entry too, recorded by the machine with
// nobody watching (OF-BLD-013 §3.1): it puts the person at Learning and
// leaves the step to Supervised with the assessor who hears them talk it back.
//
// Two overlays on Qualified, both of which make the gate treat the person as
// Supervised until an assessor sees them again:
//
//   lapsed       nobody has seen them perform within the skill's recency
//                window (a witnessed check or a supervised run counts)
//   suspended    their latest witnessed check did not pass
//
// An Assessor neither lapses nor is suspended here: the designation is the
// lead's standing judgment, and the lead withdraws it when it stops being
// true. That is the same rule `guild.write_evidence` applies when it asks
// whether an observer may sign, so the screen and the service agree on who
// is an assessor without either computing the other's answer.
import type { GuildEvidence, GuildPerson, Skill, Step } from '@/data/types';

export type Level = 0 | 1 | 2 | 3 | 4;

export const LEVEL_NAME: Record<Level, string> = {
  0: 'Not started',
  1: 'Learning',
  2: 'Supervised',
  3: 'Qualified',
  4: 'Assessor',
};

export type Confidence = 'high' | 'medium' | 'low';

export interface CompetenceStatus {
  personId: string;
  skillId: string;
  level: Level;
  lapsed: boolean;
  suspended: boolean;
  /** What the gate acts on: a lapsed or suspended Qualified acts as Supervised. */
  effective: Level;
  /**
   * An honest three-way sort, in the spirit of `Prediction.confidence`, and
   * never presented as a probability. It ranks where an assessor's next look
   * is best spent.
   */
  confidence: Confidence;
  lastPerformedAt: string | null;
  lapsesAt: string | null;
  supervisedCount: number;
  /** A training sign-off stands. Lessons passed do not set it; they are counted where they are shown. */
  knowledgeComplete: boolean;
  /** Prerequisites still below Supervised, which hold this skill at Learning. */
  blockedBy: string[];
  /** The entries the level rests on, oldest first. */
  basis: string[];
}

export type StatusMap = Map<string, CompetenceStatus>;

const key = (personId: string, skillId: string) => `${personId}|${skillId}`;

/** Days from `a` to `b`, both read as calendar days. */
export function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(b.slice(0, 10) + 'T12:00:00Z') - Date.parse(a.slice(0, 10) + 'T12:00:00Z')) / 864e5);
}

export function addDays(day: string, n: number): string {
  const d = new Date(day.slice(0, 10) + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Today as YYYY-MM-DD in the browser's own calendar. */
export function localToday(now: Date = new Date()): string {
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${m}-${d}`;
}

/** Ledger order: by the day it happened, then by when it was recorded, then id. */
export function byWhen(a: GuildEvidence, b: GuildEvidence): number {
  const da = a.at.slice(0, 10);
  const db = b.at.slice(0, 10);
  if (da !== db) return da < db ? -1 : 1;
  const ra = a.recordedAt ?? '';
  const rb = b.recordedAt ?? '';
  if (ra !== rb) return ra < rb ? -1 : 1;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

const PERFORMED = new Set(['witnessed', 'supervised', 'independent']);

/** Knowledge an assessor signed off. A lesson passed counts toward Learning only. */
const signedOff = (ev: GuildEvidence[]) =>
  ev.some((e) => e.kind === 'knowledge' && e.outcome === 'pass' && e.source.kind === 'signoff');

/**
 * Every person's status on every skill. `people` decides who is computed (an
 * auditor holds no skills and is left out); `skills` is the seed.
 */
export function competenceOf(
  evidence: GuildEvidence[],
  people: GuildPerson[],
  skills: Record<string, Skill>,
  today: string,
): StatusMap {
  const live = evidence.filter((e) => !e.withdrawnAt).slice().sort(byWhen);
  const byKey = new Map<string, GuildEvidence[]>();
  for (const e of live) {
    const k = key(e.personId, e.skillId);
    const list = byKey.get(k);
    if (list) list.push(e);
    else byKey.set(k, [e]);
  }

  const base = new Map<string, Level>();
  const visiting = new Set<string>();
  const levelOf = (personId: string, skillId: string): Level => {
    const k = key(personId, skillId);
    const known = base.get(k);
    if (known !== undefined) return known;
    const skill = skills[skillId];
    if (!skill || visiting.has(k)) return 0;
    visiting.add(k);
    const ev = byKey.get(k) ?? [];
    const pass = (kind: string) => ev.some((e) => e.kind === kind && e.outcome === 'pass');
    const knowledge = signedOff(ev);
    const supervised = ev.filter((e) => e.kind === 'supervised' && e.outcome === 'pass').length;
    const prereqOK = skill.prerequisites.every((p) => levelOf(personId, p) >= 2);
    let level: Level = 0;
    if (pass('designation')) level = 4;
    else if (knowledge && prereqOK && pass('witnessed') && supervised >= skill.supervisedRuns) level = 3;
    else if (knowledge && prereqOK) level = 2;
    else if (ev.length > 0) level = 1;
    visiting.delete(k);
    base.set(k, level);
    return level;
  };

  const out: StatusMap = new Map();
  for (const person of people) {
    if (person.role === 'auditor') continue;
    for (const skill of Object.values(skills)) {
      const k = key(person.id, skill.id);
      const ev = byKey.get(k) ?? [];
      const level = levelOf(person.id, skill.id);
      const knowledgeComplete = signedOff(ev);
      const supervisedCount = ev.filter((e) => e.kind === 'supervised' && e.outcome === 'pass').length;
      const performed = ev.filter((e) => PERFORMED.has(e.kind) && e.outcome === 'pass');
      const lastPerformedAt = performed.length ? performed[performed.length - 1].at.slice(0, 10) : null;
      const witnessed = ev.filter((e) => e.kind === 'witnessed');
      const latestWitness = witnessed[witnessed.length - 1];
      const lapsesAt = level === 3 && lastPerformedAt ? addDays(lastPerformedAt, skill.recencyDays) : null;
      const lapsed = Boolean(lapsesAt && lapsesAt < today);
      const suspended = level === 3 && latestWitness?.outcome === 'fail';
      const effective: Level = lapsed || suspended ? 2 : level;
      const blockedBy = skill.prerequisites.filter((p) => levelOf(person.id, p) < 2);

      let score = 0;
      if (level === 4) score += 3;
      if (witnessed.some((e) => e.outcome === 'pass' && daysBetween(e.at, today) <= skill.recencyDays)) score += 2;
      score += Math.min(2, performed.filter((e) => daysBetween(e.at, today) <= 60).length);
      score -= 2 * ev.filter((e) => e.kind === 'deviation' && daysBetween(e.at, today) <= 90).length;
      if (suspended) score -= 3;
      if (lapsed) score -= 2;
      else if (lapsesAt && daysBetween(today, lapsesAt) <= 21) score -= 1;
      if (level === 2 && supervisedCount >= skill.supervisedRuns) score += 1;
      const confidence: Confidence = score >= 3 ? 'high' : score >= 1 ? 'medium' : 'low';

      out.set(k, {
        personId: person.id,
        skillId: skill.id,
        level,
        lapsed,
        suspended,
        effective,
        confidence,
        lastPerformedAt,
        lapsesAt,
        supervisedCount,
        knowledgeComplete,
        blockedBy,
        basis: ev.map((e) => e.id),
      });
    }
  }
  return out;
}

const NOTHING: Omit<CompetenceStatus, 'personId' | 'skillId'> = {
  level: 0,
  lapsed: false,
  suspended: false,
  effective: 0,
  confidence: 'low',
  lastPerformedAt: null,
  lapsesAt: null,
  supervisedCount: 0,
  knowledgeComplete: false,
  blockedBy: [],
  basis: [],
};

export function statusOf(map: StatusMap, personId: string, skillId: string): CompetenceStatus {
  return map.get(key(personId, skillId)) ?? { personId, skillId, ...NOTHING };
}

/** Knowledge and supervised runs complete: a passed witnessed check would qualify them. */
export function readyForCheck(st: CompetenceStatus, skill: Skill): boolean {
  return st.level === 2 && st.blockedBy.length === 0 && st.supervisedCount >= skill.supervisedRuns;
}

/** Whether this person may witness and sign off this skill. */
export function isAssessor(map: StatusMap, personId: string, skillId: string): boolean {
  return statusOf(map, personId, skillId).effective === 4;
}

/** Whether this person may perform alone and cosign every one of these skills. */
export function mayCosign(map: StatusMap, personId: string, skillIds: string[]): boolean {
  return skillIds.every((s) => statusOf(map, personId, s).effective >= 3);
}

// ── the gate (OF-BLD-013 §2) ───────────────────────────────────────────

export type GateState = 'none' | 'clear' | 'cosign' | 'blocked';

/**
 * What a step asks of this person. `none`: the step needs no skill. `clear`:
 * Qualified or above on every skill it needs. `cosign`: somewhere at
 * Supervised, lapsed or suspended. `blocked`: somewhere below Supervised.
 */
export function gateFor(
  step: Pick<Step, 'skills'>,
  personId: string,
  map: StatusMap,
): { state: GateState; cosign: string[]; blocked: string[] } {
  const tags = step.skills ?? [];
  if (tags.length === 0) return { state: 'none', cosign: [], blocked: [] };
  const cosign: string[] = [];
  const blocked: string[] = [];
  for (const s of tags) {
    const e = statusOf(map, personId, s).effective;
    if (e <= 1) blocked.push(s);
    else if (e === 2) cosign.push(s);
  }
  return { state: blocked.length ? 'blocked' : cosign.length ? 'cosign' : 'clear', cosign, blocked };
}

/** Who can run every step of a set of steps alone, needs a cosigner somewhere, or cannot run it yet. */
export function verdictFor(
  steps: Pick<Step, 'skills'>[],
  personId: string,
  map: StatusMap,
): { verdict: 'alone' | 'cosign' | 'blocked'; cosignSteps: number; missing: string[] } {
  let cosignSteps = 0;
  const missing = new Set<string>();
  for (const st of steps) {
    const g = gateFor(st, personId, map);
    if (g.state === 'cosign') cosignSteps += 1;
    for (const s of g.blocked) missing.add(s);
  }
  if (missing.size) return { verdict: 'blocked', cosignSteps, missing: [...missing] };
  return { verdict: cosignSteps ? 'cosign' : 'alone', cosignSteps, missing: [] };
}
