/**
 * Prediction-lock contract (OF-BLD-006 §3.3).
 *
 * §3.3 requires immutability after locking "enforced in the store, not by
 * convention". A convention is a comment; this is the test that says whether
 * the code actually does it. It runs against the real seeded store, not a
 * fixture, so a regression in freezeLocked or in the guarded actions fails the
 * build rather than being discovered by a prediction that quietly drifted
 * toward a result somebody had already seen.
 *
 *   pnpm check:lock
 */
import { useStore } from '../src/store';
import { readFileSync } from 'node:fs';
import { lockIntact, runbookLockHash } from '../src/engine/lock';
import { RUNBOOKS } from '../src/data/runbooks';

let fails = 0;
const check = (l: string, ok: boolean, x = '') => {
  console.log((ok ? '✓' : '✗') + ' ' + l + (x ? '  ' + x : ''));
  if (!ok) fails++;
};

const s = () => useStore.getState();
const locked = s().runbooks.find((r) => r.lockedAt)!;
const open = s().runbooks.find((r) => !r.lockedAt)!;
check('seed has a locked and an unlocked runbook', !!locked && !!open, `${locked.id} / ${open.id}`);

// §3.3 — enforcement at the object level, not by agreement.
check('locked predictions array is frozen', Object.isFrozen(locked.predictions));
check('locked schema array is frozen', Object.isFrozen(locked.measurementSchema));
check('each locked prediction object is frozen', locked.predictions.every(Object.isFrozen));

let threw = false;
try { (locked.predictions as any).push({ id: 'x' }); } catch { threw = true; }
check('pushing onto a locked predictions array throws', threw);

threw = false;
try { (locked.predictions[0] as any).value = 999; } catch { threw = true; }
check('assigning to a locked prediction throws', threw);

check('unlocked predictions are NOT frozen', !Object.isFrozen(open.predictions));

// The guarded action refuses on locked and succeeds on unlocked.
check('revise refused on a locked runbook',
  s().reviseRunbookPrediction(locked.id, locked.predictions[0].id, 1) === false);
check('locked value unchanged after refusal',
  s().runbooks.find((r) => r.id === locked.id)!.predictions[0].value === locked.predictions[0].value);
check('revise allowed on an unlocked runbook',
  s().reviseRunbookPrediction(open.id, open.predictions[0].id, 42) === true);
check('unlocked value did change',
  s().runbooks.find((r) => r.id === open.id)!.predictions[0].value === 42);

// Locking the edited one seals the edit, and the hash covers it.
s().lockRunbook(open.id);
const nowLocked = s().runbooks.find((r) => r.id === open.id)!;
check('lock set a timestamp and hash', !!nowLocked.lockedAt && !!nowLocked.lockHash);
check('hash matches the content it froze', lockIntact(nowLocked));
check('newly locked content is frozen', Object.isFrozen(nowLocked.predictions));
check('revise now refused', s().reviseRunbookPrediction(open.id, open.predictions[0].id, 7) === false);

// Supersede is the way through, and leaves the original alone.
const revId = s().supersedeRunbook(open.id)!;
const rev = s().runbooks.find((r) => r.id === revId)!;
check('supersede produced an unlocked revision', !!rev && rev.lockedAt === null);
check('revision is editable', s().reviseRunbookPrediction(revId, rev.predictions[0].id, 5) === true);
check('original still locked and unchanged',
  s().runbooks.find((r) => r.id === open.id)!.lockedAt !== null &&
  s().runbooks.find((r) => r.id === open.id)!.predictions[0].value === 42);

// OF-BLD-014 §9.1 — every locked seed runbook still hashes to the digest it
// had before canonical() learned the interval fields, and those fields are
// covered once a prediction carries them.
{
  const digests = JSON.parse(readFileSync('scripts/fixtures/seed-lock-digests.json', 'utf8')) as Record<string, string>;
  const lockedSeed = RUNBOOKS.filter((r) => r.lockedAt);
  check('the fixture names every locked seed runbook', lockedSeed.length === 8 && lockedSeed.every((r) => r.id in digests), String(lockedSeed.length));
  for (const r of lockedSeed)
    check(`${r.id} hashes as it did before §9.1`, runbookLockHash(r.predictions, r.measurementSchema) === digests[r.id]);
  const rb = lockedSeed[0];
  const asInterval = rb.predictions.map((p, i) => (i === 0 ? { ...p, kind: 'interval' as const, interval: { low: 1, high: 2 }, artifactId: 'a1' } : p));
  const h = runbookLockHash(asInterval, rb.measurementSchema);
  check('adding an interval changes the digest', h !== digests[rb.id]);
  const moved = asInterval.map((p, i) => (i === 0 ? { ...p, interval: { low: 1, high: 2.5 } } : p));
  check('changing one end of an interval changes the digest', runbookLockHash(moved, rb.measurementSchema) !== h);
  const other = asInterval.map((p, i) => (i === 0 ? { ...p, artifactId: 'a2' } : p));
  check('changing an artifactId changes the digest', runbookLockHash(other, rb.measurementSchema) !== h);
}

// OF-BLD-016 §3.3 (D3) — every locked seed runbook is an example, and the
// flag sits outside the digest: the eight digests above are the ones taken
// before the flag existed, each runbook still reads as intact, and a copy
// with the flag dropped hashes the same.
{
  const lockedSeed = RUNBOOKS.filter((r) => r.lockedAt);
  check('every locked seed runbook is marked an example', lockedSeed.every((r) => r.example === true));
  check('a locked example still reads as intact', lockedSeed.every((r) => lockIntact(r)));
  check('the example flag is not part of the digest', lockedSeed.every((r) => {
    const { example: _drop, ...plain } = r;
    return lockIntact({ ...plain, lockHash: r.lockHash });
  }));
  check('canonical() names no example field', !/example/.test(readFileSync('src/engine/lock.ts', 'utf8').split('function canonical')[1]?.split('\n}\n')[0] ?? 'example'));
}

console.log(fails === 0 ? '\nFREEZE CONTRACT HOLDS' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
