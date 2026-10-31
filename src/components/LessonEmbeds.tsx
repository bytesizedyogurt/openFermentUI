// Live lesson embeds (OF-DES-001 §8.14). These are the real components, not
// screenshots — the pedagogy is the product. A decision made in the mini-queue
// here propagates to the strain pages and the validation metrics.
//
// An embed shows what the store holds and nothing typed in its place: one
// whose lesson block names no paper, record, protocol, question or scenario
// says so.
import { useMemo, useState } from 'react';
import { ArrowRight, Check, SkipForward, X } from 'lucide-react';
import { useStore, provenanceOf, aggregateExclusion, isAggregatable, EXCLUSION_NOTE, useSkillById } from '@/store';
import { href, navigate } from '@/router';
import type { FieldId, LessonBlock } from '@/data/types';
import { ONTOLOGY_BY_ID, fieldName } from '@/data/ontology';
import { convert, fmt, asNumber } from '@/engine/units';
import { computeRunMetrics } from '@/engine/metrics';
import { renderStepText } from '@/engine/scale';
import { Card, Button, Callout } from './ui';
import { CitationChip } from './Chip';
import { ProvDot, ProvenanceBadge, Tick } from './Provenance';

type EmbedKind = Extract<LessonBlock, { kind: 'embed' }>['embed'];

function Frame({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="my-5">
      <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">{label}</div>
      <Card className="p-3">{children}</Card>
    </div>
  );
}

function ChipDemo({ paperId }: { paperId: string }) {
  // The sentence is built from the paper's own record rather than hardcoded, so
  // the lesson cannot drift away from what the source actually reports. A demo
  // that misquotes a real paper to teach citation would be self-refuting.
  const paper = useStore((s) => s.papers.find((p) => p.id === paperId));
  const record = useStore((s) =>
    s.records.find((r) => r.paperId === paperId && r.isPrimary) ??
    s.records.find((r) => r.paperId === paperId),
  );

  if (!paper || !record) {
    return (
      <Frame label="Live component — citation chip">
        <p className="text-body text-ink-soft">
          This project holds no record from {paperId}.
        </p>
      </Frame>
    );
  }

  return (
    <Frame label="Live component — hover the chip">
      <p className="text-reading font-serif">
        {paper.title} reports {fieldName(record.field)} of{' '}
        <span className="font-mono text-body">
          {record.value} {record.unit}
        </span>{' '}
        <CitationChip paperId={paperId} />.
      </p>
      <p className="text-caption text-ink-soft mt-2">
        That chip is the same component used in agent answers, protocol references, and simulation
        assumptions. Hover it for the source, click through to read the paper. The sentence above is
        assembled from record{' '}
        <span className="font-mono">{record.id}</span> at render time — change the record and this
        line changes with it.
      </p>
    </Frame>
  );
}

function RecordCard({ recordId }: { recordId: string }) {
  const record = useStore((s) => s.records.find((r) => r.id === recordId));
  if (!record) {
    return (
      <Frame label="Extraction record">
        <p className="text-body text-ink-soft">
          This project holds no record {recordId}.
        </p>
      </Frame>
    );
  }
  const prov = provenanceOf(record);
  return (
    <Frame label="Live extraction record">
      <Tick p={prov}>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="text-caption text-ink-soft">{fieldName(record.field)}</div>
            <div className="font-num text-section-title">
              {fmt(record.value)} {record.unit}
              {record.si.unit !== record.unit && (
                <span className="text-ink-soft text-body ml-2">
                  = {fmt(record.si.value)} {record.si.unit}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <ProvenanceBadge
              p={prov}
              confidence={record.status === 'unverified' ? record.confidence : undefined}
              compact
            />
            <CitationChip recordId={record.id} />
          </div>
        </div>
        <blockquote className="font-serif italic text-body mt-2 border-l-2 border-line pl-2.5">
          “{record.quote}”
        </blockquote>
      </Tick>
    </Frame>
  );
}

function MiniQueue() {
  const records = useStore((s) => s.records);
  const reviewDecide = useStore((s) => s.reviewDecide);
  const [idx, setIdx] = useState(0);
  const [decided, setDecided] = useState<string[]>([]);

  const queue = useMemo(
    () => records.filter((r) => r.status === 'unverified').slice(0, 5),
    // Freeze the queue on first render so decisions do not reshuffle it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const record = queue[idx];

  if (!record) {
    return (
      <Frame label="Review mini-queue">
        <div className="text-center py-4">
          <Check size={22} className="text-accent mx-auto mb-2" />
          <p className="text-body">
            {decided.length > 0
              ? `${decided.length} decision${decided.length === 1 ? '' : 's'} recorded — they are live, and the strain pages and validation metrics have already moved.`
              : 'No unverified records left in this session.'}
          </p>
          <Button className="mt-3" onClick={() => navigate('/guild')}>
            Open the full review queue <ArrowRight size={13} />
          </Button>
        </div>
      </Frame>
    );
  }

  const def = ONTOLOGY_BY_ID[record.field];
  const paper = useStore.getState().papers.find((p) => p.id === record.paperId);
  const section = paper?.sections.find((s) => s.id === record.sectionId);
  const context = section
    ? (() => {
        const at = section.text.indexOf(record.quote);
        if (at < 0) return record.quote;
        const start = Math.max(0, section.text.lastIndexOf('. ', at) + 1);
        const end = section.text.indexOf('. ', at + record.quote.length);
        return section.text.slice(start, end < 0 ? at + record.quote.length + 80 : end + 1).trim();
      })()
    : record.quote;

  const decide = (action: 'accept' | 'reject' | 'skip') => {
    if (action !== 'skip') reviewDecide(record.id, action, { reason: 'wrong value' });
    setDecided((d) => [...d, record.id]);
    setIdx((i) => i + 1);
  };

  return (
    <Frame label={`Review mini-queue — ${idx + 1} of ${queue.length}`}>
      <div className="flex items-center justify-between gap-2 mb-2">
        <CitationChip paperId={record.paperId} />
        <span className="font-num text-caption text-ink-soft">
          confidence {record.confidence.toFixed(2)}
        </span>
      </div>
      <div className="text-caption text-ink-soft">{def.name}</div>
      <div className="font-num text-section-title mb-1">
        {fmt(record.value)} {record.unit}
      </div>
      <p className="text-caption text-ink-soft mb-2">{def.definition}</p>
      <div className="rounded-input border border-line bg-surface-0 p-2 font-serif text-body mb-3">
        {context.split(record.quote).map((part, i, arr) => (
          <span key={i}>
            {part}
            {i < arr.length - 1 && <mark className="span-unverified">{record.quote}</mark>}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" onClick={() => decide('accept')}>
          <Check size={13} /> Accept
        </Button>
        <Button onClick={() => decide('reject')}>
          <X size={13} /> Reject
        </Button>
        <Button onClick={() => decide('skip')}>
          <SkipForward size={13} /> Skip
        </Button>
      </div>
      <p className="text-caption text-ink-soft mt-2">
        These call the real store actions — whatever you decide here is what the rest of the platform
        will show.
      </p>
    </Frame>
  );
}

function MetricsTiles() {
  const runOutputs = useStore((s) => s.runOutputs);
  const records = useStore((s) => s.records);
  const latest = runOutputs[runOutputs.length - 1];
  const metrics = latest ? computeRunMetrics(latest, records) : null;

  if (!metrics) {
    return (
      <Frame label="Validation metrics">
        <p className="text-body text-ink-soft">No extractor runs are loaded in this session.</p>
      </Frame>
    );
  }

  return (
    <Frame label={`Live metrics — extractor ${metrics.run}`}>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Precision', value: metrics.micro.precision },
          { label: 'Recall', value: metrics.micro.recall },
          { label: 'F1', value: metrics.micro.f1 },
        ].map((t) => (
          <Tick key={t.label} p="gold">
            <div className="text-caption uppercase tracking-wide text-ink-soft">{t.label}</div>
            <div className="font-num text-section-title">{t.value.toFixed(3)}</div>
          </Tick>
        ))}
        <Tick p="gold">
          <div className="text-caption uppercase tracking-wide text-ink-soft">Gold set</div>
          <div className="font-num text-section-title">{metrics.goldSize}</div>
          <div className="text-caption text-ink-soft">{metrics.papersCovered} papers</div>
        </Tick>
      </div>
      <p className="text-caption text-ink-soft mt-2">
        Computed from this session's gold set. TP {metrics.micro.tp} · FP {metrics.micro.fp} · FN{' '}
        {metrics.micro.fn}.{' '}
        <button className="text-accent hover:underline" onClick={() => navigate('/biorepo/witness')}>
          Open the full dashboard
        </button>
      </p>
    </Frame>
  );
}

function StripPlot({ field }: { field: FieldId }) {
  const records = useStore((s) => s.records);
  const def = ONTOLOGY_BY_ID[field];

  const points = useMemo(() => {
    if (!def) return [];
    return records
      .filter((r) => r.field === field && r.status !== 'rejected')
      .map((r) => {
        try {
          return {
            r,
            v:
              def.canonicalUnit === ''
                ? asNumber(r.value)
                : convert(asNumber(r.value) ?? NaN, r.unit, def.canonicalUnit),
          };
        } catch {
          return null;
        }
      })
      .filter(Boolean) as { r: (typeof records)[number]; v: number }[];
  }, [records, field, def]);

  if (!def || points.length === 0) {
    return (
      <Frame label="Strip plot">
        <p className="text-body text-ink-soft">No records for this parameter in this session.</p>
      </Frame>
    );
  }

  const values = points.map((p) => p.v);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;

  // Every record is drawn — the plot is how you reach a single span. The count
  // below separates the ones that may enter a statistic from the ones that may
  // not, because two dots for one measurement is exactly the reading error the
  // primacy flag exists to prevent.
  const held = points.filter((p) => !isAggregatable(p.r)).length;

  return (
    <Frame label={`Live strip plot — ${def.name}`}>
      <div className="relative h-16">
        <div className="absolute left-0 right-0 top-7 h-px bg-line" />
        {points.map((p, i) => {
          const excl = aggregateExclusion(p.r);
          return (
            <button
              key={p.r.id}
              className="absolute -translate-x-1/2 hover:scale-150 transition-transform"
              style={{ left: `${((p.v - lo) / span) * 96 + 2}%`, top: 22 + ((i % 5) - 2) * 6 }}
              onClick={() => navigate(`/biorepo/paper/${p.r.paperId}?span=${p.r.id}`)}
              title={`${fmt(p.v)} ${def.canonicalUnit} — ${p.r.paperId} · ${p.r.status}${
                excl ? ` · ${EXCLUSION_NOTE[excl]}` : ''
              }`}
              aria-label={`${fmt(p.v)} ${def.canonicalUnit} from ${p.r.paperId}${
                excl ? ', excluded from the statistics' : ''
              }`}
            >
              <ProvDot p={provenanceOf(p.r)} size={9} />
            </button>
          );
        })}
        <span className="absolute left-0 bottom-0 text-caption font-num text-ink-soft">
          {fmt(lo)} {def.canonicalUnit}
        </span>
        <span className="absolute right-0 bottom-0 text-caption font-num text-ink-soft">
          {fmt(hi)}
        </span>
      </div>
      <p className="text-caption text-ink-soft mt-1">
        {points.length} records, every one clickable through to its source span. Colour is
        provenance, not value.
        {held > 0 && (
          <>
            {' '}
            {held} of them never enter a median or range — industry estimates, and records quoting
            another paper&rsquo;s measurement rather than reporting their own.
          </>
        )}
      </p>
    </Frame>
  );
}

function ProtocolCard({ protocolId }: { protocolId: string }) {
  const protocol = useStore((s) => s.protocols.find((p) => p.id === protocolId));
  if (!protocol) {
    return (
      <Frame label="Protocol">
        <p className="text-body text-ink-soft">Protocol {protocolId} is not loaded in this session.</p>
      </Frame>
    );
  }
  const v = protocol.versions.find((x) => x.version === protocol.currentVersion);
  return (
    <Frame label="Live protocol">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="font-serif text-section-title font-semibold">{protocol.title}</div>
          <div className="text-caption text-ink-soft font-num">
            {protocol.id} · v{protocol.currentVersion} · {v?.steps.length} steps ·{' '}
            {v?.estMinutes.active} min active / {v?.estMinutes.total} min total
          </div>
          <p className="text-body text-ink-soft mt-1">{protocol.purpose}</p>
        </div>
        <Button variant="primary" onClick={() => navigate(`/runbooks/protocols/${protocol.id}`)}>
          Open <ArrowRight size={13} />
        </Button>
      </div>
    </Frame>
  );
}

/**
 * The steps a skill is needed for, read live from the protocols, with what an
 * assessor watches for (OF-BLD-013 §3.1). Every number the learner sees here
 * is the protocol's own, rendered by the same code run mode uses, so a lesson
 * built on this embed carries no quantity of its own.
 */
function SkillSteps({ skillId }: { skillId: string }) {
  const SKILL_BY_ID = useSkillById();
  const protocols = useStore((s) => s.protocols);
  const skill = SKILL_BY_ID[skillId];
  if (!skill) {
    return (
      <Frame label="Skill">
        <p className="text-body text-ink-soft">{skillId || 'This embed'} names no skill the lab holds.</p>
      </Frame>
    );
  }
  const uses = protocols.flatMap((p) => {
    const v = p.versions.find((x) => x.version === p.currentVersion) ?? p.versions[0];
    return v.steps.filter((st) => st.skills?.includes(skillId)).map((st) => ({ p, v, st }));
  });
  return (
    <Frame label={`Where ${skill.name} is used`}>
      <p className="text-body text-ink-soft mb-2">
        {skill.summary}{' '}
        <a className="text-accent hover:underline" href={href(`/guild/skills/${skill.id}`)}>
          The skill in Guild
        </a>
      </p>
      <ol className="space-y-2.5">
        {uses.map(({ p, v, st }) => (
          <li key={p.id + st.id} className="border-l-2 border-line pl-3">
            <div className="text-caption text-ink-soft">
              <a className="text-accent hover:underline" href={href(`/runbooks/protocols/${p.id}`)}>
                {p.id}
              </a>{' '}
              · step <span className="font-num">{st.id}</span>
            </div>
            <div className="text-body">{renderStepText(st, v, 1)}</div>
            {st.note && <div className="text-caption text-ink-soft mt-0.5">Why: {st.note}</div>}
          </li>
        ))}
      </ol>
      <div className="mt-3 pt-2 border-t border-line">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">What an assessor watches for</div>
        <ul className="list-disc pl-5 space-y-0.5">
          {skill.mastery.map((m) => (
            <li key={m} className="text-body">
              {m}
            </li>
          ))}
        </ul>
      </div>
    </Frame>
  );
}

function AskPrompt({ question }: { question: string }) {
  return (
    <Frame label="Try it">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="font-serif text-reading italic flex-1 min-w-[200px]">“{question}”</p>
        <Button
          variant="primary"
          onClick={() => navigate(`/postdoc?q=${encodeURIComponent(question)}`)}
        >
          Ask the agent <ArrowRight size={13} />
        </Button>
      </div>
    </Frame>
  );
}

/** A scenario a lesson names, opened where the service simulates it. */
function ScenarioWidget({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  if (!scenario) {
    return (
      <Frame label="Scenario">
        <p className="text-body text-ink-soft">Scenario {scenarioId} is not loaded in this session.</p>
      </Frame>
    );
  }
  return (
    <Frame label={`Scenario — ${scenario.name}`}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-body text-ink-soft flex-1 min-w-[200px]">
          {scenario.name} is simulated on the service. Its page shows every input with where it came from.
        </p>
        <Button variant="primary" onClick={() => navigate(`/proforma/scenario/${encodeURIComponent(scenario.id)}`)}>
          Open in Proforma <ArrowRight size={13} />
        </Button>
      </div>
    </Frame>
  );
}

/** What an embed shows when its lesson block names nothing for it to show. */
function Unnamed({ label, what }: { label: string; what: string }) {
  return (
    <Frame label={label}>
      <p className="text-body text-ink-soft">This embed names no {what}.</p>
    </Frame>
  );
}

export function LessonEmbed({ embed, arg }: { embed: EmbedKind; arg?: string }) {
  switch (embed) {
    case 'chip-demo':
      return arg ? <ChipDemo paperId={arg} /> : <Unnamed label="Citation chip" what="paper" />;
    case 'record-card':
      return arg ? <RecordCard recordId={arg} /> : <Unnamed label="Extraction record" what="record" />;
    case 'mini-queue':
      return <MiniQueue />;
    case 'metrics-tiles':
      return <MetricsTiles />;
    case 'strip-plot':
      return <StripPlot field={(arg as FieldId) ?? 'growth_rate_mu'} />;
    case 'protocol-card':
      return arg ? <ProtocolCard protocolId={arg} /> : <Unnamed label="Protocol" what="protocol" />;
    case 'ask-prompt':
      return arg ? <AskPrompt question={arg} /> : <Unnamed label="Try it" what="question" />;
    case 'skill-steps':
      return <SkillSteps skillId={arg ?? ''} />;
    case 'scenario-widget':
      return arg ? <ScenarioWidget scenarioId={arg} /> : <Unnamed label="Scenario" what="scenario" />;
    default:
      return (
        <div className="my-4">
          <Callout kind="warn">
            This lesson asks for an embed of type <span className="font-num">{String(embed)}</span>,
            which this build does not implement. Nothing is being hidden — the block simply has no
            component behind it yet.
          </Callout>
        </div>
      );
  }
}
