// Facet vocabulary for the molecule catalogue (OF-BLD-005 §3).
//
// Everything here is new: unit operations, pathways, genetic elements, storage
// formats, regulatory routes, scale bands and clearance states. Hosts are NOT
// here — they live in `strains.ts` as full `Strain` records, because an
// organism is a page in this platform and a facet value is not.
//
// Nothing in this file touches the corpus. These are the axes a molecule is
// described along, not claims about the literature.
import type {
  ClearanceState,
  GeneticElement,
  Pathway,
  ProcessScale,
  RegulatoryPathway,
  StorageFormat,
  UnitOperation,
  UnitOperationStage,
} from './types';

/**
 * Construct-level vocabulary: what goes into the cell. Promoter, secretion
 * signal, purification tag, how the cassette is maintained, and the two
 * sequence-level knobs (codon optimisation, copy number).
 */
export const GENETIC_ELEMENTS: GeneticElement[] = [
  {
    id: 'prom-aox1',
    label: 'AOX1 promoter',
    kind: 'promoter',
    hostFit: ['k-phaffii'],
    induction: 'methanol',
    strength: 'very high',
  },
  {
    id: 'prom-gap',
    label: 'GAP promoter',
    kind: 'promoter',
    hostFit: ['k-phaffii'],
    induction: 'constitutive',
    strength: 'high',
  },
  {
    id: 'prom-t7',
    label: 'T7 promoter',
    kind: 'promoter',
    hostFit: ['e-coli-bl21'],
    induction: 'IPTG / autoinduction',
    strength: 'very high',
  },
  {
    id: 'prom-tac',
    label: 'tac promoter',
    kind: 'promoter',
    hostFit: ['e-coli-bl21', 'e-coli-k12'],
    induction: 'IPTG',
    strength: 'high',
  },
  {
    id: 'prom-cbh1',
    label: 'cbh1 promoter',
    kind: 'promoter',
    hostFit: ['t-reesei'],
    induction: 'cellulose/sophorose',
    strength: 'very high',
  },
  {
    id: 'sig-alpha-mf',
    label: 'alpha-mating factor signal',
    kind: 'signal_peptide',
    hostFit: ['k-phaffii', 's-cerevisiae'],
  },
  {
    id: 'sig-suc2',
    label: 'SUC2 invertase signal',
    kind: 'signal_peptide',
    hostFit: ['s-cerevisiae', 'k-phaffii'],
  },
  {
    id: 'sig-cbh1',
    label: 'CBH1 carrier fusion',
    kind: 'signal_peptide',
    hostFit: ['t-reesei'],
    note: 'carrier fusion boosts secretion',
  },
  {
    id: 'tag-his',
    label: 'His6 tag',
    kind: 'fusion_tag',
    purification: 'IMAC',
    cleavable: true,
  },
  {
    id: 'tag-mbp',
    label: 'MBP fusion',
    kind: 'fusion_tag',
    purification: 'amylose',
    cleavable: true,
    note: 'solubility enhancer',
  },
  {
    id: 'tag-sumo',
    label: 'SUMO fusion',
    kind: 'fusion_tag',
    cleavable: true,
    note: 'native N-terminus after cleavage',
  },
  {
    id: 'tag-intein',
    label: 'Self-cleaving intein',
    kind: 'fusion_tag',
    cleavable: 'autocatalytic',
    note: 'tagless product, no protease cost',
  },
  {
    id: 'int-genome',
    label: 'Genomic integration',
    kind: 'maintenance',
    stability: 'high',
    copy: '1-10',
  },
  {
    id: 'int-episomal',
    label: 'Episomal plasmid',
    kind: 'maintenance',
    stability: 'low-moderate',
    copy: '10-300',
  },
  {
    id: 'codon-opt',
    label: 'Codon optimisation',
    kind: 'sequence_design',
    tool: 'DnaChisel',
  },
  {
    id: 'copy-multi',
    label: 'Multi-copy cassette',
    kind: 'dosage',
    note: 'titre gains saturate; can trigger UPR stress',
  },
];

/** Metabolic routes, each named by the branch point flux must be pushed through. */
export const PATHWAYS: Pathway[] = [
  {
    id: 'mva',
    label: 'Mevalonate pathway',
    products: ['terpenes', 'sterols', 'squalene'],
    fluxNode: 'acetyl-CoA → IPP/DMAPP',
  },
  {
    id: 'mep',
    label: 'MEP/DXP pathway',
    products: ['terpenes'],
    fluxNode: 'pyruvate + G3P → IPP/DMAPP',
    note: 'bacterial alternative to MVA',
  },
  {
    id: 'heme-c4',
    label: 'Heme biosynthesis, C4 (Shemin)',
    products: ['heme proteins'],
    fluxNode: 'glycine + succinyl-CoA → ALA',
  },
  {
    id: 'heme-c5',
    label: 'Heme biosynthesis, C5 (glutamyl-tRNA)',
    products: ['heme proteins'],
    fluxNode: 'glutamate → ALA',
  },
  {
    id: 'gdp-fuc-denovo',
    label: 'GDP-fucose, de novo',
    products: ['fucosylated HMOs'],
    fluxNode: 'GDP-mannose → GDP-fucose',
  },
  {
    id: 'gdp-fuc-salvage',
    label: 'GDP-fucose, salvage',
    products: ['fucosylated HMOs'],
    fluxNode: 'L-fucose → GDP-fucose',
    note: 'bifunctional kinase/pyrophosphorylase; heavily claimed, functionally substitutable across Bacteroidetes',
  },
  {
    id: 'cmp-neu5ac',
    label: 'CMP-sialic acid pathway',
    products: ['sialylated HMOs'],
    fluxNode: 'GlcNAc → Neu5Ac → CMP-Neu5Ac',
  },
  {
    id: 'shikimate',
    label: 'Shikimate pathway',
    products: ['aromatics', 'vanillin', 'aromatic amino acids'],
    fluxNode: 'PEP + E4P',
  },
  {
    id: 'steviol',
    label: 'Steviol glycoside pathway',
    products: ['Reb M', 'Reb D'],
    fluxNode: 'GGPP → steviol → UGT glycosylation',
  },
  {
    id: 'polyketide',
    label: 'Polyketide/PKS',
    products: ['specialty molecules'],
    fluxNode: 'malonyl-CoA extension',
  },
];

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
  },
  {
    id: 'distillation',
    label: 'Distillation / rectification',
    stage: 'purification',
    note: 'terpene finishing',
  },
  {
    id: 'spray-dry',
    label: 'Spray drying',
    stage: 'drying',
    note: 'ambient-stable powder',
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
];

/**
 * Storage and shipping formats. This is the cold-chain decision made explicit:
 * for a landlocked facility the difference between -80 °C and lyophilised
 * ambient is the difference between dry-ice logistics and ordinary air freight.
 */
export const STORAGE_FORMATS: StorageFormat[] = [
  {
    id: 'minus80',
    label: '-80 °C',
    tempC: -80,
    shelfLife: 'years',
    logistics: 'dry ice',
    cost: 'high',
    note: 'research enzymes; dry-ice export from Kigali is the constraint to model',
  },
  {
    id: 'minus20-glycerol',
    label: '-20 °C in 50% glycerol',
    tempC: -20,
    shelfLife: '1-2 years',
    logistics: 'dry ice or gel pack',
    cost: 'moderate',
    note: 'standard molecular-biology enzyme format',
  },
  {
    id: 'cold-2-8',
    label: '2-8 °C',
    tempC: 5,
    shelfLife: 'months',
    logistics: 'gel pack / cold chain',
    cost: 'moderate',
  },
  {
    id: 'lyo-ambient',
    label: 'Lyophilised, ambient',
    tempC: 25,
    shelfLife: '1-3 years',
    logistics: 'ordinary air freight',
    cost: 'low',
    note: 'the strategic format for landlocked export — removes cold chain entirely',
  },
  {
    id: 'spray-ambient',
    label: 'Spray-dried, ambient',
    tempC: 25,
    shelfLife: '1-2 years',
    logistics: 'ordinary air freight',
    cost: 'low',
  },
  {
    id: 'liquid-stabilised',
    label: 'Stabilised liquid',
    tempC: 25,
    shelfLife: 'months',
    logistics: 'ambient',
    cost: 'low',
    note: 'industrial enzyme format; needs preservative/stabiliser system',
  },
];

/** Regulatory routes, ordered loosely by how much work they represent. */
export const REGULATORY_PATHWAYS: RegulatoryPathway[] = [
  {
    id: 'ruo',
    label: 'Research use only',
    burden: 'low',
    note: 'no premarket approval; fastest route to revenue',
  },
  {
    id: 'gras',
    label: 'US FDA GRAS / no-questions letter',
    burden: 'moderate',
  },
  {
    id: 'efsa-novel',
    label: 'EFSA novel food',
    burden: 'high',
  },
  {
    id: 'fema',
    label: 'FEMA GRAS (flavour)',
    burden: 'moderate',
  },
  {
    id: 'cosmetic',
    label: 'Cosmetic ingredient',
    burden: 'low-moderate',
  },
  {
    id: 'food-enzyme',
    label: 'Food enzyme authorisation',
    burden: 'moderate',
  },
  {
    id: 'ivd',
    label: 'IVD component / ISO 13485',
    burden: 'high',
  },
  {
    id: 'gmp',
    label: 'GMP drug substance',
    burden: 'very high',
    note: 'second-wave only; the barrier is quality systems, not fermentation',
  },
];

/** Fermenter scale bands, with the role each one plays in a build-out. */
export const SCALES: ProcessScale[] = [
  {
    id: 'bench',
    label: 'Bench',
    volumeL: '1-10',
    role: 'strain screening',
  },
  {
    id: 'pilot',
    label: 'Pilot',
    volumeL: '100-1000',
    role: 'process definition',
  },
  {
    id: 'small-prod',
    label: 'Small production',
    volumeL: '1000-10000',
    role: 'high-value enzymes and proteins',
  },
  {
    id: 'prod',
    label: 'Production',
    volumeL: '10000-50000',
    role: 'food proteins',
  },
  {
    id: 'large-prod',
    label: 'Large production',
    volumeL: '50000-200000',
    role: 'commodity — deliberately out of scope for a first Rwandan plant',
  },
];

/**
 * Patent clearance states (OF-BLD-005 §8). Each carries the action it implies
 * — never a legal opinion. Every surface that renders one also renders the
 * fixed counsel warning; the platform produces research leads, not advice.
 */
export const CLEARANCE_STATES: ClearanceState[] = [
  {
    id: 'clear-expired',
    label: 'Foundational IP expired',
    risk: 'low',
    action: 'proceed; document the evidence',
  },
  {
    id: 'clear-none',
    label: 'No blocking claims found',
    risk: 'low-moderate',
    action: 'counsel confirmation before commitment',
  },
  {
    id: 'watch-variant',
    label: 'Core free, variants fenced',
    risk: 'moderate',
    action: 'stay inside the free region; map the boundary',
  },
  {
    id: 'watch-process',
    label: 'Process claims live',
    risk: 'moderate',
    action: 'design around the process, not the molecule',
  },
  {
    id: 'blocked',
    label: 'Live blocking claims',
    risk: 'high',
    action: 'do not build; enumerate the genus or pick another target',
  },
  {
    id: 'unknown',
    label: 'Not yet assessed',
    risk: 'unknown',
    action: 'run clearance before any commitment',
  },
];

// ── lookups ────────────────────────────────────────────────────────────

const byId = <T extends { id: string }>(xs: T[]): Record<string, T> =>
  Object.fromEntries(xs.map((x) => [x.id, x]));

export const GENETIC_ELEMENTS_BY_ID = byId(GENETIC_ELEMENTS);
export const PATHWAYS_BY_ID = byId(PATHWAYS);
export const UNIT_OPERATIONS_BY_ID = byId(UNIT_OPERATIONS);
export const STORAGE_FORMATS_BY_ID = byId(STORAGE_FORMATS);
export const REGULATORY_PATHWAYS_BY_ID = byId(REGULATORY_PATHWAYS);
export const SCALES_BY_ID = byId(SCALES);
export const CLEARANCE_STATES_BY_ID = byId(CLEARANCE_STATES);

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
];

/** Lower is safer. Orders clearance chips and sorts a risk column. */
export const CLEARANCE_RISK_RANK: Record<string, number> = {
  low: 0,
  'low-moderate': 1,
  moderate: 2,
  high: 3,
  unknown: 4,
};

/** Lower is cheaper to clear. Orders the regulatory facet. */
export const REGULATORY_BURDEN_RANK: Record<string, number> = {
  low: 0,
  'low-moderate': 1,
  moderate: 2,
  high: 3,
  'very high': 4,
};

/** Ascending value per kilogram. Orders the value-density facet and column. */
export const VALUE_DENSITY_RANK: Record<string, number> = {
  'low-moderate': 0,
  moderate: 1,
  high: 2,
  'very high': 3,
  extreme: 4,
};
