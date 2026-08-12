// Live lesson embeds (OF-DES-001 §8.14). These are the real components, not
// screenshots — the pedagogy is the product. A decision made in the mini-queue
// here propagates to the strain pages and the validation metrics.
import { useMemo, useState } from 'react';
import { ArrowRight, Check, SkipForward, X } from 'lucide-react';
import { useStore, provenanceOf, aggregateExclusion, isAggregatable, EXCLUSION_NOTE } from '@/store';
import { navigate } from '@/router';
import type { FieldId, LessonBlock } from '@/data/types';
import { ONTOLOGY } from '@/data/source';
import { ONTOLOGY_BY_ID, fieldName } from '@/data/ontology';
import { convert, fmt, asNumber } from '@/engine/units';
import { computeRunMetrics } from '@/engine/metrics';
import { evaluateGrid } from '@/engine/grids';
import { Card, Button, cx, Callout } from './ui';
import { CitationChip } from './Chip';
import { QuantityField } from './QuantityField';
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
          No catalogued record for {paperId} in this session — it may have been reset.
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
          Record {recordId} is not in this session — it may have been reset.
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

function UnitPlayground() {
  const [field, setField] = useState<FieldId>('growth_rate_mu');
  const def = ONTOLOGY_BY_ID[field];
  // Seeded the same way switching fields reseeds it, so the starting value is a
  // point in the ontology's declared range rather than a leftover literal.
  const [value, setValue] = useState<{ value: number; unit: string }>(() => ({
    value: Number(((def.range[0] + def.range[1]) / 4).toPrecision(2)),
    unit: def.canonicalUnit,
  }));

  return (
    <Frame label="Live unit field — type into it">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[220px]">
          <label className="text-caption text-ink-soft block mb-1" htmlFor="pg-field">
            Parameter
          </label>
          <select
            id="pg-field"
            className="input"
            value={field}
            onChange={(e) => {
              const next = e.target.value as FieldId;
              setField(next);
              const d = ONTOLOGY_BY_ID[next];
              setValue({
                value: Number(((d.range[0] + d.range[1]) / 4).toPrecision(2)),
                unit: d.canonicalUnit,
              });
            }}
          >
            {ONTOLOGY.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-[220px] flex-1">
          <label className="text-caption text-ink-soft block mb-1" htmlFor="pg-value">
            Value with unit
          </label>
          <QuantityField
            id="pg-value"
            field={field}
            value={value}
            onChange={(v) => v && setValue(v)}
          />
        </div>
      </div>
      <p className="text-caption text-ink-soft mt-2">
        Canonical unit <span className="font-num">{def.canonicalUnit || 'dimensionless'}</span>,
        validation range{' '}
        <span className="font-num">
          {def.range[0]}–{def.range[1]}
        </span>
        . Try a per-day rate, an out-of-range value, and something dimensionally wrong.
      </p>
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
          <Button className="mt-3" onClick={() => navigate('/trawl/review')}>
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
        <button className="text-accent hover:underline" onClick={() => navigate('/assay')}>
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

  const values = points.map((p) => p.v).filter((v) => v >= def.range[0] && v <= def.range[1]);
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
        {points
          .filter((p) => p.v >= def.range[0] && p.v <= def.range[1])
          .map((p, i) => {
            const excl = aggregateExclusion(p.r);
            return (
              <button
                key={p.r.id}
                className="absolute -translate-x-1/2 hover:scale-150 transition-transform"
                style={{ left: `${((p.v - lo) / span) * 96 + 2}%`, top: 22 + ((i % 5) - 2) * 6 }}
                onClick={() => navigate(`/library/papers/${p.r.paperId}?span=${p.r.id}`)}
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
        <Button variant="primary" onClick={() => navigate(`/protocols/${protocol.id}`)}>
          Open <ArrowRight size={13} />
        </Button>
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
          onClick={() => navigate(`/ask?q=${encodeURIComponent(question)}`)}
        >
          Ask the agent <ArrowRight size={13} />
        </Button>
      </div>
    </Frame>
  );
}

function ScenarioWidget({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const grids = useStore((s) => s.grids);
  const [local, setLocal] = useState<number | null>(null);

  if (!scenario) {
    return (
      <Frame label="Scenario">
        <p className="text-body text-ink-soft">Scenario {scenarioId} is not loaded in this session.</p>
      </Frame>
    );
  }
  const grid = grids[scenario.modelId];
  const dim = scenario.dims[0];
  const value = local ?? scenario.point[dim.key];
  const result = grid ? evaluateGrid(grid, { ...scenario.point, [dim.key]: value }) : null;

  return (
    <Frame label={`Live model — ${scenario.name}`}>
      <div className="flex flex-wrap items-end gap-5">
        <Tick p="demo" className="min-w-[170px]">
          <div className="text-caption uppercase tracking-wide text-ink-soft">
            Minimum selling price
          </div>
          <div className="font-num text-display leading-none">
            ${result ? fmt(result.msp, 1) : '—'}
            <span className="text-body text-ink-soft ml-1">/kg</span>
          </div>
          <div className="text-caption text-ink-soft">
            Demo model v0 — illustrative economics, not validated
          </div>
        </Tick>
        <div className="flex-1 min-w-[220px]">
          <div className="flex items-baseline justify-between mb-1">
            <label htmlFor={`w-${dim.key}`} className="text-body">
              {dim.label}
            </label>
            <span className="font-num text-body">
              {fmt(value)} {dim.unit}
            </span>
          </div>
          <input
            id={`w-${dim.key}`}
            type="range"
            min={dim.values[0]}
            max={dim.values[dim.values.length - 1]}
            step={(dim.values[dim.values.length - 1] - dim.values[0]) / 100}
            value={value}
            onChange={(e) => setLocal(Number(e.target.value))}
            aria-label={dim.label}
          />
        </div>
      </div>
    </Frame>
  );
}

export function LessonEmbed({ embed, arg }: { embed: EmbedKind; arg?: string }) {
  switch (embed) {
    case 'chip-demo':
      return <ChipDemo paperId={arg ?? 'M7'} />;
    case 'record-card':
      return <RecordCard recordId={arg ?? 'r-C2-1'} />;
    case 'unit-playground':
      return <UnitPlayground />;
    case 'mini-queue':
      return <MiniQueue />;
    case 'metrics-tiles':
      return <MetricsTiles />;
    case 'strip-plot':
      return <StripPlot field={(arg as FieldId) ?? 'growth_rate_mu'} />;
    case 'protocol-card':
      return <ProtocolCard protocolId={arg ?? 'PR-TAP-01'} />;
    case 'ask-prompt':
      return <AskPrompt question={arg ?? 'What growth rates are reported for cw15 in TAP'} />;
    case 'scenario-widget':
      return <ScenarioWidget scenarioId={arg ?? 'sc-s1'} />;
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
