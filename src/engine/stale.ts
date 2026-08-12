// Staleness propagation (OF-FE-003 §5.3).
//
// A correction that does not visibly age what consumed it is a correction only
// in the record. This module walks the dependency graph the seed already
// encodes — sourceRecordId on protocol materials, recordId on scenario
// assumptions and sweep dimensions — and names every artifact downstream of a
// record.
//
// Pure, and takes only what it reads, so it stays testable and stays out of the
// store's way.
import type { ExtractionRecord, Protocol, Scenario } from '@/data/types';

export interface Dependents {
  protocols: string[];
  scenarios: string[];
  /** Design records, once fermOS writes them. Empty until then, never faked. */
  designs: string[];
}

export interface StaleSource {
  protocols: Protocol[];
  scenarios: Scenario[];
}

/**
 * Everything that consumed a record. A protocol depends on a record when any
 * version binds a material to it; a scenario depends on one when an assumption
 * or a sweep dimension cites it.
 */
export function dependents(recordId: string, s: StaleSource): Dependents {
  const protocols = s.protocols
    .filter((p) =>
      p.versions.some((v) => v.materials.some((m) => m.sourceRecordId === recordId)),
    )
    .map((p) => p.id);

  // Walk the assumption basis, not the legacy optional recordId. Before
  // OF-FE-004 §1 every assumption cited a paper and none cited a record, so
  // this branch matched nothing and a corrected record could not reach an MSP —
  // the architecture's central circuit severed at its most important joint.
  const scenarios = s.scenarios
    .filter(
      (sc) =>
        sc.assumptions.some(
          (a) =>
            (a.basis.kind === 'record' && a.basis.recordId === recordId) ||
            a.recordId === recordId,
        ) ||
        sc.dims.some((d) => d.sourceRecordId === recordId),
    )
    .map((sc) => sc.id);

  return { protocols, scenarios, designs: [] };
}

export interface StaleDiff {
  label: string;
  before: number;
  after: number;
  unit: string;
}

export interface StalePatch {
  recordId: string;
  changedAt: string;
  diff: StaleDiff | null;
  dependents: Dependents;
}

/**
 * The patch a record edit produces. `diff` carries the numeric before/after so a
 * downstream screen can say what changed rather than only that something did —
 * "stale" on its own tells a reader to redo work without telling them whether
 * it matters.
 *
 * Returns null when nothing consumed the record: an edit with no dependents is
 * not a propagation event, and reporting one would train people to ignore the
 * marker.
 */
export function markStale(
  before: ExtractionRecord,
  after: ExtractionRecord,
  s: StaleSource,
  at: string,
): StalePatch | null {
  const deps = dependents(after.id, s);
  if (deps.protocols.length === 0 && deps.scenarios.length === 0 && deps.designs.length === 0) {
    return null;
  }
  const b = typeof before.value === 'number' ? before.value : null;
  const a = typeof after.value === 'number' ? after.value : null;
  return {
    recordId: after.id,
    changedAt: at,
    diff:
      b !== null && a !== null && b !== a
        ? { label: after.field, before: b, after: a, unit: after.unit }
        : null,
    dependents: deps,
  };
}

/** How many artifacts a record edit would touch, for a pre-edit warning. */
export function blastRadius(recordId: string, s: StaleSource): number {
  const d = dependents(recordId, s);
  return d.protocols.length + d.scenarios.length + d.designs.length;
}
