// Structural diff of two protocol versions (OF-DES-001 §8.11). A version is
// the project's (lib/protocols.ts, served whole): a list it keeps none of
// reads as empty, and a timer it keeps none of as null.
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
    else if (
      prev.text !== s.text ||
      (prev.timerSec ?? null) !== (s.timerSec ?? null) ||
      JSON.stringify(prev.multiCheck?.length ? prev.multiCheck : null) !== JSON.stringify(s.multiCheck?.length ? s.multiCheck : null)
    )
      steps.push({ kind: 'modified', a: prev, b: s });
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
    else if (prev.amount !== m.amount || prev.unit !== m.unit || prev.scaling !== m.scaling)
      materials.push({ kind: 'modified', name: m.name, a: prev, b: m });
    else materials.push({ kind: 'unchanged', name: m.name, a: prev, b: m });
  }
  for (const m of aMatList) {
    if (!bMats.has(m.name)) materials.push({ kind: 'removed', name: m.name, a: m });
  }

  return { steps, materials, changelog: b.changelog };
}
