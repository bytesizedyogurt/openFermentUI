// Resolving the corpus pool's plants into the frame their price is quoted in.
//
// Kept apart from the demo pool's resolver on purpose, exactly as
// `trace-corpus.ts` is kept apart from `accessionTrace`. Both produce the same
// `QuotationBasis`, and nothing imports both — a single resolver that took an id
// and chose a pool by its prefix would be the first module in the build to hold
// a `Scenario` and a `FacilityConcept` at once.
//
// ── EVERYTHING HERE IS DERIVED, NOTHING IS SEEDED ─────────────────────────
//
// The numbers already live in `baseTEA()` and in the module-global `CE`. Putting
// them in `data/corpus/scenarios.json` would add a `Scenario` field, force a
// corpus edit, and put `check:servers` — whose whole job is that `proforma_mcp`'s
// derivation equals `COST_MODELS` byte for byte — at risk for no gain.
import type { QuotationBasis } from '@/data/types';
import { CE, CEPCI_BY_YEAR, CEPCI_LATEST_YEAR } from '@/engine/biosteam/cepci';
import { FLOWSHEET_BY_MODEL } from '@/sim/flowsheets/plants';
import type { TEAOptions } from '@/engine/biosteam/tea';

/**
 * What the corpus plants do not have, said plainly.
 *
 * This list is the reason `QuotationBasis` exists. A basis that enumerates what
 * it covers is marketing; one that enumerates what it does not is an estimate.
 */
const CORPUS_EXCLUDES = [
  'No regional location factor — installed capital is bioSTEAM’s correlations at face value.',
  'No regional labour rate. Labour is one line, 2.1 M USD yr⁻¹, wherever the plant is.',
  'No regional utility prices — bioSTEAM’s published US list, reproduced rather than adjusted.',
  'No import duty, freight or site-specific civil works.',
  'No co-product credit except where a flowsheet states one in its own limitations.',
];

/**
 * The regional gap, stated rather than guessed.
 *
 * This is the decision that makes the corpus half honest. Proforma's charter is
 * "techno-economics against an explicit regional and temporal basis" and the
 * temporal half is real — a cost index, a project life, a discount rate. The
 * regional half does not exist, and it cannot be invented: the β-casein corpus
 * is literature about a protein, and no paper in it says where a plant would be
 * built. Naming a region to satisfy the charter would be fabricating data.
 *
 * So it takes the same shape as `year: 0` and the venue sentinel — an absence
 * with a reason attached, which a reader can act on, rather than a plausible
 * default they cannot tell from a measurement.
 */
const REGION_UNDECLARED = {
  kind: 'undeclared' as const,
  why:
    'Nothing in the β-casein corpus states where this plant is sited, so no region has been ' +
    'declared and no location factor applied. The 21 % income tax is US federal, which is the ' +
    'one geographic assumption in here — inherited from bioSTEAM’s TEA defaults rather than chosen.',
};

/**
 * No accuracy class, and that said out loud.
 *
 * `CapexCurve` argues on the demo side that "a crisp line drawn without that
 * band is a promise the number cannot keep". The corpus MSP has been exactly
 * that crisp line since it was first rendered. The Monte Carlo is the only
 * interval on offer and it has to be asked for, which is stated here rather than
 * left for a reader to discover.
 */
const ACCURACY_UNSTATED = {
  kind: 'unstated' as const,
  why:
    'No accuracy class has been assigned to this estimate. The Monte Carlo on this screen is the ' +
    'only interval available, and it does not run until it is asked for.',
};

/**
 * The CEPCI year matching a given index value, when one matches exactly.
 *
 * `undefined` rather than a nearest-year guess: `setCEPCI` throws instead of
 * falling back for the same reason, and a year attributed to an index that is
 * not in the table would be a fact nobody put there.
 */
function yearForIndex(value: number): number | undefined {
  const hit = Object.entries(CEPCI_BY_YEAR).find(([, v]) => v === value);
  return hit ? Number(hit[0]) : undefined;
}

/**
 * The basis one corpus plant is priced against.
 *
 * `tea` is passed in rather than read off the spec so the price screen can show
 * the basis the reader has actually edited — the settings panel is the basis,
 * and a stamp that ignored it would describe a plant nobody is looking at.
 */
export function corpusBasis(
  modelId: string,
  opts?: { tea?: Partial<TEAOptions>; CE?: number },
): QuotationBasis | null {
  const spec = FLOWSHEET_BY_MODEL[modelId];
  if (!spec) return null;
  const tea = { ...spec.tea, ...opts?.tea };
  const ce = opts?.CE ?? CE.value;

  return {
    statedFor: modelId,
    currency: 'USD',
    // No conversion is performed anywhere in the corpus pool. `undefined` says
    // that, and it is a different claim from a rate of 1.0.
    costIndex: {
      name: 'CEPCI',
      year: yearForIndex(ce),
      value: ce,
      covers: [1980, CEPCI_LATEST_YEAR],
      note:
        ce === 567.5
          ? 'bioSTEAM’s own default, a 2017 basis. The table ends at ' +
            `${CEPCI_LATEST_YEAR}, and this plant is built from ${tea.duration[0]} — no index ` +
            'exists for its construction years, so capital is quoted in the basis year and not ' +
            'escalated to it.'
          : 'Set on this screen. Every purchase-cost correlation is scaled by CE ÷ its own ' +
            'published index at the moment it is applied.',
    },
    discountRate: tea.IRR,
    discountRateKind: 'IRR',
    projectLife: [tea.duration[0], tea.duration[1]],
    incomeTax: tea.incomeTax,
    taxNote: 'US federal, bioSTEAM’s default. No state or local tax is modelled.',
    operatingDays: tea.operatingDays,
    region: REGION_UNDECLARED,
    accuracy: ACCURACY_UNSTATED,
    excludes: CORPUS_EXCLUDES as [string, ...string[]],
  };
}
