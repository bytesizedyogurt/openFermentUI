// The sample team (OF-BLD-013 §1.3). INVENTED PEOPLE, for showing Guild to
// someone before a real team is on the ledger.
//
// Loaded from Guild's empty state with a button that says what it is, held in
// the store beside the real ledger and never in place of it: nothing here is
// posted to the service, written to guild.json or kept in the Durable tier,
// and a banner sits above every Guild view while it is shown. A reload drops
// it. Every name is made up.
//
// HOW IT IS BUILT. A table says roughly where each person stands on each
// skill; `sampleGuild` writes the entries that would put them there, dated
// back from the day it is loaded. Nothing downstream reads the table:
// `competenceOf` computes every level from the entries alone, which makes the
// sample a working test of the engine as much as a demonstration.
import type { Guild, GuildEvidence, GuildPerson } from './types';
import { SKILLS, SKILL_BY_ID } from './skills';
import { PROTOCOLS } from './protocols';
import { addDays } from '@/engine/competence';

export const SAMPLE_LEAD = 'p-sample-lead';

const PEOPLE: [id: string, name: string, title: string, role: GuildPerson['role'], daysIn: number][] = [
  [SAMPLE_LEAD, 'Aimée Uwera', 'Lead', 'lead', 400],
  ['p-sample-eric', 'Eric Habimana', 'Senior process scientist', 'member', 250],
  ['p-sample-diane', 'Diane Mukamana', 'QC lead', 'member', 205],
  ['p-sample-jp', 'Jean-Paul Niyonzima', 'Process operator', 'member', 185],
  ['p-sample-grace', 'Grace Ingabire', 'Process operator', 'member', 185],
  ['p-sample-patrick', 'Patrick Mugisha', 'Operator trainee', 'member', 129],
  ['p-sample-claudine', 'Claudine Uwimana', 'Operator trainee', 'member', 129],
  ['p-sample-olivier', 'Olivier Ndayisaba', 'Operator trainee', 'member', 66],
  ['p-sample-sandrine', 'Sandrine Umutoni', 'Operator trainee', 'member', 66],
  ['p-sample-emmanuel', 'Emmanuel Hakizimana', 'Operator trainee', 'member', 25],
  ['p-sample-aline', 'Aline Uwase', 'Operator trainee', 'member', 25],
  ['p-sample-auditor', 'Client QA reviewer', 'Auditor, read-only', 'auditor', 8],
];

const ORDER = [
  'SK-ASEP', 'SK-STER', 'SK-HOLD', 'SK-ISOL', 'SK-CIP', 'SK-ASSY', 'SK-PROBE',
  'SK-ENV', 'SK-OD', 'SK-DCW', 'SK-FACTOR', 'SK-LOG', 'SK-CAUSTIC', 'SK-PRESS',
];

// - nothing · L learning · S supervised · SR supervised, runs complete ·
// Q qualified · QL qualified and lapsed · X qualified, then failed a check ·
// A assessor
type Code = '-' | 'L' | 'S' | 'SR' | 'Q' | 'QL' | 'X' | 'A';

const TARGETS: Record<string, string> = {
  'p-sample-eric': 'A A A A A A A A A A Q A A A',
  'p-sample-diane': 'Q S Q Q S L Q Q A A A A Q Q',
  'p-sample-jp': 'Q Q S Q Q Q QL Q Q S L Q Q Q',
  'p-sample-grace': 'Q S L Q SR Q Q Q Q Q S Q Q Q',
  'p-sample-patrick': 'SR L - S L S L Q X S - S Q Q',
  'p-sample-claudine': 'S - - L L S S Q Q Q L Q S S',
  'p-sample-olivier': 'L - - L - L - S S L - L L L',
  'p-sample-sandrine': 'L - - - - - - L S S - L L S',
  'p-sample-emmanuel': '- - - - - - - - L - - - L L',
  'p-sample-aline': 'L - - - - - - - - - - L - -',
};

const codeOf = (personId: string, skillId: string): Code =>
  ((TARGETS[personId] ?? '').split(' ')[ORDER.indexOf(skillId)] ?? '-') as Code;

function stepFor(skillId: string): { ref: string; stepId: string } {
  for (const p of PROTOCOLS)
    for (const v of p.versions)
      for (const st of v.steps) if (st.skills?.includes(skillId)) return { ref: p.id, stepId: st.id };
  return { ref: 'induction', stepId: '' };
}

const daysInOf = (id: string): number => PEOPLE.find((p) => p[0] === id)?.[4] ?? 0;

function assessorFor(skillId: string, personId: string): string {
  for (const who of ['p-sample-eric', 'p-sample-diane'])
    if (who !== personId && codeOf(who, skillId) === 'A') return who;
  return 'p-sample-eric';
}

/** The sample ledger, dated back from `today` (YYYY-MM-DD). Deterministic for a given day. */
export function sampleGuild(today: string): Guild {
  const people: GuildPerson[] = PEOPLE.map(([id, name, title, role, daysIn]) => ({
    id,
    name,
    title,
    role,
    joinedAt: addDays(today, -daysIn),
    active: true,
    addedBy: id === SAMPLE_LEAD ? null : SAMPLE_LEAD,
    addedAt: `${addDays(today, -daysIn)}T09:00:00Z`,
  }));
  const evidence: GuildEvidence[] = [];
  let n = 0;
  const add = (
    personId: string,
    skillId: string,
    kind: GuildEvidence['kind'],
    daysAgo: number,
    observerId: string,
    raw: string,
    outcome: 'pass' | 'fail' = 'pass',
  ) => {
    n += 1;
    const step = stepFor(skillId);
    evidence.push({
      id: `e-sample-${String(n).padStart(4, '0')}`,
      personId,
      skillId,
      kind,
      outcome,
      at: addDays(today, -Math.max(0, Math.round(daysAgo))),
      observerId,
      source:
        kind === 'designation'
          ? { kind: 'lead', ref: 'founding assessors' }
          : { kind: 'signoff', ref: step.ref, stepId: step.stepId || null },
      raw,
      recordedAt: null,
    });
  };

  for (const [personId, , , role, daysIn] of PEOPLE) {
    if (role !== 'member') continue;
    for (const skillId of ORDER) {
      const code = codeOf(personId, skillId);
      const skill = SKILL_BY_ID[skillId];
      const obs = assessorFor(skillId, personId);
      // Nobody signs before they joined and were designated: an assessor's
      // designation is dated just after they joined, and what they sign
      // comes after that.
      const t = Math.min(daysIn, daysInOf(obs) * 0.95);
      switch (code) {
        case '-':
          break;
        case 'L':
          // Something on the ledger, short of a training sign-off.
          add(personId, skillId, 'supervised', t * 0.3, obs, 'Shadowed the step; not yet briefed on it');
          break;
        case 'S':
        case 'SR': {
          add(personId, skillId, 'knowledge', t * 0.55, obs, 'Briefed on the SOP and talked it back');
          const runs = code === 'SR' ? skill.supervisedRuns : Math.max(0, skill.supervisedRuns - 1);
          for (let k = 0; k < runs; k++) add(personId, skillId, 'supervised', t * 0.4 - k * 4, obs, 'Performed with me beside them');
          break;
        }
        case 'A':
          add(personId, skillId, 'designation', daysIn * 0.98, SAMPLE_LEAD, 'Founding assessor');
          break;
        default: {
          // Q, QL, X
          const lapsed = code === 'QL';
          add(personId, skillId, 'knowledge', t * 0.95, obs, 'Briefed on the SOP and talked it back');
          for (let k = 0; k < skill.supervisedRuns; k++)
            add(personId, skillId, 'supervised', (lapsed ? skill.recencyDays + 40 : t * 0.88) - k * 5, obs, 'Performed with me beside them');
          add(
            personId,
            skillId,
            'witnessed',
            lapsed ? skill.recencyDays + 20 : Math.min(t * 0.45, skill.recencyDays - 10 - (n % 20)),
            obs,
            'Met every criterion at the bench',
          );
          if (code === 'X')
            add(personId, skillId, 'witnessed', 4, obs, 'Read a sample that had been standing, and blanked on fresh medium', 'fail');
        }
      }
    }
  }
  // Designations for the skills Eric does not assess come from Diane's table
  // above; every skill needs at least one assessor or nobody could sign it.
  for (const sk of SKILLS)
    if (!evidence.some((e) => e.kind === 'designation' && e.skillId === sk.id))
      add('p-sample-diane', sk.id, 'designation', daysInOf('p-sample-diane') * 0.98, SAMPLE_LEAD, 'Founding assessor');

  return { version: 1, people, evidence };
}
