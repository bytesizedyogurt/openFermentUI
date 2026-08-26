// Component attribution (OF-BLD-006 §2.4). When a named component does work,
// this says which one.
//
// openFerment's architecture has eighteen named components (COMPONENTS.md),
// and since §2.2 was reversed those names are also what the rail says. This
// tag still has a separate job from the label above it: the label names the
// surface you are standing on, and the tag names the component that produced a
// particular piece of work. It answers "who did this", not "where am I" — so
// it survives the rename unchanged, and it must not be mistaken for a heading.
//
// A THIRD VISUAL FAMILY. The screen already carries two labelled vocabularies
// and this must not read as either:
//
//   provenance  ProvenanceBadge — `chip`: 1px border, surface-1 background,
//               a lucide icon, coloured by confidence.
//   clearance   ClearanceChip — 1px border, a filled colour wash, an FTO
//               stamp, a lock icon.
//   attribution this — NO border, NO background, monospace, ink-soft.
//
// The distinction is structural rather than chromatic, so it survives both
// themes and holds for a reader who cannot separate the hues: the other two
// are enclosed and this one is not. Being unenclosed is also what makes it
// quiet enough to sit beside work without competing with it.
import { cx } from './ui';

/**
 * The eighteen. A union rather than a string so a typo is a compile error and
 * the naming layer is real in the codebase rather than a convention people
 * remember. 'Guild' is the attribution short form of "Guild of Applied Life".
 */
export type ComponentName =
  | 'Postdoc'
  | 'Intake'
  | 'BioRepo'
  | 'geneOS'
  | 'fermOS'
  | 'pureOS'
  | 'Proforma'
  | 'Primer'
  | 'Audit'
  | 'Witness'
  | 'Common Seal'
  | 'Claim Workbench'
  | 'Priority Engine'
  | 'Clearance'
  | 'Dominion'
  | 'Enablement'
  | 'Notary'
  | 'Guild'
  | 'Runbook'
  | 'Deposition';

/**
 * One line per component, shown on hover and to screen readers. A name with no
 * explanation is worse than no name — it reads as jargon rather than as
 * architecture.
 */
export const COMPONENT_ROLE: Record<ComponentName, string> = {
  Postdoc: 'The agent — plans, retrieves, and answers with its working shown',
  Intake: 'Evidence in — ingest and extraction of parameters from sources',
  BioRepo: 'Evidence in — the corpus and everything retrieved from it',
  geneOS: 'The organism as an engineered system — host, parts, pathway, model, strain design',
  fermOS: 'The reactor — kinetics, transport, operating mode, scale, control. None of it built',
  pureOS: 'Downstream — harvest, capture, polish, recovery, formulation, storage',
  Proforma: 'Computing — cost models, sweeps and scenario economics',
  Primer: 'Keeping it honest — the introductory text: the platform taught through itself',
  Audit: 'Keeping it honest — provenance, and what is held out of aggregates',
  Witness: 'Keeping it honest — extractor validation against the gold set',
  'Common Seal': 'Keeping it honest — timestamping and attestation (not built)',
  'Claim Workbench': 'Patents — claim drafting and analysis (not built)',
  'Priority Engine': 'Patents — priority and filing strategy (not built)',
  Dominion: 'Patents and clearance — what is fenced and what is open',
  Clearance: 'Patents — freedom to operate, per jurisdiction',
  Enablement: 'Patents — enablement and written description (not built)',
  Notary: 'Patents — inventorship and conception records (not built)',
  Guild: 'People and permissions — review, roles and who decided what',
  Runbook: 'Assay — the outbound falsifiable claim',
  Deposition: 'Assay — the inbound account of what actually happened',
};

/**
 * `geneOS · homology sweep`. The component is the subject; `action` is what it
 * did, in the platform's own words.
 *
 * Use it where a component visibly acts and the reader benefits from knowing
 * which one. Do not scatter it: a tag on every card is decoration, and
 * decoration is how a naming layer stops being read.
 */
export function ComponentTag({
  component,
  unnamed,
  action,
  className,
  title,
}: {
  component?: ComponentName;
  /**
   * For work done by code that has no name (COMPONENTS.md, "Named nothing
   * yet"). The unit engine lost its name when Primer moved to the Learn
   * screens, and its refusals still need attributing: saying "the unit engine
   * refused this" is honest, and leaving the refusal unattributed or crediting
   * it to a component that no longer does that job is not.
   */
  unnamed?: string;
  action?: string;
  className?: string;
  /** Overrides the default role tooltip when the context needs something sharper. */
  title?: string;
}) {
  const who = component ?? unnamed ?? '';
  return (
    <span
      className={cx(
        // No border and no background — that absence is the family marker.
        'inline-flex items-baseline gap-1 font-num text-[11px] leading-tight text-ink-soft',
        className,
      )}
      title={title ?? (component ? `${component} — ${COMPONENT_ROLE[component]}` : who)}
    >
      <span className="sr-only">Produced by </span>
      <span className={cx('text-ink/75', !component && 'font-sans italic')}>{who}</span>
      {action && (
        <>
          <span aria-hidden className="opacity-45">
            ·
          </span>
          <span>{action}</span>
        </>
      )}
    </span>
  );
}
