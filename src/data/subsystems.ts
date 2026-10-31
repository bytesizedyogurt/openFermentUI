// The named subsystems with no implementation yet (OF-BLD-010 §3, rebuilt on
// OF-BLD-011 §2–§4), which each owner's reference shelf lists.
//
// The three OS components are the three stages of making something:
//
//   geneOS  the organism as an engineered system.  What CAN this cell do?
//   fermOS  the reactor.                           What DOES a vessel achieve?
//   pureOS  downstream.                            How does product become vial?
//
// A subsystem that is built has a view of its own and is not listed here: the
// shelf says "named parts that have no implementation", and a built part on it
// would be a false statement on a screen whose purpose is not making them.
export type SubsystemOwner =
  | 'Intake'
  | 'BioRepo'
  | 'geneOS'
  | 'fermOS'
  | 'pureOS'
  | 'Proforma'
  | 'Guild';

export interface Subsystem {
  /** `owner.subsystem`, lowercase. */
  id: string;
  owner: SubsystemOwner;
  /** What §2–§4's coverage tables call it. */
  label: string;
  /**
   * What is true about the CODE today, in one sentence, kept to the plainest
   * statement that is certainly true. It deliberately does NOT describe what
   * the subsystem will contain: that would be inventing product intent.
   */
  state: string;
}

const UNBUILT = 'Not built. Nothing here computes, stores or retrieves anything yet.';

export const SUBSYSTEMS: Subsystem[] = [
  // ── Intake ───────────────────────────────────────────────────────────
  { id: 'intake.sources', owner: 'Intake', label: 'Sources', state: UNBUILT },
  { id: 'intake.parser', owner: 'Intake', label: 'Parser', state: UNBUILT },
  { id: 'intake.instrument', owner: 'Intake', label: 'Instrument ingest', state: UNBUILT },

  // ── BioRepo ──────────────────────────────────────────────────────────
  { id: 'biorepo.audit', owner: 'BioRepo', label: 'Audit', state: UNBUILT },

  // ── geneOS — the organism as an engineered system (§2) ───────────────
  { id: 'geneos.parts', owner: 'geneOS', label: 'Parts', state: UNBUILT },
  { id: 'geneos.search', owner: 'geneOS', label: 'Sequence search', state: UNBUILT },
  { id: 'geneos.structure', owner: 'geneOS', label: 'Structure', state: UNBUILT },
  { id: 'geneos.function', owner: 'geneOS', label: 'Function', state: UNBUILT },
  { id: 'geneos.design', owner: 'geneOS', label: 'Strain design', state: UNBUILT },

  // ── fermOS — the reactor (§3) ────────────────────────────────────────
  {
    // OF-BLD-020 D15 — says what would build it.
    id: 'fermos.control',
    owner: 'fermOS',
    label: 'Control',
    state:
      'Not built. Nothing here computes, stores or retrieves anything yet. Dissolved oxygen as a state of the simulation ' +
      'with a control loop on it, and an instrument such as a Pioreactor sending its readings to fermOS, would build it.',
  },

  // ── Guild ────────────────────────────────────────────────────────────
  { id: 'guild.powers', owner: 'Guild', label: 'Powers', state: UNBUILT },
];

/** The owner's unbuilt subsystems, which are what a reference shelf is for. */
export function stubsFor(owner: SubsystemOwner): Subsystem[] {
  return SUBSYSTEMS.filter((s) => s.owner === owner);
}
