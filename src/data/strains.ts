// openFerment Sim — seeded strains (cw15, cc1690, gs115, aplat).
//
// SYNTHETIC CONTENT. The binomials and taxonomic lineages below are real taxa,
// which is deliberate: taxonomy is not attribution. Everything authored — the
// curator descriptions and every CuratorNote — is written for the working
// simulation by the fictional demo curator "S. Creighton" and describes bench
// experience that did not happen (BUILD-SPEC §20).
import type { Strain } from './types';

export const STRAINS: Strain[] = [
  {
    id: 'cw15',
    binomial: 'Chlamydomonas reinhardtii',
    designation: 'cw15',
    taxonomy: [
      'Eukaryota',
      'Viridiplantae',
      'Chlorophyta',
      'Chlorophyceae',
      'Chlamydomonadales',
      'Chlamydomonadaceae',
      'Chlamydomonas',
    ],
    description:
      'A cell-wall-deficient mutant lacking most of the hydroxyproline-rich glycoprotein wall of the wild type. The missing wall is why it dominates bioprocess work: cells lyse at a fraction of the specific energy a walled strain demands, so protein and pigment release cheaply and reproducibly. The same absence makes cultures shear-sensitive, and impeller tip speed, pump selection and sparge rate become process variables rather than details. It remains the reference eukaryotic phototroph for transformation, photosynthesis and product-formation work.',
    badges: ['cell-wall deficient', 'model organism', 'BSL-1'],
    bsl: 1,
    notes: [
      {
        at: '2026-06-04',
        who: 'S. Creighton',
        text: 'cw15 lyses under handling a walled strain shrugs off — we lost most of a 2 L culture to a peristaltic transfer at 300 rpm, visible as green supernatant within minutes of the pump starting. Read the disruption notes in PR-HARV-01 as a shear budget for the whole line rather than for the disruption step alone; SP-006 is the record of how little energy this strain actually needs.',
      },
      {
        at: '2026-05-12',
        who: 'S. Creighton',
        text: 'The OD-to-dry-weight factor everyone reaches for is an exponential-phase, 750 nm number, and stationary cultures read low against it. Re-calibrate at harvest density before quoting a volumetric productivity, or the two ends of the growth curve end up biased in opposite directions.',
      },
      {
        at: '2026-03-27',
        who: 'S. Creighton',
        text: 'Inoculate from mid-exponential precultures only. A stationary-phase inoculum adds four to six hours of lag and carries enough storage carbon to distort the early yield calculation, which is the most common reason a repeat of the flask kinetics comes back slow.',
      },
    ],
  },
  {
    id: 'cc1690',
    binomial: 'Chlamydomonas reinhardtii',
    designation: 'CC-1690 (wild type)',
    taxonomy: [
      'Eukaryota',
      'Viridiplantae',
      'Chlorophyta',
      'Chlorophyceae',
      'Chlamydomonadales',
      'Chlamydomonadaceae',
      'Chlamydomonas',
    ],
    description:
      'The walled wild-type reference against which cw15 results are checked. An intact glycoprotein wall makes it slower, denser per unit optical density and far more tolerant of pumping and sparging, at the cost of a much higher specific energy demand for disruption. Use it whenever a claim has to hold for walled cells — settling behaviour, shear tolerance, protein partitioning — and never assume a rate or a conversion factor measured on cw15 transfers across.',
    badges: ['walled wild type', 'reference strain', 'BSL-1'],
    bsl: 1,
    notes: [
      {
        at: '2026-04-21',
        who: 'S. Creighton',
        text: 'cc1690 settles cleanly enough to concentrate by gravity overnight, which cw15 will not do, and it reads consistently higher in Lowry protein at matched growth phase. Budget substantially more disruption energy for it: the wall is the point of the comparison and it is not free to break.',
      },
    ],
  },
  {
    id: 'gs115',
    binomial: 'Komagataella phaffii',
    designation: 'GS115',
    taxonomy: [
      'Eukaryota',
      'Fungi',
      'Ascomycota',
      'Saccharomycetes',
      'Saccharomycetales',
      'Pichiaceae',
      'Komagataella',
    ],
    description:
      'The methylotrophic yeast host used here for recombinant protein production, formerly classified as Pichia pastoris. Growth proceeds on glycerol to high cell density, after which the AOX1 promoter is induced by a controlled methanol feed and the product accumulates over a defined induction window. It secretes into a low-protein background, tolerates stirred-tank shear without difficulty, and reaches biomass densities an order of magnitude above the phototrophs in this corpus.',
    badges: ['methylotrophic yeast', 'recombinant protein host', 'BSL-1'],
    bsl: 1,
    notes: [
      {
        at: '2026-05-30',
        who: 'S. Creighton',
        text: 'The hazard here is the carbon source, not the organism. Run the AOX1 induction feed on a gravimetric loop with a dissolved-oxygen interlock — a stalled or overshooting feed shows up as a DO excursion long before the offline assay sees it, and residual methanol accumulating in the broth costs viability well before it costs titer.',
      },
      {
        at: '2026-02-16',
        who: 'S. Creighton',
        text: 'Take the glycerol batch to genuine exhaustion before switching to methanol; carried-over glycerol represses AOX1 and produces the flat first hours of induction that get misread as a bad clone. The sharp DO spike at glycerol depletion is the cleanest transition trigger available.',
      },
    ],
  },
  {
    id: 'aplat',
    binomial: 'Arthrospira platensis',
    designation: 'PCC-style filamentous cyanobacterium',
    taxonomy: [
      'Bacteria',
      'Cyanobacteriota',
      'Cyanophyceae',
      'Oscillatoriales',
      'Microcoleaceae',
      'Arthrospira',
    ],
    description:
      'A filamentous cyanobacterium cultivated in strongly alkaline, high-bicarbonate medium, where the pH itself suppresses most competing organisms and makes open-pond operation practical. The helical trichomes are large enough to harvest by screen filtration rather than centrifugation, and the biomass is the established food-grade protein reference for photosynthetic production. Included here mainly as a contrast case for medium chemistry, carbon supply and harvest cost.',
    badges: ['cyanobacterium', 'alkaliphilic', 'BSL-1'],
    bsl: 1,
    notes: [
      {
        at: '2026-06-22',
        who: 'S. Creighton',
        text: 'Corpus coverage for this organism is thin, and the platform should not be read as if it were not: there are few records, none in the gold set, and effectively nothing on harvest recovery or downstream processing. Treat anything returned for Arthrospira platensis as the starting point for a literature search rather than as a defensible process number.',
      },
    ],
  },
];

export const STRAINS_BY_ID: Record<string, Strain> = Object.fromEntries(
  STRAINS.map((s) => [s.id, s]),
);
