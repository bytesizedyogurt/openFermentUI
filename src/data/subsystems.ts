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
// OF-BLD-014 §3.2 adds a third value, `live`, for a subsystem whose code
// computes or stores at run time: Artifacts is the first.
//
// Two subsystems are `seeded`, and both were seeded from data this repository
// already had: Hosts is the strain catalogue, moved here from fermOS by §7.3;
// Pathway is the biosynthetic-pathway vocabulary. The other twenty-five are
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
 * `live`   — code behind it computes or stores from data that arrives at run
 *            time, and its view says what it holds today (OF-BLD-014 §3.2).
 * `stub`   — named, no implementation. Renders on the owner's reference shelf.
 *
 * There is no "in progress": a status nobody can check is one everybody
 * believes. `live` can be checked, because it names the files that implement
 * it in `implementedIn`, and `check:seed` fails when one of them is missing.
 */
export type SubsystemStatus = 'seeded' | 'live' | 'stub';

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
  /** For a `live` subsystem: the files whose code it is. `check:seed` holds each to existing. */
  implementedIn?: string[];
}

const UNBUILT = 'Not built. Nothing here computes, stores or retrieves anything yet.';

export const SUBSYSTEMS: Subsystem[] = [
  // ── Intake ───────────────────────────────────────────────────────────
  { id: 'intake.sources', owner: 'Intake', label: 'Sources', status: 'stub', state: UNBUILT },
  { id: 'intake.parser', owner: 'Intake', label: 'Parser', status: 'stub', state: UNBUILT },
  { id: 'intake.instrument', owner: 'Intake', label: 'Instrument ingest', status: 'stub', state: UNBUILT },

  // ── BioRepo ──────────────────────────────────────────────────────────
  {
    id: 'biorepo.artifacts',
    owner: 'BioRepo',
    label: 'Artifacts',
    status: 'live',
    state:
      'Every value the service computed, kept with the inputs it was computed from and the source ' +
      'of each, and replayable. It holds what the running service has computed; a fresh clone ' +
      'holds none.',
    implementedIn: [
      'core/openferment_core/artifacts.py',
      'core/openferment_core/basis.py',
      'src/screens/BioRepoArtifacts.tsx',
    ],
  },
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
  {
    id: 'geneos.model',
    owner: 'geneOS',
    label: 'Model',
    status: 'live',
    state:
      'Flux balance analysis on a shelf of published reaction networks: the most of a product each allows ' +
      'from a sugar (PHB from the E. coli and C. necator models, ethanol from the yeast models Yeast9 and ' +
      'iMM904), its production envelope and a sugar-mix line, each kept as an artifact and drawn beside the ' +
      'reported yields of that product. No time axis and no vessel; strain design is not built.',
    implementedIn: [
      'core/openferment_core/geneos.py',
      'core/openferment_core/geneos_models.py',
      'core/openferment_core/workers/geneos_worker.py',
      'src/screens/GeneOSModel.tsx',
    ],
  },
  { id: 'geneos.design', owner: 'geneOS', label: 'Strain design', status: 'stub', state: UNBUILT },

  // ── fermOS — the reactor (§3) ────────────────────────────────────────
  //
  // All five. Kinetics went live with OF-BLD-014 Phase 7; transport (the
  // oxygen balance) and scale (the vessel design) with OF-BLD-020 §4.2 (D15).
  // Operating mode and control remain stubs.
  {
    id: 'fermos.kinetics',
    owner: 'fermOS',
    label: 'Kinetics',
    status: 'live',
    state:
      'Fits a growth rate and a kinetic model (logistic growth, Luedeking–Piret production, the substrate ' +
      'balance) to a deposited run’s time series, keeps each fit as an artifact, and forecasts a run like it as a ' +
      'band. Fitted from depositions alone; one run says nothing of run-to-run variation.',
    implementedIn: [
      'core/openferment_core/fermos.py',
      'src/engine/series.ts',
      'src/screens/FermOS.tsx',
      'src/screens/FermOSForecast.tsx',
    ],
  },
  {
    // OF-BLD-020 §4.2, D15 — the oxygen balance of a designed vessel.
    id: 'fermos.transport',
    owner: 'fermOS',
    label: 'Transport',
    status: 'live',
    state:
      'Checks the oxygen a kept simulation takes up over its batch against what the vessel BioSTEAM designed transfers ' +
      '(kLa by its named correlation times the driving force at the dissolved-oxygen setpoint), names the hours it falls ' +
      'short, and sets BioSTEAM’s heat duty beside a convention’s estimate from the oxygen consumed. Dissolved oxygen is ' +
      'not a state of the simulation: the balance is checked after it, not fed back into it.',
    implementedIn: [
      'core/openferment_core/vessel.py',
      'core/openferment_core/flowsheets/vessel.py',
      'src/screens/FermOSVessel.tsx',
      'src/components/figures/OxygenBalance.tsx',
    ],
  },
  { id: 'fermos.mode', owner: 'fermOS', label: 'Operating mode', status: 'stub', state: UNBUILT },
  {
    // OF-BLD-020 §4.2, D15 — the vessel design.
    id: 'fermos.scale',
    owner: 'fermOS',
    label: 'Scale',
    status: 'live',
    state:
      'Designs the vessel a kept simulation (or, anaerobic, a kept fit) needs on BioSTEAM in the Proforma worker: its ' +
      'AeratedBioreactor, a stirred tank or a bubble column, or the NREL batch fermenter, sized for a plant scale or one ' +
      'vessel’s batch volume a named person types, every design parameter in the panel with its source, kept as a ' +
      'fermos.vessel artifact with BioSTEAM’s own cost. Scale-down to the bench and pricing the vessel in Proforma are not built.',
    implementedIn: [
      'core/openferment_core/vessel.py',
      'core/openferment_core/flowsheets/vessel.py',
      'core/openferment_core/workers/proforma_worker.py',
      'src/screens/FermOSVessel.tsx',
    ],
  },
  {
    // OF-BLD-020 D15 — stays a stub, and says what would build it.
    id: 'fermos.control',
    owner: 'fermOS',
    label: 'Control',
    status: 'stub',
    state:
      'Not built. Nothing here computes, stores or retrieves anything yet. Dissolved oxygen as a state of the simulation ' +
      'with a control loop on it, and an instrument such as a Pioreactor sending its readings to fermOS, would build it ' +
      '(OF-BLD-020 Appendix 4).',
  },

  // ── pureOS — downstream (§4) ─────────────────────────────────────────
  { id: 'pureos.harvest', owner: 'pureOS', label: 'Harvest', status: 'stub', state: UNBUILT },
  { id: 'pureos.capture', owner: 'pureOS', label: 'Capture', status: 'stub', state: UNBUILT },
  { id: 'pureos.polish', owner: 'pureOS', label: 'Polish', status: 'stub', state: UNBUILT },
  { id: 'pureos.recovery', owner: 'pureOS', label: 'Recovery', status: 'stub', state: UNBUILT },
  {
    id: 'proforma.uncertainty',
    owner: 'Proforma',
    label: 'Uncertainty',
    status: 'live',
    state:
      'Runs a BioSTEAM flowsheet over 500 seeded Latin-hypercube samples of inputs bound to records or to a named ' +
      'person\u2019s assumption, and shows the price as a distribution, what moves it, and the infeasible share by ' +
      'reason. Two flowsheets a scenario runs: glucose to ethanol for the yeast program, and the archived PHA draft.',
    implementedIn: [
      'core/openferment_core/proforma.py',
      'core/openferment_core/flowsheets/pha_sugar_v0.py',
      'core/openferment_core/flowsheets/ethanol_glucose_v0.py',
      'core/openferment_core/workers/proforma_worker.py',
      'src/screens/ProformaBiosteam.tsx',
      'src/components/figures/Distribution.tsx',
      'src/components/figures/Tornado.tsx',
    ],
  },

  // ── the rest, unchanged by this increment ────────────────────────────
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
