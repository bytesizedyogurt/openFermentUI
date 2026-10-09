/**
 * Competence, recorded (OF-BLD-013 §2.1).
 *
 * `src/engine/competence.ts` is the reference and
 * `core/openferment_core/competence.py` its mirror, which the service uses to
 * decide whether a cosigner holds a skill. This writes what the TypeScript side
 * answers for every person and skill on two ledgers, and
 * core/tests/test_competence.py asserts the Python side answers the same.
 * Nothing here is a hand-typed expectation.
 *
 * THE LEDGERS ARE CHOSEN TO BE AWKWARD. The sample team, read on three days,
 * covers every level, a suspension and lapses; a second ledger adds withdrawn
 * entries, a failed check followed by a passed one, entries recorded on the
 * same day in an order their ids do not follow, a prerequisite chain, and a
 * qualification whose recency window closes on the very day it is read.
 *
 * Emits core/tests/fixtures/competence.json, gitignored like units.json.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { SKILL_BY_ID } from '../src/data/skills';
import { sampleGuild } from '../src/data/guildSample';
import { addDays, competenceOf } from '../src/engine/competence';
import type { Guild, GuildEvidence, GuildPerson } from '../src/data/types';

const OUT = 'core/tests/fixtures/competence.json';
const DAY = '2026-10-09';

const person = (id: string, role: GuildPerson['role'] = 'member'): GuildPerson => ({
  id, name: id, role, title: '', joinedAt: '2026-01-01', active: true, addedBy: null, addedAt: '2026-01-01T00:00:00Z',
});
let n = 0;
const ev = (personId: string, skillId: string, kind: GuildEvidence['kind'], at: string, extra: Partial<GuildEvidence> = {}): GuildEvidence => ({
  id: `e-fx-${String(++n).padStart(4, '0')}`,
  personId, skillId, kind, outcome: 'pass', at, observerId: 'p-a',
  source: { kind: kind === 'designation' ? 'lead' : 'signoff', ref: 'fixture' },
  raw: 'fixture', recordedAt: null, ...extra,
});

const awkward: Guild = {
  version: 1,
  people: [person('p-lead', 'lead'), person('p-a'), person('p-b'), person('p-c'), person('p-qa', 'auditor')],
  evidence: [
    ev('p-a', 'SK-OD', 'knowledge', '2026-08-01'),
    ...[1, 2, 3].map((k) => ev('p-a', 'SK-OD', 'supervised', `2026-08-0${k + 1}`)),
    ev('p-a', 'SK-OD', 'witnessed', '2026-08-10'),
    ev('p-a', 'SK-OD', 'witnessed', '2026-09-01', { outcome: 'fail' }),
    // Same day, recorded later, lower id: order is by recordedAt before id.
    ev('p-a', 'SK-OD', 'witnessed', '2026-09-20', { recordedAt: '2026-09-20T15:00:00Z' }),
    ev('p-a', 'SK-OD', 'witnessed', '2026-09-20', { outcome: 'fail', recordedAt: '2026-09-20T09:00:00Z' }),
    ev('p-a', 'SK-DCW', 'knowledge', '2026-08-01'),
    ev('p-a', 'SK-FACTOR', 'knowledge', '2026-08-02'),
    ev('p-b', 'SK-FACTOR', 'knowledge', '2026-08-02'),
    ev('p-b', 'SK-OD', 'knowledge', '2026-08-02', { withdrawnAt: '2026-08-03' }),
    ev('p-b', 'SK-CIP', 'designation', '2026-02-01'),
    ev('p-b', 'SK-PRESS', 'designation', '2026-02-01', { withdrawnAt: '2026-03-01' }),
    ev('p-b', 'SK-STER', 'knowledge', '2026-08-01'),
    ev('p-b', 'SK-HOLD', 'knowledge', '2026-08-01'),
    // Qualified, last seen exactly one recency window before the day read:
    // the window closes today, and today is still inside it.
    ev('p-c', 'SK-OD', 'knowledge', '2026-07-01'),
    ...[1, 2, 3].map((k) => ev('p-c', 'SK-OD', 'supervised', `2026-07-0${k + 1}`)),
    ev('p-c', 'SK-OD', 'witnessed', addDays(DAY, -60)),
  ],
};

const sample = sampleGuild(DAY);
const cases = [
  { name: 'sample, its own day', guild: sample, today: DAY },
  { name: 'sample, a month on', guild: sample, today: addDays(DAY, 31) },
  { name: 'sample, a year on', guild: sample, today: addDays(DAY, 365) },
  { name: 'awkward', guild: awkward, today: DAY },
  { name: 'awkward, much later', guild: awkward, today: '2027-06-01' },
].map(({ name, guild, today }) => {
  const map = competenceOf(guild.evidence, guild.people, SKILL_BY_ID, today);
  return {
    name,
    today,
    people: guild.people,
    evidence: guild.evidence,
    statuses: [...map.values()].map((s) => ({
      personId: s.personId,
      skillId: s.skillId,
      level: s.level,
      effective: s.effective,
      lapsed: s.lapsed,
      suspended: s.suspended,
      lapsesAt: s.lapsesAt,
      supervisedCount: s.supervisedCount,
      knowledgeComplete: s.knowledgeComplete,
    })),
  };
});

mkdirSync('core/tests/fixtures', { recursive: true });
writeFileSync(OUT, JSON.stringify({ skills: Object.values(SKILL_BY_ID), cases }, null, 1) + '\n');
console.log(`✓ ${OUT} — ${cases.reduce((k, c) => k + c.statuses.length, 0)} statuses over ${cases.length} ledgers`);
