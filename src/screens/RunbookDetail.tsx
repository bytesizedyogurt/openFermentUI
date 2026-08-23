// Runbook detail (OF-BLD-005 §6, §7) — one synthesised answer, and whatever it
// is currently waiting on.
//
// The page leads with the state, because for seven of the ten seeded runbooks
// the state IS the content: a halted input, an unauthorised spend, a boundary
// a person should rule on. Only then the stages, the train, the cost and the
// clearance summary.
//
// The blocked-input panel deliberately borrows the tone of `explainRefusal()`
// in engine/units.ts. That function refuses to convert %TSP into g/L and then
// says exactly why and what would make the conversion possible, rather than
// throwing. A stage that halts on a number with no source is the same shape of
// event: not an error, a guardrail, with two honest ways forward.
import { useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  Boxes,
  CircleDollarSign,
  Clock,
  FileCheck2,
  FlaskConical,
  GitBranch,
  Link2,
  Sparkles,
  Wallet,
} from 'lucide-react';
import type { Runbook } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { RUNBOOK_STATUS_LABEL, RUNBOOK_STATUS_NOTE } from '@/data/runbooks';
import { PRODUCT_CATEGORY_LABEL } from '@/data/products';
import { STRAINS_BY_ID } from '@/data/strains';
import { CLEARANCE_STATES_BY_ID } from '@/data/vocabulary';
import { enumerationFunnel, funnelSummary, funnelWidest } from '@/engine/enumeration';
import { territorialityNote } from '@/engine/clearance';
import {
  ClearanceChip,
  ClearanceStrip,
  CounselCallout,
  JurisdictionMatrix,
} from '@/components/Clearance';
import { ProcessTrain } from '@/components/ProcessTrain';
import { RunbookStatusIcon, StageIcon, stageMeta } from '@/components/RunbookBits';
import { Tick } from '@/components/Provenance';
import {
  Bar,
  Button,
  Callout,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  SectionTitle,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

// ── the state panel — what this runbook is waiting on ──────────────────

function StatePanel({ runbook }: { runbook: Runbook }) {
  const products = useStore((s) => s.products);
  const resolveInput = useStore((s) => s.resolveRunbookInput);
  const authorise = useStore((s) => s.authoriseRunbookBudget);
  const resolveReview = useStore((s) => s.resolveRunbookReview);
  const promote = useStore((s) => s.promoteRunbook);
  const product = runbook.productId ? products.find((p) => p.id === runbook.productId) : undefined;

  const blockedStage = runbook.stages.find((s) => s.status === 'blocked');
  const reviewStage = runbook.stages.find((s) => s.status === 'review');

  if (runbook.status === 'blocked_unverified') {
    return (
      <Card className="p-4 border-signal-error/40">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Halted — and this is the system working
        </div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          {blockedStage?.name ?? 'A stage'} tried to consume a number with no source.
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">
          {blockedStage?.detail ?? 'The input has no provenance.'} The cascade stopped here rather
          than carrying the figure forward, because a number without a source does not become one
          by being used — it becomes several, one in each stage downstream, all of them looking
          equally solid. openFerment will not launder an input by consuming it.
        </p>
        <p className="text-body text-ink-soft mt-2 max-w-3xl">
          Two ways forward, and both of them are honest. Attach a source and the value carries a
          citation. Or mark it an explicit assumption and continue with it labelled as one — every
          number downstream inherits the label, so the conclusion says out loud what it rests on.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button variant="primary" onClick={() => resolveInput(runbook.id, 'source')}>
            <Link2 size={14} /> Attach a source
          </Button>
          <Button onClick={() => resolveInput(runbook.id, 'assumption')}>
            <FileCheck2 size={14} /> Mark it an assumption and continue
          </Button>
        </div>
      </Card>
    );
  }

  if (runbook.status === 'awaiting_budget') {
    const blockedByClaims = product?.clearanceState === 'blocked';
    return (
      <Card className="p-4 border-signal-warn/40">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Priced, not authorised
        </div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          {runbook.estCostUsd === null
            ? 'This run has not been priced.'
            : `Running this costs about $${runbook.estCostUsd} of compute.`}
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">
          Enumeration is the one input somebody authorises before it is spent, so the board has a
          state for it rather than a footnote. Nothing runs until you say yes.
        </p>
        {blockedByClaims && (
          <p className="text-body text-signal-warn mt-2 max-w-3xl">
            Worth reading the clearance first: {product?.name} has live blocking claims, so the
            industrial route below cannot proceed as written. Authorising this spend buys a process
            definition for a molecule you may not be free to make. The research handoff asks the
            cheaper question — whether there is anything outside the fence that does the same job.
          </p>
        )}
        <div className="flex flex-wrap gap-2 mt-3">
          {blockedByClaims && product && (
            <Button
              variant="primary"
              onClick={() => navigate(`/runbooks?handoff=${product.id}`)}
            >
              <Sparkles size={14} /> Enumerate around the fence instead
            </Button>
          )}
          <Button
            variant={blockedByClaims ? 'default' : 'primary'}
            onClick={() => authorise(runbook.id)}
          >
            <Wallet size={14} /> Authorise
            {runbook.estCostUsd === null ? '' : ` $${runbook.estCostUsd}`}
          </Button>
        </div>
      </Card>
    );
  }

  if (runbook.status === 'needs_review') {
    return (
      <Card className="p-4 border-signal-warn/40">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Held for a person
        </div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          {reviewStage?.detail ?? 'Something here needs a human decision.'}
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">
          Candidates sitting close to a claimed identity band are exactly what a person, not a
          model, should rule on. The model can say where the boundary appears to be and how close
          each candidate sits to it. Whether that distance is enough is a judgement with legal
          consequences, and it is not the model&rsquo;s to make.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button
            variant="primary"
            onClick={() => resolveReview(runbook.id, 'boundary accepted as mapped')}
          >
            Accept the boundary map
          </Button>
          <Button
            onClick={() =>
              resolveReview(runbook.id, 'near-boundary candidates excluded pending counsel')
            }
          >
            Exclude the near-boundary candidates
          </Button>
          {product && (
            <LinkButton to={`/molecules/${product.id}`}>
              Read the clearance <ArrowRight size={14} />
            </LinkButton>
          )}
        </div>
      </Card>
    );
  }

  if (runbook.status === 'cache_hit') {
    return (
      <Card className="p-4">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Resolved from cache
        </div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          A prior run already answered this, for{' '}
          {runbook.estCostUsd === null ? 'nothing' : `$${runbook.estCostUsd.toFixed(2)}`}.
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">
          {runbook.note} Caching artifacts rather than answers is what makes the second question
          about a host and a train nearly free — and it is why the catalogue is worth building out
          before the compute budget is.
        </p>
      </Card>
    );
  }

  if (runbook.kind === 'research' && runbook.status === 'complete') {
    return (
      <Card className="p-4">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Finished — and promotable
        </div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          A research runbook that finds something becomes an industrial one in a single action.
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">
          Promotion carries the finding across rather than restarting the work: the clearance
          reading becomes the industrial runbook&rsquo;s first stage, already done, and the host
          and molecule come with it.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button
            variant="primary"
            onClick={() => {
              const id = promote(runbook.id);
              if (id) navigate(`/runbooks/${id}`);
            }}
          >
            <GitBranch size={14} /> Promote to an industrial runbook
          </Button>
        </div>
      </Card>
    );
  }

  if (runbook.status === 'draft') {
    return (
      <Card className="p-4">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Scoped only</div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          {runbook.stages[0]?.detail ?? 'Nothing has been run yet.'}
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">{runbook.note}</p>
      </Card>
    );
  }

  return null;
}

// ── the enumeration funnel (research runbooks only) ────────────────────

function EnumerationFunnel({ runbook }: { runbook: Runbook }) {
  const funnel = useMemo(() => enumerationFunnel(runbook), [runbook]);
  const widest = funnelWidest(funnel);
  const summary = funnelSummary(funnel);

  return (
    <Card className="p-4">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <div className="text-caption uppercase tracking-wide text-ink-soft">
          Enumeration funnel
        </div>
        <Explain label="How the funnel is derived">
          Read back out of the stages rather than authored beside them, so the two cannot
          disagree. A number counts as a population only when the stage&rsquo;s own words say what
          it counts &mdash; a strain designation and a buffer percentage both contain digits and
          neither is a candidate. Stages that have produced no count are listed, not interpolated.
        </Explain>
      </div>

      {funnel.steps.length === 0 ? (
        <EmptyState
          title="Nothing quantified yet"
          body="No stage has reported a candidate count. The funnel appears as soon as one does — it is derived from the stages, so there is nothing to draw until they say something."
        />
      ) : (
        <ol className="space-y-2">
          {funnel.steps.map((s, i) => (
            <li key={`${s.stage.name}-${i}`}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-body truncate">{s.stage.name}</span>
                <span className="font-num text-body shrink-0">
                  {s.count.toLocaleString()}{' '}
                  <span className="text-ink-soft text-caption">{s.unit}</span>
                </span>
              </div>
              <div className="mt-1 h-2 w-full rounded-full bg-ink-soft/12 overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${widest > 0 ? Math.max(1.5, (s.count / widest) * 100) : 0}%` }}
                />
              </div>
            </li>
          ))}
        </ol>
      )}

      {summary && <p className="text-caption text-ink-soft mt-2">{summary}</p>}

      {funnel.unquantified.length > 0 && (
        <div className="mt-3 pt-3 border-t border-line">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
            Not quantified
          </div>
          <ul className="space-y-1">
            {funnel.unquantified.map((s, i) => (
              <li key={`${s.name}-${i}`} className="flex items-start gap-2 text-caption">
                <StageIcon status={s.status} size={13} />
                <span className="text-ink-soft">
                  <span className="text-ink">{s.name}</span> — {stageMeta(s.status).label}
                  {s.status === 'blocked' && ' · the run stopped here'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

export default function RunbookDetail({ runbookId }: { runbookId: string }) {
  const runbooks = useStore((s) => s.runbooks);
  const products = useStore((s) => s.products);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    setReady(false);
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, [runbookId]);

  const runbook = runbooks.find((r) => r.id === runbookId);
  const product = runbook?.productId
    ? products.find((p) => p.id === runbook.productId)
    : undefined;
  const strain = runbook?.strainId ? STRAINS_BY_ID[runbook.strainId] : undefined;

  if (!runbook) {
    return (
      <>
        <PageHeader
          eyebrow="Runbooks"
          title="Runbook not found"
          subtitle="Session state resets on refresh, so a deep link from an earlier session can point at nothing."
        />
        <Card>
          <EmptyState
            icon={<GitBranch size={22} aria-hidden />}
            title={`No runbook with the id “${runbookId}”`}
            body="The board lists every runbook in this session, grouped by what it is waiting on."
            action={<LinkButton to="/runbooks">Back to the board</LinkButton>}
          />
        </Card>
      </>
    );
  }

  if (!ready) {
    return (
      <>
        <PageHeader eyebrow="Runbooks" title={runbook.title} />
        <Card className="p-4 mb-4">
          <Skeleton rows={3} />
        </Card>
        <Card>
          <Skeleton rows={8} />
        </Card>
      </>
    );
  }

  const done = runbook.stages.filter((s) => s.status === 'done').length;
  const territoriality = product ? territorialityNote(product) : null;

  return (
    <>
      <PageHeader
        eyebrow={`Runbooks · ${runbook.kind}`}
        title={runbook.title}
        subtitle={RUNBOOK_STATUS_NOTE[runbook.status]}
        actions={
          <>
            {product && (
              <LinkButton to={`/molecules/${product.id}`}>
                <Boxes size={14} /> {product.name}
              </LinkButton>
            )}
            <LinkButton to="/runbooks">
              <ArrowRight size={14} className="rotate-180" /> All runbooks
            </LinkButton>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="chip inline-flex items-center gap-1.5">
          <RunbookStatusIcon status={runbook.status} size={13} />
          {RUNBOOK_STATUS_LABEL[runbook.status]}
        </span>
        <span
          className={cx(
            'chip',
            runbook.kind === 'research' ? 'text-signal-info border-signal-info/40' : 'text-ink-soft',
          )}
        >
          {runbook.kind}
        </span>
        {product && <ClearanceChip state={product.clearanceState} compact />}
        {strain && (
          <a href={href(`/organisms/${strain.id}`)} className="chip text-ink-soft hover:border-accent/45">
            <FlaskConical size={12} aria-hidden />
            <span className="italic">{strain.binomial}</span>
          </a>
        )}
        <span className="chip text-ink-soft font-num">{runbook.id}</span>
      </div>

      <Card className="p-4 mb-5">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="min-w-[180px] flex-1">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <span className="text-caption uppercase tracking-wide text-ink-soft">Progress</span>
              <span className="font-num text-body">{runbook.progressPct}%</span>
            </div>
            <Bar
              value={runbook.progressPct}
              max={100}
              className={
                runbook.status === 'blocked_unverified'
                  ? 'bg-signal-error'
                  : runbook.status === 'needs_review'
                    ? 'bg-signal-warn'
                    : undefined
              }
            />
            <div className="text-caption text-ink-soft mt-1">
              <span className="font-num">{done}</span> of{' '}
              <span className="font-num">{runbook.stages.length}</span> stages resolved
            </div>
          </div>
          <div>
            <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
              <Clock size={12} aria-hidden /> Remaining
            </div>
            <div className="font-num text-section-title">{runbook.eta ?? '—'}</div>
          </div>
          <Tick p="demo">
            <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
              <CircleDollarSign size={12} aria-hidden /> Compute
            </div>
            <div className="font-num text-section-title">
              {runbook.estCostUsd === null
                ? 'unpriced'
                : `$${runbook.estCostUsd < 1 ? runbook.estCostUsd.toFixed(2) : runbook.estCostUsd}`}
            </div>
            <div className="text-caption text-ink-soft">modeled, not a quotation</div>
          </Tick>
        </div>
      </Card>

      <div className="mb-5">
        <StatePanel runbook={runbook} />
      </div>

      <Card className="p-4 mb-6">
        <Tick p="demo" title="Curator framing — modeled, not measured">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
            Why this runbook is here
          </div>
          <p className="font-serif text-reading">{runbook.note}</p>
        </Tick>
      </Card>

      {/* ── stages ─────────────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-stages">
        <SectionTitle
          right={
            runbook.outputs.length > 0 ? (
              <span className="font-num text-caption text-ink-soft">
                {runbook.outputs.length} outputs
              </span>
            ) : undefined
          }
        >
          <span id="band-stages">Stages</span>
        </SectionTitle>

        <div
          className={cx(
            'grid grid-cols-1 gap-4',
            runbook.kind === 'research' ? 'lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]' : '',
          )}
        >
          <Card className="p-4">
            <ol className="space-y-3">
              {runbook.stages.map((s, i) => {
                const meta = stageMeta(s.status);
                return (
                  <li key={`${s.name}-${i}`} className="flex items-start gap-2.5">
                    <span className="mt-[3px]">
                      <StageIcon status={s.status} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-3">
                        <span
                          className={cx(
                            'font-medium leading-snug',
                            s.status === 'pending' && 'text-ink-soft',
                          )}
                        >
                          {s.name}
                        </span>
                        <span className={cx('text-caption shrink-0', meta.color)}>{meta.label}</span>
                      </div>
                      {s.detail && (
                        <div className="text-body text-ink-soft mt-0.5 leading-snug">{s.detail}</div>
                      )}
                      {s.value && (
                        <div className="mt-1">
                          {CLEARANCE_STATES_BY_ID[s.value] ? (
                            <ClearanceChip
                              state={CLEARANCE_STATES_BY_ID[s.value].id}
                              compact
                              title={`Stage verdict — ${CLEARANCE_STATES_BY_ID[s.value].label}`}
                            />
                          ) : (
                            <span className="font-num text-body text-accent">{s.value}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>

            {runbook.outputs.length > 0 && (
              <div className="mt-4 pt-3 border-t border-line">
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
                  Outputs
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {runbook.outputs.map((o) => (
                    <span key={o} className="chip text-accent border-accent/40">
                      <FileCheck2 size={12} aria-hidden />
                      {o}
                    </span>
                  ))}
                </div>
                <p className="text-caption text-ink-soft mt-2">
                  Artifacts, not files. This build names what a finished runbook hands over; it
                  does not generate the documents themselves.
                </p>
              </div>
            )}
          </Card>

          {runbook.kind === 'research' && <EnumerationFunnel runbook={runbook} />}
        </div>
      </section>

      {/* ── process train ──────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-train">
        <SectionTitle>
          <span id="band-train">Process train</span>
        </SectionTitle>
        <Card className="p-4">
          <ProcessTrain
            unitOperationIds={product?.unitOperationIds ?? []}
            strainId={runbook.strainId ?? product?.defaultStrainId ?? null}
            storageIds={product?.storageIds ?? []}
            scaleId={product?.scaleId ?? null}
            processCode={product?.processCode}
            emptyBody={
              product
                ? 'This molecule declares no unit operations, so there is no train to draw yet.'
                : 'This runbook is not attached to a molecule — it asks a cross-cutting question, and a cross-cutting question does not have one train. Attaching a product would give it one.'
            }
          />
        </Card>
      </section>

      {/* ── clearance summary ──────────────────────────────────────────── */}
      <section className="mb-4" aria-labelledby="band-clearance">
        <SectionTitle>
          <span id="band-clearance">Clearance summary</span>
        </SectionTitle>

        {product ? (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4">
              <Card className="p-4">
                <ClearanceStrip state={product.clearanceState} />
                <div className="mt-3 pt-3 border-t border-line text-body text-ink-soft">
                  {territoriality ??
                    'Every office in the model reads this molecule the same way, so the manufacture and export answers do not diverge here.'}
                </div>
                <div className="mt-3">
                  <a
                    href={href(`/molecules/${product.id}`)}
                    className="text-caption text-accent hover:underline"
                  >
                    Full clearance on {product.name} ({PRODUCT_CATEGORY_LABEL[product.category]})
                  </a>
                </div>
              </Card>
              <Card className="p-4">
                <JurisdictionMatrix product={product} />
              </Card>
            </div>
            <div className="mt-3">
              <CounselCallout scope={product.name} />
            </div>
          </>
        ) : (
          <>
            <Card>
              <EmptyState
                title="No molecule attached"
                body="Clearance attaches to a molecule, and this runbook asks a question that spans several. There is nothing here to clear until it is pointed at one."
                action={<LinkButton to="/molecules">Open the catalogue</LinkButton>}
              />
            </Card>
            <div className="mt-3">
              <CounselCallout />
            </div>
          </>
        )}
      </section>

      <Callout kind="info" title="What this runbook is claiming">
        Everything here is synthesised from a catalogue of modeled molecules and a facet
        vocabulary — nothing in it was measured, and no stage output has been checked against a
        source document. A runbook is a defensible starting point and a record of what was
        assumed; it is not a validated process and it is not a clearance opinion.
      </Callout>
    </>
  );
}
