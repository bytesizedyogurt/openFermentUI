// Clearance surfaces (OF-BLD-005 §8). Clearance renders wherever a molecule
// renders — it is an ambient property, never a separate mode — so the pieces
// live here and every screen composes the same ones.
//
// Three rules hold everywhere:
//   1. The state is shown with the action it implies, never bare.
//   2. Territoriality is structural, so the matrix is per jurisdiction.
//   3. The counsel warning is fixed and non-dismissible.
//
// No new colour or confidence vocabulary: risk maps onto the existing signal
// tokens, and the modeled nature of the verdict is carried by the same 'demo'
// tick every other modeled value wears.
import { AlertTriangle, ScaleIcon, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react';
import type { ClearanceStateId } from '@/data/types';
import { CLEARANCE_STATES_BY_ID } from '@/data/vocabulary';
import {
  CLEARANCE_MODEL_NOTE,
  clearanceMatrix,
  type JurisdictionVerdict,
} from '@/engine/clearance';
import type { Product } from '@/data/types';
import { Callout, cx } from './ui';

/** Risk band → the signal token already in the palette. Nothing new. */
const RISK_STYLE: Record<string, { chip: string; text: string; Icon: typeof ShieldCheck }> = {
  low: { chip: 'text-accent border-accent/40', text: 'text-accent', Icon: ShieldCheck },
  'low-moderate': { chip: 'text-accent/80 border-accent/30', text: 'text-accent/80', Icon: ShieldCheck },
  moderate: {
    chip: 'text-signal-warn border-signal-warn/40',
    text: 'text-signal-warn',
    Icon: ShieldAlert,
  },
  high: {
    chip: 'text-signal-error border-signal-error/40',
    text: 'text-signal-error',
    Icon: ShieldAlert,
  },
  unknown: { chip: 'text-ink-soft border-line', text: 'text-ink-soft', Icon: ShieldQuestion },
};

export function clearanceStyle(state: ClearanceStateId) {
  const meta = CLEARANCE_STATES_BY_ID[state];
  return RISK_STYLE[meta?.risk ?? 'unknown'] ?? RISK_STYLE.unknown;
}

export function clearanceLabel(state: ClearanceStateId): string {
  return CLEARANCE_STATES_BY_ID[state]?.label ?? 'Not yet assessed';
}

/** Compact form for a table cell, a card corner or a runbook stage. */
export function ClearanceChip({
  state,
  compact,
  title,
}: {
  state: ClearanceStateId;
  compact?: boolean;
  title?: string;
}) {
  const meta = CLEARANCE_STATES_BY_ID[state];
  const { chip, Icon } = clearanceStyle(state);
  return (
    <span
      className={cx('chip', chip, compact && 'text-[11px] py-0')}
      title={title ?? `${meta?.label ?? state} — ${meta?.action ?? 'run clearance'}`}
    >
      <Icon size={12} aria-hidden />
      {meta?.label ?? state}
    </span>
  );
}

/**
 * The fixed counsel warning. Non-dismissible by construction: it takes no
 * onClose and holds no state, so there is nowhere for a dismissal to live.
 * Every clearance surface renders exactly one.
 */
export function CounselCallout({ scope }: { scope?: string }) {
  return (
    <Callout kind="warn" title="This is a research lead, not a legal opinion">
      openFerment reads claim structure and filing patterns{scope ? ` for ${scope}` : ''}; it does
      not read national registers, does not check file histories, and does not know what has been
      licensed. Nothing here clears a molecule for manufacture or export. Have counsel confirm
      before any commitment — and before any spend that assumes freedom to operate.
    </Callout>
  );
}

/** The headline state with the action it implies. Never the state alone. */
export function ClearanceStrip({ state }: { state: ClearanceStateId }) {
  const meta = CLEARANCE_STATES_BY_ID[state];
  const { text, Icon } = clearanceStyle(state);
  return (
    <div className="flex items-start gap-2.5">
      <Icon size={18} className={cx('mt-[2px] shrink-0', text)} aria-hidden />
      <div className="min-w-0">
        <div className={cx('font-medium', text)}>{meta?.label ?? state}</div>
        <div className="text-body text-ink-soft mt-0.5">
          {meta?.action ?? 'Run clearance before any commitment.'}
        </div>
      </div>
      <span className="chip text-ink-soft ml-auto shrink-0" title="Risk band from the shared vocabulary">
        {meta?.risk ?? 'unknown'} risk
      </span>
    </div>
  );
}

function VerdictRow({ v }: { v: JurisdictionVerdict }) {
  const meta = CLEARANCE_STATES_BY_ID[v.state];
  const { text, chip, Icon } = clearanceStyle(v.state);
  return (
    <tr className={cx('border-b border-line/70 last:border-0', v.blocksExport && 'bg-signal-error/[0.05]')}>
      <td className="px-2 py-1.5 align-top">
        <span className="font-num text-ink">{v.jurisdiction.code}</span>{' '}
        <span className="text-ink-soft">{v.jurisdiction.name}</span>
        <div className="text-caption text-ink-soft">
          {v.jurisdiction.role === 'manufacture' ? 'where you would build' : 'export market'}
        </div>
      </td>
      <td className="px-2 py-1.5 align-top whitespace-nowrap">
        <span className={cx('inline-flex items-center gap-1.5', text)}>
          <Icon size={13} aria-hidden />
          {meta?.label ?? v.state}
        </span>
      </td>
      <td className="px-2 py-1.5 align-top text-ink-soft">
        {v.jurisdiction.because}
        {v.blocksExport && (
          <div className="mt-0.5 text-signal-error">
            Stricter than Rwanda — clear to make, not clear to ship here.
          </div>
        )}
      </td>
      <td className="px-2 py-1.5 align-top">
        <span className={cx('chip', chip)} title="Risk band">
          {meta?.risk ?? 'unknown'}
        </span>
      </td>
    </tr>
  );
}

/**
 * The per-jurisdiction matrix. The whole point of §8: a single global verdict
 * is the thing this replaces, so this component never renders one.
 */
export function JurisdictionMatrix({ product }: { product: Product }) {
  const rows = clearanceMatrix(product);
  const blockers = rows.filter((r) => r.blocksExport);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 mb-1.5">
        <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
          <ScaleIcon size={13} aria-hidden /> Where the fence actually stands
        </div>
        <span className="chip text-signal-warn border-signal-warn/40 text-[11px] py-0">
          modeled · not searched
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-body min-w-[520px]">
          <thead>
            <tr className="border-b border-line text-caption uppercase tracking-wide text-ink-soft">
              <th className="text-left font-medium px-2 py-1.5 w-[30%]">Office</th>
              <th className="text-left font-medium px-2 py-1.5 w-[22%]">Reads as</th>
              <th className="text-left font-medium px-2 py-1.5">Why</th>
              <th className="text-left font-medium px-2 py-1.5 w-[86px]">Risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => (
              <VerdictRow key={v.jurisdiction.id} v={v} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-caption text-ink-soft mt-2">{CLEARANCE_MODEL_NOTE}</p>
      {blockers.length > 0 && (
        <div className="mt-2 flex items-start gap-1.5 text-caption text-signal-error">
          <AlertTriangle size={13} className="mt-[2px] shrink-0" aria-hidden />
          <span>
            {blockers.length} export market{blockers.length === 1 ? '' : 's'} read
            {blockers.length === 1 ? 's' : ''} stricter than the manufacturing jurisdiction. Freedom
            to operate in Kigali is not freedom to sell.
          </span>
        </div>
      )}
    </div>
  );
}
