// Extractor run outputs against the gold set (OF-DES-001 §14.3, §8.8).
//
// SYNTHETIC. These are seeded confusion data, not the output of a real model —
// the Sim computes metrics over them but does not train or run an extractor
// (fidelity matrix rows 8 and 9).
//
// The story the dashboard should tell:
//   * Precision climbs sharply across the three runs (0.44 → 0.65 → 0.86), and
//     unit-normalization failures are the visible driver — five of them in
//     v0.3, two in v0.4, none in v0.4+rules.
//   * Recall barely moves and stays low. Fifteen gold parameters were annotated
//     by a curator and have never been produced by any configuration; they are
//     'miss' in every run. That ceiling is real and the screen says so rather
//     than hiding it.
import type { RunOutput, ExtractorRun } from './types';

/** Every gold-annotated record, in id order. */
const GOLD_IDS = [
  'ex-0001', 'ex-0005', 'ex-0006', 'ex-0010', 'ex-0011', 'ex-0018', 'ex-0019',
  'ex-0020', 'ex-0021', 'ex-0027', 'ex-0028', 'ex-0030', 'ex-0033', 'ex-0035',
  'ex-0036', 'ex-0042', 'ex-0043', 'ex-0046', 'ex-0051', 'ex-0052', 'ex-0057',
  'ex-0061', 'ex-0062', 'ex-0069', 'ex-0070', 'ex-0071', 'ex-0079', 'ex-0080',
  'ex-0082', 'ex-0086', 'ex-0090', 'ex-0091', 'ex-0095', 'ex-0099', 'ex-0108',
  'ex-0109', 'ex-0115', 'ex-0117', 'ex-0118', 'ex-0125', 'ex-0132',
];

/**
 * Curator-annotated parameters with no extraction from any run. These are the
 * platform's honest recall ceiling: 15 of 41 gold entries have never been found.
 */
const NEVER_FOUND = [
  'ex-0010', 'ex-0019', 'ex-0035', 'ex-0042', 'ex-0051', 'ex-0061', 'ex-0069',
  'ex-0079', 'ex-0086', 'ex-0090', 'ex-0099', 'ex-0108', 'ex-0117', 'ex-0125',
  'ex-0132',
];

type Exception = {
  outcome: 'value_mismatch' | 'unit_error' | 'span_error';
  extracted: { value: number; unit: string };
};

/** Per-run deviations from 'match'; everything else in GOLD_IDS is a match. */
const EXCEPTIONS: Record<ExtractorRun, Record<string, Exception>> = {
  // v0.3 — no unit normalization at all. Rates published per day are carried
  // through verbatim; the OD basis is dropped from conversion factors.
  'v0.3': {
    'ex-0033': { outcome: 'unit_error', extracted: { value: 0.038, unit: 'd⁻¹' } },
    'ex-0071': { outcome: 'unit_error', extracted: { value: 0.038, unit: 'd⁻¹' } },
    'ex-0082': { outcome: 'unit_error', extracted: { value: 0.31, unit: 'g L⁻¹' } },
    'ex-0095': { outcome: 'unit_error', extracted: { value: 2.1, unit: 'mg g⁻¹ d⁻¹' } },
    'ex-0115': { outcome: 'unit_error', extracted: { value: 0.248, unit: 'g L⁻¹ d⁻¹' } },
    'ex-0027': { outcome: 'value_mismatch', extracted: { value: 0.079, unit: 'h⁻¹' } },
    'ex-0018': { outcome: 'span_error', extracted: { value: 7, unit: '' } },
  },
  // v0.4 — a unit dictionary lands, fixing the per-day rate cases. The
  // dimensionally-silent failures (a dropped OD basis) survive it.
  'v0.4': {
    'ex-0082': { outcome: 'unit_error', extracted: { value: 0.31, unit: 'g L⁻¹' } },
    'ex-0115': { outcome: 'unit_error', extracted: { value: 0.248, unit: 'g L⁻¹ d⁻¹' } },
    'ex-0027': { outcome: 'value_mismatch', extracted: { value: 0.079, unit: 'h⁻¹' } },
    'ex-0018': { outcome: 'span_error', extracted: { value: 7, unit: '' } },
  },
  // v0.4+rules — dimensional rules keyed to the parameter definition catch the
  // remaining unit failures. What is left is a genuinely hard reading: a rate
  // quoted for the wrong growth interval.
  'v0.4r': {
    'ex-0027': { outcome: 'value_mismatch', extracted: { value: 0.079, unit: 'h⁻¹' } },
  },
};

function results(run: ExtractorRun): RunOutput['results'] {
  return GOLD_IDS.map((goldRecordId) => {
    if (NEVER_FOUND.includes(goldRecordId)) return { goldRecordId, outcome: 'miss' as const };
    const ex = EXCEPTIONS[run][goldRecordId];
    if (ex) return { goldRecordId, outcome: ex.outcome, extracted: ex.extracted };
    return { goldRecordId, outcome: 'match' as const };
  });
}

export const RUN_OUTPUTS: RunOutput[] = [
  {
    run: 'v0.3',
    results: results('v0.3'),
    falsePositives: [
      {
        id: 'fp-v03-01',
        paperId: 'SP-001',
        field: 'final_biomass_density',
        extracted: { value: 0.05, unit: 'g L⁻¹' },
        note: 'Read the inoculation optical density as a final biomass density.',
      },
      {
        id: 'fp-v03-02',
        paperId: 'SP-002',
        field: 'growth_rate_mu',
        extracted: { value: 0.112, unit: 'h⁻¹' },
        note: 'Extracted a rate from the Introduction’s summary of prior work rather than this study’s result.',
      },
      {
        id: 'fp-v03-03',
        paperId: 'SP-003',
        field: 'medium_component_conc',
        extracted: { value: 20, unit: 'g L⁻¹' },
        note: 'Captured an agar concentration from a plating method as a liquid-medium component.',
      },
      {
        id: 'fp-v03-04',
        paperId: 'SP-006',
        field: 'disruption_efficiency',
        extracted: { value: 100, unit: '%' },
        note: 'Took a rhetorical “complete disruption” as a measured efficiency.',
      },
      {
        id: 'fp-v03-05',
        paperId: 'SP-007',
        field: 'light_intensity',
        extracted: { value: 2000, unit: 'µmol m⁻² s⁻¹' },
        note: 'Read an instrument’s stated measurement ceiling as a culture setpoint.',
      },
      {
        id: 'fp-v03-06',
        paperId: 'SP-010',
        field: 'od_dcw_factor',
        extracted: { value: 750, unit: 'g L⁻¹ OD⁻¹' },
        note: 'Parsed the 750 nm wavelength as the conversion coefficient.',
      },
      {
        id: 'fp-v03-07',
        paperId: 'SP-012',
        field: 'product_titer',
        extracted: { value: 30, unit: 'g L⁻¹' },
        note: 'Extracted a target titer from the Discussion’s outlook as a measured result.',
      },
      {
        id: 'fp-v03-08',
        paperId: 'SP-014',
        field: 'temperature',
        extracted: { value: 30, unit: '°C' },
        note: 'Attributed a cited literature condition to this study’s process.',
      },
    ],
  },
  {
    run: 'v0.4',
    results: results('v0.4'),
    falsePositives: [
      {
        id: 'fp-v04-01',
        paperId: 'SP-002',
        field: 'growth_rate_mu',
        extracted: { value: 0.112, unit: 'h⁻¹' },
        note: 'Still reading prior-work rates from the Introduction as this study’s own.',
      },
      {
        id: 'fp-v04-02',
        paperId: 'SP-006',
        field: 'disruption_efficiency',
        extracted: { value: 100, unit: '%' },
        note: 'Took a rhetorical “complete disruption” as a measured efficiency.',
      },
      {
        id: 'fp-v04-03',
        paperId: 'SP-010',
        field: 'od_dcw_factor',
        extracted: { value: 750, unit: 'g L⁻¹ OD⁻¹' },
        note: 'Parsed the 750 nm wavelength as the conversion coefficient.',
      },
      {
        id: 'fp-v04-04',
        paperId: 'SP-012',
        field: 'product_titer',
        extracted: { value: 30, unit: 'g L⁻¹' },
        note: 'Extracted a target titer from the Discussion’s outlook as a measured result.',
      },
      {
        id: 'fp-v04-05',
        paperId: 'SP-015',
        field: 'protein_content',
        extracted: { value: 70, unit: '% DW' },
        note: 'Captured a genus-level range from the Introduction as a measurement of this culture.',
      },
    ],
  },
  {
    run: 'v0.4r',
    results: results('v0.4r'),
    falsePositives: [
      {
        id: 'fp-v04r-01',
        paperId: 'SP-002',
        field: 'growth_rate_mu',
        extracted: { value: 0.112, unit: 'h⁻¹' },
        note: 'Section-aware rules cut most of these, but an Introduction rate stated without hedging still passes.',
      },
      {
        id: 'fp-v04r-02',
        paperId: 'SP-012',
        field: 'product_titer',
        extracted: { value: 30, unit: 'g L⁻¹' },
        note: 'A forward-looking target phrased in the past tense still reads as a result.',
      },
      {
        id: 'fp-v04r-03',
        paperId: 'SP-015',
        field: 'protein_content',
        extracted: { value: 70, unit: '% DW' },
        note: 'Genus-level literature range attributed to the measured culture.',
      },
    ],
  },
];
