// Runbook board (OF-BLD-005 §6) — every runbook grouped by status.
//
// The board is ordered by what needs a person, not by what is newest. Running
// work first, then the three states waiting on a decision — a halted input, a
// boundary a model should not rule on, an unauthorised spend — then the
// finished ones and the drafts. A board is read top-left first, and what is
// waiting on you belongs there.
//
// A runbook is not a job. The jobs tray shows the progress bar for whatever is
// in flight; this board shows the records, including the ones that are not
// running at all and will not be until somebody acts.
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Boxes, GitBranch, Sparkles } from 'lucide-react';
import type { Runbook, RunbookStatus } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { RUNBOOK_STATUS_LABEL, RUNBOOK_STATUS_NOTE, RUNBOOK_STATUS_ORDER } from '@/data/runbooks';
import { PRODUCT_CATEGORY_LABEL } from '@/data/products';
import { ClearanceChip, CounselCallout } from '@/components/Clearance';
import { RunbookStatusIcon, StageDot } from '@/components/RunbookBits';
import {
  Bar,
  Button,
  Card,
  EmptyState,
  Explain,
  PageHeader,
  SectionTitle,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

function RunbookCard({ r }: { r: Runbook }) {
  const products = useStore((s) => s.products);
  const product = r.productId ? products.find((p) => p.id === r.productId) : undefined;
  const done = r.stages.filter((s) => s.status === 'done').length;
  const halted = r.stages.find((s) => s.status === 'blocked' || s.status === 'review');

  return (
    <a
      href={href(`/runbooks/${r.id}`)}
      className="card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium leading-snug">{r.title}</span>
        <span
          className={cx(
            'chip shrink-0 text-[11px] py-0',
            r.kind === 'research' ? 'text-signal-info border-signal-info/40' : 'text-ink-soft',
          )}
          title={
            r.kind === 'research'
              ? 'Open question — outputs a prediction and the experiments that would test it'
              : 'Established product — outputs a process you could build and defend'
          }
        >
          {r.kind}
        </span>
      </div>

      {product && (
        <div className="text-caption text-ink-soft mt-1 truncate">
          {product.name} · {PRODUCT_CATEGORY_LABEL[product.category]}
        </div>
      )}

      <div className="mt-2 flex items-center gap-1" aria-hidden>
        {r.stages.map((s, i) => (
          <StageDot key={`${s.name}-${i}`} status={s.status} />
        ))}
      </div>
      <div className="mt-1.5">
        <Bar
          value={r.progressPct}
          max={100}
          className={
            r.status === 'blocked_unverified'
              ? 'bg-signal-error'
              : r.status === 'needs_review'
                ? 'bg-signal-warn'
                : undefined
          }
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-caption text-ink-soft mt-1.5">
        <span className="font-num">{r.progressPct}%</span>
        <span>
          <span className="font-num">{done}</span>/<span className="font-num">{r.stages.length}</span>{' '}
          stages
        </span>
        {r.eta && <span className="font-num">{r.eta}</span>}
        {r.estCostUsd !== null && (
          <span className="font-num" title="Modeled compute spend, not a quotation">
            ${r.estCostUsd < 1 ? r.estCostUsd.toFixed(2) : r.estCostUsd}
          </span>
        )}
      </div>

      {halted && (
        <div className="text-caption text-signal-warn mt-1.5 leading-snug">
          {halted.name}: {halted.detail ?? 'waiting on a person'}
        </div>
      )}

      {product && (
        <div className="mt-2">
          <ClearanceChip state={product.clearanceState} compact />
        </div>
      )}
    </a>
  );
}

/** §8 — the blocked → research handoff, offered before anything is created. */
function HandoffPanel({ productId }: { productId: string }) {
  const products = useStore((s) => s.products);
  const handoff = useStore((s) => s.handoffToResearchRunbook);
  const product = products.find((p) => p.id === productId);
  if (!product) return null;

  const blocked = product.clearanceState === 'blocked';
  const unknown = product.clearanceState === 'unknown';

  return (
    <Card className="p-4 mb-5 border-accent/40">
      <div className="flex items-start gap-3">
        <span className="w-9 h-9 rounded-btn bg-accent/10 border border-accent/25 grid place-items-center shrink-0">
          <Sparkles size={17} className="text-accent" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-caption uppercase tracking-wide text-ink-soft">
            Handoff from the molecule catalogue
          </div>
          <h2 className="font-serif text-section-title font-semibold leading-snug mt-0.5">
            {blocked
              ? `${product.name} is fenced. Ask the question the fence does not cover.`
              : unknown
                ? `${product.name} has never been assessed.`
                : `Open a research runbook on ${product.name}?`}
          </h2>
          <p className="text-body text-ink-soft mt-1 max-w-3xl">
            {blocked
              ? 'Blocking claims stop the industrial route, not the enquiry. A research runbook reads what the claims actually recite: if they name sequences, it enumerates the genus around them and ranks what falls outside. If they name a function, it will tell you that instead — and save you the compute rather than spending it to rediscover that molecular diversity does not escape a functional claim.'
              : unknown
                ? 'Nothing has been assessed here, so every process below it describes work that may or may not be yours to run. A clearance sweep classifies the claims before anything else is worth scheduling.'
                : 'This molecule is not fenced, so there is nothing to enumerate around. Opening a runbook here will say so and stop, which is a cheap answer worth having on the record.'}
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <ClearanceChip state={product.clearanceState} />
            <Button
              variant="primary"
              onClick={() => {
                const id = handoff(product.id);
                if (id) navigate(`/runbooks/${id}`);
              }}
            >
              <Sparkles size={14} /> Open the research runbook
            </Button>
            <Button onClick={() => navigate('/runbooks')}>Not now</Button>
            <a
              href={href(`/molecules/${product.id}`)}
              className="text-caption text-accent hover:underline ml-1"
            >
              Back to {product.name}
            </a>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function Runbooks() {
  const runbooks = useStore((s) => s.runbooks);
  const products = useStore((s) => s.products);
  const route = useRoute();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const handoffId = route.query.get('handoff');

  const columns = useMemo(() => {
    const by = new Map<RunbookStatus, Runbook[]>();
    for (const r of runbooks) {
      const arr = by.get(r.status);
      if (arr) arr.push(r);
      else by.set(r.status, [r]);
    }
    return RUNBOOK_STATUS_ORDER.filter((s) => (by.get(s)?.length ?? 0) > 0).map((status) => ({
      status,
      items: by.get(status)!,
    }));
  }, [runbooks]);

  const waiting = useMemo(
    () =>
      runbooks.filter((r) =>
        ['blocked_unverified', 'needs_review', 'awaiting_budget'].includes(r.status),
      ).length,
    [runbooks],
  );
  const spend = useMemo(
    () => runbooks.reduce((n, r) => n + (r.estCostUsd ?? 0), 0),
    [runbooks],
  );

  const subtitle =
    'A runbook is a synthesised, followable answer to a question about making something. Industrial runbooks output a process you could build and defend; research runbooks output a prediction and the experiments that would test it. Same toolchain, different question.';

  if (!ready) {
    return (
      <>
        <PageHeader eyebrow="Module 6 · Runbooks" title="Runbooks" subtitle={subtitle} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <Skeleton rows={6} />
            </Card>
          ))}
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Module 6 · Runbooks"
        title="Runbooks"
        subtitle={subtitle}
        actions={
          <a href={href('/molecules')} className="btn">
            <Boxes size={14} /> Molecules
          </a>
        }
      />

      {handoffId && <HandoffPanel productId={handoffId} />}

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-4 text-caption text-ink-soft">
        <span className="inline-flex items-center gap-1.5">
          <GitBranch size={13} aria-hidden />
          <span className="font-num text-ink">{runbooks.length}</span> runbooks
        </span>
        <span>
          <span className="font-num text-ink">
            {runbooks.filter((r) => r.kind === 'industrial').length}
          </span>{' '}
          industrial ·{' '}
          <span className="font-num text-ink">
            {runbooks.filter((r) => r.kind === 'research').length}
          </span>{' '}
          research
        </span>
        <span>
          <span className={cx('font-num', waiting > 0 ? 'text-signal-warn' : 'text-ink')}>
            {waiting}
          </span>{' '}
          waiting on a person
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="font-num text-ink">${spend.toFixed(2)}</span> modeled compute spend
          <Explain label="What the cost figure means">
            An estimate of the compute a runbook consumes — retrieval, prediction, enumeration —
            not a quotation and not a process cost. It is here because enumeration compute is the
            one input a person authorises before it is spent, which is why{' '}
            <span className="font-medium">awaiting budget</span> is a state on this board rather
            than a footnote. The cache-hit runbook is the argument for artifact caching: near-zero
            cost for an answer a previous run already paid for.
          </Explain>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {columns.map(({ status, items }) => (
          <section key={status} aria-labelledby={`col-${status}`}>
            <SectionTitle
              right={<span className="font-num text-caption text-ink-soft">{items.length}</span>}
            >
              <span id={`col-${status}`} className="inline-flex items-center gap-2">
                <RunbookStatusIcon status={status} />
                {RUNBOOK_STATUS_LABEL[status]}
              </span>
            </SectionTitle>
            <p className="text-caption text-ink-soft mb-2 leading-snug">
              {RUNBOOK_STATUS_NOTE[status]}
            </p>
            <div className="space-y-3">
              {items.map((r) => (
                <RunbookCard key={r.id} r={r} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {runbooks.length === 0 && (
        <Card>
          <EmptyState
            icon={<GitBranch size={22} aria-hidden />}
            title="No runbooks in this session"
            body="Runbooks are synthesised against a molecule. Open the catalogue and start one — a blocked molecule is usually the most interesting place to begin."
            action={
              <a href={href('/molecules')} className="btn btn-primary">
                Open the catalogue <ArrowRight size={14} />
              </a>
            }
          />
        </Card>
      )}

      <div className="mt-5">
        <CounselCallout scope="every clearance stage on this board" />
      </div>

      <p className="text-caption text-ink-soft mt-3 max-w-3xl">
        Runbooks carry the modeled provenance of everything they are built from:{' '}
        <span className="font-num">{products.length}</span> catalogued molecules, a facet
        vocabulary, and a claim reading. None of it was measured, and a stage that reports a number
        reports where the number came from or refuses to pass it on.
      </p>
    </>
  );
}
