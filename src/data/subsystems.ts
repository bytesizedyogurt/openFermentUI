// The subsystem registry (OF-BLD-010 §3, rebuilt on OF-BLD-011 §2–§4).
//
// WHAT CHANGED, AND WHY IT IS NOT A REDESIGN. OF-BLD-011 §1 corrects a boundary
// error: geneOS and fermOS had been split along SOFTWARE categories — sequence
// tools in one, metabolic-modelling libraries in the other — which is how a
// toolkit is organised, not how bioprocess work is. The three OS components are
// the three stages of making something:
//
//   geneOS  the organism as an engineered system.  What CAN this cell do?
//   fermOS  the reactor.                           What DOES a vessel achieve?
//   pureOS  downstream.                            How does product become vial?
//
// Two consequences of the old split were actively wrong. Strain design sat in
// fermOS, when deciding which genes to knock out is genetic design. And fermOS
// held nothing about running a fermenter — the component named after
// fermentation contained no kinetics, no transport, no scale-up. Both are
// fixed here.
//
// THE STATUS COLUMN IS TRANSCRIBED, NOT INVENTED. OF-BLD-010's registry
// deliberately carried no status field: OF-BLD-009 was never built in this
// repository, so a `stub` marker would have been a dial this file installed and
// then promised not to turn. OF-BLD-011 §2–§4 hands the column over with a
// value against every id, which settles it — `status` below is a transcription
// of those three tables, the same as `label` and `owner` already were.
//
// Two subsystems are `seeded`, and both were seeded from data this repository
// already had: Hosts is the strain catalogue, moved here from fermOS by §7.3;
// Pathway is the biosynthetic-pathway vocabulary. The other twenty-six are
// `stub` and render as a shelf, unchanged — a subsystem showing reference
// content stays a stub (§8), because domain knowledge below the line does not
// make code exist above it.
//
// Three of the eleven own no subsystems: Postdoc, Runbooks and Primer.
export type SubsystemOwner =
  | 'Intake'
  | 'BioRepo'
  | 'geneOS'
  | 'fermOS'
  | 'pureOS'
  | 'Proforma'
  | 'Dominion'
  | 'Guild';

/**
 * `seeded` — real data stands behind it, and it has a view of its own.
 * `stub`   — named, no implementation. Renders on the owner's reference shelf.
 *
 * There is no third value on purpose. "In progress" is a status nobody can
 * check and everybody believes.
 */
export type SubsystemStatus = 'seeded' | 'stub';

export interface Subsystem {
  /** `owner.subsystem`, lowercase — the key `referenceFor()` takes. */
  id: string;
  owner: SubsystemOwner;
  /** What §2–§4's coverage tables call it. */
  label: string;
  status: SubsystemStatus;
  /**
   * What is true about the CODE today, in one sentence.
   *
   * For a stub this sits above the reference divider, and is kept to the
   * plainest statement that is certainly true. It deliberately does NOT
   * describe what the subsystem will contain: that would be inventing product
   * intent under cover of a transcription.
   */
  state: string;
}

const UNBUILT = 'Not built. Nothing here computes, stores or retrieves anything yet.';

export const SUBSYSTEMS: Subsystem[] = [
  // ── Intake ───────────────────────────────────────────────────────────
  { id: 'intake.sources', owner: 'Intake', label: 'Sources', status: 'stub', state: UNBUILT },
  { id: 'intake.parser', owner: 'Intake', label: 'Parser', status: 'stub', state: UNBUILT },
  { id: 'intake.instrument', owner: 'Intake', label: 'Instrument ingest', status: 'stub', state: UNBUILT },

  // ── BioRepo ──────────────────────────────────────────────────────────
  { id: 'biorepo.artifacts', owner: 'BioRepo', label: 'Artifacts', status: 'stub', state: UNBUILT },
  { id: 'biorepo.audit', owner: 'BioRepo', label: 'Audit', status: 'stub', state: UNBUILT },

  // ── geneOS — the organism as an engineered system (§2) ───────────────
  {
    id: 'geneos.hosts',
    owner: 'geneOS',
    label: 'Hosts',
    status: 'seeded',
    state:
      'The strain catalogue, with the corpus that stands behind each host. Chassis comparison ' +
      'and host recommendation are not built.',
  },
  { id: 'geneos.parts', owner: 'geneOS', label: 'Parts', status: 'stub', state: UNBUILT },
  {
    id: 'geneos.pathway',
    owner: 'geneOS',
    label: 'Pathway',
    status: 'seeded',
    state:
      'The biosynthetic-pathway vocabulary, and which molecules in the catalogue declare each ' +
      'route. Nothing here balances a pathway or checks it against a host.',
  },
  { id: 'geneos.search', owner: 'geneOS', label: 'Sequence search', status: 'stub', state: UNBUILT },
  { id: 'geneos.structure', owner: 'geneOS', label: 'Structure', status: 'stub', state: UNBUILT },
  { id: 'geneos.function', owner: 'geneOS', label: 'Function', status: 'stub', state: UNBUILT },
  { id: 'geneos.model', owner: 'geneOS', label: 'Model', status: 'stub', state: UNBUILT },
  { id: 'geneos.design', owner: 'geneOS', label: 'Strain design', status: 'stub', state: UNBUILT },

  // ── fermOS — the reactor (§3) ────────────────────────────────────────
  //
  // All five. This makes fermOS the emptiest of the eleven, and honestly so:
  // there is no kinetic model, no transport calculation and no scale-up logic
  // anywhere in this codebase.
  { id: 'fermos.kinetics', owner: 'fermOS', label: 'Kinetics', status: 'stub', state: UNBUILT },
  { id: 'fermos.transport', owner: 'fermOS', label: 'Transport', status: 'stub', state: UNBUILT },
  { id: 'fermos.mode', owner: 'fermOS', label: 'Operating mode', status: 'stub', state: UNBUILT },
  { id: 'fermos.scale', owner: 'fermOS', label: 'Scale', status: 'stub', state: UNBUILT },
  { id: 'fermos.control', owner: 'fermOS', label: 'Control', status: 'stub', state: UNBUILT },

  // ── pureOS — downstream (§4) ─────────────────────────────────────────
  { id: 'pureos.harvest', owner: 'pureOS', label: 'Harvest', status: 'stub', state: UNBUILT },
  { id: 'pureos.capture', owner: 'pureOS', label: 'Capture', status: 'stub', state: UNBUILT },
  { id: 'pureos.polish', owner: 'pureOS', label: 'Polish', status: 'stub', state: UNBUILT },
  { id: 'pureos.recovery', owner: 'pureOS', label: 'Recovery', status: 'stub', state: UNBUILT },

  // ── the rest, unchanged by this increment ────────────────────────────
  { id: 'proforma.uncertainty', owner: 'Proforma', label: 'Uncertainty', status: 'stub', state: UNBUILT },
  { id: 'dominion.claims', owner: 'Dominion', label: 'Claim Workbench', status: 'stub', state: UNBUILT },
  { id: 'dominion.priority', owner: 'Dominion', label: 'Priority Engine', status: 'stub', state: UNBUILT },
  { id: 'dominion.enablement', owner: 'Dominion', label: 'Enablement', status: 'stub', state: UNBUILT },
  { id: 'dominion.notary', owner: 'Dominion', label: 'Notary', status: 'stub', state: UNBUILT },
  { id: 'guild.powers', owner: 'Guild', label: 'Powers', status: 'stub', state: UNBUILT },
];

export function subsystemsFor(owner: SubsystemOwner): Subsystem[] {
  return SUBSYSTEMS.filter((s) => s.owner === owner);
}

/**
 * The unbuilt ones, which are what a reference shelf is for.
 *
 * A seeded subsystem is deliberately NOT on the shelf: the shelf's own copy
 * says "named parts that have no implementation", and putting Hosts there —
 * above a live catalogue of strains — would be a false statement on a screen
 * whose entire purpose is not making false statements. Seeded subsystems carry
 * their reference content on their own view instead.
 */
export function stubsFor(owner: SubsystemOwner): Subsystem[] {
  return SUBSYSTEMS.filter((s) => s.owner === owner && s.status === 'stub');
}

export function subsystemById(id: string): Subsystem | null {
  return SUBSYSTEMS.find((s) => s.id === id) ?? null;
}
