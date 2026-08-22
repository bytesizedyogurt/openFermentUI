// The Monte Carlo, behind the same door as the solve.
//
// Two hundred Latin hypercube samples, each one a full flowsheet build and a
// fresh discounted cash flow. It is the most expensive thing the app does, and
// it is deliberately a button rather than something that happens on arrival —
// `deep-paths.mjs` asserts that it has not run when the screen loads, because a
// result that appears without being asked for reads as a lookup rather than as
// work.
//
// It lives beside `use-plant.ts` for the same reason that file gives: nothing
// under `src/screens/**` may import `@/engine/uncertainty` at runtime, and
// `scripts/check-seam.mjs` enforces it. The engine call happens here, once.
import { useCallback, useState } from 'react';

import { useStore } from '@/store';
import { runPlantUncertainty, type PlantUncertainty } from '@/engine/uncertainty';
import { FLOWSHEET_BY_MODEL } from '@/sim/flowsheets/plants';
import { scaled } from '@/sim/latency';

export type { PlantUncertainty };

/** How many samples. Named because the screen prints it in two places. */
export const UNCERTAINTY_SAMPLES = 200;

export interface UncertaintyRun {
  uncertainty: PlantUncertainty | null;
  running: boolean;
  run: () => void;
}

export function usePlantUncertainty(scenarioId: string): UncertaintyRun {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const toast = useStore((s) => s.toast);
  const [uncertainty, setUncertainty] = useState<PlantUncertainty | null>(null);
  const [running, setRunning] = useState(false);

  const run = useCallback(() => {
    const spec = scenario ? FLOWSHEET_BY_MODEL[scenario.modelId] : undefined;
    if (!scenario || !spec) return;
    setRunning(true);
    // Deferred so the button's disabled state paints before the main thread is
    // taken for the better part of a second.
    window.setTimeout(() => {
      try {
        setUncertainty(runPlantUncertainty(spec, scenario.point, { n: UNCERTAINTY_SAMPLES }));
      } catch {
        toast({ text: 'The uncertainty run could not build a plant at any sample.', kind: 'error' });
      }
      setRunning(false);
    }, scaled(900));
  }, [scenario, toast]);

  return { uncertainty, running, run };
}
