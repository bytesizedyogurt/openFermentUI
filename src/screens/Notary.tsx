// Notary (OF-FE-004 §3) — the disclosure queue and the enablement checklist.
//
// The honest first result is that nothing passes, and that is the artifact.
// A design derived from a cost grid has an equipment train and a mass balance
// and no genotype, no medium composition, no conditions. A screen itemising
// exactly what a disclosure would need before it could bar a patent is worth
// more than a queue of publishable cards, because it makes the gap precise
// instead of implying there isn't one.
//
// Enablement is computed from the design, not stored on it — §0's rule that
// anything the engine can compute is computed.
import { useMemo, useState } from 'react';
import { Stamp, Check, X } from 'lucide-react';
import { DESIGNS } from '@/data/designs';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { Card, PageHeader, SectionTitle, Callout, Button, Explain, cx } from '@/components/ui';
import type { DesignRecord, PublicationStatus } from '@/data/types';

interface Requirement {
  id: string;
  label: string;
  met: boolean;
  /** What is missing, when it is. Named specifically, never "incomplete". */
  missing?: string;
}

/**
 * A disclosure is enabling when someone skilled in the art could reproduce the
 * result from it. Each item below is a thing a reader would need and cannot
 * currently get from a design derived from a sweep grid.
 */
function enablement(d: DesignRecord): Requirement[] {
  const t0 = d.tiers.find((t) => t.tier === 'T0');
  const t3 = d.tiers.find((t) => t.tier === 'T3');
  const hasFlux = d.tiers.some((t) => t.tier === 'T1' && t.state !== 'absent');
  const hasReactor = d.tiers.some((t) => t.tier === 'T2' && t.state !== 'absent');

  return [
    {
      id: 'host',
      label: 'Host and genotype',
      met: false,
      missing:
        'A design is a point in a cost sweep. It names no strain, no construct, no integration locus — none of which a grid carries.',
    },
    {
      id: 'medium',
      label: 'Medium composition',
      met: false,
      missing:
        'The model prices a medium; it does not state what is in it. A price is not a recipe.',
    },
    {
      id: 'conditions',
      label: 'Cultivation conditions',
      met: false,
      missing:
        'Temperature, light regime, pH and feed schedule are absent. Ontology v1 has no field for most of them, so no record could supply them either.',
    },
    {
      id: 'equipment',
      label: 'Equipment train with sizing basis',
      met: Boolean(t3),
      missing: t3 ? undefined : 'No cost tier ran, so there is no sizing basis.',
    },
    {
      id: 'balance',
      label: 'Mass and energy balance',
      met: t0?.state === 'passed',
      missing:
        t0?.state === 'passed'
          ? undefined
          : 'T0 did not pass, so the configuration is not known to sit inside physically meaningful bounds.',
    },
    {
      id: 'performance',
      label: 'Performance with uncertainty',
      met: false,
      missing:
        'The grid holds one MSP per point and no interval. A point estimate is a performance claim without an uncertainty, which is exactly what a disclosure may not assert.',
    },
    {
      id: 'reasoning',
      label: 'Reasoning from biology to result',
      met: hasFlux && hasReactor,
      missing:
        hasFlux && hasReactor
          ? undefined
          : 'T1 and T2 are absent. The economics were modelled without the biology being checked, so nothing connects the host to the number.',
    },
  ];
}

const COLUMNS: { status: string; label: string }[] = [
  { status: 'draft', label: 'Draft' },
  { status: 'counsel-review', label: 'Counsel review' },
  { status: 'hold', label: 'Hold' },
  { status: 'publish', label: 'Cleared to publish' },
  { status: 'published', label: 'Published' },
];

function statusKey(p: PublicationStatus): string {
  return typeof p === 'string' ? p : 'embargo';
}

export function Notary() {
  const [selected, setSelected] = useState<string | null>(null);
  const design = useMemo(() => DESIGNS.find((d) => d.id === selected) ?? DESIGNS[0], [selected]);
  const reqs = design ? enablement(design) : [];
  const unmet = reqs.filter((r) => !r.met);

  const blockedByScope = design?.scope === 'claimed';
  const canPublish = unmet.length === 0 && !blockedByScope;

  const everPasses = DESIGNS.filter((d) => enablement(d).every((r) => r.met)).length;

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        eyebrow="Return · Notary"
        title="Disclosure queue"
        subtitle="A disclosure that does not enable is worthless as prior art. Publish stays disabled until it would teach someone to reproduce the result."
      />

      <div className="max-w-3xl mb-5">
        <Callout
          kind="warn"
          title={`Nothing currently passes — ${everPasses} of ${DESIGNS.length} designs are publishable`}
        >
          <p className="mb-2">
            That is the finding, not a bug. Every design in this build is a point in a cost sweep:
            it has an equipment train and a mass balance, and no genotype, no medium composition
            and no conditions. None of those live in a grid, and most have no ontology field a
            record could supply them through.
          </p>
          <p>
            The checklist below is the gap made precise — a list of exactly what would have to
            exist before a disclosure could bar a patent.
          </p>
        </Callout>
      </div>

      {/* ── queue by status ── */}
      <section className="mb-6">
        <SectionTitle>Queue</SectionTitle>
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {COLUMNS.map((col) => {
            const items = DESIGNS.filter((d) => statusKey(d.publication) === col.status);
            return (
              <div key={col.status} className="min-w-0">
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
                  {col.label}{' '}
                  <span className="font-num">{items.length}</span>
                </div>
                <div className="space-y-1">
                  {items.slice(0, 6).map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setSelected(d.id)}
                      className={cx(
                        'w-full text-left text-caption border rounded-card px-2 py-1.5 transition-colors',
                        design?.id === d.id
                          ? 'border-accent bg-accent-wash'
                          : 'border-line hover:border-accent/45',
                      )}
                    >
                      <span className="font-mono">{d.id}</span>
                    </button>
                  ))}
                  {items.length > 6 && (
                    <div className="text-caption text-ink-soft">
                      …and {items.length - 6} more
                    </div>
                  )}
                  {items.length === 0 && (
                    <div className="text-caption text-ink-soft">—</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── enablement ── */}
      {design && (
        <section>
          <SectionTitle
            right={
              <Explain label="What is enablement?">
                A patent application must teach someone skilled in the art to reproduce the
                invention. A defensive publication has to clear the same bar to count as prior
                art — a disclosure nobody could follow blocks nothing. Publish is disabled here
                until every item is satisfied, with the missing ones named rather than counted.
              </Explain>
            }
          >
            Enablement — <span className="font-mono">{design.id}</span>
          </SectionTitle>

          <div className="space-y-1.5 mb-4">
            {reqs.map((r) => (
              <Card key={r.id} className={cx('p-2.5', !r.met && 'border-signal-warn/40')}>
                <div className="flex items-start gap-2">
                  {r.met ? (
                    <Check size={14} className="text-accent mt-0.5 shrink-0" aria-hidden />
                  ) : (
                    <X size={14} className="text-signal-warn mt-0.5 shrink-0" aria-hidden />
                  )}
                  <div className="min-w-0">
                    <div className="text-body">{r.label}</div>
                    {r.missing && (
                      <div className="text-caption text-ink-soft mt-0.5">{r.missing}</div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Button disabled={!canPublish}>
              <Stamp size={13} /> Publish
            </Button>
            <span className="text-caption text-signal-warn">
              {blockedByScope
                ? 'Blocked: a design inside a live claim can never be published from here.'
                : `Disabled — ${unmet.length} enablement item${unmet.length === 1 ? '' : 's'} outstanding: ${unmet
                    .map((r) => r.label.toLowerCase())
                    .join(', ')}.`}
            </span>
          </div>

          <p className="text-caption text-ink-soft mt-3 max-w-3xl">
            Scope for this design is <span className="font-mono">{design.scope}</span>, but{' '}
            <span className="font-mono">scopeEvaluated</span> is{' '}
            {String(design.scopeEvaluated)} — Parchment holds no parsed claim bounds, so nothing
            has checked it. The hard gate on a{' '}
            <span className="font-mono">claimed</span> design is in place and has not been
            exercised, because nothing has been classified.{' '}
            <a href={href('/parchment')} className="text-accent hover:underline">
              Open Parchment
            </a>
          </p>
        </section>
      )}
    </div>
  );
}
