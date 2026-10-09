// Which checks to propose (OF-BLD-013 §5.2): every person and skill on the
// ledger ranked by what makes an assessor's next look worth taking, by fixed
// rules over the ledger, with each reason written out. Pure, like
// `competenceOf`; no model sets a reason or a rank.
//
// `core/openferment_core/checks.py` mirrors this for the nightly job and the
// service, held to it by the competence fixture (`pnpm
// export:competence-fixtures`). When the two disagree, this side is right.
//
// A pair is looked at when the person performs the skill: Supervised or
// Qualified. Learning has nothing yet to check, and an Assessor's standing
// is the lead's to withdraw. The reasons, and what each adds:
//
//   suspended   5   the latest witnessed check did not pass
//   lapsed      4   no performance on the ledger within the recency window
//   lapsing     3   the window closes within LAPSING_DAYS
//   ready       3   supervised runs done: a passed check would qualify them
//   deviation   3   a deviation recorded within DEVIATION_DAYS
//   confidence  2   Qualified, current, and the ledger's confidence is low
//   rate        2   a critical skill with fewer witnessed checks this quarter
//                   than the lead's policy asks for
//
// and one more for a critical skill. A person's three highest pairs make one
// check; the highest checks are proposed first. A pair an open check already
// covers is not proposed again.
import type { CheckReason, Guild, Skill } from '@/data/types';
import { competenceOf, daysBetween, policyOf, readyForCheck, statusOf } from './competence';

export const LAPSING_DAYS = 21;
export const DEVIATION_DAYS = 30;
export const SKILLS_PER_CHECK = 3;
export const PROPOSALS_PER_RUN = 5;

const WEIGHT: Record<CheckReason['kind'], number> = {
  suspended: 5,
  lapsed: 4,
  lapsing: 3,
  ready: 3,
  deviation: 3,
  confidence: 2,
  rate: 2,
  requested: 0,
};

export interface RankedPair {
  personId: string;
  skillId: string;
  score: number;
  reasons: CheckReason[];
}

export interface Proposal {
  personId: string;
  skillIds: string[];
  score: number;
  reasons: CheckReason[];
}

/** The first day of the calendar quarter `day` falls in. */
export function quarterStart(day: string): string {
  const y = day.slice(0, 4);
  const m = Number(day.slice(5, 7));
  const first = Math.floor((m - 1) / 3) * 3 + 1;
  return `${y}-${String(first).padStart(2, '0')}-01`;
}

export function rankPairs(
  ledger: Guild,
  skills: Record<string, Skill>,
  today: string,
  covered: Set<string> = new Set(),
): RankedPair[] {
  const map = competenceOf(ledger.evidence, ledger.people, skills, today);
  const policy = policyOf(ledger);
  const quarter = quarterStart(today);
  const live = ledger.evidence.filter((e) => !e.withdrawnAt);
  const out: RankedPair[] = [];
  for (const person of ledger.people) {
    if (!person.active || person.role === 'auditor') continue;
    for (const skill of Object.values(skills)) {
      if (covered.has(`${person.id}|${skill.id}`)) continue;
      const st = statusOf(map, person.id, skill.id);
      if (st.level !== 2 && st.level !== 3) continue;
      const mine = live.filter((e) => e.personId === person.id && e.skillId === skill.id);
      const reasons: CheckReason[] = [];
      const add = (kind: CheckReason['kind'], text: string) => reasons.push({ kind, skillId: skill.id, text });
      if (st.level === 3 && st.suspended) {
        const failed = mine.filter((e) => e.kind === 'witnessed' && e.outcome === 'fail').map((e) => e.at.slice(0, 10)).sort().pop();
        add('suspended', `Did not meet every criterion at the witnessed check on ${failed}; a passed re-check lifts the suspension.`);
      }
      if (st.level === 3 && st.lapsed) add('lapsed', `Lapsed on ${st.lapsesAt}: nothing on the ledger shows it performed within ${skill.recencyDays} days.`);
      else if (st.level === 3 && st.lapsesAt && daysBetween(today, st.lapsesAt) <= LAPSING_DAYS) add('lapsing', `Lapses on ${st.lapsesAt}.`);
      if (readyForCheck(st, skill))
        add('ready', `Supervised runs done (${st.supervisedCount} of ${skill.supervisedRuns}); a passed check would make it Qualified.`);
      const deviated = mine
        .filter((e) => e.kind === 'deviation' && daysBetween(e.at, today) <= DEVIATION_DAYS && daysBetween(e.at, today) >= 0)
        .map((e) => e.at.slice(0, 10))
        .sort()
        .pop();
      if (deviated) add('deviation', `A deviation recorded on ${deviated}.`);
      if (st.level === 3 && !st.lapsed && !st.suspended && st.confidence === 'low')
        add('confidence', 'Qualified and current, with low confidence on the ledger’s own evidence.');
      if (st.level === 3 && skill.criticality === 'critical' && policy.checksPerQuarter > 0) {
        const checked = mine.filter((e) => e.kind === 'witnessed' && e.at.slice(0, 10) >= quarter && e.at.slice(0, 10) <= today).length;
        if (checked < policy.checksPerQuarter)
          add('rate', `A critical skill with ${checked} witnessed check${checked === 1 ? '' : 's'} this quarter; the lead asks for ${policy.checksPerQuarter}.`);
      }
      if (reasons.length === 0) continue;
      const score = reasons.reduce((n, r) => n + WEIGHT[r.kind], 0) + (skill.criticality === 'critical' ? 1 : 0);
      out.push({ personId: person.id, skillId: skill.id, score, reasons });
    }
  }
  return out.sort((a, b) => b.score - a.score || (a.personId < b.personId ? -1 : a.personId > b.personId ? 1 : 0) || (a.skillId < b.skillId ? -1 : 1));
}

/**
 * The checks to propose: a person's highest pairs grouped into one check,
 * the highest checks first, at most `limit`. `covered` holds the
 * person|skill pairs an open check already covers.
 */
export function proposeChecks(
  ledger: Guild,
  skills: Record<string, Skill>,
  today: string,
  covered: Set<string> = new Set(),
  limit: number = PROPOSALS_PER_RUN,
): Proposal[] {
  const byPerson = new Map<string, RankedPair[]>();
  for (const pair of rankPairs(ledger, skills, today, covered)) {
    const list = byPerson.get(pair.personId) ?? [];
    if (list.length < SKILLS_PER_CHECK) list.push(pair);
    byPerson.set(pair.personId, list);
  }
  const proposals: Proposal[] = [...byPerson.entries()].map(([personId, pairs]) => ({
    personId,
    skillIds: pairs.map((p) => p.skillId),
    score: pairs.reduce((n, p) => n + p.score, 0),
    reasons: pairs.flatMap((p) => p.reasons),
  }));
  return proposals
    .sort((a, b) => b.score - a.score || (a.personId < b.personId ? -1 : a.personId > b.personId ? 1 : 0))
    .slice(0, limit);
}
