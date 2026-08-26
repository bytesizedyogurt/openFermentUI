// Reference content for subsystems that have no data yet (OF-BLD-010, revised OF-BLD-011).
//
// THE DISTINCTION THIS FILE RESTS ON. Reference content is domain knowledge: the
// seven EC classes, the chromatography modes that exist, the published
// genome-scale models, what sets kLa in a stirred tank. None of it is a
// measurement, a prediction, or a claim about any particular molecule. A
// textbook contains these. Showing them is not fabrication.
//
// What is NOT in here, and must never be added: titres, yields, costs, patent
// statuses, or any number presented as a result. A stub subsystem may show what
// the FIELD looks like. It may never show what YOUR ANSWER would be.
//
// COMPONENT BOUNDARIES (revised). The three OS components are the three stages
// of making something, in order:
//
//   geneOS  - the organism as an engineered system. Host choice, genetic parts,
//             pathway assembly, the genome-scale model, strain design.
//             Stoichiometry. Answers: what CAN this cell do?
//
//   fermOS  - the reactor. Kinetics, oxygen and heat transport, operating mode
//             and feeding, scale-up, instrumentation and control.
//             Dynamics. Answers: what DOES a real vessel achieve over time?
//
//   pureOS  - downstream. Harvest, disruption, capture, polishing, recovery,
//             formulation and storage. Answers: how does product become vial?
//
// The seam between geneOS and fermOS is stoichiometry versus dynamics: a GEM
// gives a yield ceiling with no time axis; kinetics gives the curve in a
// specific vessel. The seam between fermOS and pureOS is the harvest step, and
// it carries one decision made far upstream - secreted or intracellular - which
// dictates the entire downstream train.
export interface ReferenceTable {
  title: string;
  cols: string[];
  rows: string[][];
}

export interface ReferenceContent {
  blurb: string;
  tables: ReferenceTable[];
  note?: string;
}

export const REFERENCE: Record<string, ReferenceContent> = {
  'intake.sources': {
    blurb: 'Identifiers openFerment can resolve, and the routes it would fetch from.',
    tables: [
      {
        title: 'Identifier types',
        cols: ['Type', 'Example shape', 'Resolves via'],
        rows: [
          ['DOI', '10.1038/s41586-000-0000-0', 'Crossref'],
          ['PMID', '38123456', 'NCBI E-utilities'],
          ['PMCID', 'PMC10123456', 'Europe PMC'],
          ['arXiv', '2401.01234', 'arXiv API'],
          ['bioRxiv DOI', '10.1101/2024.01.01.000000', 'bioRxiv API'],
          ['Patent publication', 'US10377787B2', 'Google Patents Public Data'],
        ],
      },
      {
        title: 'Open-access retrieval routes',
        cols: ['Route', 'Covers', 'Returns'],
        rows: [
          ['Unpaywall', 'OA status for any DOI', 'Best OA PDF location'],
          ['PMC OA Subset', 'Life-sciences OA articles', 'Full-text JATS XML'],
          ['Europe PMC', 'Broader European index', 'XML or PDF'],
          ['arXiv / bioRxiv', 'Preprints', 'PDF, sometimes LaTeX source'],
          ['Crossref TDM', 'Publisher text-mining links', 'Licensed full text'],
        ],
      },
      {
        title: 'Parse status ladder',
        cols: ['State', 'Means'],
        rows: [
          ['unresolved', 'Identifier not yet matched to a record'],
          ['resolved', 'Metadata retrieved, no document yet'],
          ['fetched', 'Document on disk, hashed'],
          ['parsed', 'Sections extracted with character offsets'],
          ['anchored', 'Records point at spans in this exact version'],
        ],
      },
    ],
    note: 'Records today anchor by quote-substring match, which is ambiguous when a phrase appears twice. The target is (documentHash, sectionId, startOffset, endOffset).',
  },
  'intake.parser': {
    blurb: 'The section structure a scientific document is broken into.',
    tables: [
      {
        title: 'Section types',
        cols: ['Section', 'Typically holds'],
        rows: [
          ['Abstract', 'Headline claims, rarely the conditions behind them'],
          ['Introduction', 'Prior work and framing'],
          ['Methods', 'Strain, media, conditions, instrument settings'],
          ['Results', 'Measured values, usually in tables and figures'],
          ['Discussion', 'Interpretation, and comparison to other work'],
          ['Supplementary', 'Where the actual numbers frequently live'],
          ['References', 'Provenance for secondary claims'],
        ],
      },
      {
        title: 'The anchor tuple',
        cols: ['Field', 'Why it is needed'],
        rows: [
          ['documentHash', 'Papers get revised; this pins the version read'],
          ['sectionId', 'Methods and results say different things about one number'],
          ['startOffset', 'Character position, not a search string'],
          ['endOffset', 'Together with start, an unambiguous span'],
        ],
      },
    ],
  },
  'intake.instrument': {
    blurb: 'Instrument output formats a deposition would ingest.',
    tables: [
      {
        title: 'Formats',
        cols: ['Format', 'Instrument class', 'Notes'],
        rows: [
          ['mzML', 'Mass spectrometry', 'Open HUPO-PSI standard'],
          ['netCDF / .cdf', 'Chromatography', 'ANDI/AIA legacy standard, widely exported'],
          ['ASM (Allotrope)', 'Many', 'JSON-based; the direction of travel for lab data'],
          ['AnIML', 'Analytical instruments', 'XML analytical markup'],
          ['FCS', 'Flow cytometry', 'Binary, well specified'],
          ['CSV export', 'Plate readers, balances, probes', 'Ubiquitous and unstandardised'],
        ],
      },
      {
        title: 'Common measurements',
        cols: ['Measure', 'Instrument', 'Typical unit'],
        rows: [
          ['Optical density', 'Spectrophotometer / plate reader', 'OD600, dimensionless'],
          ['Total protein', 'BCA or Bradford assay', 'mg/mL'],
          ['Target titre', 'HPLC or ELISA', 'g/L'],
          ['Purity', 'SDS-PAGE densitometry or HPLC', '% of total'],
          ['Specific activity', 'Activity assay', 'U/mg'],
          ['Endotoxin', 'LAL assay', 'EU/mg'],
          ['Residual DNA', 'qPCR', 'pg/mg'],
        ],
      },
    ],
  },
  'biorepo.artifacts': {
    blurb: 'The computed results a cache would hold. Nothing is cached yet.',
    tables: [
      {
        title: 'Artifact kinds',
        cols: ['Kind', 'Produced by', 'Reuse potential'],
        rows: [
          ['Retrieval result', 'Postdoc', 'High - same question, same corpus'],
          ['Homology sweep', 'geneOS', 'High - sequence and database rarely change'],
          ['Structure prediction', 'geneOS', 'Very high - expensive, deterministic per sequence'],
          ['FBA solution', 'fermOS', 'High - same model, same constraints'],
          ['Strain design search', 'fermOS', 'Very high - the most expensive thing here'],
          ['TEA run', 'Proforma', 'Medium - assumptions shift often'],
          ['Clearance sweep', 'Dominion', 'Low - legal status changes underneath you'],
        ],
      },
      {
        title: 'Cache key inputs',
        cols: ['Component', 'Why it belongs in the key'],
        rows: [
          ['Input hash', 'Same inputs must return the same artifact'],
          ['Tool version', 'A solver update can change which optimum it finds'],
          ['Model or database version', 'The corpus underneath moved'],
          ['Parameter set', 'Different constraints, different answer'],
        ],
      },
    ],
    note: 'Artifact caching decides who can afford to use the platform. An expensive analysis paid for once is the difference between a tool a student can run and one they cannot.',
  },
  'biorepo.audit': {
    blurb: 'The chain a provenance tick summarises.',
    tables: [
      {
        title: 'Chain steps',
        cols: ['Step', 'Records'],
        rows: [
          ['Source', 'Document, version hash, exact span'],
          ['Extraction', 'Which extractor, which version, when'],
          ['Normalisation', 'Unit conversions applied, and their factors'],
          ['Review', 'Who checked it, against what, when'],
          ['Derivation', 'What was computed from it, by which tool version'],
          ['Dependants', 'What now rests on this value'],
        ],
      },
      {
        title: 'Provenance levels',
        cols: ['Level', 'Shown as', 'In aggregates'],
        rows: [
          ['measured', 'Measured - first-party', 'Yes'],
          ['gold', 'Curated - gold set', 'Yes'],
          ['verified', 'Verified against source', 'Yes'],
          ['curated', 'Curated - pending source check', 'Yes'],
          ['unverified', 'Extracted - unverified', 'Yes'],
          ['user', 'User-entered', 'Yes'],
          ['industry-estimate', 'Industry estimate - not evidence', 'No'],
          ['demo', 'Modeled - not measured', 'No'],
        ],
      },
    ],
  },
  'geneos.hosts': {
    blurb: 'Choosing the chassis. The host decides what the construct can look like and what the downstream train will have to be.',
    tables: [
      {
        title: 'Chassis trade-offs',
        cols: ['Host', 'Secretion', 'Decides downstream'],
        rows: [
          ['E. coli', 'Poor - intracellular', 'Lysis, refolding if inclusion bodies, endotoxin clearance mandatory'],
          ['B. subtilis', 'Excellent - true secretion', 'No lysis step; native proteases must be managed'],
          ['K. phaffii (Pichia)', 'Excellent', 'Centrifuge and filter; low native secretome eases capture'],
          ['S. cerevisiae', 'Moderate', 'GRAS status; hypermannosylation can complicate glycoproteins'],
          ['Y. lipolytica', 'Good', 'Tolerates lipophilic products; fewer off-the-shelf parts'],
          ['T. reesei', 'Exceptional', 'Highest titres; viscous broth and morphology control'],
          ['A. oryzae / A. niger', 'Excellent', 'Long food-enzyme precedent; protease background'],
          ['C. glutamicum', 'Good', 'No endotoxin - removes a whole clearance burden'],
          ['C. reinhardtii', 'Moderate', 'Photoautotrophic option; cell-wall-deficient strains ease lysis'],
        ],
      },
      {
        title: 'What the host determines',
        cols: ['Decision', 'Consequence'],
        rows: [
          ['Secreted or intracellular', 'Sets the entire downstream train'],
          ['Glycosylation machinery', 'Whether the product carries the right post-translational modifications'],
          ['Protease background', 'How much product survives to harvest'],
          ['Endotoxin', 'Whether a clearance step is mandatory'],
          ['Growth rate and media cost', 'Cycle time and operating cost'],
          ['Regulatory precedent', 'How hard approval will be for the intended use'],
        ],
      },
    ],
    note: 'Host choice is made in geneOS and paid for in pureOS. Secreted versus intracellular is the single decision with the largest downstream consequence, and it is a genetic design choice, not a purification one.',
  },
  'geneos.parts': {
    blurb: 'The genetic parts a construct is assembled from.',
    tables: [
      {
        title: 'Part classes',
        cols: ['Class', 'Chooses', 'Example decisions'],
        rows: [
          ['Promoter', 'When and how strongly the gene is read', 'Inducible or constitutive; strength; leakiness'],
          ['Ribosome binding site / Kozak', 'Translation initiation rate', 'Tuning expression without changing the promoter'],
          ['Signal peptide', 'Whether the product is secreted', 'Native, alpha-mating factor, or host-optimised'],
          ['Fusion tag', 'Solubility and purification handle', 'His, MBP, SUMO, GST, intein'],
          ['Linker and protease site', 'How the tag is removed', 'TEV, thrombin, or self-cleaving'],
          ['Terminator', 'Transcript stability', 'Often overlooked, occasionally decisive'],
          ['Selection marker', 'How transformants are kept', 'Antibiotic, auxotrophy, or marker-free'],
          ['Origin or integration site', 'Copy number and stability', 'Episomal for speed, genomic for stability'],
        ],
      },
      {
        title: 'Sequence design operations',
        cols: ['Operation', 'Why'],
        rows: [
          ['Codon optimisation', 'Match host codon usage and tRNA availability'],
          ['Restriction site removal', 'Enable the intended assembly standard'],
          ['Repeat and hairpin removal', 'Avoid synthesis failure and recombination'],
          ['GC balancing', 'Improve synthesis success and expression'],
          ['Domestication', 'Conform to an assembly standard such as MoClo or Golden Gate'],
        ],
      },
    ],
    note: 'A tagless product via self-cleaving intein removes a protease step and its cost from the downstream train. Construct decisions and purification decisions are the same decision viewed twice.',
  },
  'geneos.pathway': {
    blurb: 'Assembling and balancing a metabolic pathway in the chosen host.',
    tables: [
      {
        title: 'Precursor pathways',
        cols: ['Pathway', 'From', 'Feeds'],
        rows: [
          ['Mevalonate (MVA)', 'Acetyl-CoA', 'IPP and DMAPP for terpenes and sterols'],
          ['MEP / DXP', 'Pyruvate and G3P', 'IPP and DMAPP - the bacterial route'],
          ['Shikimate', 'PEP and erythrose-4-phosphate', 'Aromatics and aromatic amino acids'],
          ['Heme C4 (Shemin)', 'Glycine and succinyl-CoA', 'ALA, then heme'],
          ['Heme C5', 'Glutamate via glutamyl-tRNA', 'ALA, then heme'],
          ['GDP-fucose de novo', 'GDP-mannose', 'Fucosylated oligosaccharides'],
          ['GDP-fucose salvage', 'Free L-fucose', 'Same, via a bifunctional kinase'],
          ['CMP-sialic acid', 'GlcNAc to Neu5Ac', 'Sialylated oligosaccharides'],
          ['Malonyl-CoA extension', 'Acetyl-CoA', 'Polyketides and fatty acids'],
        ],
      },
      {
        title: 'Balancing problems',
        cols: ['Problem', 'Symptom', 'Typical handle'],
        rows: [
          ['Precursor limitation', 'Low titre despite high expression', 'Push flux into the precursor node'],
          ['Cofactor imbalance', 'NADPH or ATP starvation', 'Swap cofactor specificity, or rebalance the network'],
          ['Intermediate toxicity', 'Growth arrest mid-pathway', 'Tune relative enzyme levels; compartmentalise'],
          ['Product export', 'Product accumulates intracellularly', 'Add or upregulate a transporter'],
          ['Competing flux', 'Carbon lost to byproducts', 'Delete or attenuate the competing branch'],
          ['Regulatory repression', 'Pathway silent under process conditions', 'Remove the regulator or decouple the promoter'],
        ],
      },
    ],
  },
  'geneos.search': {
    blurb: 'Finding the protein you want to build, and its relatives. Sequence databases and the tools that search them.',
    tables: [
      {
        title: 'Databases',
        cols: ['Database', 'Holds', 'Scale'],
        rows: [
          ['UniProtKB / Swiss-Prot', 'Manually reviewed proteins', 'Hundreds of thousands'],
          ['UniRef90', 'Clustered reference proteins', 'Tens of millions'],
          ['NCBI NR', 'Non-redundant protein sequences', 'Hundreds of millions'],
          ['Pfam', 'Protein family profile HMMs', 'Around twenty thousand families'],
          ['InterPro', 'Integrated signatures across member databases', 'Aggregated'],
          ['PDB', 'Experimentally determined structures', 'Hundreds of thousands'],
          ['AlphaFold DB', 'Predicted structures', 'Hundreds of millions'],
          ['BRENDA', 'Enzyme function and kinetics', 'Curated per EC class'],
        ],
      },
      {
        title: 'Search tools',
        cols: ['Tool', 'Method', 'Best for'],
        rows: [
          ['pyhmmer', 'Profile HMM, in-process', 'Family assignment without subprocess overhead'],
          ['HMMER', 'Profile HMM', 'Remote homologs, sensitive'],
          ['MMseqs2', 'Iterative prefiltering', 'Very large searches, permissive licence'],
          ['DIAMOND', 'Double-index alignment', 'Fast protein-protein against huge databases'],
          ['foldseek', 'Structural alignment', 'Homologs sequence search cannot see'],
          ['ESM embeddings', 'Language-model similarity', 'Remote relationships with no alignment'],
        ],
      },
    ],
    note: 'foldseek matters most for genus enumeration - a claim fenced by percent identity cannot reach a protein that shares no sequence but shares a fold.',
  },
  'geneos.structure': {
    blurb: 'Structure prediction methods and what each requires.',
    tables: [
      {
        title: 'Methods',
        cols: ['Method', 'Needs', 'Licence note'],
        rows: [
          ['Boltz', 'Sequence', 'Fully open, no weights restriction'],
          ['ESMFold', 'Sequence only, no MSA', 'Fastest for single sequences'],
          ['ColabFold', 'Sequence, fast MSA via MMseqs2', 'Practical AlphaFold pipeline'],
          ['AlphaFold2', 'Sequence, deep MSA', 'Large database dependency'],
          ['AlphaFold3', 'Sequence, complexes and ligands', 'Code Apache; weights separately restricted'],
        ],
      },
      {
        title: 'Confidence measures',
        cols: ['Measure', 'Means'],
        rows: [
          ['pLDDT', 'Per-residue confidence; low regions are often genuinely disordered'],
          ['PAE', 'Predicted aligned error; how reliable relative domain placement is'],
          ['pTM', 'Predicted TM-score for the whole fold'],
          ['ipTM', 'Interface confidence, for complexes'],
        ],
      },
    ],
    note: 'Every predicted property must carry the method that produced it. \'Predicted Tm: 68\' is not evidence; \'Tm 68, method named, interval stated\' is a claim someone can disagree with.',
  },
  'geneos.function': {
    blurb: 'Enzyme classification and the annotation methods that assign it.',
    tables: [
      {
        title: 'EC top-level classes',
        cols: ['EC', 'Class', 'Reaction'],
        rows: [
          ['1', 'Oxidoreductases', 'Electron transfer'],
          ['2', 'Transferases', 'Group transfer'],
          ['3', 'Hydrolases', 'Hydrolytic cleavage'],
          ['4', 'Lyases', 'Non-hydrolytic bond cleavage or addition'],
          ['5', 'Isomerases', 'Intramolecular rearrangement'],
          ['6', 'Ligases', 'Bond formation coupled to ATP'],
          ['7', 'Translocases', 'Movement across a membrane'],
        ],
      },
      {
        title: 'Annotation methods',
        cols: ['Method', 'Basis', 'Caveat'],
        rows: [
          ['Pfam / InterPro', 'Profile match to a family', 'Family is not always function'],
          ['Best-hit transfer', 'Similarity to an annotated protein', 'Propagates errors silently'],
          ['CLEAN', 'Contrastive learning on sequence', 'No licence file - private research only'],
          ['Active-site matching', 'Catalytic residue conservation', 'Needs structure'],
        ],
      },
    ],
    note: 'Analogous enzymes - proteins with no sequence similarity catalysing the same reaction - exist across a large share of EC classes. That space is the design-around space in its purest form.',
  },
  'geneos.model': {
    blurb: 'The genome-scale model - a stoichiometric description of what the engineered cell can do. Steady state, no time axis.',
    tables: [
      {
        title: 'Published models',
        cols: ['Model', 'Organism', 'Note'],
        rows: [
          ['iML1515', 'E. coli K-12 MG1655', 'The most used and best curated GEM'],
          ['iJO1366', 'E. coli K-12', 'Earlier widely cited reconstruction'],
          ['Yeast8 / yeast-GEM', 'S. cerevisiae', 'Actively maintained consensus model'],
          ['iMM904', 'S. cerevisiae', 'Older, still widely referenced'],
          ['iRC1080', 'C. reinhardtii', 'Includes lipid metabolism detail'],
          ['iYali4', 'Y. lipolytica', 'Oleaginous yeast reconstruction'],
          ['Human-GEM', 'H. sapiens', 'Reference for the consensus approach'],
        ],
      },
      {
        title: 'Analyses',
        cols: ['Method', 'Answers', 'Cost'],
        rows: [
          ['FBA', 'Maximum theoretical flux to a product', 'Milliseconds'],
          ['pFBA', 'Same optimum, minimal total flux', 'Milliseconds'],
          ['FVA', 'The range each reaction can carry', 'Seconds to minutes'],
          ['Single deletion scan', 'Which genes are essential', 'Seconds'],
          ['Double deletion scan', 'Which pairs decouple growth from production', 'Millions of solves'],
          ['MOMA / ROOM', 'Flux immediately after a knockout, not re-optimised', 'Moderate'],
          ['Thermodynamic FBA', 'Rules out directionally impossible routes', 'Moderate'],
          ['Enzyme-constrained (GECKO)', 'Adds the finite protein budget', 'Moderate'],
        ],
      },
      {
        title: 'Solvers',
        cols: ['Solver', 'Licence', 'Note'],
        rows: [
          ['GLPK', 'GPL', 'The common default; slow on strain-design MILPs'],
          ['HiGHS', 'MIT', 'The intended replacement - permissive and far faster'],
          ['CBC', 'EPL', 'COIN-OR alternative'],
          ['Gurobi / CPLEX', 'Commercial', 'Fastest; incompatible with an open commons'],
        ],
      },
    ],
    note: 'A GEM gives a yield ceiling, not a titre. It has no time axis and no vessel. What a real reactor achieves is fermOS\'s question, and the gap between the two is exactly what Deposition measures.',
  },
  'geneos.design': {
    blurb: 'Searching for the genetic modifications that raise yield.',
    tables: [
      {
        title: 'Design methods',
        cols: ['Method', 'Searches for', 'Shape'],
        rows: [
          ['OptKnock', 'Knockouts coupling growth to production', 'Bilevel MILP'],
          ['RobustKnock', 'Knockouts robust to the cell re-optimising', 'Bilevel MILP'],
          ['OptGene', 'Knockout sets, heuristically', 'Evolutionary search'],
          ['OptForce', 'Which fluxes must change, and by how much', 'MILP'],
          ['FSEOF', 'Overexpression targets', 'Flux scanning under enforced objective'],
          ['GDLS', 'Knockouts by local search', 'Iterative'],
          ['cameo', 'Enumerate and rank designs', 'Wraps several of the above'],
        ],
      },
      {
        title: 'Why the search is expensive',
        cols: ['Search', 'Approximate scale'],
        rows: [
          ['Single deletion', 'One solve per gene'],
          ['Double deletion', 'One solve per gene pair - millions on a mid-size model'],
          ['Triple and deeper', 'Combinatorial; frequently fails to converge'],
          ['Bilevel MILP', 'Hard even at shallow depth; solver choice dominates runtime'],
        ],
      },
    ],
    note: 'This is the most compute-hungry thing in the platform, and the reason the solver choice is a real decision rather than a detail.',
  },
  'fermos.kinetics': {
    blurb: 'What actually happens in the vessel over time. Where a genome-scale model gives a ceiling, kinetics gives the curve.',
    tables: [
      {
        title: 'Rates and yields',
        cols: ['Symbol', 'Name', 'What it tells you'],
        rows: [
          ['mu', 'Specific growth rate', 'How fast biomass accumulates, per hour'],
          ['mu_max', 'Maximum specific growth rate', 'The ceiling under unlimited substrate'],
          ['qs', 'Specific substrate uptake rate', 'How fast each gram of cells consumes feed'],
          ['qp', 'Specific productivity', 'How fast each gram of cells makes product'],
          ['Yxs', 'Biomass yield on substrate', 'Grams of cells per gram of feed'],
          ['Yps', 'Product yield on substrate', 'Grams of product per gram of feed'],
          ['Ks', 'Half-saturation constant', 'Substrate level at half of mu_max'],
          ['ms', 'Maintenance coefficient', 'Feed consumed just to stay alive'],
        ],
      },
      {
        title: 'Kinetic models',
        cols: ['Model', 'Describes', 'Use when'],
        rows: [
          ['Monod', 'Growth limited by one substrate', 'The default starting point'],
          ['Contois', 'Growth inhibited by biomass density', 'High-cell-density culture'],
          ['Haldane', 'Substrate inhibition at high concentration', 'Feeding a toxic or inhibitory substrate'],
          ['Luedeking-Piret', 'Product formation growth- and non-growth-associated', 'Separating the two contributions'],
          ['Logistic', 'Biomass approaching a carrying capacity', 'Fitting a curve without mechanism'],
          ['Structured / dynamic FBA', 'Metabolism changing through the run', 'When a single set of rates will not fit'],
        ],
      },
      {
        title: 'Phases of a run',
        cols: ['Phase', 'What dominates'],
        rows: [
          ['Lag', 'Adaptation; no net growth'],
          ['Exponential', 'mu near mu_max; substrate in excess'],
          ['Transition', 'Substrate or oxygen becomes limiting'],
          ['Fed-batch production', 'Feed rate sets mu; product accumulates'],
          ['Stationary', 'Growth stops; maintenance and product formation continue'],
          ['Decline', 'Lysis, proteolysis, product degradation'],
        ],
      },
    ],
    note: 'Kinetic parameters are fitted to real runs, not derived from a genome. This is the component that most needs Deposition data, and the one that cannot be built from literature alone.',
  },
  'fermos.transport': {
    blurb: 'Getting oxygen in and heat out. Transport is what usually limits a real fermentation, not biology.',
    tables: [
      {
        title: 'Oxygen transfer',
        cols: ['Term', 'Means', 'Why it bites'],
        rows: [
          ['OTR', 'Oxygen transfer rate', 'What the vessel can deliver'],
          ['OUR', 'Oxygen uptake rate', 'What the cells demand'],
          ['kLa', 'Volumetric mass transfer coefficient', 'The vessel\'s capacity to deliver oxygen'],
          ['DO', 'Dissolved oxygen', 'The controlled variable, usually held above a setpoint'],
          ['C*', 'Saturation concentration', 'Falls with temperature and rising salt'],
          ['Oxygen limitation', 'OUR exceeds OTR', 'Growth and production stall; byproducts appear'],
        ],
      },
      {
        title: 'What sets kLa',
        cols: ['Variable', 'Effect'],
        rows: [
          ['Agitation rate', 'Raises kLa and shear together'],
          ['Aeration rate', 'More gas, more transfer, more foam'],
          ['Impeller type and count', 'Rushton for gas dispersion, axial for bulk mixing'],
          ['Back pressure', 'Raises saturation concentration'],
          ['Broth viscosity', 'Filamentous cultures collapse kLa as they thicken'],
          ['Antifoam', 'Suppresses foam and lowers kLa as a side effect'],
        ],
      },
      {
        title: 'Other transport limits',
        cols: ['Limit', 'Symptom'],
        rows: [
          ['Heat removal', 'Temperature drifts up at scale; jacket area per volume falls'],
          ['Mixing time', 'Gradients in pH, substrate and oxygen across a large vessel'],
          ['Shear', 'Cell damage in shear-sensitive cultures'],
          ['CO2 accumulation', 'Dissolved CO2 inhibits growth in tall vessels'],
          ['Foaming', 'Carries cells into the exhaust; fouls filters'],
        ],
      },
    ],
    note: 'Oxygen transfer is the usual reason a strain that performed at bench scale disappoints at production scale. The biology did not change; the vessel did.',
  },
  'fermos.mode': {
    blurb: 'How the vessel is operated, and the feeding strategy that follows.',
    tables: [
      {
        title: 'Operating modes',
        cols: ['Mode', 'How it runs', 'Suits'],
        rows: [
          ['Batch', 'Everything charged at the start', 'Simple products; screening'],
          ['Fed-batch', 'Feed added over the run', 'Most industrial protein production'],
          ['Continuous / chemostat', 'Feed in, broth out, steady state', 'Parameter estimation; some commodity products'],
          ['Perfusion', 'Cells retained, medium exchanged', 'Very high cell density; sensitive products'],
          ['Repeated batch', 'Partial harvest, refill', 'Reduces turnaround between runs'],
        ],
      },
      {
        title: 'Feeding strategies',
        cols: ['Strategy', 'Basis', 'Trade-off'],
        rows: [
          ['Constant rate', 'Fixed feed', 'Simple; mu falls through the run'],
          ['Exponential', 'Feed tracks a target mu', 'Holds growth rate; needs a good model'],
          ['DO-stat', 'Feed on a dissolved-oxygen trigger', 'Self-correcting; noisy'],
          ['pH-stat', 'Feed on a pH trigger', 'Works when substrate exhaustion shifts pH'],
          ['Substrate-limited', 'Hold substrate near zero', 'Suppresses overflow metabolism'],
        ],
      },
      {
        title: 'Why overflow metabolism matters',
        cols: ['Host', 'Byproduct', 'Cause'],
        rows: [
          ['E. coli', 'Acetate', 'Excess glucose uptake beyond respiratory capacity'],
          ['S. cerevisiae', 'Ethanol', 'Crabtree effect at high glucose'],
          ['K. phaffii', 'Methanol toxicity', 'Overfeeding the inducer'],
          ['Many', 'Lactate, formate', 'Oxygen limitation'],
        ],
      },
    ],
    note: 'Feeding strategy is the main lever an operator has once the strain is fixed. Most of the difference between a good run and a poor one lives here.',
  },
  'fermos.scale': {
    blurb: 'Moving from bench to production. What is held constant decides what breaks.',
    tables: [
      {
        title: 'Scale-up criteria',
        cols: ['Hold constant', 'Preserves', 'Sacrifices'],
        rows: [
          ['kLa', 'Oxygen supply', 'Mixing time and shear change'],
          ['Power per volume', 'Energy input', 'kLa and tip speed drift'],
          ['Impeller tip speed', 'Shear environment', 'kLa usually falls'],
          ['Mixing time', 'Homogeneity', 'Impractical at large scale'],
          ['Volumetric feed rate', 'Nominal feed profile', 'Gradients appear'],
        ],
      },
      {
        title: 'Scale tiers',
        cols: ['Tier', 'Volume', 'Role'],
        rows: [
          ['Microplate / shake flask', 'Millilitres', 'Strain screening; no DO or pH control'],
          ['Bench bioreactor', '1-10 L', 'Process definition; full instrumentation'],
          ['Pilot', '100-1000 L', 'Confirms the process survives scale'],
          ['Small production', '1000-10000 L', 'High-value proteins and enzymes'],
          ['Production', '10000-50000 L', 'Food proteins'],
          ['Large production', '50000-200000 L', 'Commodity; deliberately out of scope'],
        ],
      },
      {
        title: 'What breaks on the way up',
        cols: ['Problem', 'Why it appears'],
        rows: [
          ['Oxygen limitation', 'kLa falls as volume rises'],
          ['Mixing gradients', 'Blend time grows faster than volume'],
          ['Heat removal', 'Jacket surface area per unit volume falls'],
          ['CO2 accumulation', 'Taller column, longer gas residence'],
          ['Hydrostatic pressure', 'Cells cycle through pressure and DO gradients'],
          ['Feed distribution', 'A single feed point creates a local excess zone'],
        ],
      },
    ],
    note: 'Value density per litre of fermenter capacity is the metric that matters more than tonnage. A 2,000 L train making research enzymes can outperform a 200,000 L plant making commodity protein.',
  },
  'fermos.control': {
    blurb: 'Instrumentation and control loops during a run.',
    tables: [
      {
        title: 'Measured online',
        cols: ['Variable', 'Sensor', 'Controlled by'],
        rows: [
          ['Temperature', 'RTD or thermocouple', 'Jacket heating and cooling'],
          ['pH', 'Glass electrode', 'Acid and base addition'],
          ['Dissolved oxygen', 'Optical or polarographic', 'Agitation, aeration, oxygen enrichment'],
          ['Pressure', 'Transducer', 'Back-pressure valve'],
          ['Weight', 'Load cells', 'Feed and harvest accounting'],
          ['Off-gas O2 and CO2', 'Analyser', 'Nothing directly; used to infer OUR and RQ'],
          ['Foam', 'Conductivity probe', 'Antifoam addition'],
        ],
      },
      {
        title: 'Inferred, not measured',
        cols: ['Quantity', 'Derived from', 'Why it matters'],
        rows: [
          ['OUR and CER', 'Off-gas balance', 'The best real-time proxy for metabolic state'],
          ['Respiratory quotient', 'CER over OUR', 'Signals a metabolic shift'],
          ['Specific growth rate', 'Biomass over time', 'The variable a feed strategy targets'],
          ['Biomass', 'OD, dry weight, or capacitance', 'Rarely available continuously'],
        ],
      },
      {
        title: 'Offline sampling',
        cols: ['Measure', 'Method', 'Typical cadence'],
        rows: [
          ['Optical density', 'Spectrophotometer', 'Every few hours'],
          ['Dry cell weight', 'Filter and dry', 'Once or twice per run'],
          ['Substrate concentration', 'HPLC or enzymatic assay', 'Every few hours'],
          ['Product titre', 'HPLC or ELISA', 'Key timepoints'],
          ['Byproducts', 'HPLC', 'Alongside substrate'],
          ['Contamination check', 'Microscopy or plating', 'Daily'],
        ],
      },
    ],
    note: 'Off-gas analysis is the most informative measurement on a fermenter and the most often omitted at small scale. It gives metabolic state continuously and without touching the broth.',
  },
  'pureos.harvest': {
    blurb: 'The boundary. Separating cells from broth, and deciding which phase holds the product.',
    tables: [
      {
        title: 'The decision that sets everything',
        cols: ['Product location', 'First operation', 'Consequences'],
        rows: [
          ['Secreted into broth', 'Remove cells, keep supernatant', 'Shorter train; capture from a dilute stream'],
          ['Intracellular, soluble', 'Keep cells, then lyse', 'Concentrated start; host protein burden is high'],
          ['Intracellular, inclusion bodies', 'Keep cells, lyse, solubilise, refold', 'Longest train; refolding yield often dominates'],
          ['Periplasmic', 'Osmotic shock or selective release', 'Middle ground; gentler than full lysis'],
          ['Cell-associated / surface', 'Wash and elute', 'Uncommon; product-specific'],
        ],
      },
      {
        title: 'Solid-liquid separation',
        cols: ['Operation', 'Suits', 'Watch'],
        rows: [
          ['Disc-stack centrifugation', 'Bacteria and yeast at scale', 'Shear; fines carried over'],
          ['Tubular centrifugation', 'Small volumes, fine solids', 'Batch operation'],
          ['Microfiltration (TFF)', 'Shear-sensitive cultures', 'Fouling; long processing time'],
          ['Depth filtration', 'Polishing after centrifugation', 'Product adsorption to media'],
          ['Rotary vacuum filtration', 'Filamentous fungal broth', 'Bulk operation, lower resolution'],
          ['Flocculation then settling', 'Very large volumes', 'Adds a chemical to be removed later'],
        ],
      },
      {
        title: 'Cell disruption',
        cols: ['Method', 'Scale', 'Note'],
        rows: [
          ['High-pressure homogenisation', 'Production', 'The industrial default; multiple passes, heat generated'],
          ['Bead milling', 'Bench to pilot', 'Effective on tough-walled yeast and algae'],
          ['Enzymatic lysis', 'Any', 'Gentle; adds an enzyme to be removed'],
          ['Osmotic shock', 'Bench', 'Periplasmic release without full disruption'],
          ['Freeze-thaw', 'Bench only', 'Does not scale'],
        ],
      },
    ],
    note: 'Secreted versus intracellular is decided in geneOS and paid for here. It is the single choice with the largest effect on downstream cost, and it is made before anyone touches a purification column.',
  },
  'pureos.capture': {
    blurb: 'The first purification step. Highest volume, crudest feed, largest cost lever.',
    tables: [
      {
        title: 'Chromatography modes',
        cols: ['Mode', 'Separates by', 'Typical use'],
        rows: [
          ['Ion exchange (Q, SP, DEAE, CM)', 'Net surface charge', 'The workhorse capture step'],
          ['Hydrophobic interaction', 'Surface hydrophobicity', 'Polishing after a high-salt step'],
          ['Affinity - IMAC', 'His-tag binding immobilised metal', 'Tagged research proteins'],
          ['Affinity - custom ligand', 'Specific molecular recognition', 'Highest resolution, highest cost'],
          ['Mixed-mode', 'Charge and hydrophobicity together', 'Difficult separations; salt-tolerant loading'],
          ['Hydroxyapatite', 'Calcium and phosphate interactions', 'Orthogonal to charge-based steps'],
          ['Size exclusion', 'Hydrodynamic radius', 'Polishing and buffer exchange; low throughput'],
        ],
      },
      {
        title: 'Non-chromatographic capture',
        cols: ['Method', 'When it wins'],
        rows: [
          ['Thermal clarification', 'Product is thermostable and the host proteome is not'],
          ['Ammonium sulfate precipitation', 'Cheap bulk concentration; crude'],
          ['PEG precipitation', 'Gentle; adds a component to remove'],
          ['Aqueous two-phase extraction', 'Scalable, avoids resin cost'],
          ['Expanded-bed adsorption', 'Capture directly from unclarified feed'],
          ['Crystallisation', 'Product crystallises readily; very high purity in one step'],
        ],
      },
      {
        title: 'Capture economics',
        cols: ['Driver', 'Effect'],
        rows: [
          ['Dynamic binding capacity', 'How much resin is needed per batch'],
          ['Resin cost and lifetime', 'Amortised per cycle; often the largest consumable'],
          ['Cycle time', 'Determines batches per year'],
          ['Buffer volume', 'Water, storage, disposal - frequently underestimated'],
          ['Feed dilution', 'A dilute secreted stream needs concentration before capture'],
        ],
      },
    ],
    note: 'For a thermostable product, a heat step can replace most of the capture chromatography. That single substitution is much of why molecular-biology enzymes are attractive to manufacture.',
  },
  'pureos.polish': {
    blurb: 'Reaching final specification. Removing what capture left behind.',
    tables: [
      {
        title: 'What has to be removed',
        cols: ['Contaminant', 'Why', 'Typical step'],
        rows: [
          ['Host cell protein', 'Immunogenicity and assay interference', 'Orthogonal chromatography'],
          ['Residual DNA', 'Regulatory limit', 'Anion exchange in flow-through; nuclease treatment'],
          ['Endotoxin', 'Mandatory for anything from a Gram-negative host', 'Dedicated clearance step'],
          ['Aggregates', 'Loss of activity; immunogenicity', 'Size exclusion or HIC'],
          ['Product variants', 'Clipped, oxidised or misfolded forms', 'High-resolution polishing'],
          ['Leached ligand', 'From affinity resin', 'Orthogonal step downstream of affinity'],
          ['Process additives', 'Antifoam, flocculant, protease inhibitors', 'Diafiltration'],
          ['Nucleases', 'For molecular-biology enzyme grade', 'Assay-driven; defines the grade'],
        ],
      },
      {
        title: 'Concentration and exchange',
        cols: ['Operation', 'Does', 'Note'],
        rows: [
          ['Ultrafiltration', 'Concentrates by molecular weight cutoff', 'Choose cutoff well below product size'],
          ['Diafiltration', 'Exchanges buffer at constant volume', 'Buffer consumption scales with diavolumes'],
          ['Nanofiltration', 'Retains small molecules such as oligosaccharides', 'Used in sugar and HMO trains'],
          ['Electrodialysis', 'Removes salts by charge', 'Desalting without dilution'],
        ],
      },
      {
        title: 'Orthogonality',
        cols: ['Principle', 'Meaning'],
        rows: [
          ['Vary the separation basis', 'Charge, then hydrophobicity, then size'],
          ['Avoid repeating a mechanism', 'Two ion exchanges remove nearly the same impurities'],
          ['Sequence by volume', 'Highest-volume step first, most expensive resin last'],
          ['Count the steps', 'Every added step multiplies yield loss'],
        ],
      },
    ],
    note: 'For a molecular-biology enzyme, nuclease and endotoxin clearance is what defines the grade rather than a purity percentage. That is the specification the customer actually buys.',
  },
  'pureos.recovery': {
    blurb: 'What drives yield loss at each stage of a downstream train.',
    tables: [
      {
        title: 'Loss mechanisms',
        cols: ['Stage', 'Where product is lost'],
        rows: [
          ['Harvest', 'Product left in the discarded phase'],
          ['Cell disruption', 'Incomplete lysis; degradation by released proteases'],
          ['Clarification', 'Adsorption to filter media and cell debris'],
          ['Capture', 'Breakthrough past a saturated column; incomplete elution'],
          ['Polishing', 'Overlapping peaks discarded at the cut points'],
          ['Concentration', 'Membrane fouling and retentate holdup'],
          ['Drying', 'Thermal or shear inactivation'],
          ['Formulation', 'Aggregation, adsorption to the container'],
        ],
      },
      {
        title: 'Cumulative recovery',
        cols: ['Concept', 'Note'],
        rows: [
          ['Step yield', 'Fraction surviving one operation'],
          ['Cumulative yield', 'Product of every step yield - falls fast'],
          ['Purity vs yield', 'Tighter cuts raise purity and lose product'],
          ['Step count', 'Every added step multiplies loss; fewer steps usually wins'],
        ],
      },
      {
        title: 'Where a train usually loses most',
        cols: ['Stage', 'Typical dominant loss'],
        rows: [
          ['Refolding', 'Frequently the largest single loss in an inclusion-body route'],
          ['Capture', 'Breakthrough on an overloaded column; incomplete elution'],
          ['Polishing cuts', 'Product deliberately discarded to hit purity'],
          ['Diafiltration', 'Membrane adsorption and system holdup'],
          ['Drying', 'Thermal or shear inactivation'],
        ],
      },
    ],
    note: 'A train of many high-yielding steps still ends low. The strategic move for a thermostable product is a heat step that removes most host protein in one operation.',
  },
  'proforma.uncertainty': {
    blurb: 'Why a point estimate is close to worthless, and what a range needs.',
    tables: [
      {
        title: 'Uncertain inputs',
        cols: ['Input', 'Why it moves'],
        rows: [
          ['Titre', 'Varies between runs and scales non-linearly'],
          ['Recovery yield', 'Depends on decisions not yet made'],
          ['Feedstock price', 'Commodity markets'],
          ['Utilities', 'Regional and seasonal'],
          ['Capital cost', 'Vendor quotes vary widely at small scale'],
          ['Labour', 'Regional, and scale-dependent'],
          ['Uptime', 'Rarely as assumed'],
        ],
      },
      {
        title: 'What a defensible TEA reports',
        cols: ['Element', 'Note'],
        rows: [
          ['Distribution, not a number', 'A range with the driver named is usable'],
          ['Sensitivity ranking', 'Which input dominates the spread'],
          ['Mass balance closure', 'The error, stated rather than hidden'],
          ['Assumption version', 'Which set produced this result'],
          ['Benchmark comparison', 'Calibration against a published case'],
        ],
      },
    ],
  },
  'dominion.claims': {
    blurb: 'The distinction the Claim Workbench exists to make.',
    tables: [
      {
        title: 'Limitation kinds',
        cols: ['Kind', 'Example shape', 'Enumerable'],
        rows: [
          ['Structure', 'a polypeptide at least 70% identical to SEQ ID NO:1', 'Yes'],
          ['Function', 'having alpha-1,2-fucosyltransferase activity', 'No'],
          ['Application', 'a food product comprising', 'No'],
          ['Process step', 'culturing under conditions such that', 'Sometimes'],
          ['Field of use', 'for use in infant nutrition', 'No'],
        ],
      },
      {
        title: 'Verdicts',
        cols: ['Verdict', 'Means', 'Action'],
        rows: [
          ['ENUMERABLE', 'Every independent limitation recites structure', 'Enumeration is worth paying for'],
          ['IMMUNE', 'At least one recites function or application', 'Do not spend compute here'],
          ['PARTIAL', 'Mixed across the family', 'Target the enumerable claims only'],
          ['UNCERTAIN', 'Cannot be decided confidently', 'Route to human review'],
        ],
      },
    ],
    note: 'Enumeration defeats claims reciting structure. It does nothing against claims reciting function. A cross-kingdom protein substitution has been held to infringe a claim to a functional class - claim architecture decides this, not molecular diversity.',
  },
  'dominion.priority': {
    blurb: 'How an effective filing date is computed, and why it differs from the printed one.',
    tables: [
      {
        title: 'Chain types',
        cols: ['Type', 'Priority rule'],
        rows: [
          ['Provisional', 'Sets the earliest date, for matter it actually supports'],
          ['Non-provisional', 'Inherits, limited to supported matter'],
          ['Continuation', 'Same disclosure; inherits the parent date'],
          ['Continuation-in-part', 'New matter takes the later date - claim by claim'],
          ['Divisional', 'Inherits, restricted to the divided subject matter'],
          ['PCT national phase', 'International filing date, per office requirements'],
        ],
      },
      {
        title: 'Term calculation',
        cols: ['Filing era', 'Term'],
        rows: [
          ['Pre-GATT (filed before 8 June 1995)', '17 years from issue'],
          ['Post-GATT', '20 years from earliest non-provisional filing'],
          ['Adjustments', 'Office delay can extend; terminal disclaimers can shorten'],
        ],
      },
    ],
    note: 'Term expiry is arithmetic. Litigation outcomes are contingent and often unresolved. For a clearance question the expiry date usually settles it and the litigation history is colour.',
  },
  'dominion.enablement': {
    blurb: 'What raises a disclosure from a list of sequences to something that anticipates.',
    tables: [
      {
        title: 'Reduction-to-practice ladder',
        cols: ['Level', 'Contains', 'Strength'],
        rows: [
          ['Sequence only', 'A candidate and nothing else', 'Weak'],
          ['Construct', 'Codon-optimised, vector, promoter, tags, terminator', 'Better'],
          ['Host and conditions', 'Temperature, pH, induction, media, duration', 'Better still'],
          ['Protocol', 'Machine-readable, step by step', 'Strong'],
          ['Predicted properties', 'With method and confidence interval stated', 'Strong'],
          ['Expressed', 'Actually made', 'Very strong'],
          ['Assayed', 'Made and measured', 'Strongest'],
        ],
      },
    ],
    note: 'A disclosure that does not enable anticipates nothing. The same enablement logic that killed broad functional genus claims applies to your own publications.',
  },
  'dominion.notary': {
    blurb: 'Where a defensive publication can be deposited.',
    tables: [
      {
        title: 'Venues',
        cols: ['Venue', 'Cost', 'Trade-off'],
        rows: [
          ['TDCommons', 'Free', 'Indexed by Google Patents; small footprint'],
          ['IP.com', 'Paid', 'Largest database; evidentiary opinion supports authentication'],
          ['Research Disclosure', 'Paid', 'Long-established, examiner-recognised'],
          ['Abandoned US application', 'Filing fees', 'The only route that reliably reaches examiner search'],
          ['Preprint or journal', 'Varies', 'Citable and dated, but not searched as prior art'],
        ],
      },
      {
        title: 'What a deposit must fix',
        cols: ['Element', 'Purpose'],
        rows: [
          ['Content hash', 'Proves the artifact has not changed'],
          ['Independent timestamp', 'Proves it existed by a date without trusting your clock'],
          ['Signature', 'Proves who deposited it'],
          ['Manifest', 'Records what it contains and what produced it'],
          ['Persistent identifier', 'A citable, resolvable reference'],
        ],
      },
    ],
  },
  'guild.powers': {
    blurb: 'Actions that will require standing. All are currently unguarded.',
    tables: [
      {
        title: 'Guarded actions',
        cols: ['Power', 'Why it needs standing'],
        rows: [
          ['Promote to verified', 'Asserts a human checked the source'],
          ['Promote to gold', 'Gold is the evaluation benchmark'],
          ['Reject a record', 'Removes evidence from consideration'],
          ['Override a claim verdict', 'Wrong either way is expensive'],
          ['Approve a budget', 'Real money'],
          ['Publish a disclosure', 'Permanent and public'],
          ['Sign a deposit', 'Attaches a name to a timestamped claim'],
          ['Release a protocol version', 'Someone may run it in a lab'],
          ['Resolve a blocked input', 'Declaring an assumption is a judgement'],
        ],
      },
      {
        title: 'Standing models',
        cols: ['If the user is', 'Model'],
        rows: [
          ['One researcher', 'No checks. Attribution still matters for future-you'],
          ['A lab', 'Fixed roles - curator, reviewer, principal investigator'],
          ['A public commons', 'Standing earned through contribution history'],
        ],
      },
    ],
    note: 'Until this exists, \'verified\' is an unsigned assertion. Provenance strength should eventually depend on who did the verifying, not just that someone did.',
  },
};

export function referenceFor(subsystemId: string): ReferenceContent | null {
  return REFERENCE[subsystemId] ?? null;
}
