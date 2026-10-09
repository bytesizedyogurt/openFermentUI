/**
 * Guild's competence engine and its slice of the store (OF-BLD-013 §1.3).
 *
 *   pnpm check:guild
 *
 * A level is computed, never stored, so the computation is the thing to hold
 * still. Three parts:
 *
 *   1. the ladder, step by step, on a ledger built here: each rung needs
 *      exactly what the header of src/engine/competence.ts says it needs,
 *      the overlays (lapsed, suspended) land on the right side of their
 *      boundary, withdrawn entries count for nothing, and the gate reads
 *      the result the way run mode will;
 *   2. the sample team: every entry in it is one the service's rules would
 *      accept, and the people the sample was written to show at a level
 *      come out at that level;
 *   3. the store: writes made with the service down are kept and marked
 *      pending, the sample never leaks into the ledger, and `syncGuild`
 *      posts people, then entries, then withdrawals, and drops what the
 *      service refuses.
 *
 * Runs with no service and no network: the service is a stub `fetch` here.
 */
import { useStore, guildView, actingIdOf } from '../src/store';
import { SKILLS, SKILL_BY_ID } from '../src/data/skills';
import { sampleGuild, SAMPLE_LEAD } from '../src/data/guildSample';
import { offlineRefusal } from '../src/lib/guild';
import {
  addDays,
  competenceOf,
  gateFor,
  isAssessor,
  readyForCheck,
  statusOf,
  verdictFor,
} from '../src/engine/competence';
import type { Guild, GuildEvidence, GuildPerson } from '../src/data/types';

let fails = 0;
const check = (label: string, ok: boolean, extra: unknown = '') => {
  console.log(`${ok ? '✓' : '✗'} ${label}${extra === '' ? '' : `  ${JSON.stringify(extra)}`}`);
  if (!ok) fails++;
};

const TODAY = '2026-10-09';
const SKILLS_MAP = SKILL_BY_ID;

// ── 1. the ladder ──────────────────────────────────────────────────────

const person = (id: string, role: GuildPerson['role'] = 'member'): GuildPerson => ({
  id,
  name: id,
  role,
  title: '',
  joinedAt: '2026-01-01',
  active: true,
  addedBy: null,
  addedAt: '2026-01-01T00:00:00Z',
});
const PEOPLE = [person('p-lead', 'lead'), person('p-ann'), person('p-tom'), person('p-qa', 'auditor')];

let n = 0;
const ev = (
  personId: string,
  skillId: string,
  kind: GuildEvidence['kind'],
  at: string,
  extra: Partial<GuildEvidence> = {},
): GuildEvidence => ({
  id: `e-test-${String(++n).padStart(4, '0')}`,
  personId,
  skillId,
  kind,
  outcome: 'pass',
  at,
  observerId: kind === 'designation' ? 'p-lead' : 'p-ann',
  source: kind === 'designation' ? { kind: 'lead', ref: 'test' } : { kind: 'signoff', ref: 'test' },
  raw: 'seen',
  recordedAt: null,
  ...extra,
});

const level = (entries: GuildEvidence[], personId: string, skillId: string, today = TODAY) =>
  statusOf(competenceOf(entries, PEOPLE, SKILLS_MAP, today), personId, skillId);

const OD = SKILL_BY_ID['SK-OD'];
check('SK-OD is the fixture this part assumes', OD.supervisedRuns === 3 && OD.recencyDays === 60 && OD.prerequisites.length === 0, {
  supervisedRuns: OD.supervisedRuns,
  recencyDays: OD.recencyDays,
});

const L: GuildEvidence[] = [];
check('nothing on the ledger is Not started', level(L, 'p-tom', 'SK-OD').level === 0);

L.push(ev('p-tom', 'SK-OD', 'supervised', '2026-09-01'));
check('anything at all is Learning', level(L, 'p-tom', 'SK-OD').level === 1);

L.push(ev('p-tom', 'SK-OD', 'knowledge', '2026-09-02'));
check('a training sign-off with no prerequisites is Supervised', level(L, 'p-tom', 'SK-OD').level === 2);

L.push(ev('p-tom', 'SK-OD', 'witnessed', '2026-09-20'), ev('p-tom', 'SK-OD', 'supervised', '2026-09-05'));
const two = level(L, 'p-tom', 'SK-OD');
check('a witnessed pass short of the supervised runs stays Supervised', two.level === 2 && two.supervisedCount === 2, two.supervisedCount);

L.push(ev('p-tom', 'SK-OD', 'supervised', '2026-09-10'));
const q = level(L, 'p-tom', 'SK-OD');
check('the third supervised run makes it Qualified', q.level === 3 && q.effective === 3);
check('recency runs from the latest performance', q.lastPerformedAt === '2026-09-20' && q.lapsesAt === addDays('2026-09-20', 60), q);

check('the day the window closes is still inside it', !level(L, 'p-tom', 'SK-OD', addDays('2026-09-20', 60)).lapsed);
const lapsed = level(L, 'p-tom', 'SK-OD', addDays('2026-09-20', 61));
check('the day after, it has lapsed and acts as Supervised', lapsed.lapsed && lapsed.level === 3 && lapsed.effective === 2);

const failAt = ev('p-tom', 'SK-OD', 'witnessed', '2026-10-01', { outcome: 'fail' });
L.push(failAt);
const susp = level(L, 'p-tom', 'SK-OD');
check('a failed latest check suspends a Qualified skill', susp.suspended && susp.effective === 2 && susp.level === 3);
L.push(ev('p-tom', 'SK-OD', 'witnessed', '2026-10-05'));
check('a later pass lifts the suspension', !level(L, 'p-tom', 'SK-OD').suspended);

const withdrawn = L.map((e) => (e.kind === 'witnessed' && e.outcome === 'pass' ? { ...e, withdrawnAt: '2026-10-06' } : e));
check('withdrawn entries count for nothing', level(withdrawn, 'p-tom', 'SK-OD').level === 2);

// Prerequisites: SK-FACTOR needs SK-OD and SK-DCW at Supervised or above.
const F: GuildEvidence[] = [ev('p-ann', 'SK-FACTOR', 'knowledge', '2026-09-01')];
const held = level(F, 'p-ann', 'SK-FACTOR');
check('a prerequisite below Supervised holds a skill at Learning', held.level === 1 && held.blockedBy.join() === 'SK-OD,SK-DCW', held.blockedBy);
F.push(ev('p-ann', 'SK-OD', 'knowledge', '2026-09-01'), ev('p-ann', 'SK-DCW', 'knowledge', '2026-09-01'));
check('with both prerequisites at Supervised it moves up', level(F, 'p-ann', 'SK-FACTOR').level === 2);

// Designation.
const D: GuildEvidence[] = [ev('p-ann', 'SK-CIP', 'designation', '2026-02-01')];
const map = competenceOf(D, PEOPLE, SKILLS_MAP, TODAY);
check('a standing designation is Assessor', isAssessor(map, 'p-ann', 'SK-CIP'));
check('an Assessor does not lapse', !statusOf(competenceOf(D, PEOPLE, SKILLS_MAP, '2030-01-01'), 'p-ann', 'SK-CIP').lapsed);
check(
  'a withdrawn designation is not',
  !isAssessor(competenceOf([{ ...D[0], withdrawnAt: '2026-03-01' }], PEOPLE, SKILLS_MAP, TODAY), 'p-ann', 'SK-CIP'),
);
check('an auditor holds no skills at all', !map.has('p-qa|SK-CIP'));

// The gate.
const G = competenceOf(
  [
    ev('p-ann', 'SK-CIP', 'designation', '2026-02-01'),
    ev('p-ann', 'SK-CAUSTIC', 'designation', '2026-02-01'),
    ev('p-tom', 'SK-CAUSTIC', 'knowledge', '2026-09-01'),
  ],
  PEOPLE,
  SKILLS_MAP,
  TODAY,
);
check('a step with no skills asks nothing', gateFor({ skills: [] }, 'p-tom', G).state === 'none');
check('qualified on every tag is clear', gateFor({ skills: ['SK-CIP', 'SK-CAUSTIC'] }, 'p-ann', G).state === 'clear');
check('Supervised somewhere needs a cosigner', gateFor({ skills: ['SK-CAUSTIC'] }, 'p-tom', G).state === 'cosign');
const blocked = gateFor({ skills: ['SK-CIP', 'SK-CAUSTIC'] }, 'p-tom', G);
check('below Supervised anywhere is blocked, and says where', blocked.state === 'blocked' && blocked.blocked.join() === 'SK-CIP' && blocked.cosign.join() === 'SK-CAUSTIC');
check(
  'a protocol verdict collects every missing skill',
  verdictFor([{ skills: ['SK-CIP'] }, { skills: ['SK-CAUSTIC'] }, { skills: [] }], 'p-tom', G).missing.join() === 'SK-CIP',
);

// ── 2. the sample team ─────────────────────────────────────────────────

const sample = sampleGuild(TODAY);
const sampleMap = competenceOf(sample.evidence, sample.people, SKILLS_MAP, TODAY);
const unacceptable = sample.evidence.filter((e) => offlineRefusal(e, sample) !== null);
check('every sample entry is one the service would accept', unacceptable.length === 0, unacceptable.slice(0, 3).map((e) => [e.id, offlineRefusal(e, sample)?.why]));
check('every sample entry is dated on or before the day it was built', sample.evidence.every((e) => e.at <= TODAY));
check('every sample entry is dated after its person joined', sample.evidence.every((e) => e.at >= (sample.people.find((p) => p.id === e.personId)?.joinedAt ?? '')));
check('every skill has at least one sample assessor', SKILLS.every((sk) => sample.people.some((p) => isAssessor(sampleMap, p.id, sk.id))));
const st = (p: string, sk: string) => statusOf(sampleMap, p, sk);
check('the sample shows a suspension', st('p-sample-patrick', 'SK-OD').suspended);
check('the sample shows a lapse', st('p-sample-jp', 'SK-PROBE').lapsed);
check('the sample shows someone ready for a check', readyForCheck(st('p-sample-grace', 'SK-CIP'), SKILL_BY_ID['SK-CIP']));
check('the sample shows a prerequisite holding a skill back', st('p-sample-claudine', 'SK-ISOL').level === 1);
check('the sample lead is a lead and is added by nobody', sample.people.find((p) => p.id === SAMPLE_LEAD)?.role === 'lead' && sample.people[0].addedBy === null);

// ── 3. the store ───────────────────────────────────────────────────────

const s = () => useStore.getState();

async function main() {
  useStore.setState({ serviceUp: false });
  const lead = await s().guildAddPerson({ name: 'Ada Lead', title: 'Lead', role: 'lead', joinedAt: '2026-01-01' });
  check('the first person is added by nobody and becomes who is signing', lead?.addedBy === null && s().guildActingId === lead?.id);
  const tom = await s().guildAddPerson({ name: 'Tom Trainee', title: 'Trainee', role: 'member', joinedAt: '2026-06-01' });
  check('the next is added by whoever is signing', tom?.addedBy === lead?.id);
  const entry = await s().guildRecord({
    personId: tom!.id,
    skillId: 'SK-OD',
    kind: 'knowledge',
    outcome: 'pass',
    at: TODAY,
    observerId: lead!.id,
    source: { kind: 'signoff', ref: 'PR-OD-01' },
    raw: 'Briefed on the SOP',
  });
  check('with the service down a write is kept and marked pending', !!entry && s().guildPending.includes(entry.id) && s().guildPending.length === 3, s().guildPending);
  await s().guildWithdraw(entry!.id, 'Wrong skill');
  check('a withdrawal made offline is kept to send later', s().guildPendingWithdrawals.length === 1 && !!s().guild.evidence.find((e) => e.id === entry!.id)?.withdrawnAt);

  s().guildLoadSample();
  const before = s().guild;
  check('the sample is what Guild shows while it is loaded', guildView(s()) === s().guildSample && actingIdOf(s()) === 'p-sample-eric');
  await s().guildRecord({
    personId: 'p-sample-aline',
    skillId: 'SK-OD',
    kind: 'knowledge',
    outcome: 'pass',
    at: TODAY,
    observerId: 'p-sample-eric',
    source: { kind: 'signoff', ref: 'PR-OD-01' },
    raw: 'Briefed',
  });
  check('a write on the sample touches the sample and nothing else', s().guild === before && s().guildPending.length === 3);
  s().guildClearSample();
  check('clearing the sample brings the ledger back unchanged', guildView(s()) === before && actingIdOf(s()) === lead?.id);

  // The service comes back: people, then entries, then withdrawals; one refused.
  const posted: string[] = [];
  const server: Guild = { version: 1, people: [], evidence: [] };
  (globalThis as any).fetch = async (url: string, init?: { body: string }) => {
    const reply = (status: number, body: unknown) =>
      ({ ok: status === 200, status, json: async () => body }) as Response;
    if (!init?.body) return reply(200, server);
    const body = JSON.parse(init.body);
    posted.push(url.replace('/api/guild/', '') + ':' + (body.id ?? body.evidenceId));
    if (url.endsWith('/people')) {
      if (body.name === 'Tom Trainee') return reply(422, { detail: 'name: refused for the test' });
      server.people.push(body);
      return reply(200, body);
    }
    if (url.endsWith('/evidence')) {
      server.evidence.push({ ...body, recordedAt: '2026-10-09T12:00:00Z' });
      return reply(200, body);
    }
    if (url.endsWith('/withdraw')) return reply(200, server.evidence.find((e) => e.id === body.evidenceId));
    return reply(404, {});
  };
  useStore.setState({ serviceUp: true });
  await s().syncGuild();
  check(
    'sync posts people, then entries, then withdrawals',
    posted.map((x) => x.split(':')[0]).join(' ') === 'people people evidence withdraw',
    posted,
  );
  check('afterwards the service ledger is the truth and nothing is pending', s().guild.people.length === 1 && s().guildPending.length === 0 && s().guildPendingWithdrawals.length === 0);
  check('the refusal is said out loud', s().toasts.some((t) => t.kind === 'error' && /refused 1 Guild change/.test(t.text)));

  s().resetDemo();
  check('a reset clears what was only ever in this browser', s().guildPending.length === 0 && s().guildSample === null);

  console.log(fails ? `\n✗ ${fails} Guild check(s) failed` : '\n✓ Guild levels are computed the way the ladder says.');
  process.exit(fails ? 1 : 0);
}

void main();
