// Vocabulary the software reads: downstream unit operations and the carbon
// sources a record's wording resolves to.
//
// Names, stages, spellings and the BioSTEAM classes each step maps to. No
// value, range or claim about any organism or product lives here. alpha 2.0
// (ADR-010) kept these two lists from the old facet vocabulary and deleted
// the rest with the seeded catalogue.
import type { CarbonSource, UnitOperation, UnitOperationStage } from './types';

/**
 * The id a paper's wording names, by the whole-word rule (OF-BLD-014 §2.1).
 *
 * The wording is trimmed, its runs of whitespace collapsed and lower-cased.
 * An exact alias wins. Otherwise every alias that stands inside the wording as
 * a whole word — no letter or digit touching either end — is a hit, and when
 * all the hits name ONE id that id is the answer. No hit is null, and so is
 * hits naming two different ids: "E. coli expressing bovine β-casein" names
 * two organisms, and choosing one would merge measurements this table exists
 * to keep apart.
 *
 * `carbonSourceId` in vocabulary.ts applies the same rule, and
 * `core/openferment_core/validate.py` mirrors it line for line, held to it by
 * the fixture `scripts/export-unit-fixtures.ts` records from this function.
 */
export function matchWholeWord(text: string, aliases: Record<string, string>): string | null {
  const wording = text.trim().replace(/\s+/g, ' ').toLowerCase();
  if (wording === '') return null;
  // Own keys only: 'constructor' is not an alias.
  if (Object.prototype.hasOwnProperty.call(aliases, wording)) return aliases[wording];
  const hits = new Set<string>();
  for (const [alias, id] of Object.entries(aliases)) {
    if (alias !== '' && containsWord(wording, alias)) hits.add(id);
  }
  return hits.size === 1 ? [...hits][0] : null;
}

const WORD_CHAR = /[a-z0-9]/;

/** Whether `needle` occurs in `haystack` with no letter or digit touching it. */
function containsWord(haystack: string, needle: string): boolean {
  for (let at = haystack.indexOf(needle); at !== -1; at = haystack.indexOf(needle, at + 1)) {
    const before = at === 0 ? '' : haystack[at - 1];
    const after = at + needle.length < haystack.length ? haystack[at + needle.length] : '';
    if (!WORD_CHAR.test(before) && !WORD_CHAR.test(after)) return true;
  }
  return false;
}

/**
 * Downstream unit operations. A product's `unitOperationIds` array is ordered
 * fermenter to vial and is the authority on its train; `stage` here only says
 * what kind of job the operation does.
 */
export const UNIT_OPERATIONS: UnitOperation[] = [
  {
    id: 'centrifugation',
    label: 'Centrifugation',
    stage: 'harvest',
    scale: 'all',
    note: 'disc-stack at production scale',
    biosteamClasses: [
      'SolidsCentrifuge',
      'LiquidsCentrifuge',
      'LiquidsSplitCentrifuge',
      'LiquidsRatioCentrifuge',
      'SolidLiquidsSplitCentrifuge',
      'SLLECentrifuge',
    ],
  },
  {
    id: 'microfiltration',
    label: 'Microfiltration',
    stage: 'harvest',
    note: 'cell removal, secreted products',
  },
  {
    id: 'depth-filtration',
    label: 'Depth filtration',
    stage: 'clarification',
  },
  {
    id: 'homogenisation',
    label: 'High-pressure homogenisation',
    stage: 'cell disruption',
    note: 'intracellular products',
  },
  {
    id: 'bead-mill',
    label: 'Bead milling',
    stage: 'cell disruption',
    scale: 'bench-pilot',
  },
  {
    id: 'uf-df',
    label: 'Ultrafiltration / diafiltration',
    stage: 'concentration',
    note: 'buffer exchange + concentration',
  },
  {
    id: 'nanofiltration',
    label: 'Nanofiltration',
    stage: 'concentration',
    note: 'oligosaccharide retention',
  },
  {
    id: 'electrodialysis',
    label: 'Electrodialysis',
    stage: 'desalting',
    note: 'HMO salt removal',
  },
  {
    id: 'iex',
    label: 'Ion exchange chromatography',
    stage: 'capture/polish',
    resin: 'Q / SP',
  },
  {
    id: 'hic',
    label: 'Hydrophobic interaction chromatography',
    stage: 'polish',
  },
  {
    id: 'imac',
    label: 'IMAC affinity',
    stage: 'capture',
    note: 'His-tagged products',
  },
  {
    id: 'affinity-custom',
    label: 'Custom affinity chromatography',
    stage: 'capture',
  },
  {
    id: 'sec',
    label: 'Size exclusion chromatography',
    stage: 'polish',
    note: 'low throughput, high resolution',
  },
  {
    id: 'mixed-mode',
    label: 'Mixed-mode chromatography',
    stage: 'polish',
  },
  {
    id: 'heat-step',
    label: 'Thermal clarification',
    stage: 'capture',
    note: 'thermostable enzymes only — huge cost saver for Taq-class products',
  },
  {
    id: 'refolding',
    label: 'Inclusion body solubilisation + refolding',
    stage: 'recovery',
    note: 'E. coli intracellular route',
  },
  {
    id: 'protease-cleavage',
    label: 'Protease tag cleavage',
    stage: 'polish',
  },
  {
    id: 'crystallisation',
    label: 'Crystallisation',
    stage: 'isolation',
    biosteamClasses: ['BatchCrystallizer'],
  },
  {
    id: 'precipitation',
    label: 'Precipitation',
    stage: 'capture',
    note: 'ammonium sulfate / PEG',
  },
  {
    id: 'lle',
    label: 'Liquid-liquid extraction',
    stage: 'recovery',
    note: 'terpene recovery',
    biosteamClasses: [
      'LLEUnit',
      'LLESettler',
      'LLECentrifuge',
      'MixerSettler',
      'LiquidsSettler',
      'LiquidsSplitSettler',
      'LiquidsPartitionSettler',
    ],
  },
  {
    id: 'distillation',
    label: 'Distillation / rectification',
    stage: 'purification',
    note: 'terpene finishing; the beer column and rectifier of an ethanol plant',
    biosteamClasses: ['Distillation', 'BinaryDistillation', 'MESHDistillation', 'AdiabaticMultiStageVLEColumn'],
  },
  {
    // OF-BLD-019 §4.1 — the step after the rectifier in every fuel-ethanol
    // train BioSTEAM ships; vocabulary, so it carries no number.
    id: 'molecular-sieve',
    label: 'Molecular sieve dehydration',
    stage: 'purification',
    note: 'adsorbs the water distillation cannot take past the ethanol-water azeotrope',
    biosteamClasses: ['MolecularSieve'],
  },
  {
    id: 'spray-dry',
    label: 'Spray drying',
    stage: 'drying',
    note: 'ambient-stable powder',
    biosteamClasses: ['SprayDryer'],
  },
  {
    id: 'lyophilisation',
    label: 'Lyophilisation',
    stage: 'drying',
    note: 'highest stability, highest cost',
  },
  {
    id: 'granulation',
    label: 'Granulation',
    stage: 'formulation',
    note: 'dust-free industrial enzyme',
  },
  {
    id: 'sterile-filtration',
    label: 'Sterile filtration',
    stage: 'finishing',
  },
  {
    id: 'endotoxin-removal',
    label: 'Endotoxin clearance',
    stage: 'polish',
    note: 'mandatory for E. coli-derived research/clinical proteins',
  },
  {
    id: 'nuclease-clearance',
    label: 'Nuclease/residual-DNA clearance',
    stage: 'polish',
    note: 'defining step for molecular-biology enzyme grade',
  },
  // OF-BLD-020 §5.1 — the steps pureOS's unit catalogue builds a train from
  // (core/openferment_core/pureos/catalogue.py), each a catalogue id. The
  // vocabulary carries no number; a class is one step (check:seed), so the
  // shortcut column and the counter-current extractor left `distillation` and
  // `lle` for entries of their own.
  {
    id: 'pressure-filtration',
    label: 'Pressure filtration',
    stage: 'clarification',
    note: 'a filter press: solids stay as a cake, the filtrate passes',
    biosteamClasses: ['PressureFilter'],
  },
  {
    id: 'rotary-vacuum-filtration',
    label: 'Rotary vacuum filtration',
    stage: 'clarification',
    note: 'a turning drum under vacuum: the cake stays on the drum',
    biosteamClasses: ['RotaryVacuumFilter'],
  },
  {
    id: 'clarifier',
    label: 'Clarifier',
    stage: 'clarification',
    note: 'solids settle; the clear liquid overflows',
    biosteamClasses: ['Clarifier'],
  },
  {
    id: 'flash',
    label: 'Flash',
    stage: 'concentration',
    note: 'part of the broth boils at a set pressure or temperature; vapour and liquid leave at equilibrium',
    biosteamClasses: ['Flash'],
  },
  {
    id: 'distillation-shortcut',
    label: 'Distillation, shortcut column',
    stage: 'purification',
    note: 'stages by the Fenske–Underwood–Gilliland shortcut',
    biosteamClasses: ['ShortcutColumn'],
  },
  {
    id: 'evaporation',
    label: 'Multi-effect evaporation',
    stage: 'concentration',
    note: 'water boiled off in effects at falling pressures',
    biosteamClasses: ['MultiEffectEvaporator'],
  },
  {
    id: 'lle-multistage',
    label: 'Counter-current extraction',
    stage: 'recovery',
    note: 'mixer-settlers in series, the solvent against the broth',
    biosteamClasses: ['MultiStageMixerSettlers'],
  },
  {
    id: 'adsorption',
    label: 'Adsorption column',
    stage: 'purification',
    note: 'a lead, guard and standby column swap as the bed loads',
    biosteamClasses: ['SingleComponentAdsorptionColumn'],
  },
  {
    id: 'drying-drum',
    label: 'Drum drying',
    stage: 'drying',
    note: 'hot gas through a turning drum, the gas heated by burning fuel',
    biosteamClasses: ['DrumDryer'],
  },
  {
    id: 'cell-disruption',
    label: 'Cell disruption',
    stage: 'cell disruption',
    note: 'homogeniser or bead mill: the product the cells hold moves into the liquid',
  },
  {
    id: 'chromatography',
    label: 'Chromatography',
    stage: 'capture/polish',
    note: 'a column step by its mode, with declared recovery and purity until a column model computes them',
  },
  {
    id: 'heat-exchange',
    label: 'Heat exchange',
    stage: 'utility',
    note: 'heats or cools a stream with a utility',
    biosteamClasses: ['HXutility'],
  },
  {
    id: 'tank',
    label: 'Storage tank',
    stage: 'utility',
    note: 'holds a stream for a residence time',
    biosteamClasses: ['StorageTank'],
  },
  {
    id: 'mix-tank',
    label: 'Mix tank',
    stage: 'utility',
    note: 'mixes streams in a stirred tank',
    biosteamClasses: ['MixTank'],
  },
  {
    id: 'pump',
    label: 'Pump',
    stage: 'utility',
    note: 'raises a stream\'s pressure',
    biosteamClasses: ['Pump'],
  },
  {
    id: 'mixer',
    label: 'Mixer',
    stage: 'utility',
    note: 'joins streams into one',
    biosteamClasses: ['Mixer'],
  },
  {
    id: 'splitter',
    label: 'Splitter',
    stage: 'utility',
    note: 'divides a stream by each component\'s split',
    biosteamClasses: ['Splitter'],
  },
];

/**
 * What the cells were fed (OF-BLD-014 §2.1). A record's `carbonSource` keeps
 * the paper's own words; this list is the names those words resolve to, with
 * the spellings papers use for each. Names and spellings only — a
 * concentration or a feed rate is a measurement, and belongs on a record.
 *
 * `spellings` are lower-case and include the name itself. `carbonSourceId`
 * reads them by the whole-word rule `normalizeStrain` uses, and
 * `scripts/export-corpus.ts` carries the list to the service, where
 * `validate.carbon_source_id` applies the same rule.
 */
export const CARBON_SOURCES: CarbonSource[] = [
  { id: 'glucose', label: 'Glucose', spellings: ['glucose', 'd-glucose', 'dextrose'] },
  { id: 'xylose', label: 'Xylose', spellings: ['xylose', 'd-xylose'] },
  { id: 'fructose', label: 'Fructose', spellings: ['fructose', 'd-fructose'] },
  { id: 'glycerol', label: 'Glycerol', spellings: ['glycerol', 'glycerin', 'glycerine'] },
  { id: 'acetate', label: 'Acetate', spellings: ['acetate', 'acetic acid'] },
  {
    id: 'mixed-sugars',
    label: 'Mixed sugars',
    spellings: ['mixed sugars', 'mixed sugar', 'sugar mixture', 'mixture of sugars'],
  },
  { id: 'hydrolysate', label: 'Hydrolysate', spellings: ['hydrolysate', 'hydrolyzate'] },
];

const CARBON_SPELLINGS: Record<string, string> = Object.fromEntries(
  CARBON_SOURCES.flatMap((c) => c.spellings.map((sp) => [sp, c.id])),
);

/**
 * The carbon source a paper's wording names, or null: an exact spelling, or
 * spellings standing in the wording as whole words that all name one source
 * (`matchWholeWord` in strains.ts). "Crude glycerol" is glycerol; "glucose
 * and xylose" names two and is null, and the record keeps the words.
 */
export function carbonSourceId(text: string): string | null {
  return matchWholeWord(text, CARBON_SPELLINGS);
}

const byId = <T extends { id: string }>(xs: T[]): Record<string, T> =>
  Object.fromEntries(xs.map((x) => [x.id, x]));

export const UNIT_OPERATIONS_BY_ID = byId(UNIT_OPERATIONS);

/**
 * The vocabulary's step for a BioSTEAM unit class, or null (OF-BLD-019 §4.1).
 * A class names at most one step (`check:seed` holds it), so a unit in a
 * train links to one entry or to none.
 */
export function operationForClass(unitClass: string): UnitOperation | null {
  return UNIT_OPERATIONS.find((op) => op.biosteamClasses?.includes(unitClass)) ?? null;
}

/**
 * Display order for the stage vocabulary, fermenter to vial. Used to group the
 * unit-operation facet sheet; a product's own array order still wins when its
 * train is drawn, because the same operation lands at different points in
 * different processes (IEX captures for Taq and polishes for brazzein).
 */
export const UNIT_OP_STAGE_ORDER: UnitOperationStage[] = [
  'harvest',
  'clarification',
  'cell disruption',
  'recovery',
  'capture',
  'capture/polish',
  'polish',
  'concentration',
  'desalting',
  'isolation',
  'purification',
  'drying',
  'formulation',
  'finishing',
  'utility',
];
