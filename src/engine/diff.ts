// MIRROR of openferment_core/protocol/diff.py. Python is canonical. Changes go
// there first, then here, and parity is enforced by pnpm verify.
//
// This file is not dead weight and is not scheduled for deletion: the UI runs
// offline in the browser, where there is no Python, and the version-compare
// view has to render without a round trip. The diff OF RECORD is a Ledger
// concern and is computed server-side from the canonical models; this copy is
// what a reviewer reads offline, and it has to say the same thing. So the
// mirror stays — and because it stays, the agreement between the two has to be
// mechanically checked rather than remembered. `pnpm check:protocol` replays
// fixtures/diff.json, the language-neutral pin, against this file. If you change
// what counts as a modification, or the order the diff comes out in, here
// without changing it in Python, that check fails.
//
// Structural diff of two protocol versions (OF-DES-001 §8.11).
import type { ProtocolVersion, Step, Material } from '@/data/types';

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
  changelog?: string;
}

export function diffVersions(a: ProtocolVersion, b: ProtocolVersion): VersionDiff {
  const steps: StepDiff[] = [];
  const aSteps = new Map(a.steps.map((s) => [s.id, s]));
  const bSteps = new Map(b.steps.map((s) => [s.id, s]));
  // Walk b's order (the newer version), marking removed a-steps in place.
  for (const s of b.steps) {
    const prev = aSteps.get(s.id);
    if (!prev) steps.push({ kind: 'added', b: s });
    else if (
      prev.text !== s.text ||
      prev.timerSec !== s.timerSec ||
      JSON.stringify(prev.multiCheck ?? null) !== JSON.stringify(s.multiCheck ?? null)
    )
      steps.push({ kind: 'modified', a: prev, b: s });
    else steps.push({ kind: 'unchanged', a: prev, b: s });
  }
  for (const s of a.steps) {
    if (!bSteps.has(s.id)) steps.push({ kind: 'removed', a: s });
  }

  const materials: MaterialDiff[] = [];
  const aMats = new Map(a.materials.map((m) => [m.name, m]));
  const bMats = new Map(b.materials.map((m) => [m.name, m]));
  for (const m of b.materials) {
    const prev = aMats.get(m.name);
    if (!prev) materials.push({ kind: 'added', name: m.name, b: m });
    else if (prev.amount !== m.amount || prev.unit !== m.unit || prev.scaling !== m.scaling)
      materials.push({ kind: 'modified', name: m.name, a: prev, b: m });
    else materials.push({ kind: 'unchanged', name: m.name, a: prev, b: m });
  }
  for (const m of a.materials) {
    if (!bMats.has(m.name)) materials.push({ kind: 'removed', name: m.name, a: m });
  }

  return { steps, materials, changelog: b.changelog };
}
