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
import { lockIntact } from '../src/engine/lock';

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

console.log(fails === 0 ? '\nFREEZE CONTRACT HOLDS' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
