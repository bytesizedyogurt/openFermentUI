// Process train (OF-BLD-005 §6) — the downstream chain from fermenter to
// finished vial, annotated per step.
//
// This is the one genuinely new visual in this build, and it earns its place
// because it answers the question a facility asks before it buys anything:
// what equipment does this molecule need, in what order, and where does the
// cost actually sit. Two products that look unrelated in a catalogue turn out
// to share a train; two that look adjacent turn out to need separate lines.
//
// It sits BENEATH the gold provenance tick in the visual hierarchy, and does
// so on purpose. Evidence outranks process. So the train draws in accent and
// line tokens and never in gold, uses the existing radii and type scale, and
// introduces no colour of its own.
//
// Every node is a Sheet away from its full vocabulary record — that is how
// unit operations get detail pages without earning a rail destination.
import { Fragment, useState } from 'react';
import { ArrowRight, FlaskConical, Package, Snowflake, Sun } from 'lucide-react';
import { STRAINS_BY_ID } from '@/data/strains';
import { SCALES_BY_ID, STORAGE_FORMATS_BY_ID, UNIT_OPERATIONS_BY_ID } from '@/data/vocabulary';
import type { UnitOperation } from '@/data/types';
import { Callout, EmptyState, Sheet, cx } from './ui';

/** Terminal nodes are drawn differently from operations — they are context. */
function Terminal({
  kind,
  title,
  lines,
}: {
  kind: 'start' | 'end';
  title: string;
  lines: { text: string; className?: string }[];
}) {
  const Icon = kind === 'start' ? FlaskConical : Package;
  return (
    <li className="shrink-0 w-[172px]">
      <div className="rounded-card border border-accent/35 bg-accent-wash/50 p-2.5 h-full">
        <div className="flex items-center gap-1.5 text-caption uppercase tracking-wide text-accent">
          <Icon size={12} aria-hidden />
          {kind === 'start' ? 'Fermenter' : 'Finished form'}
        </div>
        <div className="text-body font-medium mt-1 leading-snug">{title}</div>
        {lines.map((l) => (
          <div key={l.text} className={cx('text-caption mt-0.5 leading-snug', l.className ?? 'text-ink-soft')}>
            {l.text}
          </div>
        ))}
      </div>
    </li>
  );
}

function Connector() {
  return (
    <li className="shrink-0 self-center px-0.5 text-accent/50" aria-hidden>
      <ArrowRight size={14} />
    </li>
  );
}

function OpNode({
  op,
  index,
  onOpen,
}: {
  op: UnitOperation;
  index: number;
  onOpen: () => void;
}) {
  return (
    <li className="shrink-0 w-[164px]">
      <button
        onClick={onOpen}
        className="w-full h-full text-left rounded-card border border-line bg-surface-1 p-2.5 transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
        title={op.note ? `${op.label} — ${op.note}` : op.label}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-caption uppercase tracking-wide text-ink-soft truncate">
            {op.stage}
          </span>
          <span className="font-num text-caption text-ink-soft shrink-0">{index}</span>
        </div>
        <div className="text-body font-medium mt-1 leading-snug">{op.label}</div>
        {op.note && <div className="text-caption text-ink-soft mt-0.5 leading-snug">{op.note}</div>}
      </button>
    </li>
  );
}

export function ProcessTrain({
  unitOperationIds,
  strainId,
  storageIds = [],
  scaleId,
  processCode,
  emptyBody,
}: {
  /** Ordered fermenter to vial. This array is the train — stage order is not. */
  unitOperationIds: string[];
  strainId?: string | null;
  storageIds?: string[];
  scaleId?: string | null;
  processCode?: string;
  emptyBody?: string;
}) {
  const [open, setOpen] = useState<UnitOperation | null>(null);

  const ops = unitOperationIds
    .map((id) => UNIT_OPERATIONS_BY_ID[id])
    .filter((o): o is UnitOperation => Boolean(o));

  const strain = strainId ? STRAINS_BY_ID[strainId] : undefined;
  const scale = scaleId ? SCALES_BY_ID[scaleId] : undefined;

  // The warmest available format is the one that decides the cold chain: if
  // anything ships at 25 °C, the facility has an option that skips dry ice.
  const formats = storageIds.map((s) => STORAGE_FORMATS_BY_ID[s]).filter(Boolean);
  const warmest = [...formats].sort((a, b) => b.tempC - a.tempC)[0];
  const ambient = warmest ? warmest.tempC >= 25 : false;

  if (ops.length === 0) {
    return (
      <EmptyState
        title="No process train defined"
        body={
          emptyBody ??
          'No unit operations are declared here yet. A train is a sequence of named operations, not a simulation — this one has not been named.'
        }
        icon={<Package size={22} aria-hidden />}
      />
    );
  }

  return (
    <div>
      <ol className="flex items-stretch gap-1 overflow-x-auto pb-2" aria-label="Process train">
        <Terminal
          kind="start"
          title={strain ? strain.binomial : 'Host not chosen'}
          lines={[
            { text: strain ? strain.designation : 'Pick a host to fix the train' },
            ...(scale ? [{ text: `${scale.label} · ${scale.volumeL} L` }] : []),
          ]}
        />
        {ops.map((op, i) => (
          // A step can legitimately repeat inside one train, so the key pairs
          // the operation id with its position rather than trusting the id.
          <Fragment key={`${op.id}-${i}`}>
            <Connector />
            <OpNode op={op} index={i + 1} onOpen={() => setOpen(op)} />
          </Fragment>
        ))}
        <Connector />
        <Terminal
          kind="end"
          title={warmest ? warmest.label : 'Format not chosen'}
          lines={
            warmest
              ? [
                  { text: warmest.logistics, className: ambient ? 'text-accent' : 'text-ink-soft' },
                  { text: `shelf life ${warmest.shelfLife}` },
                ]
              : [{ text: 'No storage format declared' }]
          }
        />
      </ol>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-soft">
        <span className="font-num">
          {ops.length} unit operation{ops.length === 1 ? '' : 's'}
        </span>
        {processCode && <span>process family {processCode}</span>}
        {warmest && (
          <span className={cx('inline-flex items-center gap-1', ambient ? 'text-accent' : undefined)}>
            {ambient ? <Sun size={12} aria-hidden /> : <Snowflake size={12} aria-hidden />}
            {ambient
              ? 'ships ambient — no cold chain'
              : `cold chain required down to ${warmest.tempC} °C`}
          </span>
        )}
        <span>click a step for its definition</span>
      </div>

      <Sheet
        open={open !== null}
        onClose={() => setOpen(null)}
        title={open?.label ?? 'Unit operation'}
        width={480}
      >
        {open && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip text-ink-soft">{open.stage}</span>
              <span className="chip text-ink-soft font-num">{open.id}</span>
              {open.scale && <span className="chip text-ink-soft">scale: {open.scale}</span>}
              {open.resin && <span className="chip text-ink-soft">{open.resin}</span>}
            </div>

            {open.note && <p className="font-serif text-reading">{open.note}</p>}

            {/* §10 — a shallow facet is a labelled black box, not a failure. */}
            <Callout kind="info" title="No process model yet">
              This unit operation is defined but not simulated. openFerment knows where the step
              sits in the train and what it is for; it does not model its yield, its buffer
              consumption or its cycle time. Those would come from a process model this build does
              not have, and inventing them would be worse than saying so.
            </Callout>
          </div>
        )}
      </Sheet>
    </div>
  );
}
