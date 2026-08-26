// The subsystem registry (OF-BLD-010 §3).
//
// SCOPE, DELIBERATELY NARROW. This is a transcription of §3's coverage table
// and nothing else: seventeen ids, the owner each belongs to, and the label §3
// gives it. Every column here was handed over in the specification; none of it
// was designed.
//
// IT CARRIES NO STATUS FIELD, ON PURPOSE. OF-BLD-009 — subsystem tabs, status
// markers, per-subsystem empty states — was never built in this repository.
// Inventing a `stub` marker here would invent the very dial OF-BLD-010 §2 says
// must not move when reference content appears, and you cannot promise not to
// turn a dial you have just installed. Whether a subsystem shows a reference
// shelf is decided by `referenceFor(id)` returning content, never by a status
// this file asserts.
//
// Every one of the seventeen is unbuilt. That is not a field, it is the reason
// the file exists: §3 lists exactly the subsystems that have no data yet. When
// OF-BLD-009 lands with real statuses and a tab strip, its registry supersedes
// this one and `ReferenceView` does not change.
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

export interface Subsystem {
  /** `owner.subsystem`, lowercase — the key `referenceFor()` takes. */
  id: string;
  owner: SubsystemOwner;
  /** What §3's coverage table calls it. */
  label: string;
  /**
   * What is true about the CODE today, in one sentence, above the divider.
   *
   * Kept to the plainest statement that is certainly true — this subsystem has
   * no implementation. It deliberately does NOT describe what the subsystem
   * will contain: that copy belongs to OF-BLD-009's per-subsystem empty
   * states, and writing it here would be inventing product intent under cover
   * of a transcription.
   */
  state: string;
}

const UNBUILT = 'Not built. Nothing here computes, stores or retrieves anything yet.';

export const SUBSYSTEMS: Subsystem[] = [
  { id: 'intake.sources', owner: 'Intake', label: 'Sources', state: UNBUILT },
  { id: 'intake.parser', owner: 'Intake', label: 'Parser', state: UNBUILT },
  { id: 'intake.instrument', owner: 'Intake', label: 'Instrument ingest', state: UNBUILT },
  { id: 'biorepo.artifacts', owner: 'BioRepo', label: 'Artifacts', state: UNBUILT },
  { id: 'biorepo.audit', owner: 'BioRepo', label: 'Audit', state: UNBUILT },
  { id: 'geneos.search', owner: 'geneOS', label: 'Sequence search', state: UNBUILT },
  { id: 'geneos.structure', owner: 'geneOS', label: 'Structure', state: UNBUILT },
  { id: 'geneos.function', owner: 'geneOS', label: 'Function', state: UNBUILT },
  { id: 'fermos.models', owner: 'fermOS', label: 'Models', state: UNBUILT },
  { id: 'fermos.design', owner: 'fermOS', label: 'Strain design', state: UNBUILT },
  { id: 'pureos.recovery', owner: 'pureOS', label: 'Recovery', state: UNBUILT },
  { id: 'proforma.uncertainty', owner: 'Proforma', label: 'Uncertainty', state: UNBUILT },
  { id: 'dominion.claims', owner: 'Dominion', label: 'Claim Workbench', state: UNBUILT },
  { id: 'dominion.priority', owner: 'Dominion', label: 'Priority Engine', state: UNBUILT },
  { id: 'dominion.enablement', owner: 'Dominion', label: 'Enablement', state: UNBUILT },
  { id: 'dominion.notary', owner: 'Dominion', label: 'Notary', state: UNBUILT },
  { id: 'guild.powers', owner: 'Guild', label: 'Powers', state: UNBUILT },
];

export function subsystemsFor(owner: SubsystemOwner): Subsystem[] {
  return SUBSYSTEMS.filter((s) => s.owner === owner);
}

export function subsystemById(id: string): Subsystem | null {
  return SUBSYSTEMS.find((s) => s.id === id) ?? null;
}
