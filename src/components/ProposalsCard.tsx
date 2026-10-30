// What a model asked for at a gate, waiting for a person (OF-BLD-015 §7.4).
//
// One card a proposal, one button each. The service runs the action in the
// person's name where it can (a check asked for; an extraction once the
// budget allows); otherwise the button takes the person to the place the
// gate names and the proposal records that they took it. The name on the
// button is the reviewer name from Settings: with none set, the buttons say
// so and do nothing, because an unsigned carry-out is what the gates exist
// to prevent.
//
// A Guild proposal is about a person, and shows only where the check rules
// would show a check (OF-BLD-016 §1.R finding 9, `shownProposals`): to the
// lead and assessors, never to the person it names. Its note is never drawn:
// the service lists it without its words. Asking for a check needs who is
// acting on Guild, because Guild knows people by id (finding 11).
import { useEffect, useState } from 'react';
import { Inbox } from 'lucide-react';
import type { Proposal } from '@/data/types';
import { useStore, reviewerName } from '@/store';
import { navigate } from '@/router';
import { carryOut, dismiss, listProposals, needsActing, shownProposals } from '@/lib/proposals';
import { useGuild } from './GuildBits';
import { Button, Card } from './ui';

const MODULE_LABEL: Record<string, string> = {
  runbooks: 'Runbooks', geneos: 'geneOS', fermos: 'fermOS', pureos: 'pureOS',
  proforma: 'Proforma', biorepo: 'BioRepo', guild: 'Guild', primer: 'Primer', intake: 'Intake', home: 'Home',
};

export function ProposalsCard() {
  const serviceUp = useStore((s) => s.serviceUp);
  const [items, setItems] = useState<Proposal[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const person = reviewerName();
  const guild = useGuild();

  useEffect(() => {
    if (!serviceUp) return;
    const ctrl = new AbortController();
    listProposals(ctrl.signal)
      .then(setItems)
      .catch(() => setItems([]));
    return () => ctrl.abort();
  }, [serviceUp]);

  const shown = shownProposals(items, guild.acting, guild.status);
  if (!serviceUp || shown.length === 0) return null;

  const run = async (p: Proposal, verb: 'carry-out' | 'dismiss') => {
    if (!person) return;
    if (verb === 'carry-out' && needsActing(p) && !guild.actingId) {
      setProblem('Choose who you are acting as on Guild first: a check is asked for by a person on Guild.');
      return;
    }
    setBusy(p.id);
    setProblem(null);
    try {
      const acting = p.module === 'guild' ? guild.actingId : null;
      const done =
        verb === 'carry-out' ? await carryOut(p.id, person, acting) : await dismiss(p.id, person, 'dismissed on Home');
      setItems((xs) => xs.filter((x) => x.id !== p.id));
      if (verb === 'carry-out' && !p.server && p.route) navigate(p.route);
      if (verb === 'carry-out' && done.result) setProblem(null);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="p-4" data-testid="home-proposals">
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
          <Inbox size={13} aria-hidden /> Awaiting you
        </div>
        <span className="font-num text-caption text-ink-soft">{shown.length}</span>
      </div>
      <p className="text-caption text-ink-soft mt-1">
        Postdoc asked for these at a gate and wrote nothing. Each waits for a person; the button carries it out in your name.
      </p>
      {!person && (
        <p className="text-caption text-signal-warn mt-1" data-testid="home-proposals-unsigned">
          Set a reviewer name in Settings → Corpus to act on them.
        </p>
      )}
      {problem && (
        <p className="text-caption text-signal-warn mt-1" role="alert">
          {problem}
        </p>
      )}
      <ul className="mt-2 divide-y divide-line/60">
        {shown.map((p) => (
          <li key={p.id} className="py-2" data-testid="home-proposal">
            <div className="text-body font-medium leading-snug">{p.title}</div>
            <div className="text-caption text-ink-soft mt-0.5">
              <span className="font-num">{MODULE_LABEL[p.module] ?? p.module}</span> · gate: {p.gate} · asked by{' '}
              <span className="font-num">{p.by}</span>
            </div>
            {p.note && p.module !== 'guild' && <div className="text-caption text-ink mt-1">“{p.note}”</div>}
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                disabled={!person || busy === p.id}
                onClick={() => run(p, 'carry-out')}
                title={
                  !person
                    ? 'Set a reviewer name first'
                    : p.module === 'guild' && guild.acting
                      ? `${p.how} — as ${person}, acting as ${guild.acting.name} on Guild`
                      : `${p.how} — as ${person}`
                }
              >
                {p.how}
              </Button>
              <Button size="sm" disabled={!person || busy === p.id} onClick={() => run(p, 'dismiss')}>
                Dismiss
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
