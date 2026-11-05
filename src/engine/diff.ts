// Structural diff of two protocol versions (OF-DES-001 §8.11). A version is
// the project's (lib/protocols.ts, served whole): a list it keeps none of
// reads as empty, and a timer it keeps none of as null. A step differs in any
// field it keeps (its words, its timer and the timer's label, its sub-checks,
// its note, its references and the skills it needs), and a material in any of
// its own (its amount, unit, scaling, rounding, stock and the record it rests
// on), each named in words by `stepChanges` and `materialChanges`.
import type { ProtocolVersion, Step, Material } from '@/lib/protocols';

export interface StepDiff {
  kind: 'unchanged' | 'modified' | 'added' | 'removed';
  a?: Step;
  b?: Step;
}

export interface MaterialDiff {
  kind: 'unchanged' | 'modified' | 'added' | 'removed';
  name: string;
  a?: Material;
  b?: Material;
}

export interface VersionDiff {
  steps: StepDiff[];
  materials: MaterialDiff[];
  changelog?: string | null;
}

const list = (v: readonly string[] | null | undefined) => JSON.stringify(v ?? []);

/** What differs between two versions of one step, each field in words, in the order the step shows them. */
export function stepChanges(a: Step, b: Step): string[] {
  return [
    a.text !== b.text ? 'instruction' : null,
    (a.timerSec ?? null) !== (b.timerSec ?? null) ? 'timer' : null,
    (a.timerLabel ?? null) !== (b.timerLabel ?? null) ? 'timer label' : null,
    list(a.multiCheck) !== list(b.multiCheck) ? 'sub-checks' : null,
    (a.note ?? null) !== (b.note ?? null) ? 'note' : null,
    list(a.refs) !== list(b.refs) ? 'references' : null,
    list(a.skills) !== list(b.skills) ? 'skills' : null,
  ].filter((c): c is string => c !== null);
}

/** What differs between two versions of one material, each field in words. */
export function materialChanges(a: Material, b: Material): string[] {
  return [
    a.amount !== b.amount ? 'amount' : null,
    a.unit !== b.unit ? 'unit' : null,
    a.scaling !== b.scaling ? 'scaling' : null,
    a.precision !== b.precision ? 'rounding' : null,
    JSON.stringify(a.stock ?? null) !== JSON.stringify(b.stock ?? null) ? 'stock' : null,
    (a.sourceRecordId ?? null) !== (b.sourceRecordId ?? null) ? 'record' : null,
  ].filter((c): c is string => c !== null);
}

export function diffVersions(a: ProtocolVersion, b: ProtocolVersion): VersionDiff {
  const steps: StepDiff[] = [];
  const aList = a.steps ?? [];
  const bList = b.steps ?? [];
  const aSteps = new Map(aList.map((s) => [s.id, s]));
  const bSteps = new Map(bList.map((s) => [s.id, s]));
  // Walk b's order (the newer version), marking removed a-steps in place.
  for (const s of bList) {
    const prev = aSteps.get(s.id);
    if (!prev) steps.push({ kind: 'added', b: s });
    else if (stepChanges(prev, s).length > 0) steps.push({ kind: 'modified', a: prev, b: s });
    else steps.push({ kind: 'unchanged', a: prev, b: s });
  }
  for (const s of aList) {
    if (!bSteps.has(s.id)) steps.push({ kind: 'removed', a: s });
  }

  const materials: MaterialDiff[] = [];
  const aMatList = a.materials ?? [];
  const bMatList = b.materials ?? [];
  const aMats = new Map(aMatList.map((m) => [m.name, m]));
  const bMats = new Map(bMatList.map((m) => [m.name, m]));
  for (const m of bMatList) {
    const prev = aMats.get(m.name);
    if (!prev) materials.push({ kind: 'added', name: m.name, b: m });
    else if (materialChanges(prev, m).length > 0) materials.push({ kind: 'modified', name: m.name, a: prev, b: m });
    else materials.push({ kind: 'unchanged', name: m.name, a: prev, b: m });
  }
  for (const m of aMatList) {
    if (!bMats.has(m.name)) materials.push({ kind: 'removed', name: m.name, a: m });
  }

  return { steps, materials, changelog: b.changelog };
}
