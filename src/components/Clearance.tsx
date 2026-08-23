// Clearance surfaces (OF-BLD-005 §8). Clearance renders wherever a molecule
// renders — it is an ambient property, never a separate mode — so the pieces
// live here and every screen composes the same ones.
//
// Four rules hold everywhere:
//   1. The state is shown with the action it implies, never bare.
//   2. The headline state is marked as NOT jurisdiction-resolved, so it cannot
//      be misread as an office-by-office verdict.
//   3. Territoriality is structural, so the matrix is per jurisdiction — and a
//      cell nobody has assessed says so rather than showing a guess.
//   4. The counsel warning is fixed and non-dismissible.
//
// VISUAL SEPARATION FROM PROVENANCE. These two vocabularies must not look
// alike. "This number is unverified" and "this molecule is patent-blocked" are
// different kinds of claim with different consequences, and an earlier version
// of this file rendered them identically: clearance reused `chip` with the
// same signal colours and the same lucide shields that `ProvenanceBadge` uses,
// so a moderate-risk clearance and a 'demo' provenance were the same amber
// outline chip, and a low-risk clearance was pixel-for-pixel the ShieldCheck
// used by 'verified'. Three independent differentiators now separate them,
// none of which needs a new colour or typeface:
//
//   · an FTO stamp — a mono uppercase tag no provenance badge carries;
//   · a filled wash background, where provenance chips are outline-only;
//   · lock-family icons, disjoint from the provenance icon set (which uses
//     Award, ShieldCheck, CircleDashed, UserPen, FlaskConical, Ban,
//     BookMarked, TrendingUp).
import {
  AlertTriangle,
  CircleHelp,
  Lock,
  LockKeyhole,
  LockOpen,
  ScaleIcon,
} from 'lucide-react';
import type { ClearanceStateId, Product } from '@/data/types';
import { CLEARANCE_STATES_BY_ID } from '@/data/vocabulary';
import { termFalls, type ClearanceFinding } from '@/data/clearanceFindings';
import {
  CLEARANCE_MODEL_NOTE,
  HEADLINE_SCOPE_NOTE,
  clearanceMatrix,
  matrixCoverage,
  type JurisdictionVerdict,
} from '@/engine/clearance';
import { Callout, cx } from './ui';

/**
 * Risk band → existing signal tokens, as a filled wash. No new colour enters
 * the system; what changes is that clearance FILLS and provenance OUTLINES.
 */
const RISK_STYLE: Record<
  string,
  { wash: string; text: string; Icon: typeof Lock }
> = {
  low: { wash: 'border-accent/45 bg-accent/[0.10]', text: 'text-accent', Icon: LockOpen },
  'low-moderate': {
    wash: 'border-accent/35 bg-accent/[0.07]',
    text: 'text-accent/85',
    Icon: LockOpen,
  },
  moderate: {
    wash: 'border-signal-warn/45 bg-signal-warn/[0.12]',
    text: 'text-signal-warn',
    Icon: LockKeyhole,
  },
  high: {
    wash: 'border-signal-error/45 bg-signal-error/[0.12]',
    text: 'text-signal-error',
    Icon: Lock,
  },
  unknown: {
    wash: 'border-line bg-ink-soft/[0.08]',
    text: 'text-ink-soft',
    Icon: CircleHelp,
  },
};

export function clearanceStyle(state: ClearanceStateId) {
  const meta = CLEARANCE_STATES_BY_ID[state];
  return RISK_STYLE[meta?.risk ?? 'unknown'] ?? RISK_STYLE.unknown;
}

export function clearanceLabel(state: ClearanceStateId): string {
  return CLEARANCE_STATES_BY_ID[state]?.label ?? 'Not yet assessed';
}

/**
 * Freedom-to-operate stamp. Present on every clearance surface and on nothing
 * else — the fastest way to tell the two vocabularies apart is that one of
 * them is stamped and the other is not.
 */
function FTO({ compact }: { compact?: boolean }) {
  return (
    <span
      className={cx(
        'font-num uppercase tracking-wide opacity-70 shrink-0',
        compact ? 'text-[9px]' : 'text-[10px]',
      )}
      title="Freedom to operate — a patent question, not a confidence rating"
    >
      FTO
    </span>
  );
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
  const { wash, text, Icon } = clearanceStyle(state);
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1.5 rounded-input border whitespace-nowrap',
        compact ? 'px-1.5 py-0 text-[11px]' : 'px-2 py-px text-[12px]',
        wash,
        text,
      )}
      title={title ?? `Freedom to operate — ${meta?.label ?? state}. ${meta?.action ?? ''}`}
    >
      <FTO compact={compact} />
      <Icon size={compact ? 11 : 12} aria-hidden />
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
      openFerment reads claim structure{scope ? ` for ${scope}` : ''}; it does not read national
      registers, does not check file histories, and does not know what has been licensed. Nothing
      here clears a molecule for manufacture or export. Have counsel confirm before any commitment
      — and before any spend that assumes freedom to operate.
    </Callout>
  );
}

/**
 * The headline state with the action it implies, and — mandatory — the note
 * saying it is not resolved to any jurisdiction. The state and the scope
 * caveat travel together; there is no prop to suppress it.
 */
export function ClearanceStrip({ state }: { state: ClearanceStateId }) {
  const meta = CLEARANCE_STATES_BY_ID[state];
  const { text, Icon } = clearanceStyle(state);
  return (
    <div>
      <div className="flex items-start gap-2.5">
        <Icon size={18} className={cx('mt-[2px] shrink-0', text)} aria-hidden />
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FTO />
            <span className={cx('font-medium', text)}>{meta?.label ?? state}</span>
          </div>
          <div className="text-body text-ink-soft mt-0.5">
            {meta?.action ?? 'Run clearance before any commitment.'}
          </div>
        </div>
        <span
          className="chip text-ink-soft ml-auto shrink-0"
          title="Risk band from the shared vocabulary"
        >
          {meta?.risk ?? 'unknown'} risk
        </span>
      </div>
      <p className="text-caption text-ink-soft mt-2 pt-2 border-t border-line">
        <span className="text-signal-warn font-medium">Global summary. </span>
        {HEADLINE_SCOPE_NOTE}
      </p>
    </div>
  );
}

/**
 * One patent, with its term expiry given primacy over its litigation history.
 *
 * That ordering is the point, not a layout preference. Term expiry is
 * arithmetic and it is usually the whole answer; a dispute is contingent, and
 * can run for years without ever producing a result you could rely on. Reading
 * the litigation first is how somebody concludes a patent is unenforceable
 * when what actually happened is that it expired.
 */
function PatentEntry({ patent }: { patent: ClearanceFinding['patents'][number] }) {
  return (
    <li className="text-caption">
      <span className="font-num text-ink">{patent.number}</span>{' '}
      <span className="text-ink-soft">— {patent.title}</span>
      <div className="text-ink-soft">{patent.assignee}</div>

      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="uppercase tracking-wide text-ink-soft shrink-0">Term</span>
        {patent.expiresOnTerm ? (
          <span className="font-num text-accent">expires {patent.expiresOnTerm}</span>
        ) : (
          <span className="text-signal-warn">not established</span>
        )}
      </div>
      {patent.termBasis && <div className="text-ink-soft">{patent.termBasis}</div>}

      <div className="mt-1 text-ink-soft">
        <span className="uppercase tracking-wide">History</span>
        {patent.at && (
          <>
            {' · '}
            <span className="font-num">{patent.at}</span>
          </>
        )}
      </div>
      <div className="text-ink-soft">{patent.status}</div>
    </li>
  );
}

function FindingDetail({ finding }: { finding: ClearanceFinding }) {
  const falls = termFalls(finding);
  return (
    <div className="mt-2 space-y-2">
      <div
        className={cx(
          'rounded-input border px-2 py-1.5',
          falls ? 'border-accent/40 bg-accent/[0.07]' : 'border-signal-warn/40 bg-signal-warn/[0.07]',
        )}
      >
        <div className="text-caption uppercase tracking-wide text-ink-soft">
          When the fence falls on term
        </div>
        {falls ? (
          <div className="text-body font-num text-accent">{falls}</div>
        ) : (
          <div className="text-body text-signal-warn">Not established</div>
        )}
        <div className="text-caption text-ink-soft mt-0.5">
          {falls
            ? 'Latest term expiry across the patents below — arithmetic, and independent of how any dispute over them turned out.'
            : 'At least one patent below has no established term date, so the latest expiry across the family is unknown. The maximum of a partial set is not the maximum.'}
        </div>
      </div>

      <ul className="space-y-2.5">
        {finding.patents.map((p) => (
          <PatentEntry key={p.number} patent={p} />
        ))}
      </ul>
      <p className="text-caption text-ink-soft">{finding.summary}</p>
      <div className="text-caption text-ink-soft">
        <span className="uppercase tracking-wide">Read from</span>
        <ul className="mt-0.5 space-y-0.5">
          {finding.sources.map((s) => (
            <li key={s.url}>
              <a
                href={s.url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-accent hover:underline break-words"
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="mt-1">
          <span className="font-num">{finding.readAt}</span> · marked{' '}
          <span className="text-ink">{finding.provenance}</span> — secondary sources, primary
          documents not yet pulled.
        </div>
        <div className="mt-0.5">
          <span className="uppercase tracking-wide">To verify:</span> {finding.toVerify}
        </div>
      </div>
    </div>
  );
}

function VerdictRow({ v }: { v: JurisdictionVerdict }) {
  const meta = CLEARANCE_STATES_BY_ID[v.state];
  const { text, Icon } = clearanceStyle(v.state);
  const assessed = v.finding !== null;
  return (
    <tr
      className={cx(
        'border-b border-line/70 last:border-0 align-top',
        v.blocksExport && 'bg-signal-error/[0.05]',
      )}
    >
      <td className="px-2 py-2">
        <span className="font-num text-ink">{v.jurisdiction.code}</span>{' '}
        <span className="text-ink-soft">{v.jurisdiction.name}</span>
        <div className="text-caption text-ink-soft">
          {v.jurisdiction.role === 'manufacture' ? 'where you would build' : 'export market'}
        </div>
      </td>
      <td className="px-2 py-2 whitespace-nowrap">
        <span className={cx('inline-flex items-center gap-1.5', text)}>
          <Icon size={13} aria-hidden />
          {assessed && v.state === 'unknown'
            ? 'Examined · unresolved'
            : assessed
              ? (meta?.label ?? v.state)
              : 'Not assessed'}
        </span>
      </td>
      <td className="px-2 py-2 text-ink-soft">
        {assessed ? (
          <FindingDetail finding={v.finding!} />
        ) : (
          <>
            <div>Not assessed for this jurisdiction.</div>
            <div className="text-caption mt-0.5">{v.jurisdiction.why}</div>
          </>
        )}
        {v.blocksExport && (
          <div className="mt-1 text-signal-error text-caption">
            Stricter than Rwanda — clear to make, not clear to ship here.
          </div>
        )}
      </td>
    </tr>
  );
}

/**
 * The per-jurisdiction matrix. The whole point of §8: a single global verdict
 * is the thing this replaces, so this component never renders one — and it
 * renders honestly empty rather than filling itself in.
 */
export function JurisdictionMatrix({ product }: { product: Product }) {
  const rows = clearanceMatrix(product);
  const blockers = rows.filter((r) => r.blocksExport);
  const { assessed, total, resolved } = matrixCoverage(product);

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-1.5">
        <div className="text-caption uppercase tracking-wide text-ink-soft inline-flex items-center gap-1.5">
          <ScaleIcon size={13} aria-hidden /> Where the fence actually stands
        </div>
        <span
          className={cx(
            'chip text-[11px] py-0',
            assessed === 0 ? 'text-ink-soft' : 'text-accent border-accent/40',
          )}
          title="How many offices anybody has actually looked at for this molecule"
        >
          <span className="font-num">
            {assessed}/{total}
          </span>{' '}
          offices assessed
          {assessed > 0 && (
            <>
              {' · '}
              <span className="font-num">{resolved}</span> resolved
            </>
          )}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-body min-w-[520px]">
          <thead>
            <tr className="border-b border-line text-caption uppercase tracking-wide text-ink-soft">
              <th className="text-left font-medium px-2 py-1.5 w-[27%]">Office</th>
              <th className="text-left font-medium px-2 py-1.5 w-[23%]">Reads as</th>
              <th className="text-left font-medium px-2 py-1.5">What is on file here</th>
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

      {assessed === 0 && (
        <div className="mt-2 flex items-start gap-1.5 text-caption text-signal-warn">
          <AlertTriangle size={13} className="mt-[2px] shrink-0" aria-hidden />
          <span>
            No office has been assessed for this molecule. The table is empty because the work has
            not been done, not because the molecule is free — and an empty row is the one thing
            here that must never be read as a green light.
          </span>
        </div>
      )}

      {blockers.length > 0 && (
        <div className="mt-2 flex items-start gap-1.5 text-caption text-signal-error">
          <AlertTriangle size={13} className="mt-[2px] shrink-0" aria-hidden />
          <span>
            {blockers.length} assessed export market{blockers.length === 1 ? '' : 's'} read
            {blockers.length === 1 ? 's' : ''} stricter than the manufacturing jurisdiction.
            Freedom to operate in Kigali is not freedom to sell.
          </span>
        </div>
      )}
    </div>
  );
}
