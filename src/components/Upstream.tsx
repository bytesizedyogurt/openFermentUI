// The upstream-status vocabulary: what a part will be derived from, and how far
// along that decision actually is.
//
// WHY THIS IS POOL-NEUTRAL. `UPSTREAM` describes the thirteen PARTS of the
// architecture, not either object pool — the same table names Intake and
// Proforma whether you are looking at a casein ExtractionRecord or a demo
// Accession. The mark and its key used to be module-private inside
// `components/demo/UpstreamNote.tsx`, which meant the Bench could not draw the
// parts map without importing from the demo directory and quietly implying the
// parts belong to the demo pool. They live here; `UpstreamNote` imports them.
//
// THE THREE STATES ARE THE CONTENT. "will wrap BioSTEAM" and "wraps BioSTEAM"
// are very different claims, and a demo is exactly the setting where they get
// conflated. Form carries the epistemic state, as it does for the evidence tick:
//
//   ported     a solid bar. Code from that project is in this repository now.
//   named      an open bar. The decision is recorded in the repo; nothing calls it.
//   candidate  a dashed bar. An obvious fit nobody has committed to.
//
// STATUS IS PER PART, NOT PER PROJECT. Inspect AI is `ported` for Audit's scorer
// and only `named` for Intake, and that is not a rendering fault — a project can
// be load-bearing in one part and an intention in another. Any surface that
// shows more than one part at once should say so, or a reader decodes the two
// marks as a bug and stops trusting the key.
import type { UpstreamStatus } from '@/data/demo/upstream';

export const STATUS_LABEL: Record<UpstreamStatus, string> = {
  ported: 'in the repo now',
  named: 'decided, not yet called',
  candidate: 'candidate — nobody has committed',
};

/** The short form, for a key or a legend. */
export const STATUS_SHORT: Record<UpstreamStatus, string> = {
  ported: 'ported',
  named: 'named',
  candidate: 'candidate',
};

/** Tick geometry, reusing the house rule: form carries the epistemic state. */
export function StatusMark({ status }: { status: UpstreamStatus }) {
  const base = 'inline-block w-[3px] h-3.5 align-middle shrink-0';
  if (status === 'ported')
    return <span className={base} style={{ background: 'rgb(var(--accent))' }} aria-hidden />;
  if (status === 'named')
    return (
      <span
        className={base}
        style={{ border: '1px solid rgb(var(--accent))', background: 'transparent' }}
        aria-hidden
      />
    );
  return (
    <span
      className={base}
      style={{
        backgroundImage:
          'repeating-linear-gradient(to bottom, rgb(var(--ink-soft)) 0 2px, transparent 2px 4px)',
      }}
      aria-hidden
    />
  );
}
