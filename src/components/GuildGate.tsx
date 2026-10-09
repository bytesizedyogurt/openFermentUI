// The gate in run mode (OF-BLD-013 §2). Mounted inside Deposition under the
// step text, so it inherits that screen's constraints and keeps them: touch
// targets of 44 px and more, every word on `ink` for 7:1 at arm's length,
// nothing that appears only on hover.
//
// ADVISE AND ENFORCE (OF-BLD-013 §2, §5.1). The gate says what the step asks
// of the person performing it. On a skill the lead set to advise, the step
// can always be completed, and a step done without the level it needs is
// written as a deviation. On a skill set to enforce (critical skills, by
// default) the step is held: until someone is named as performing it, until
// a cosigner who holds the skill is recorded beside a Supervised, lapsed or
// suspended operator, or until someone qualified takes over from an operator
// below Supervised. `useGateHold` is what Deposition asks before completing.
import { useMemo, useState } from 'react';
import { ShieldAlert, ShieldCheck, UserCheck } from 'lucide-react';
import type { Step } from '@/data/types';
import { useStore, guildView } from '@/store';
import { SKILL_BY_ID } from '@/data/skills';
import {
  competenceOf,
  gateFor,
  holdFor,
  localToday,
  mayCosign,
  policyOf,
  statusOf,
  type Hold,
  type StatusMap,
} from '@/engine/competence';
import { Button, cx } from '@/components/ui';

const names = (ids: string[]) => ids.map((s) => SKILL_BY_ID[s]?.name ?? s).join(', ');

/** Why a cosign is asked: each skill named with the state the operator is in on it. */
function cosignReason(map: StatusMap, personId: string, skills: string[]): string {
  const by: Record<string, string[]> = {};
  for (const s of skills) {
    const st = statusOf(map, personId, s);
    const why = st.suspended ? 'suspended' : st.lapsed ? 'lapsed' : 'Supervised';
    (by[why] ??= []).push(s);
  }
  return Object.entries(by)
    .map(([why, ids]) => `${why} on ${names(ids)}`)
    .join('; ');
}

/** What holds this step in enforce mode, or null. */
export function useGateHold(runId: string, step: Step | undefined): Hold | null {
  const run = useStore((s) => s.runs[runId]);
  const ledger = useStore((s) => guildView(s));
  return useMemo(() => {
    if (!run || !step) return null;
    const people = ledger.people.filter((p) => p.active && p.role !== 'auditor');
    const named = (id: string | null | undefined) => (id && people.some((p) => p.id === id) ? id : null);
    const map = competenceOf(ledger.evidence, ledger.people, SKILL_BY_ID, localToday());
    return holdFor(step, named(run.operatorId), named(run.cosigned?.[step.id]), map, SKILL_BY_ID, policyOf(ledger), people.length > 0);
  }, [run, step, ledger]);
}

/** The hold in words, for the button and for a screen reader. */
export function holdText(hold: Hold): string {
  const which = names(hold.skills);
  if (hold.kind === 'operator') return `Held: name who is performing this step first (${which} is enforced).`;
  if (hold.kind === 'qualified') return `Held: ${which} needs someone qualified. Hand over to complete it.`;
  return `Held: ${which} needs a cosigner beside the operator. Record one to complete it.`;
}

export function GuildGate({ runId, step }: { runId: string; step: Step | undefined }) {
  const run = useStore((s) => s.runs[runId]);
  const ledger = useStore((s) => guildView(s));
  const setOperator = useStore((s) => s.setRunOperator);
  const setCosigner = useStore((s) => s.setRunCosigner);
  const [choosing, setChoosing] = useState(false);
  const [pickingCosigner, setPickingCosigner] = useState(false);
  const hold = useGateHold(runId, step);

  if (!run || !step || ledger.people.length === 0) return null;
  const today = localToday();
  const map = competenceOf(ledger.evidence, ledger.people, SKILL_BY_ID, today);
  const people = ledger.people.filter((p) => p.active && p.role !== 'auditor');
  const operator = people.find((p) => p.id === run.operatorId) ?? null;
  const gate = operator ? gateFor(step, operator.id, map) : null;
  const cosignerId = run.cosigned?.[step.id] ?? null;
  const cosigner = people.find((p) => p.id === cosignerId) ?? null;
  const candidates = gate ? people.filter((p) => p.id !== operator?.id && mayCosign(map, p.id, gate.cosign)) : [];
  const canRun = gate ? people.filter((p) => p.id !== operator?.id && mayCosign(map, p.id, step.skills ?? [])) : [];
  const recorded = run.guildRecorded?.[step.id];

  const choose = (
    <div className="grid sm:grid-cols-2 gap-2 mt-2">
      {people.map((p) => (
        <button
          key={p.id}
          type="button"
          className={cx(
            'rounded-card border-2 bg-surface-1 text-left px-4 text-reading text-ink',
            p.id === operator?.id ? 'border-accent' : 'border-line',
          )}
          style={{ minHeight: 52 }}
          onClick={() => {
            setOperator(runId, p.id);
            setChoosing(false);
            setPickingCosigner(false);
          }}
        >
          {p.name}
          {p.title && <span className="block text-caption text-ink">{p.title}</span>}
        </button>
      ))}
    </div>
  );

  return (
    <div className="card p-4 mt-4 space-y-3" aria-label="Who may perform this step">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-caption uppercase tracking-wide text-ink">Operator</span>
        <span className="text-reading text-ink font-medium flex-1 min-w-[140px]">{operator ? operator.name : 'Nobody chosen'}</span>
        <Button style={{ minHeight: 44 }} onClick={() => setChoosing((v) => !v)}>
          {operator ? 'Hand over' : 'Choose operator'}
        </Button>
      </div>
      {(choosing || !operator) && (
        <div>
          {!operator && (
            <p className="text-body text-ink">
              Choose who is performing these steps. Until then no step is checked against Guild or written to its ledger.
            </p>
          )}
          {choose}
        </div>
      )}

      {operator && gate && gate.state === 'none' && <p className="text-body text-ink">This step needs no skill.</p>}

      {operator && gate && gate.state === 'clear' && (
        <div className="rounded-card border border-accent/50 bg-accent-wash px-3 py-2 text-reading text-ink flex items-start gap-2">
          <ShieldCheck size={20} className="text-accent shrink-0 mt-[3px]" aria-hidden />
          <span>
            {operator.name} holds every skill this step needs: {names(step.skills ?? [])}. Completing it records a run alone.
          </span>
        </div>
      )}

      {operator && gate && gate.state === 'cosign' && (
        <div className="rounded-card border-2 border-signal-warn/60 bg-signal-warn/[0.06] px-3 py-3 space-y-2">
          <div className="text-reading text-ink flex items-start gap-2">
            <UserCheck size={20} className="text-signal-warn shrink-0 mt-[3px]" aria-hidden />
            <span>
              <strong>Cosign needed.</strong> {operator.name} is {cosignReason(map, operator.id, gate.cosign)}.
            </span>
          </div>
          {cosigner ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-reading text-ink">
                Cosigned by <strong>{cosigner.name}</strong>
              </span>
              <Button style={{ minHeight: 44 }} onClick={() => setCosigner(runId, step.id, null)} disabled={!!recorded}>
                Change
              </Button>
            </div>
          ) : pickingCosigner ? (
            <div className="grid sm:grid-cols-2 gap-2">
              {candidates.length === 0 && <p className="text-body text-ink">Nobody else holds these skills today.</p>}
              {candidates.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className="rounded-card border-2 border-line bg-surface-1 text-left px-4 text-reading text-ink"
                  style={{ minHeight: 52 }}
                  onClick={() => {
                    setCosigner(runId, step.id, p.id);
                    setPickingCosigner(false);
                  }}
                >
                  {p.name}
                  {p.title && <span className="block text-caption text-ink">{p.title}</span>}
                </button>
              ))}
            </div>
          ) : (
            <Button variant="primary" style={{ minHeight: 44 }} onClick={() => setPickingCosigner(true)}>
              <UserCheck size={16} /> Record cosigner
            </Button>
          )}
          {!cosigner && (
            <p className="text-body text-ink">
              {hold?.kind === 'cosigner'
                ? `The lead set ${names(hold.skills)} to enforce, so this step waits for a cosigner.`
                : `Completing it without one records a deviation on ${operator.name}\u2019s ledger.`}
            </p>
          )}
        </div>
      )}

      {operator && gate && gate.state === 'blocked' && (
        <div className="rounded-card border-2 border-signal-error/60 bg-signal-error/[0.06] px-3 py-3 space-y-2">
          <div className="text-reading text-ink flex items-start gap-2">
            <ShieldAlert size={20} className="text-signal-error shrink-0 mt-[3px]" aria-hidden />
            <span>
              <strong>Needs a qualified operator.</strong> {operator.name} is below Supervised on {names(gate.blocked)}.
            </span>
          </div>
          <p className="text-body text-ink">
            Can perform it alone: {canRun.length === 0 ? 'nobody on the team today' : canRun.map((p) => p.name).join(', ')}.
          </p>
          {canRun.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {canRun.slice(0, 3).map((p) => (
                <Button key={p.id} style={{ minHeight: 44 }} onClick={() => setOperator(runId, p.id)}>
                  Hand over to {p.name.split(' ')[0]}
                </Button>
              ))}
            </div>
          )}
          <p className="text-body text-ink">
            {hold?.kind === 'qualified'
              ? `The lead set ${names(hold.skills)} to enforce, so this step waits for someone qualified to take over.`
              : `Completing it anyway records a deviation on ${operator.name}\u2019s ledger.`}
          </p>
        </div>
      )}

      {recorded && <p className="text-caption text-ink">Written to Guild&rsquo;s ledger when this step was completed.</p>}
    </div>
  );
}
