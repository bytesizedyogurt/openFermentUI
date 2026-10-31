// Rendering an AnswerPlan (OF-BLD-007 §8).
//
// THIS COMPONENT IS WHERE ADR-006 BECOMES VISIBLE. The model wrote the sentence
// and cited a record; every number on this screen is read out of that record, or
// out of a claim's typed values (a computed value or a record the service read,
// or the model's own estimate, marked as one with the model that made it), by
// the code below. Nothing here prints model prose containing a quantity,
// because the validator guarantees the prose has none:
//
//   plan says    "Ethanol yield on glucose in cenpk113-7d under anaerobic conditions"  <record id>
//   this renders  Ethanol yield on glucose in cenpk113-7d under anaerobic conditions
//                 <the record's value and unit> · <its provenance> · <its paper>
//
// The provenance tick reuses the existing visual language rather than inventing
// a fourth one — a claim is evidence, and evidence in this system is ticked.
import { AlertTriangle, ExternalLink, HelpCircle, Quote, SearchX } from 'lucide-react';
import type {
  AnswerPlan,
  Claim,
  ClaimValue,
  CoverageMap,
  ModuleRow,
  Evidence,
  ExtractionRecord,
  Paper,
  Passage,
  RunbookDraft,
} from '@/data/types';
import { useStore, provenanceOf } from '@/store';
import { navigate } from '@/router';
import { fmt } from '@/engine/units';
import { ProvenanceBadge, Tick } from './Provenance';
import { ComponentTag } from './ComponentTag';
import { Callout, Card } from './ui';
import { cachedShare, formatCost } from '@/lib/postdoc';
import { PassageQuote } from './PassageQuote';
import { EvidenceCard } from './EvidenceCard';
import { STOPPED_WORDS } from './PlanTrace';

/** The value, rendered from the record — never from the claim's text. */
function RecordValue({ record }: { record: ExtractionRecord }) {
  const prov = provenanceOf(record);
  return (
    <Tick p={prov} className="py-1 pl-2.5" title={`${record.id} · ${record.quote}`}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="font-num text-reading text-ink">
          {fmt(record.value)} {record.unit}
        </span>
        <ProvenanceBadge p={prov} compact />
        <button
          className="font-num text-caption text-ink-soft hover:text-accent inline-flex items-center gap-1"
          onClick={() => navigate(`/biorepo/paper/${record.paperId}?span=${record.id}`)}
          title="Open the span in the source"
        >
          {record.id} <ExternalLink size={10} aria-hidden />
        </button>
      </div>
      <div className="text-caption text-ink-soft mt-0.5 line-clamp-2">
        <Quote size={10} className="inline mr-1 -mt-0.5" aria-hidden />
        {record.quote}
      </div>
    </Tick>
  );
}

/**
 * ADR-006 — the numbers a claim states, each with where it came from, as the
 * validator typed them. A model's estimate is marked as one wherever it
 * appears: the model that made it and what it rests on, under the assumed mark.
 */
function ClaimValues({ values }: { values: ClaimValue[] }) {
  if (!values.length) return null;
  return (
    <ul className="mt-2 space-y-1" data-testid="claim-values">
      {values.map((v) => {
        const q = v.quantity;
        const o = q.origin;
        const range = q.low != null && q.high != null ? ` (${fmt(q.low)} to ${fmt(q.high)})` : '';
        return (
          <li key={`${v.label}-${v.source ?? 'estimate'}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span className="text-caption text-ink-soft">{v.label}</span>
            <span className="font-num text-reading text-ink">
              {fmt(q.value)} {q.unit}
              {range}
            </span>
            {o?.kind === 'model-estimate' ? (
              <span className="inline-flex flex-wrap items-baseline gap-1 text-caption text-ink-soft">
                <ProvenanceBadge p="assumed" compact />
                <span>
                  an estimate by {o.by}
                  {o.note ? `, resting on ${o.note}` : ''}
                </span>
              </span>
            ) : (
              <span className="font-num text-caption text-ink-soft">
                {o?.kind === 'record' ? 'record' : 'computed'} {v.source}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

const SUPPORT_NOTE: Record<Claim['support'], string | null> = {
  direct: null,
  inferred: 'Inferred — this follows from the cited records rather than being stated by one.',
  unsupported:
    'Stated as an absence. No record backs this, which is the point of it — nobody has measured it.',
};

/** OF-BLD-015 §7.2 — where a module row lives in the app, when it has a page. */
function rowHref(row: ModuleRow): string {
  const at: Record<string, string> = {
    'runbooks/runbook': `/runbooks/${row.id}`,
    'runbooks/protocol': `/runbooks/protocols/${row.id}`,
    'geneos/host': `/geneos/hosts/${row.id}`,
    'geneos/model': '/geneos/model',
    'proforma/scenario': `/proforma/scenario/${row.id}`,
    'primer/lesson': `/primer/${row.id}`,
    'intake/source': `/biorepo/paper/${row.id}`,
    'biorepo/artifact': '/biorepo/artifacts',
    'biorepo/witness-run': '/biorepo/witness',
  };
  return at[`${row.module}/${row.kind}`] ?? `/${row.module === 'home' ? '' : row.module}`;
}

/** The module rows a claim rests on, each with the state the service computed. */
function ModuleRowChips({ refs, rows }: { refs: string[]; rows: Map<string, ModuleRow> }) {
  const cited = refs.map((r) => rows.get(r)).filter((r): r is ModuleRow => Boolean(r));
  if (cited.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1" data-testid="claim-module-rows">
      {cited.map((row) => (
        <a
          key={row.ref}
          href={`#${rowHref(row)}`}
          className="text-caption text-ink-soft hover:text-accent inline-flex items-baseline gap-1"
          title={`${row.ref} · ${row.status}`}
        >
          <span className="font-num">{row.module}</span>
          <span className="truncate max-w-[28ch]">{row.label}</span>
          <span className="opacity-70">· {row.state}</span>
        </a>
      ))}
    </div>
  );
}

function ClaimRow({
  claim,
  index,
  passages,
  evidence,
  rows,
}: {
  claim: Claim;
  index: number;
  passages: Map<string, Passage>;
  evidence: Map<string, Evidence>;
  rows: Map<string, ModuleRow>;
}) {
  const records = useStore((s) => s.records);
  const papers = useStore((s) => s.papers);
  const byId = new Map(records.map((r) => [r.id, r]));
  const paperById = new Map(papers.map((p) => [p.id, p]));

  const cited = claim.recordIds.map((id) => byId.get(id)).filter(Boolean) as ExtractionRecord[];
  const citedPapers = claim.paperIds
    .map((id) => paperById.get(id))
    .filter(Boolean) as Paper[];
  const note = SUPPORT_NOTE[claim.support];

  return (
    <li className="py-3 border-b border-line/70 last:border-0">
      <div className="flex items-baseline gap-2.5">
        <span className="font-num text-caption text-ink-soft shrink-0 mt-0.5">{index + 1}</span>
        <div className="min-w-0 flex-1">
          {/* The claim, exactly as written. It contains no number — that is
              enforced server-side, not hoped for here. */}
          <p className="text-reading text-ink">{claim.text}</p>

          <ClaimValues values={claim.values ?? []} />

          {cited.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {cited.map((record) => (
                <RecordValue key={record.id} record={record} />
              ))}
            </div>
          )}

          {/* OF-BLD-014 §5.4 — sentences the claim quotes, checked word for
              word against their passages, and computed values it rests on. */}
          {(claim.passages ?? []).length > 0 && (
            <div className="mt-2 space-y-1.5">
              {(claim.passages ?? []).map((cite) => (
                <PassageQuote key={`${cite.passageId}-${cite.quote}`} cite={cite} passage={passages.get(cite.passageId)} />
              ))}
            </div>
          )}

          {(claim.evidenceIds ?? []).length > 0 && (
            <div className="mt-2 space-y-1.5">
              {(claim.evidenceIds ?? [])
                .map((id) => evidence.get(id))
                .filter((e): e is Evidence => Boolean(e))
                .map((e) => (
                  <EvidenceCard key={e.id} evidence={e} />
                ))}
            </div>
          )}

          <ModuleRowChips refs={claim.moduleRefs ?? []} rows={rows} />

          {note && <p className="text-caption text-ink-soft mt-1.5">{note}</p>}

          {citedPapers.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
              {citedPapers.map((paper) => (
                <a
                  key={paper.id}
                  href={`#/biorepo/paper/${paper.id}`}
                  className="text-caption text-ink-soft hover:text-accent inline-flex items-baseline gap-1"
                  title={paper.title}
                >
                  <span className="font-num">{paper.id}</span>
                  <span className="truncate max-w-[28ch]">{paper.title}</span>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

/** A runbook the agent drafted (OF-BLD-014 §9.2): its numbers were written by the service. */
function DraftCard({ draft }: { draft: RunbookDraft }) {
  const adopt = useStore((s) => s.adoptRunbookDraft);
  const predictionLabel = (id: string | null) => draft.predictions.find((p) => p.id === id)?.label ?? 'nothing predicted';
  return (
    <Card className="p-4" data-testid="runbook-draft">
      <div className="text-caption uppercase tracking-wide text-ink-soft">Runbook draft</div>
      <div className="font-serif text-section-title font-semibold">{draft.title}</div>
      <p className="text-caption text-ink-soft mb-2">
        Postdoc chose what to predict and measure; every value and interval below was written by the service from the
        artifact or records each prediction names. Adopting it opens an unlocked research runbook for you to read and lock.
      </p>
      <ul className="space-y-1 text-body">
        {draft.predictions.map((p) => (
          <li key={p.id}>
            <span className="font-medium">{p.label}</span>{' '}
            <span className="font-num">
              {p.kind === 'interval' && p.interval
                ? `${fmt(p.interval.low)} to ${fmt(p.interval.high)}`
                : p.kind === 'bound'
                  ? `at most ${fmt(p.value)}`
                  : fmt(p.value)}{' '}
              {p.unit}
            </span>
            <div className="text-caption text-ink-soft">{p.basis}</div>
          </li>
        ))}
      </ul>
      {draft.measures.length > 0 && (
        <div className="text-caption text-ink-soft mt-2">
          Measured: {draft.measures.map((m) => `${m.label} (${m.unit}, ${m.timepoint}) for ${predictionLabel(m.predictionId)}`).join('; ')}.
        </div>
      )}
      <button
        className="btn btn-primary mt-3"
        onClick={() => {
          const id = adopt(draft);
          navigate(`/runbooks/${id}`);
        }}
      >
        Turn into a runbook
      </button>
    </Card>
  );
}

export function AnswerPlanView({ plan }: { plan: AnswerPlan }) {
  const hasClaims = plan.claims.length > 0;
  const passages = new Map((plan.passages ?? []).map((p) => [p.id, p]));
  const evidence = new Map((plan.evidence ?? []).map((e) => [e.id, e]));
  const rows = new Map((plan.rows ?? []).map((r) => [r.ref, r]));
  const toolCalls = (plan.trace ?? []).filter((t) => t.kind === 'tool').length;
  // The loop answered only when its last step is a kept plan; a question no
  // model answered, or an answer that was not a plan, says so (§5.R).
  const last = plan.trace?.[plan.trace.length - 1];
  const answered = last?.kind === 'final' && last.ok;

  return (
    <div className="space-y-4">
      {/* A decline is an ANSWER, and rendered as one. The tone follows
          explainRefusal() in src/engine/units.ts: say what is missing and what
          would establish it, rather than apologising for the absence. */}
      {plan.declined && (
        // A decline the model chose is an answer. A question no model could
        // take up — no key, a spent budget, an answer that never arrived
        // whole — ends on a failed final step, and is titled as a failure.
        <Callout kind="info" title={last?.kind === 'final' && !last.ok ? 'Postdoc could not answer this' : 'Postdoc declined to answer this'}>
          <p className="text-ink">{plan.declined}</p>
          {hasClaims && (
            <p className="text-ink-soft mt-1.5">
              What follows is what the corpus does support, which is less than the question
              asked for.
            </p>
          )}
        </Callout>
      )}

      {hasClaims && (
        <Card className="px-4 py-1">
          <ul>
            {plan.claims.map((claim, i) => (
              <ClaimRow key={claim.id} claim={claim} index={i} passages={passages} evidence={evidence} rows={rows} />
            ))}
          </ul>
        </Card>
      )}

      {!hasClaims && !plan.declined && (
        <Callout kind="info" title="Nothing to show">
          Postdoc returned no claims and no reason. That is a fault in the answer, not a
          statement about the corpus.
        </Callout>
      )}

      {/* Gaps are a section of their own, not a footnote. Naming what is
          absent is the answer §6 asks for most often. */}
      {plan.runbookDraft && <DraftCard draft={plan.runbookDraft} />}

      {plan.gaps.length > 0 && (
        <section aria-labelledby="plan-gaps">
          <div className="flex items-center gap-2 mb-1.5">
            <SearchX size={15} className="text-ink-soft shrink-0" aria-hidden />
            <span id="plan-gaps" className="font-medium text-reading">
              What the corpus does not have
            </span>
          </div>
          <ul className="space-y-1">
            {plan.gaps.map((gap) => (
              <li key={gap} className="text-body text-ink flex items-baseline gap-2">
                <span className="w-1 h-1 rounded-full bg-ink-soft shrink-0 mt-1.5" aria-hidden />
                <span>{gap}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* §5 — rejections are surfaced, not just logged. A rate that climbs is
          the signal that the prompt has drifted, and a count that only reaches
          a log file is a count nobody looks at. */}
      {plan.rejected > 0 && (
        <div className="rounded-card border border-signal-warn/45 bg-signal-warn/[0.08] p-3">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={14} className="text-signal-warn shrink-0" aria-hidden />
            <span className="font-medium text-ink">
              <span className="font-num">{plan.rejected}</span>{' '}
              {plan.rejected === 1 ? 'claim was' : 'claims were'} dropped by the validator
            </span>
          </div>
          <p className="text-body text-ink-soft">
            Dropped whole, never repaired — a claim that fails validation is not shown in any
            form. Numbers belong to the record, not to the sentence.
          </p>
          <ul className="mt-1.5 space-y-0.5">
            {plan.rejectionReasons.map((reason) => (
              <li key={reason} className="font-num text-caption text-ink-soft">
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-1">
        <ComponentTag
          component="Postdoc"
          action={plan.declined ? 'declined' : `${plan.claims.length} claims`}
        />
        {/* Cost is quiet but present. A visible per-query price is what makes
            the budget-gating story real rather than theoretical. The models,
            the tokens with their cached share, and why the loop stopped sit
            beside it (OF-BLD-014 §5.4). */}
        <span
          className="font-num text-caption text-ink-soft inline-flex flex-wrap items-center gap-x-1 gap-y-0.5"
          data-testid="plan-footer"
          title={`${plan.usage.inputTokens} in / ${plan.usage.outputTokens} out`}
        >
          {plan.usage.models && plan.usage.models.length > 0 && (
            <>
              {plan.usage.models.join(' → ')}
              <span className="opacity-45">·</span>
            </>
          )}
          {plan.usage.inputTokens.toLocaleString()} in / {plan.usage.outputTokens.toLocaleString()} out
          {/* OF-BLD-014 §3.3 — how much of the prompt the cache served. */}
          {cachedShare(plan.usage) !== null && (
            <>
              <span className="opacity-45">·</span>
              <span
                title={`${(plan.usage.cacheReadTokens ?? 0).toLocaleString()} prompt tokens read from the cache, ${(plan.usage.cacheWriteTokens ?? 0).toLocaleString()} written to it`}
              >
                {cachedShare(plan.usage)}% of the prompt cached
              </span>
            </>
          )}
          <span className="opacity-45">·</span>
          {formatCost(plan.usage.costUsd)}
          {plan.trace && plan.trace.length > 0 && (
            <>
              <span className="opacity-45">·</span>
              <span className="font-sans">
                {toolCalls} tool {toolCalls === 1 ? 'call' : 'calls'};{' '}
                {answered ? STOPPED_WORDS[plan.stopped ?? 'done'] : 'no answer came back'}
              </span>
            </>
          )}
        </span>
        {plan.coverage && <CoverageFooter coverage={plan.coverage} />}
      </div>
    </div>
  );
}

const WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
const inWords = (n: number) => WORDS[n] ?? String(n);

/**
 * OF-BLD-015 §7.1 — which modules the coverage pass searched and where it
 * found what the question names, with the modules read only in part.
 */
function CoverageFooter({ coverage }: { coverage: CoverageMap }) {
  const found = coverage.modules.filter((m) => m.count > 0);
  const partial = coverage.modules.filter((m) => m.partial);
  return (
    <span className="text-caption text-ink-soft" data-testid="plan-coverage">
      Searched {inWords(coverage.searched)}, found in {coverage.found ? inWords(coverage.found) : 'none'}
      {found.length > 0 && <>: {found.map((m) => `${m.label} (${m.count})`).join(', ')}</>}
      {partial.length > 0 && (
        <span title={partial.map((m) => `${m.label}: ${m.partial}`).join('\n')}>
          {' '}
          · read in part: {partial.map((m) => m.label).join(', ')}
        </span>
      )}
    </span>
  );
}

/** A question the service took and could not answer. Says exactly what to do. */
export function PostdocDownNotice({ message, remedy }: { message: string; remedy: string }) {
  // A remedy writes a command between backticks; show it as one.
  const parts = remedy.split('`');
  return (
    <Callout kind="error" title={message}>
      <p className="text-ink">
        {parts.map((part, i) =>
          i % 2 === 1 ? (
            <code key={i} className="font-num text-caption bg-surface-1 rounded px-1">
              {part}
            </code>
          ) : (
            part
          ),
        )}
      </p>
      <p className="text-ink-soft mt-1.5 inline-flex items-start gap-1.5">
        <HelpCircle size={13} className="shrink-0 mt-0.5" aria-hidden />
        <span>
          Nothing answers in the service's place. A convincing fake standing in for a broken
          service is worse than a blank screen, because everything looks like it is working.
        </span>
      </p>
    </Callout>
  );
}
