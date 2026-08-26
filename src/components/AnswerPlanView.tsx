// Rendering an AnswerPlan (OF-BLD-007 §8).
//
// THIS COMPONENT IS WHERE RULE 1 BECOMES VISIBLE. The model wrote the sentence
// and cited a record; every number on this screen is read out of that record by
// the code below. Nothing here prints model prose containing a quantity,
// because the validator guarantees the prose has none:
//
//   plan says    "Titre at harvest in cw15 under mixotrophic conditions"  r-A1-1
//   this renders  Titre at harvest in cw15 under mixotrophic conditions
//                 0.2 % TSP · Curated · pending source check · A1
//
// The provenance tick reuses the existing visual language rather than inventing
// a fourth one — a claim is evidence, and evidence in this system is ticked.
import { AlertTriangle, ExternalLink, HelpCircle, Quote, SearchX } from 'lucide-react';
import type { AnswerPlan, Claim, ExtractionRecord, Paper } from '@/data/types';
import { useStore, provenanceOf } from '@/store';
import { navigate } from '@/router';
import { fmt } from '@/engine/units';
import { ProvenanceBadge, Tick } from './Provenance';
import { ComponentTag } from './ComponentTag';
import { Callout, Card } from './ui';
import { formatCost } from '@/lib/postdoc';

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

const SUPPORT_NOTE: Record<Claim['support'], string | null> = {
  direct: null,
  inferred: 'Inferred — this follows from the cited records rather than being stated by one.',
  unsupported:
    'Stated as an absence. No record backs this, which is the point of it — nobody has measured it.',
};

function ClaimRow({ claim, index }: { claim: Claim; index: number }) {
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

          {cited.length > 0 && (
            <div className="mt-2 space-y-1.5">
              {cited.map((record) => (
                <RecordValue key={record.id} record={record} />
              ))}
            </div>
          )}

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

export function AnswerPlanView({ plan }: { plan: AnswerPlan }) {
  const hasClaims = plan.claims.length > 0;

  return (
    <div className="space-y-4">
      {/* A decline is an ANSWER, and rendered as one. The tone follows
          explainRefusal() in src/engine/units.ts: say what is missing and what
          would establish it, rather than apologising for the absence. */}
      {plan.declined && (
        <Callout kind="info" title="Postdoc declined to answer this">
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
              <ClaimRow key={claim.id} claim={claim} index={i} />
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
            the budget-gating story real rather than theoretical. */}
        {plan.usage.outputTokens > 0 && (
          <span
            className="font-num text-caption text-ink-soft inline-flex items-center gap-1"
            title={`${plan.usage.inputTokens} in / ${plan.usage.outputTokens} out`}
          >
            {formatCost(plan.usage.costUsd)}
            <span className="opacity-45">·</span>
            {plan.usage.inputTokens.toLocaleString()} in / {plan.usage.outputTokens.toLocaleString()} out
          </span>
        )}
      </div>
    </div>
  );
}

/** The service is not running. Says exactly what to type. */
export function PostdocDownNotice({ message, remedy }: { message: string; remedy: string }) {
  return (
    <Callout kind="error" title={message}>
      <p className="text-ink">{remedy}</p>
      <p className="text-ink-soft mt-1.5 inline-flex items-start gap-1.5">
        <HelpCircle size={13} className="shrink-0 mt-0.5" aria-hidden />
        <span>
          The scripted conversations are not used as a fallback. A convincing fake standing in
          for a broken service is worse than a blank screen, because everything looks like it is
          working.
        </span>
      </p>
    </Callout>
  );
}
