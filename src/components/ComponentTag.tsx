// Component attribution (OF-BLD-006 §2.4). When a named component does work,
// this says which one.
//
// openFerment's architecture has named components (Settings → Architecture),
// and since §2.2 was reversed those names are also what the rail says. This
// tag still has a separate job from the label above it: the label names the
// surface you are standing on, and the tag names the component that produced a
// particular piece of work. It answers "who did this", not "where am I" — so
// it survives the rename unchanged, and it must not be mistaken for a heading.
//
// A VISUAL FAMILY OF ITS OWN. The screen already carries a labelled
// vocabulary and this must not read as it:
//
//   provenance  ProvenanceBadge — `chip`: 1px border, surface-1 background,
//               a lucide icon, coloured by confidence.
//   attribution this — NO border, NO background, monospace, ink-soft.
//
// The distinction is structural rather than chromatic, so it survives both
// themes and holds for a reader who cannot separate the hues: the badge is
// enclosed and this is not. Being unenclosed is also what makes it
// quiet enough to sit beside work without competing with it.
import { cx } from './ui';

/**
 * The named components. A union rather than a string so a typo is a compile error and
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
  BioRepo: 'Evidence in — the project\u2019s records, the decisions on them, and search over its documents',
  geneOS: 'The organism as an engineered system — host, parts, pathway, model, strain design',
  fermOS: 'The reactor — kinetics, transport, operating mode and scale; control not built',
  pureOS: 'Downstream — harvest, capture, polish, recovery, formulation, storage',
  Proforma: 'Computing — plants and flowsheets on BioSTEAM, scenario economics and studies',
  Primer: 'Keeping it honest — the introductory text: the platform taught through itself',
  Audit: 'Keeping it honest — provenance, and what is held out of aggregates',
  Witness: 'Keeping it honest — extractor validation against the values reviewers typed',
  'Common Seal': 'Keeping it honest — timestamping and attestation (not built)',
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
