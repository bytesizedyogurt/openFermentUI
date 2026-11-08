// Runbook detail (OF-BLD-005 §6, §7) — one synthesised answer, and whatever it
// is currently waiting on.
//
// The page leads with the state, because for a runbook that is waiting the
// state IS the content: a halted input, an unauthorised spend, a boundary a
// person should rule on. Only then the stages, the train and the cost.
//
// The blocked-input panel deliberately borrows the tone of `explainRefusal()`
// in engine/units.ts. That function refuses to convert %TSP into g/L and then
// says exactly why and what would make the conversion possible, rather than
// throwing. A stage that halts on a number with no source is the same shape of
// event: not an error, a guardrail, with two honest ways forward.
import { useState } from 'react';
import {
  ArrowRight,
  CircleDollarSign,
  Clock,
  FileCheck2,
  FlaskConical,
  Lock,
  Play,
  Target,
  GitBranch,
  Link2,
  Wallet,
} from 'lucide-react';
import { measuresOf, outputsOf, predictionsOf, stagesOf, type Runbook } from '@/lib/studies';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { RUNBOOK_STATUS_LABEL, RUNBOOK_STATUS_NOTE } from '@/data/labels';
import { lockIntact } from '@/engine/lock';
import { ledgerRows } from '@/engine/ledger';
import { IntervalLedger } from '@/components/figures';
import { Dossier } from '@/components/Dossier';
import { ProcessTrain } from '@/components/ProcessTrain';
import { RunbookStatusIcon, StageIcon, stageMeta } from '@/components/RunbookBits';
import { ComponentTag } from '@/components/ComponentTag';
import { Tick } from '@/components/Provenance';
import {
  Bar,
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  Modal,
  PageHeader,
  SectionTitle,
  cx,
} from '@/components/ui';

/**
 * A stage `value` is free text on purpose: a stage may answer with a titre, a
 * cost figure or a count, and free text holds each of them. This spots a value
 * written as a vocabulary id, so the page marks it as a term no vocabulary of
 * this build carries.
 */
function looksLikeVocabularyId(value: string): boolean {
  return /^[a-z]+(-[a-z]+)+$/.test(value);
}

// ── the state panel — what this runbook is waiting on ──────────────────

function StatePanel({ runbook }: { runbook: Runbook }) {
  const resolveInput = useStore((s) => s.resolveRunbookInput);
  const authorise = useStore((s) => s.authoriseRunbookBudget);
  const resolveReview = useStore((s) => s.resolveRunbookReview);
  const promote = useStore((s) => s.promoteRunbook);

  const stages = stagesOf(runbook);
  const blockedStage = stages.find((s) => s.status === 'blocked');
  const reviewStage = stages.find((s) => s.status === 'review');

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
    return (
      <Card className="p-4 border-signal-warn/40">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
          Priced, not authorised
        </div>
        <h2 className="font-serif text-section-title font-semibold leading-snug">
          {runbook.estCostUsd == null
            ? 'This run has not been priced.'
            : `Running this costs about $${runbook.estCostUsd} of compute.`}
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">
          A person authorises a runbook&rsquo;s compute before it is spent, and the board groups
          the runbooks waiting on that in a column of their own. Nothing runs until you say yes.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Button variant="primary" onClick={() => authorise(runbook.id)}>
            <Wallet size={14} /> Authorise
            {runbook.estCostUsd == null ? '' : ` $${runbook.estCostUsd}`}
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
          {runbook.estCostUsd == null ? 'nothing' : `$${runbook.estCostUsd.toFixed(2)}`}.
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
          Promotion carries the finding across: what this runbook&rsquo;s finished stages found
          becomes the industrial runbook&rsquo;s first stage, already done, and its host, its
          product, its predictions and its measures come with it.
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
          {stages[0]?.detail ?? 'Nothing has been run yet.'}
        </h2>
        <p className="text-body text-ink-soft mt-1.5 max-w-3xl">{runbook.note}</p>
      </Card>
    );
  }

  return null;
}

/**
 * What the runbook commits to, and what the bench will record against it.
 *
 * This is the falsifiable half of the Assay layer (OF-BLD-006 §3.1): a report
 * says here is what we found, a runbook says do this and you will get that.
 * The lock state sits at the top rather than in a footnote, because a
 * prediction that could still be edited is not evidence of anything.
 */
function PredictionPanel({ runbook }: { runbook: Runbook }) {
  const lock = useStore((st) => st.lockRunbook);
  const revise = useStore((st) => st.reviseRunbookPrediction);
  const supersede = useStore((st) => st.supersedeRunbook);
  const intact = lockIntact(runbook);
  // A row served as kept leaves out a field it never set: a runbook with no lock time is unlocked, and a measure
  // that names no prediction is context nobody predicted.
  const locked = runbook.lockedAt != null;
  const predictions = predictionsOf(runbook);
  const measuresFor = (predictionId: string) => measuresOf(runbook).filter((m) => m.predictionId === predictionId);
  const unpredicted = measuresOf(runbook).filter((m) => m.predictionId == null);

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-2">
        <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
          <Target size={13} aria-hidden /> What this predicts
        </div>
        {runbook.lockedAt ? (
          <span
            className={cx(
              'chip text-[11px] py-0 inline-flex items-center gap-1',
              intact ? 'text-accent border-accent/40' : 'text-signal-error border-signal-error/40',
            )}
            title={
              intact
                ? `Frozen ${runbook.lockedAt}. Content hash ${runbook.lockHash}.`
                : 'The stored content no longer matches the hash taken at lock time.'
            }
          >
            <Lock size={11} aria-hidden />
            {intact ? 'locked' : 'lock broken'}
          </span>
        ) : (
          <span className="chip text-signal-warn border-signal-warn/40 text-[11px] py-0">
            not yet locked
          </span>
        )}
      </div>

      {predictions.length === 0 ? (
        <EmptyState
          title="Nothing predicted yet"
          body="This runbook is scoped but has not committed to a number. Until it does there is nothing for a bench result to confirm or refute."
        />
      ) : (
        <ul className="space-y-3">
          {predictions.map((p) => {
            const tests = measuresFor(p.id);
            return (
              <li key={p.id}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-body">{p.label}</span>
                  <span className="font-num text-body shrink-0 inline-flex items-baseline gap-1">
                    {locked ? (
                      p.value.toLocaleString()
                    ) : (
                      <input
                        type="number"
                        className="input font-num w-[110px] text-right py-0.5"
                        value={p.value}
                        aria-label={`${p.label} predicted value`}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          if (e.target.value !== '' && isFinite(v)) revise(runbook.id, p.id, v);
                        }}
                      />
                    )}
                    <span className="text-ink-soft text-caption">{p.unit}</span>
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5">
                  <span
                    className={cx(
                      'text-caption',
                      p.confidence === 'high'
                        ? 'text-accent'
                        : p.confidence === 'low'
                          ? 'text-signal-warn'
                          : 'text-ink-soft',
                    )}
                  >
                    {p.confidence} confidence
                  </span>
                  <span className="text-caption text-ink-soft">
                    {tests.length === 0
                      ? 'no measure tests this'
                      : `tested at ${tests.map((m) => m.timepoint).join(', ')}`}
                  </span>
                </div>
                <div className="text-caption text-ink-soft mt-0.5">
                  {p.basis}
                  {p.artifactId && (
                    <>
                      {' '}
                      ·{' '}
                      {/* A study's runbook predicts an engine run's outputs, and the run's id is its artifact's. */}
                      <a
                        className="font-num underline underline-offset-2 hover:text-accent"
                        href={href(runbook.id.startsWith('rb-study-') ? `/proforma/runs/${p.artifactId}` : `/biorepo/artifacts/${p.artifactId}`)}
                        data-testid="prediction-artifact"
                      >
                        {runbook.id.startsWith('rb-study-') ? 'the run' : 'its artifact'} {p.artifactId}
                      </a>
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {unpredicted.length > 0 && (
        <div className="mt-3 pt-3 border-t border-line">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
            Recorded, not predicted
          </div>
          <ul className="space-y-0.5">
            {unpredicted.map((m) => (
              <li key={m.id} className="text-caption text-ink-soft">
                <span className="text-ink">{m.label}</span> · {m.unit} · {m.timepoint}
              </li>
            ))}
          </ul>
          <p className="text-caption text-ink-soft mt-1">
            Measured because it is worth having, not because anything forecast it. A value with no
            prediction behind it cannot confirm or refute the runbook — it is context.
          </p>
        </div>
      )}

      <div className="mt-3 pt-3 border-t border-line flex flex-wrap items-center gap-2">
        {locked ? (
          <>
            <Button onClick={() => { const id = supersede(runbook.id); if (id) navigate(`/runbooks/${id}`); }}>
              <GitBranch size={14} /> Supersede to revise
            </Button>
            <span className="text-caption text-ink-soft">
              Frozen {runbook.lockedAt?.slice(0, 10)} · hash{' '}
              <span className="font-num">{runbook.lockHash?.slice(0, 12)}</span>. Editing is
              refused at the store, not discouraged by a note.
            </span>
          </>
        ) : (
          <>
            <Button
              variant="primary"
              onClick={() => lock(runbook.id)}
              disabled={predictions.length === 0}
            >
              <Lock size={14} /> Lock predictions
            </Button>
            <span className="text-caption text-ink-soft">
              {predictions.length === 0
                ? 'Nothing to freeze yet.'
                : 'Editable until frozen. After that the runbook is superseded, never rewritten.'}
            </span>
          </>
        )}
      </div>

      <div className="mt-2">
        <ComponentTag
          component="Runbook"
          action={locked ? `frozen ${runbook.lockedAt?.slice(0, 10)}` : 'predictions still editable'}
        />
      </div>
    </Card>
  );
}

/**
 * Launching a Deposition (OF-BLD-006 §4, COMPONENTS.md).
 *
 * Deposition is launched FROM a Runbook, not from a protocol: the runbook is
 * what supplies the predictions and the measurement schema, and without those
 * a run has nothing to be reconciled against. The protocol supplies the steps.
 * The readings alone need no protocol (alpha 2.2 C.5): each of the runbook's
 * measures is recorded at the bench DepositionBench serves, and a reading a
 * person confirms there is one a scenario's value may name.
 */
function StartDeposition({ runbook }: { runbook: Runbook }) {
  const protocols = useStore((s) => s.protocols);
  const depositions = useStore((s) => s.depositions);
  const openDeposition = useStore((s) => s.openDeposition);
  // A reading names the person who took it (measurements.py), so the readings alone wait for a name.
  const reviewer = useStore((s) => s.reviewer.trim());
  const [pick, setPick] = useState(false);
  const [scale, setScale] = useState(1);

  const mine = depositions.filter((d) => d.runbookId === runbook.id);
  // A runbook with no lock time is unlocked, and a deposition waits for its predictions to freeze.
  const blocked = runbook.lockedAt == null;
  const measures = measuresOf(runbook);

  return (
    <Card className="p-4">
      <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Assay</div>
      <h3 className="font-serif text-section-title font-semibold leading-snug">
        Take this to a bench
      </h3>
      <p className="text-body text-ink-soft mt-1">
        A Deposition records what actually happened, against what this runbook predicted. It is the
        only ground truth the platform ever gets about its own numbers — nothing in the literature
        can tell you whether a yield model works.
      </p>

      {blocked && (
        <p className="text-body text-signal-warn mt-2">
          Lock the predictions first. Running against predictions that can still be edited is how
          the platform ends up grading its own homework.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2 mt-3">
        <Button variant="primary" disabled={blocked} onClick={() => setPick(true)}>
          <Play size={14} /> Start a deposition
        </Button>
        <ComponentTag component="Deposition" action={`${mine.length} on this runbook`} />
      </div>

      {mine.length > 0 && (
        <ul className="mt-3 pt-3 border-t border-line space-y-1">
          {mine.map((d) => (
            <li key={d.id}>
              <a
                href={href(`/runbooks/depositions/${d.id}`)}
                className="text-body text-accent hover:underline"
              >
                {d.state === 'closed' ? 'Closed' : d.state === 'running' ? 'Running' : 'Staged'} ·{' '}
                <span className="font-num">{d.entries.length}</span> measured ·{' '}
                <span className="font-num">{d.observations.length}</span> observed
              </a>
            </li>
          ))}
        </ul>
      )}

      <Modal open={pick} onClose={() => setPick(false)} title="How will you record it?" width={520}>
        <p className="text-body text-ink-soft mb-3">
          The runbook supplies the predictions and the measurement schema. A protocol, where you run one, supplies the
          steps and the quantities.
        </p>
        <button
          className="w-full text-left card p-3 mb-2 hover:border-accent/45 hover:bg-accent-wash/40 disabled:opacity-60"
          style={{ minHeight: 44 }}
          data-testid="deposition-readings-alone"
          disabled={!reviewer}
          onClick={() => {
            const started = openDeposition(runbook.id, null, scale);
            setPick(false);
            if (started) navigate(`/runbooks/depositions/${encodeURIComponent(started.depositionId)}/bench`);
          }}
        >
          <div className="font-medium">The readings alone</div>
          <div className="text-caption text-ink-soft">
            Each of this runbook&rsquo;s {measures.length} measure{measures.length === 1 ? '' : 's'} recorded at the
            bench, with no protocol&rsquo;s steps around them
          </div>
        </button>
        {!reviewer && (
          <p className="text-caption text-ink-soft mb-2" data-testid="deposition-needs-name">
            A reading names the person who took it: set yours in Settings first.
          </p>
        )}
        {protocols.length === 0 ? (
          <p className="text-body text-ink-soft mb-2" data-testid="no-protocols">
            No protocol is on file yet; the runbook&rsquo;s measures can be recorded alone.
          </p>
        ) : (
          <>
            <div className="text-caption uppercase tracking-wide text-ink-soft mt-3 mb-1">With a protocol&rsquo;s steps</div>
            <label className="block text-caption text-ink-soft mb-1" htmlFor="deposition-scale">
              Scale versus the protocol&rsquo;s base batch
            </label>
            <input
              id="deposition-scale"
              className="input font-num mb-3"
              style={{ minHeight: 44 }}
              type="number"
              min={0.1}
              step={0.1}
              value={scale}
              onChange={(e) => setScale(Math.max(0.1, Number(e.target.value) || 1))}
              aria-label="Scale multiplier"
            />
          </>
        )}
        <ul className="space-y-1.5 max-h-[320px] overflow-y-auto">
          {protocols.map((p) => (
            <li key={p.id}>
              <button
                className="w-full text-left card p-3 hover:border-accent/45 hover:bg-accent-wash/40"
                onClick={() => {
                  const started = openDeposition(runbook.id, p.id, scale);
                  setPick(false);
                  if (started) navigate(`/runbooks/protocols/${p.id}/run/${started.runId}`);
                }}
              >
                <div className="font-medium">{p.title}</div>
                <div className="text-caption text-ink-soft">
                  {p.id} · {p.category} · v{p.currentVersion}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </Modal>
    </Card>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

/** §9.3 — this runbook's predictions drawn against what its runs measured. */
function RunbookLedgerFigure({ runbook }: { runbook: Runbook }) {
  const depositions = useStore((s) => s.depositions);
  const tested = new Map(ledgerRows([runbook], depositions).map((r) => [r.prediction.id, r]));
  return (
    <div className="mb-4">
      <IntervalLedger
        title={`What does ${runbook.title} predict, and what was measured?`}
        rows={predictionsOf(runbook).map((p) => ({
          key: p.id,
          label: p.label,
          prediction: p,
          lockedAt: runbook.lockedAt ?? null,
          observed: tested.get(p.id)?.observed ?? null,
          held: tested.get(p.id)?.held ?? null,
        }))}
        csvName={`ledger-${runbook.id}`}
      />
    </div>
  );
}

export default function RunbookDetail({ runbookId }: { runbookId: string }) {
  const runbooks = useStore((s) => s.runbooks);
  const products = useStore((s) => s.products);
  const strains = useStore((s) => s.strains);

  const runbook = runbooks.find((r) => r.id === runbookId);
  const product = runbook?.productId
    ? products.find((p) => p.id === runbook.productId)
    : undefined;
  const strain = runbook?.strainId ? strains.find((s) => s.id === runbook.strainId) : undefined;

  if (!runbook) {
    return (
      <>
        <PageHeader
          eyebrow="Runbooks"
          title="Runbook not found"
          subtitle="This project holds no runbook with this id."
        />
        <Card>
          <EmptyState
            icon={<GitBranch size={22} aria-hidden />}
            title={`No runbook with the id “${runbookId}”`}
            body="The project keeps no runbook of that id; the link may be from another project. The board lists every runbook the project keeps, grouped by what it is waiting on."
            action={<LinkButton to="/runbooks">Back to the board</LinkButton>}
          />
        </Card>
      </>
    );
  }

  const stages = stagesOf(runbook);
  const outputs = outputsOf(runbook);
  const done = stages.filter((s) => s.status === 'done').length;
  // A row served as kept may leave out its progress, which then stands at none.
  const progress = runbook.progressPct ?? 0;

  return (
    <>
      <PageHeader
        eyebrow={`Runbooks · ${runbook.kind}`}
        title={runbook.title}
        subtitle={RUNBOOK_STATUS_NOTE[runbook.status]}
        actions={
          <LinkButton to="/runbooks">
            <ArrowRight size={14} className="rotate-180" /> All runbooks
          </LinkButton>
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
        {product && <span className="chip text-ink-soft">{product.name}</span>}
        {strain && (
          <a href={href(`/geneos/hosts/${strain.id}`)} className="chip text-ink-soft hover:border-accent/45">
            <FlaskConical size={12} aria-hidden />
            {strain.species && <span className="italic">{strain.species}</span>}
            <span>{strain.name}</span>
          </a>
        )}
        <span className="chip text-ink-soft font-num">{runbook.id}</span>
      </div>

      <Card className="p-4 mb-5">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="min-w-[180px] flex-1">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <span className="text-caption uppercase tracking-wide text-ink-soft">Progress</span>
              <span className="font-num text-body">{progress}%</span>
            </div>
            <Bar
              value={progress}
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
              <span className="font-num">{stages.length}</span> stages resolved
            </div>
          </div>
          <div>
            <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
              <Clock size={12} aria-hidden /> Remaining
            </div>
            <div className="font-num text-section-title">{runbook.eta ?? '—'}</div>
          </div>
          <Tick p="assumed">
            <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
              <CircleDollarSign size={12} aria-hidden /> Compute
            </div>
            <div className="font-num text-section-title">
              {runbook.estCostUsd == null
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
        <Tick p="assumed" title="The runbook's note — modeled, not measured">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
            Why this runbook is here
          </div>
          <p className="font-serif text-reading">{runbook.note || 'This runbook keeps no note of why it is here.'}</p>
        </Tick>
      </Card>

      {/* ── stages ─────────────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-stages">
        <SectionTitle
          right={
            outputs.length > 0 ? (
              <span className="font-num text-caption text-ink-soft">
                {outputs.length} outputs
              </span>
            ) : undefined
          }
        >
          <span id="band-stages">Stages</span>
        </SectionTitle>
        <div className="mb-2">
          <ComponentTag
            component="Runbook"
            action={`${runbook.kind} claim · ${stages.length} stages`}
          />
        </div>

        <Card className="p-4">
          {stages.length === 0 && (
            <p className="text-body text-ink-soft" data-testid="runbook-no-stages">
              This runbook holds no stages: a runbook made from a study or drafted by Postdoc
              starts with its predictions and the measures that test them, below.
            </p>
          )}
          <ol className="space-y-3">
            {stages.map((s, i) => {
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
                        {looksLikeVocabularyId(s.value) ? (
                          // A hyphenated lowercase token that resolves to
                          // nothing is a term this build does not carry, not
                          // a finding. Showing it as one would dress an
                          // unresolved reference up as an answer, so it is
                          // labelled instead.
                          <span
                            className="chip text-ink-soft font-num text-[11px] py-0"
                            title="This stage recorded a term that is in no vocabulary this build carries. It is shown as written."
                          >
                            {s.value} · not in the vocabulary
                          </span>
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

          {outputs.length > 0 && (
            <div className="mt-4 pt-3 border-t border-line">
              <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
                Outputs
              </div>
              <div className="flex flex-wrap gap-1.5">
                {outputs.map((o) => (
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
      </section>

      {/* ── predictions ─────────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-predictions">
        <SectionTitle>
          <span id="band-predictions">Predictions</span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          A runbook is a falsifiable claim. These are the numbers it commits to before anything is
          run, and the measurements that will test them — frozen together, so the platform cannot
          quietly move a prediction toward a result it has already seen.
        </p>
        {predictionsOf(runbook).length > 0 && <RunbookLedgerFigure runbook={runbook} />}
        <Dossier runbook={runbook} />
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-4">
          <PredictionPanel runbook={runbook} />
          <StartDeposition runbook={runbook} />
        </div>
      </section>

      {/* ── process train ──────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-train">
        <SectionTitle>
          <span id="band-train">Process train</span>
        </SectionTitle>
        <Card className="p-4">
          {/* A product's catalogue entry keeps its class, its location and its sequence; pureOS builds and proposes trains. */}
          <ProcessTrain
            unitOperationIds={[]}
            strainId={runbook.strainId ?? null}
            emptyBody={
              product
                ? `${product.name}'s catalogue entry keeps its class, where the cells leave it and its sequence. A train of unit operations is built in pureOS, unit by unit, or proposed there for a product and a host.`
                : 'This runbook names no product, so it has no process train to draw.'
            }
          />
        </Card>
      </section>

      <Callout kind="info" title="What this runbook is claiming">
        Everything here is synthesised, and no stage output has been checked against a source
        document. A runbook is a defensible starting point and a record of what was assumed.
      </Callout>
    </>
  );
}
