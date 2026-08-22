// One plant, solved once, read by two screens.
//
// fermOS owns the plant and Proforma owns the price. That is the architecture's
// own division — `ProcessAdapter` against `EconomicsAdapter`, `fermos_mcp`
// against `proforma_mcp` — and until this hook existed the UI ignored it, with
// a single 1,162-line screen holding the flowsheet, the capital ladder and the
// cash flow under fermOS's name.
//
// Splitting the screens without splitting the solve is the whole trick. The
// flowsheet a reader edits on `/fermos/s/:id/plant` and the price quoted on
// `/proforma/price/:id` are the same `PlantResult` from the same overrides in
// the store, so the two screens cannot drift into quoting different plants.
//
// ── WHY THE ENGINE IMPORT LIVES HERE ─────────────────────────────────────
//
// `scripts/check-seam.mjs` forbids `src/screens/**` from importing
// `@/engine/plant`, `@/engine/uncertainty` or `@/sim/flowsheets/*` at runtime.
// This module is the one door, which is what makes that gate enforceable: when
// the plant solve moves behind `adapters.economics` for real, exactly one file
// changes.
import { useCallback, useMemo } from 'react';

import { useStore } from '@/store';
import {
  evaluatePlantCached,
  plantFails,
  type PlantOverrides,
  type PlantResult,
} from '@/engine/plant';
import { CE } from '@/engine/biosteam/cepci';
import { FLOWSHEET_BY_MODEL } from '@/sim/flowsheets/plants';
import type { FlowsheetSpec } from '@/sim/flowsheets/spec';
import type { PlantSettings } from '@/components/BiosteamSettings';
import type { Scenario } from '@/data/types';

/**
 * Whether the plant fails to size at a point.
 *
 * Re-exported rather than imported directly by the scenario workspace, which is
 * the only other screen that needs it. The workspace reads the precomputed grid
 * — it must NOT solve a plant to draw a slider — so it wants the predicate
 * without the solve, and routing it through this module is what keeps
 * `check:seam` able to say that no screen touches the engine.
 */
export { plantFails };

export interface PlantSolve {
  scenario: Scenario | undefined;
  spec: FlowsheetSpec | undefined;
  /** The plant as currently edited. `null` when it did not build. */
  result: PlantResult | null;
  /** The plant as the scenario declares it, for the before-and-after. */
  baseline: PlantResult | null;
  overrides: PlantOverrides;
  /** How many attributes the reader has changed. Zero means "as declared". */
  editCount: number;
  settings: PlantSettings | null;
  settingsDefaults: PlantSettings | null;
  applySettings: (patch: Partial<PlantSettings>) => void;
  setUnitSpec: (unitID: string, key: string, value: number | string) => void;
  resetUnit: (unitID: string) => void;
  /** Put the plant back exactly as the corpus left it. */
  restore: () => void;
  /** Drop only the financial basis, keeping equipment edits. */
  restoreBasis: () => void;
}

export function usePlantSolve(scenarioId: string): PlantSolve {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const overrides = useStore((s) => s.plantOverrides[scenarioId]) ?? EMPTY;
  const setPlantOverrides = useStore((s) => s.setPlantOverrides);

  const spec = scenario ? FLOWSHEET_BY_MODEL[scenario.modelId] : undefined;

  const editCount =
    Object.values(overrides.units ?? {}).reduce((n, u) => n + Object.keys(u).length, 0) +
    Object.keys(overrides.tea ?? {}).length +
    (overrides.CE === undefined ? 0 : 1);

  const result = useMemo(() => {
    if (!scenario) return null;
    try {
      return evaluatePlantCached(scenario.modelId, scenario.point, overrides);
    } catch {
      return null;
    }
  }, [scenario, overrides]);

  const baseline = useMemo(() => {
    if (!scenario) return null;
    try {
      return evaluatePlantCached(scenario.modelId, scenario.point);
    } catch {
      return null;
    }
  }, [scenario]);

  const settingsDefaults: PlantSettings | null = spec
    ? {
        cepciYear: null,
        CE: CE.value,
        operatingDays: spec.tea.operatingDays,
        IRR: spec.tea.IRR,
        incomeTax: spec.tea.incomeTax,
        depreciation: spec.tea.depreciation,
        WC_over_FCI: spec.tea.WC_over_FCI,
        financeInterest: spec.tea.financeInterest,
        financeYears: spec.tea.financeYears,
        financeFraction: spec.tea.financeFraction,
        startupMonths: spec.tea.startupMonths,
        laborCost: spec.tea.laborCost,
        maintenance: spec.tea.maintenance,
        langFactor: spec.tea.langFactor,
      }
    : null;

  const settings: PlantSettings | null = settingsDefaults
    ? {
        ...settingsDefaults,
        ...(overrides.tea as Partial<PlantSettings> | undefined),
        ...(overrides.CE !== undefined ? { CE: overrides.CE } : {}),
      }
    : null;

  /**
   * Settings split two ways on the way out: the cost index is a plant-wide
   * global that has to be in force while the equipment is costed, and
   * everything else is a TEA constructor argument. Keeping them in one panel is
   * right for the reader and wrong for the engine, so the split happens here.
   */
  const applySettings = useCallback(
    (patch: Partial<PlantSettings>): void => {
      const next = { ...overrides };
      const { CE: ce, cepciYear, ...teaPatch } = patch;
      if (ce !== undefined) next.CE = ce;
      void cepciYear;
      const teaKeys = Object.keys(teaPatch);
      if (teaKeys.length > 0) {
        next.tea = { ...overrides.tea, ...(teaPatch as PlantOverrides['tea']) };
      }
      setPlantOverrides(scenarioId, next);
    },
    [overrides, scenarioId, setPlantOverrides],
  );

  const setUnitSpec = useCallback(
    (unitID: string, key: string, value: number | string): void => {
      setPlantOverrides(scenarioId, {
        ...overrides,
        units: {
          ...overrides.units,
          [unitID]: { ...(overrides.units?.[unitID] ?? {}), [key]: value },
        },
      });
    },
    [overrides, scenarioId, setPlantOverrides],
  );

  const resetUnit = useCallback(
    (unitID: string): void => {
      const units = { ...overrides.units };
      delete units[unitID];
      setPlantOverrides(scenarioId, { ...overrides, units });
    },
    [overrides, scenarioId, setPlantOverrides],
  );

  const restore = useCallback(() => setPlantOverrides(scenarioId, {}), [
    scenarioId,
    setPlantOverrides,
  ]);

  const restoreBasis = useCallback(() => {
    const next = { ...overrides };
    delete next.tea;
    delete next.CE;
    setPlantOverrides(scenarioId, next);
  }, [overrides, scenarioId, setPlantOverrides]);

  return {
    scenario,
    spec,
    result,
    baseline,
    overrides,
    editCount,
    settings,
    settingsDefaults,
    applySettings,
    setUnitSpec,
    resetUnit,
    restore,
    restoreBasis,
  };
}

/**
 * A stable empty object.
 *
 * `useStore(...) ?? {}` would mint a new one on every render, and `overrides` is
 * a `useMemo` dependency — a fresh identity each frame would re-solve the whole
 * flowsheet sixty times a second.
 */
const EMPTY: PlantOverrides = {};
