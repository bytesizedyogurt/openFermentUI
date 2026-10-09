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
 *      service refuses;
 *   4. a run (OF-BLD-013 §2): completing a step writes a run alone, a
 *      supervised run or a deviation, once per step, for whoever is the
 *      operator at the time.
 *
 * Parts 5 to 10 follow the same pattern for lessons, the path, what the
 * reviews found, practice, enforce mode, and checks (§5.4): the sample's
 * queue, the bench's rules, what a person may see, and the service's moves.
 *
 * Runs with no service and no network: the service is a stub `fetch` here.
 */
import { useStore, guildView, actingIdOf, checksView } from '../src/store';
import { SKILLS, SKILL_BY_ID } from '../src/data/skills';
import { sampleGuild, SAMPLE_LEAD } from '../src/data/guildSample';
import { offlineRefusal } from '../src/lib/guild';
import { REFRESH_WINDOW, pathOf } from '../src/engine/path';
import {
  DEFAULT_POLICY,
  addDays,
  competenceOf,
  gateFor,
  holdFor,
  policyOf,
  isAssessor,
  localToday,
  readyForCheck,
  statusOf,
  verdictFor,
} from '../src/engine/competence';
import type { Check, CheckResult, Checks, Guild, GuildEvidence, GuildPerson } from '../src/data/types';
import { mayQueue, proposeChecks, shownTo } from '../src/engine/checks';

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

// §3.1 — a lesson passed is knowledge nobody signed.
const lessonPassed = (personId: string, skillId: string, ref: string) =>
  ev(personId, skillId, 'knowledge', '2026-09-03', { observerId: null, source: { kind: 'lesson', ref } });
const K: GuildEvidence[] = [lessonPassed('p-tom', 'SK-DCW', 'l6-1')];
const learnt = level(K, 'p-tom', 'SK-DCW');
check('a lesson passed is Learning, and leaves the training sign-off undone', learnt.level === 1 && !learnt.knowledgeComplete, learnt.level);
K.push(lessonPassed('p-tom', 'SK-OD', 'l6-1'), ev('p-tom', 'SK-FACTOR', 'knowledge', '2026-09-04'));
check('lessons passed never satisfy a prerequisite', level(K, 'p-tom', 'SK-FACTOR').blockedBy.join() === 'SK-OD,SK-DCW');
K.push(ev('p-tom', 'SK-DCW', 'knowledge', '2026-09-05'));
check('the training sign-off beside it is what makes Supervised', level(K, 'p-tom', 'SK-DCW').level === 2);

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
check('every sample entry passes the offline fallback (test_guild replays them through the service)', unacceptable.length === 0, unacceptable.slice(0, 3).map((e) => [e.id, offlineRefusal(e, sample)?.why]));
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

  // With the service down, so the reset's own sync does not race what follows.
  useStore.setState({ serviceUp: false });
  s().resetDemo();
  check('a reset clears what was only ever in this browser', s().guildPending.length === 0 && s().guildSample === null && s().guild.people.length === 0);

  // ── 4. a run writes to the ledger (OF-BLD-013 §2) ───────────────────
  useStore.setState({
    serviceUp: false,
    guild: {
      version: 1,
      people: [person('p-lead', 'lead'), person('p-ann'), person('p-tom')],
      evidence: [
        ev('p-ann', 'SK-OD', 'designation', '2026-02-01'),
        ev('p-ann', 'SK-DCW', 'designation', '2026-02-01'),
        ev('p-tom', 'SK-OD', 'knowledge', '2026-09-01'),
      ],
    },
    guildPending: [],
    guildActingId: 'p-tom',
  });
  const lastEntry = () => s().guild.evidence[s().guild.evidence.length - 1];
  const runId = s().startRun('PR-OD-01', '1.0', 1);
  check('a run starts with whoever is signing as its operator', s().runs[runId].operatorId === 'p-tom');
  const before4 = s().guild.evidence.length;
  s().setRunCosigner(runId, 'o3', 'p-ann');
  await s().recordStepForGuild(runId, 'o3');
  const o3 = s().guild.evidence.slice(before4);
  check('Supervised with a cosigner beside them writes a supervised run', o3.length === 1 && o3[0].kind === 'supervised' && o3[0].observerId === 'p-ann' && o3[0].source.stepId === 'o3', o3.map((e) => [e.kind, e.observerId]));
  const dev4 = await s().recordStepForGuild(runId, 'o4');
  check('Supervised with nobody beside them writes a deviation', dev4 === 1 && lastEntry()?.kind === 'deviation' && lastEntry()?.observerId === null);
  const dev1 = await s().recordStepForGuild(runId, 'o1');
  check('below Supervised writes a deviation', dev1 === 1 && /below Supervised/.test(lastEntry()?.raw ?? ''));
  s().setRunCosigner(runId, 'o2', 'p-ann');
  const dev2 = await s().recordStepForGuild(runId, 'o2');
  check('below Supervised is a deviation even with a cosigner beside them', dev2 === 1 && lastEntry()?.kind === 'deviation');
  const again = s().guild.evidence.length;
  await s().recordStepForGuild(runId, 'o3');
  check('completing a step twice writes once', s().guild.evidence.length === again);
  s().setRunOperator(runId, 'p-ann');
  await s().recordStepForGuild(runId, 'o5');
  check('a handover changes who the next step is written for', lastEntry()?.personId === 'p-ann' && lastEntry()?.kind === 'independent');
  const untagged = s().guild.evidence.length;
  const seed = s().startRun('PR-SEED-01', '1.0', 1);
  await s().recordStepForGuild(seed, 's6');
  check('a step that needs no skill writes nothing', s().guild.evidence.length === untagged);
  check('every run entry is one the service would accept, as far as the browser can tell', s().guild.evidence.filter((e) => e.source.kind === 'deposition').every((e) => offlineRefusal(e, s().guild) === null));

  // ── 5. a lesson passed writes to the ledger (OF-BLD-013 §3.2) ───────
  useStore.setState({
    serviceUp: false,
    guild: { version: 1, people: [person('p-lead', 'lead'), person('p-ann'), person('p-tom'), person('p-qa', 'auditor')], evidence: [] },
    guildPending: [],
    guildActingId: 'p-tom',
    learnProgress: {},
  });
  const bench = s().modules.flatMap((m) => m.lessons).find((l) => (l.skills ?? []).length >= 2);
  const plain = s().modules.flatMap((m) => m.lessons).find((l) => (l.skills ?? []).length === 0);
  check('the seed has a lesson that counts toward skills, and one that counts toward none', !!bench && !!plain);
  const wrote = await s().recordLessonForGuild(bench!.id);
  const lessonEntries = () => s().guild.evidence.filter((e) => e.source.kind === 'lesson');
  check(
    'a lesson passed writes one knowledge entry per skill, for whoever is learning, with no observer',
    wrote?.personId === 'p-tom' &&
      wrote.skills.join() === bench!.skills!.join() &&
      lessonEntries().length === bench!.skills!.length &&
      lessonEntries().every((e) => e.kind === 'knowledge' && e.personId === 'p-tom' && e.observerId === null && e.source.ref === bench!.id),
    lessonEntries().map((e) => [e.skillId, e.kind, e.observerId]),
  );
  check('the entries wait for the service like any other write', lessonEntries().every((e) => s().guildPending.includes(e.id)));
  const after5 = competenceOf(s().guild.evidence, s().guild.people, SKILL_BY_ID, TODAY);
  check('and put the learner at Learning on each skill, no further', bench!.skills!.every((sk) => statusOf(after5, 'p-tom', sk).level === 1));
  const both = await Promise.all([s().recordLessonForGuild(bench!.id), s().recordLessonForGuild(bench!.id)]);
  check('passing it again writes nothing, however the calls overlap', lessonEntries().length === bench!.skills!.length && both.every((r) => r?.skills.length === 0));
  check('a lesson that counts toward no skill writes nothing', (await s().recordLessonForGuild(plain!.id)) === null);
  s().guildSetActing('p-qa');
  check('an auditor learning writes nothing', (await s().recordLessonForGuild(bench!.id)) === null);
  s().guildSetActing(null);
  check('nobody chosen writes nothing', (await s().recordLessonForGuild(bench!.id)) === null);
  s().guildSetActing('p-ann');
  await s().recordLessonForGuild(bench!.id);
  check('the next learner gets entries of their own', lessonEntries().filter((e) => e.personId === 'p-ann').length === bench!.skills!.length);
  check('every lesson entry is one the service would accept, as far as the browser can tell', lessonEntries().every((e) => offlineRefusal(e, s().guild) === null));
  s().guildLoadSample();
  const real = s().guild;
  await s().recordLessonForGuild(bench!.id);
  check('with the sample shown, a lesson writes to the sample alone', s().guild === real && s().guildSample!.evidence.some((e) => e.source.kind === 'lesson' && e.personId === 'p-sample-eric'));
  s().guildClearSample();
  s().completeLesson(bench!.id);
  check('completing a lesson marks it finished in this browser', s().learnProgress[bench!.id] === true);

  // ── 6. a person's path (OF-BLD-013 §3.3) ────────────────────────────
  const PATH_PEOPLE = [person('p-lead', 'lead'), person('p-ann'), person('p-tom')];
  const lessonsFor = { 'SK-OD': [{ id: 'l-a' }, { id: 'l-b' }] } as Record<string, { id: string }[]>;
  const stepFor = (entries: GuildEvidence[], skillId: string, extra: { soon?: string[]; today?: string } = {}) => {
    const today = extra.today ?? TODAY;
    const passedLessons = new Set(entries.filter((e) => e.source.kind === 'lesson').map((e) => `${e.skillId}|${e.source.ref}`));
    const items = pathOf({
      personId: 'p-tom',
      skills: SKILLS,
      status: competenceOf(entries, PATH_PEOPLE, SKILLS_MAP, today),
      lessonsFor,
      passed: (sk, l) => passedLessons.has(`${sk}|${l}`),
      soon: new Set(extra.soon ?? []),
      today,
    });
    return { item: items.find((i) => i.skill.id === skillId)!, items };
  };
  const P: GuildEvidence[] = [];
  let at = stepFor(P, 'SK-OD').item;
  check('a skill with lessons starts at its first lesson', at.section === 'next' && at.step.kind === 'lesson' && at.step.lessonId === 'l-a');
  P.push(ev('p-tom', 'SK-OD', 'knowledge', '2026-09-01', { observerId: null, source: { kind: 'lesson', ref: 'l-a' } }));
  at = stepFor(P, 'SK-OD').item;
  check('one lesson passed points at the next, and counts what is passed', at.step.kind === 'lesson' && at.step.lessonId === 'l-b' && at.step.passed === 1 && at.step.total === 2);
  P.push(ev('p-tom', 'SK-OD', 'knowledge', '2026-09-01', { observerId: null, source: { kind: 'lesson', ref: 'l-b' } }));
  at = stepFor(P, 'SK-OD').item;
  check('every lesson passed sends the skill to the bench for a training sign-off', at.section === 'bench' && at.step.kind === 'training-signoff' && at.step.lessons === 2);
  P.push(ev('p-tom', 'SK-OD', 'knowledge', '2026-09-02'), ev('p-tom', 'SK-OD', 'supervised', '2026-09-03'));
  at = stepFor(P, 'SK-OD').item;
  check('signed off, the next step is cosigned runs, counted against what the skill asks', at.section === 'next' && at.step.kind === 'cosigned-runs' && at.step.done === 1 && at.step.needed === 3);
  P.push(ev('p-tom', 'SK-OD', 'supervised', '2026-09-04'), ev('p-tom', 'SK-OD', 'supervised', '2026-09-05'));
  at = stepFor(P, 'SK-OD').item;
  check('with the runs done it goes to the bench for a witnessed check', at.section === 'bench' && at.step.kind === 'witnessed-check');
  P.push(ev('p-tom', 'SK-OD', 'witnessed', '2026-09-20'));
  check('qualified and current, it is held', stepFor(P, 'SK-OD').item.section === 'held');
  at = stepFor(P, 'SK-OD', { today: addDays('2026-09-20', 60 - REFRESH_WINDOW) }).item;
  check('inside the refresh window it is due for refresh', at.section === 'refresh' && at.step.kind === 'lapsing');
  check('the day before the window, it is still held', stepFor(P, 'SK-OD', { today: addDays('2026-09-20', 60 - REFRESH_WINDOW - 1) }).item.section === 'held');
  check('lapsed, it is due for refresh and says so', stepFor(P, 'SK-OD', { today: addDays('2026-09-20', 61) }).item.step.kind === 'lapsed');
  const failed = [...P, ev('p-tom', 'SK-OD', 'witnessed', '2026-10-01', { outcome: 'fail' })];
  check('suspended, it is due for refresh and says so', stepFor(failed, 'SK-OD').item.step.kind === 'suspended');
  at = stepFor([], 'SK-FACTOR').item;
  check('a prerequisite below Supervised makes it wait, and names the prerequisite', at.section === 'waiting' && at.step.kind === 'waiting' && at.step.on.join() === 'SK-OD,SK-DCW');
  at = stepFor([], 'SK-CAUSTIC').item;
  check('with no lesson to take, the next step is a training sign-off', at.section === 'next' && at.step.kind === 'training-signoff' && at.step.lessons === 0);
  const ordered = stepFor([], 'SK-OD', { soon: ['SK-LOG'] }).items.filter((i) => i.section === 'next');
  check('what a run in progress needs comes first', ordered[0]?.skill.id === 'SK-LOG', ordered.map((i) => i.skill.id).slice(0, 3));
  const ranked = stepFor([], 'SK-OD').items.filter((i) => i.section === 'next');
  const firstRoutine = ranked.findIndex((i) => i.skill.criticality !== 'critical');
  check('then critical skills before the rest', firstRoutine > 0 && ranked.slice(firstRoutine).every((i) => i.skill.criticality !== 'critical'));

  // ── 7. what the review found (OF-BLD-013 §3.4) ─────────────────────
  const R_PEOPLE = [person('p-lead', 'lead'), person('p-ann'), person('p-tom'), person('p-qa', 'auditor')];
  const reset7 = (extra: Partial<Parameters<typeof useStore.setState>[0]> = {}) =>
    useStore.setState({
      serviceUp: false,
      guildSample: null,
      guild: { version: 1, people: R_PEOPLE, evidence: [ev('p-ann', 'SK-OD', 'designation', '2026-02-01'), ev('p-tom', 'SK-OD', 'knowledge', '2026-09-01')] },
      guildPending: [],
      guildPendingWithdrawals: [],
      guildActingId: 'p-ann',
      ...extra,
    } as never);
  const server7: Guild = { version: 1, people: [...R_PEOPLE], evidence: [] };
  const posts7: string[] = [];
  let duringSync: (() => void) | null = null;
  (globalThis as any).fetch = async (url: string, init?: { body: string }) => {
    const reply = (status: number, body: unknown) => ({ ok: status === 200, status, json: async () => body }) as Response;
    if (!init?.body) return reply(200, server7);
    const body = JSON.parse(init.body);
    posts7.push(`${url.replace('/api/guild/', '')}:${body.kind ?? ''}:${body.id ?? body.evidenceId}`);
    if (duringSync) {
      duringSync();
      duringSync = null;
    }
    if (url.endsWith('/evidence')) {
      if (body.kind === 'independent' || (body.kind === 'supervised' && body.source?.kind === 'deposition'))
        return reply(422, { detail: 'authority: the service knows of a failed check this browser has not seen' });
      const kept = { ...body, recordedAt: '2026-10-09T12:00:00Z' };
      server7.evidence.push(kept);
      return reply(200, kept);
    }
    if (url.endsWith('/withdraw')) return reply(200, server7.evidence.find((e) => e.id === body.evidenceId));
    return reply(200, body);
  };

  reset7({ serviceUp: true });
  const r7 = s().startRun('PR-OD-01', '1.0', 1);
  check('a run started by an assessor names them', s().runs[r7].operatorId === 'p-ann');
  const dev7 = await s().recordStepForGuild(r7, 'o3');
  const o3entries = s().guild.evidence.filter((e) => e.source.stepId === 'o3');
  check(
    'a run alone the service refuses is kept as a deviation, so the step leaves its mark',
    dev7 === 1 && o3entries.length === 1 && o3entries[0].kind === 'deviation' && /refused it as a run alone/.test(o3entries[0].raw),
    o3entries.map((e) => [e.kind, e.raw]),
  );

  reset7();
  const r7b = s().startRun('PR-OD-01', '1.0', 1);
  useStore.setState((x) => ({ guild: { ...x.guild, people: x.guild.people.map((p) => (p.id === 'p-ann' ? { ...p, active: false } : p)) } }));
  const before7 = s().guild.evidence.length;
  check('an operator who is no longer active writes nothing, as the gate says', (await s().recordStepForGuild(r7b, 'o3')) === 0 && s().guild.evidence.length === before7);

  reset7({ guildActingId: 'p-tom' });
  const r7c = s().startRun('PR-OD-01', '1.0', 1);
  s().setRunCosigner(r7c, 'o3', 'p-ann');
  useStore.setState((x) => ({ guild: { ...x.guild, people: x.guild.people.map((p) => (p.id === 'p-ann' ? { ...p, active: false } : p)) } }));
  await s().recordStepForGuild(r7c, 'o3');
  check('a cosigner who is no longer active cosigns nothing: the step is a deviation', lastEntry()?.kind === 'deviation' && lastEntry()?.observerId === null);

  // Offline, then the service answers.
  reset7({ guildActingId: 'p-ann' });
  const r7d = s().startRun('PR-OD-01', '1.0', 1);
  await s().recordStepForGuild(r7d, 'o4');
  const offlineRun = lastEntry()!;
  const already = await s().guildRecord({ personId: 'p-tom', skillId: 'SK-OD', kind: 'knowledge', outcome: 'pass', at: TODAY, observerId: 'p-ann', source: { kind: 'signoff', ref: 'PR-OD-01' }, raw: 'Briefed' });
  server7.evidence.push({ ...already!, recordedAt: '2026-10-09T10:00:00Z' });
  const queued = await s().guildRecord({ personId: 'p-tom', skillId: 'SK-OD', kind: 'supervised', outcome: 'pass', at: TODAY, observerId: 'p-ann', source: { kind: 'signoff', ref: 'PR-OD-01' }, raw: 'Beside them' });
  useStore.setState({ serviceUp: true });
  await s().guildWithdraw(queued!.id, 'Wrong day');
  check('withdrawing an entry the service does not hold yet waits for it to be sent', s().guildPendingWithdrawals.some((w) => w.evidenceId === queued!.id) && !posts7.some((p) => p.startsWith('withdraw')));
  const meanwhile: GuildEvidence = { ...ev('p-tom', 'SK-DCW', 'knowledge', TODAY, { observerId: null, source: { kind: 'lesson', ref: 'l6-1' } }), id: 'e-made-meanwhile' };
  duringSync = () => useStore.setState((x) => ({ guild: { ...x.guild, evidence: [...x.guild.evidence, meanwhile] }, guildPending: [...x.guildPending, meanwhile.id] }));
  posts7.length = 0;
  await s().syncGuild();
  check('an entry the service already holds is not sent again', !posts7.some((p) => p.endsWith(`:${already!.id}`)), posts7);
  check(
    'a run alone made offline and refused at sync is sent again as a deviation',
    posts7.some((p) => p.endsWith(`:independent:${offlineRun.id}`)) && server7.evidence.some((e) => e.kind === 'deviation' && e.source.stepId === 'o4'),
    posts7,
  );
  check('the withdrawal goes after the entry it names', posts7.findIndex((p) => p.endsWith(`:${queued!.id}`)) < posts7.findIndex((p) => p.startsWith('withdraw')));
  check(
    'an entry made while the sync ran is kept, and still owed to the service',
    s().guild.evidence.some((e) => e.id === meanwhile.id) && s().guildPending.includes(meanwhile.id),
    s().guildPending,
  );

  // The sample stays out of the Durable tier.
  reset7();
  s().guildLoadSample();
  const opened = s().openDeposition(s().runbooks[0].id, 'PR-OD-01', 1)!;
  check('a deposition opened while the sample is shown names no sample person', s().depositions.find((d) => d.id === opened.depositionId)?.operatorId === null);
  s().setRunOperator(opened.runId, 'p-sample-patrick');
  check('nor does a handover to one', s().depositions.find((d) => d.id === opened.depositionId)?.operatorId === null && s().runs[opened.runId].operatorId === 'p-sample-patrick');
  s().guildClearSample();

  // ── 8. practice (OF-BLD-013 §4.3) ───────────────────────────────────
  const closedSession = (personId: string | null, evidenceId: string | null) => ({
    id: 'pt-check-1',
    scenarioId: 'ps-check-1',
    skillId: 'SK-OD',
    personId,
    turns: [],
    observed: [{ text: 'Chose to dilute, unsure why spent medium.', steps: [{ protocolId: 'PR-OD-01', stepId: 'o4' }] }],
    startedAt: `${TODAY}T09:00:00Z`,
    closedAt: `${TODAY}T09:20:00Z`,
    evidenceId,
    usage: { inputTokens: 0, outputTokens: 0, costUsd: 0, models: [] },
  });
  reset7({ guildActingId: 'p-tom' });
  check('a learner on the ledger is named to the service', s().practiceLearner() === 'p-tom');
  s().guildSetActing('p-qa');
  check('an auditor is named as nobody', s().practiceLearner() === null);
  s().guildLoadSample();
  s().guildSetActing('p-sample-olivier');
  check('a sample person is never named to the service', s().practiceLearner() === null);
  const realBefore = s().guild;
  await s().practiceClosed(closedSession(null, null), 'A reading above the range');
  const practised = s().guildSample!.evidence.filter((e) => e.kind === 'scenario');
  check(
    'with the sample shown, a closed session goes on the sample learner, in the sample alone',
    practised.length === 1 && practised[0].personId === 'p-sample-olivier' && practised[0].source.ref === 'pt-check-1' && practised[0].observerId === null && s().guild === realBefore,
  );
  check('and the offline fallback would take it', offlineRefusal(practised[0], s().guildSample!) === null);
  check('the offline fallback refuses practice that names an observer', offlineRefusal({ ...practised[0], observerId: 'p-sample-eric' }, s().guildSample!)?.rule === 'observer');
  check('and a second entry on the same session', offlineRefusal({ ...practised[0], id: 'e-second-on-session' }, s().guildSample!)?.rule === 'duplicate');
  const sampleBefore = s().guildSample!.evidence.length;
  await s().practiceClosed({ ...closedSession('p-tom', null), id: 'pt-check-3' }, 'A reading above the range');
  check('a real person\u2019s session closing while the sample is shown credits nobody in the sample', s().guildSample!.evidence.length === sampleBefore);
  s().guildClearSample();
  reset7({ guildActingId: 'p-tom', serviceUp: true });
  server7.evidence.push({ ...ev('p-tom', 'SK-OD', 'scenario', TODAY, { observerId: null, source: { kind: 'scenario', ref: 'pt-check-2' } }), id: 'e-practice-from-service', recordedAt: `${TODAY}T09:21:00Z` });
  await s().practiceClosed({ ...closedSession('p-tom', 'e-practice-from-service'), id: 'pt-check-2' }, 'A reading above the range');
  check('a session the service put on the ledger is fetched back', s().guild.evidence.some((e) => e.id === 'e-practice-from-service'));

  // ── 9. enforce mode (OF-BLD-013 §5.1) ───────────────────────────────
  const CIP = SKILL_BY_ID['SK-CIP'];
  check('SK-CIP is critical and SK-OD routine, as this part assumes', CIP.criticality === 'critical' && SKILL_BY_ID['SK-OD'].criticality === 'routine');
  check('a ledger with no policy reads with the default: routine advised, critical enforced', JSON.stringify(policyOf({})) === JSON.stringify(DEFAULT_POLICY) && DEFAULT_POLICY.criticalGate === 'enforce' && DEFAULT_POLICY.routineGate === 'advise');
  const H: GuildEvidence[] = [
    ev('p-ann', 'SK-CIP', 'designation', '2026-02-01'),
    ev('p-ann', 'SK-CAUSTIC', 'designation', '2026-02-01'),
    ev('p-tom', 'SK-CAUSTIC', 'knowledge', '2026-08-01'),
    ev('p-tom', 'SK-CIP', 'knowledge', '2026-08-01'),
  ];
  const hmap = (entries: GuildEvidence[], today = TODAY) => competenceOf(entries, PEOPLE, SKILLS_MAP, today);
  const cipStep = { skills: ['SK-CIP'] };
  const odStep = { skills: ['SK-OD'] };
  const hold = (st: { skills: string[] }, op: string | null, co: string | null, entries = H, policy = DEFAULT_POLICY, today = TODAY) =>
    holdFor(st, op, co, hmap(entries, today), SKILLS_MAP, policy, true);
  check('a Supervised operator on an enforced skill is held for a cosigner', hold(cipStep, 'p-tom', null)?.kind === 'cosigner');
  check('a cosigner who holds it releases the step', hold(cipStep, 'p-tom', 'p-ann') === null);
  check('a cosigner who does not hold it releases nothing', hold(cipStep, 'p-tom', 'p-lead')?.kind === 'cosigner');
  check('nor does naming the operator as their own cosigner', hold(cipStep, 'p-tom', 'p-tom')?.kind === 'cosigner');
  const lapsedCIP: GuildEvidence[] = [
    ...H,
    ...[1, 2, 3].map((k) => ev('p-tom', 'SK-CIP', 'supervised', `2026-03-0${k}`)),
    ev('p-tom', 'SK-CIP', 'witnessed', '2026-03-10'),
  ];
  const tomCIP = statusOf(hmap(lapsedCIP), 'p-tom', 'SK-CIP');
  check('the fixture makes a lapsed Qualified operator', tomCIP.level === 3 && tomCIP.lapsed, [tomCIP.level, tomCIP.lapsesAt]);
  check('in enforce mode a lapsed skill holds a step until a cosigner is recorded', hold(cipStep, 'p-tom', null, lapsedCIP)?.kind === 'cosigner' && hold(cipStep, 'p-tom', 'p-ann', lapsedCIP) === null);
  check('below Supervised waits for someone qualified, cosigner or not', hold(cipStep, 'p-lead', 'p-ann')?.kind === 'qualified');
  check('nobody named as operator is held for one', hold(cipStep, null, null)?.kind === 'operator');
  check('a routine skill in advise mode is never held', hold(odStep, null, null) === null && hold(odStep, 'p-lead', null) === null);
  check('with everything advised nothing is held', hold(cipStep, 'p-lead', null, H, { ...DEFAULT_POLICY, criticalGate: 'advise' }) === null);
  check('routine set to enforce holds a routine skill', hold(odStep, 'p-lead', null, H, { ...DEFAULT_POLICY, routineGate: 'enforce' })?.kind === 'qualified');
  check('with nobody on the ledger nothing is held', holdFor(cipStep, null, null, hmap(H), SKILLS_MAP, DEFAULT_POLICY, false) === null);
  reset7({ guildActingId: 'p-ann' });
  check('only the lead sets the policy', (await s().guildSetPolicy({ routineGate: 'enforce', criticalGate: 'enforce', checksPerQuarter: 2 })) === false);
  s().guildLoadSample();
  s().guildSetActing(SAMPLE_LEAD);
  const realPolicy = s().guild.policy;
  check(
    'with the sample shown, the lead sets the sample\u2019s policy alone',
    (await s().guildSetPolicy({ routineGate: 'enforce', criticalGate: 'advise', checksPerQuarter: 3 })) === true &&
      s().guildSample!.policy?.checksPerQuarter === 3 &&
      s().guild.policy === realPolicy,
  );
  s().guildClearSample();

  const audited = { ...ev('p-tom', 'SK-OD', 'witnessed', TODAY), observerId: 'p-qa' };
  check('the offline fallback refuses an auditor as observer', offlineRefusal(audited, { version: 1, people: R_PEOPLE, evidence: [] })?.rule === 'authority');

  // ── 10. checks: the queue and the bench (OF-BLD-013 §5.4) ───────────
  //
  // With the sample shown, the queue is the ranking run here on the sample,
  // every move happens in memory under the rules a screen needs, a run at the
  // bench writes witnessed entries with the check as their source, and
  // nothing reaches the service. With the service up, the moves are posts
  // and a person asking for their own check learns nothing about the queue.
  const posts10: string[] = [];
  (globalThis as any).fetch = async (url: string, init?: { body: string }) => {
    posts10.push(url);
    return { ok: false, status: 503, json: async () => ({}) } as Response;
  };
  reset7({ serviceUp: true });
  s().guildLoadSample();
  const sample10 = s().guildSample!;
  const queue10 = s().guildSampleChecks ?? [];
  const expected10 = proposeChecks(sample10, SKILLS_MAP, localToday());
  check(
    'the sample\u2019s queue is the ranking run on the sample when it loads',
    queue10.length > 0 &&
      queue10.length === expected10.length &&
      queue10.every((c, i) => c.state === 'proposed' && c.personId === expected10[i].personId && c.skillIds.join() === expected10[i].skillIds.join()),
    queue10.map((c) => c.personId),
  );
  check('checksView shows the sample\u2019s checks while it is shown', checksView(s()) === s().guildSampleChecks);
  const pat = queue10.find((c) => c.personId === 'p-sample-patrick')!;
  check('the sample proposes a check for its suspended trainee', !!pat && pat.reasons.some((r) => r.kind === 'suspended'));
  const allCalls = (c: Check, meets = (_k: string, _i: number) => true): CheckResult[] =>
    c.skillIds.flatMap((k) => SKILL_BY_ID[k].mastery.map((_, i) => ({ skillId: k, criterion: i, meets: meets(k, i), note: '' })));
  const words = (c: Check, text = 'Watched every step at the bench') => c.skillIds.map((k) => ({ skillId: k, text }));

  s().guildSetActing('p-sample-patrick');
  check('a check is never run by the person it names', (await s().checksRecord(pat.id, allCalls(pat), words(pat), localToday())) !== null);
  check('and never shows to them in the queue until it is run', !shownTo(checksView(s()), 'p-sample-patrick').some((c) => c.id === pat.id));
  s().guildSetActing('p-sample-grace');
  check('nor run by someone who is no assessor on its skills', (await s().checksRecord(pat.id, allCalls(pat), words(pat), localToday())) !== null);
  check('nor scheduled by them', (await s().checksSchedule(pat.id, addDays(localToday(), 2))) !== null);
  s().guildSetActing('p-sample-eric');
  check(
    'every criterion is called before a check is signed',
    (await s().checksRecord(pat.id, allCalls(pat).slice(1), words(pat), localToday())) !== null,
  );
  check('and every skill has the assessor\u2019s words', (await s().checksRecord(pat.id, allCalls(pat), words(pat, ' '), localToday())) !== null);
  check(
    'an assessor on every skill schedules it',
    (await s().checksSchedule(pat.id, addDays(localToday(), 2))) === null &&
      s().guildSampleChecks!.find((c) => c.id === pat.id)?.state === 'scheduled' &&
      s().guildSampleChecks!.find((c) => c.id === pat.id)?.assessorId === 'p-sample-eric',
  );
  const failOD = (k: string, i: number) => !(k === 'SK-OD' && i === 0);
  const before10 = s().guild;
  check('and runs it', (await s().checksRecord(pat.id, allCalls(pat, failOD), words(pat), localToday())) === null);
  const wrote10 = s().guildSample!.evidence.filter((e) => e.source.kind === 'check' && e.source.ref === pat.id);
  check(
    'a run writes one witnessed entry per skill, signed by the assessor, with the check as its source',
    wrote10.length === pat.skillIds.length && wrote10.every((e) => e.kind === 'witnessed' && e.observerId === 'p-sample-eric' && e.raw === 'Watched every step at the bench'),
    wrote10.map((e) => [e.skillId, e.outcome]),
  );
  check(
    'a skill passes only with every criterion met',
    wrote10.find((e) => e.skillId === 'SK-OD')?.outcome === 'fail' && wrote10.filter((e) => e.skillId !== 'SK-OD').every((e) => e.outcome === 'pass'),
  );
  const done10 = s().guildSampleChecks!.find((c) => c.id === pat.id)!;
  check('the check is done, with its calls and its entries', done10.state === 'done' && done10.results.length === allCalls(pat).length && done10.evidenceIds.length === wrote10.length);
  const after10 = competenceOf(s().guildSample!.evidence, s().guildSample!.people, SKILLS_MAP, localToday());
  const ready10 = pat.reasons.find((r) => r.kind === 'ready');
  check(
    'the Matrix reads it at once: a ready skill is Qualified, a failed one stays suspended',
    statusOf(after10, 'p-sample-patrick', 'SK-OD').suspended && (!ready10 || statusOf(after10, 'p-sample-patrick', ready10.skillId).level === 3),
  );
  check('once run, the person sees it', shownTo(checksView(s()), 'p-sample-patrick').some((c) => c.id === pat.id));
  check('a check that is done takes no second run', (await s().checksRecord(pat.id, allCalls(pat), words(pat), localToday())) !== null);
  check('the real ledger is untouched by the sample\u2019s check', s().guild === before10);

  const other = s().guildSampleChecks!.find((c) => c.state === 'proposed')!;
  check('a dismissal says why', (await s().checksDismiss(other.id, ' ')) !== null);
  s().guildSetActing(SAMPLE_LEAD);
  check(
    'the lead dismisses with a reason, kept on the check',
    (await s().checksDismiss(other.id, 'Seen at the bench yesterday')) === null &&
      s().guildSampleChecks!.find((c) => c.id === other.id)?.dismissReason === 'Seen at the bench yesterday',
  );
  check('the lead may not schedule a check on skills they do not assess', (await s().checksSchedule(s().guildSampleChecks!.find((c) => c.state === 'proposed')!.id, localToday())) !== null);

  const openFor = (pid: string) => s().guildSampleChecks!.filter((c) => c.personId === pid && (c.state === 'proposed' || c.state === 'scheduled'));
  const inQueue = s().guildSampleChecks!.find((c) => c.state === 'proposed')!;
  s().guildSetActing(inQueue.personId);
  const n10 = s().guildSampleChecks!.length;
  check(
    'asking for your own check on a skill already in the queue says the same as a fresh ask, and adds nothing',
    (await s().checksRequest(inQueue.personId, [inQueue.skillIds[0]])) === null && s().guildSampleChecks!.length === n10,
  );
  s().guildSetActing('p-sample-eric');
  check('an assessor asking for one already there is told so', (await s().checksRequest(inQueue.personId, [inQueue.skillIds[0]])) !== null);
  const fresh10 = SKILLS.find((k) => !openFor('p-sample-olivier').some((c) => c.skillIds.includes(k.id)))!.id;
  check(
    'a fresh ask lands in the queue with its reason written',
    (await s().checksRequest('p-sample-olivier', [fresh10])) === null &&
      s().guildSampleChecks!.some((c) => c.personId === 'p-sample-olivier' && c.reasons.some((r) => r.kind === 'requested' && /Eric Habimana/.test(r.text))),
  );
  const proposed10 = await s().checksPropose();
  const covered10 = s().guildSampleChecks!.filter((c) => c.state === 'proposed' || c.state === 'scheduled').flatMap((c) => c.skillIds.map((k) => `${c.personId}|${k}`));
  check('proposing again never repeats a pair an open check covers', 'made' in proposed10 && new Set(covered10).size === covered10.length, covered10);
  check(
    'a brief is the service\u2019s to draft, and the sample stays here',
    (await s().checksBrief(s().guildSampleChecks!.find((c) => c.state === 'proposed')!.id)) !== null,
  );
  s().guildClearSample();
  check('hiding the sample takes its checks with it', s().guildSampleChecks === null && checksView(s()).length === 0);
  check('nothing about the sample reached the service', posts10.filter((u) => u.startsWith('/api/guild/checks')).length === 0, posts10);

  // The queue's visibility, read the same way by the tab strip and the page.
  const vmap = competenceOf([ev('p-ann', 'SK-OD', 'designation', '2026-02-01')], R_PEOPLE, SKILLS_MAP, TODAY);
  check(
    'the queue is for the lead and assessors, never a member who assesses nothing, an auditor or nobody',
    mayQueue(R_PEOPLE[0], vmap) && mayQueue(R_PEOPLE[1], vmap) && !mayQueue(R_PEOPLE[2], vmap) && !mayQueue(R_PEOPLE[3], vmap) && !mayQueue(null, vmap),
  );

  // With the service up: the moves are posts, and the person asking learns nothing.
  const asked10: { url: string; body: any }[] = [];
  const served10: Checks = { version: 1, checks: [] };
  (globalThis as any).fetch = async (url: string, init?: { body: string }) => {
    const reply = (status: number, body: unknown) => ({ ok: status === 200, status, json: async () => body }) as Response;
    if (url === '/api/guild/checks' && !init?.body) return reply(200, served10);
    if (!init?.body) return reply(200, server7);
    const body = JSON.parse(init.body);
    asked10.push({ url, body });
    if (url.endsWith('/request')) return reply(422, { detail: 'duplicate: an open check already covers these skills for this person' });
    return reply(404, {});
  };
  reset7({ serviceUp: true, guildActingId: 'p-tom', checks: null });
  check('asking for your own check while one is open says only that it was asked', (await s().checksRequest('p-tom', ['SK-OD'])) === null);
  check('the ask went to the service in the asker\u2019s name', asked10.length === 1 && asked10[0].url === '/api/guild/checks/request' && asked10[0].body.by === 'p-tom');
  s().guildSetActing('p-ann');
  const told = await s().checksRequest('p-tom', ['SK-OD']);
  check('an assessor asking is told the service\u2019s rule and reason', told !== null && /duplicate/.test(told), told);
  await s().loadChecks();
  check('the queue is fetched from the service', s().checks === served10 || JSON.stringify(s().checks) === JSON.stringify(served10));
  (globalThis as any).fetch = async () => ({ ok: true, status: 200, json: async () => ({ version: 1, people: [], evidence: [] }) }) as Response;
  await s().loadChecks();
  check('an answer with no list of checks is no answer about checks', s().checks === null);

  console.log(fails ? `\n✗ ${fails} Guild check(s) failed` : '\n✓ Guild levels are computed the way the ladder says.');
  process.exit(fails ? 1 : 0);
}

void main();
