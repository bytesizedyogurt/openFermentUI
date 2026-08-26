// Reference content for subsystems that have no data yet (OF-BLD-010).
//
// THE DISTINCTION THIS FILE RESTS ON. Reference content is domain knowledge:
// the seven EC classes, the chromatography modes that exist, the published
// genome-scale models, the rules for computing a priority date. None of it is
// a measurement, a prediction, or a claim about any particular molecule. It is
// the kind of thing a textbook contains, and putting it on screen is not
// fabrication — it is the difference between an empty room and a reference
// shelf.
//
// What is NOT in here, and must never be added: titres, yields, costs, patent
// statuses, or any number presented as a result. A stub subsystem may show what
// the field looks like. It may not show what your answer would be.
//
// Rendered by ReferenceView beneath the EmptyState. The subsystem still reads
// as unbuilt; it just is not blank while it waits.
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
  'geneos.search': {
    blurb: 'Sequence databases and the tools that search them.',
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
        cols: ['Method', 'Needs', 'Note'],
        rows: [
          ['Boltz', 'Sequence', 'Fully open, no weights restriction'],
          ['ESMFold', 'Sequence only, no MSA', 'Fastest for single sequences'],
          ['ColabFold', 'Sequence, fast MSA via MMseqs2', 'Practical AlphaFold pipeline'],
          ['AlphaFold2', 'Sequence, deep MSA', 'Large database dependency'],
          ['AlphaFold3', 'Sequence, complexes and ligands', 'Code CC BY-NC-SA; weights gated, non-commercial'],
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
  'fermos.models': {
    blurb: 'Published genome-scale models for the hosts in this catalogue.',
    tables: [
      {
        title: 'Models',
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
        title: 'Analysis methods',
        cols: ['Method', 'Answers', 'Cost'],
        rows: [
          ['FBA', 'Maximum theoretical flux to a product', 'Milliseconds'],
          ['FVA', 'The range each reaction can carry', 'Seconds to minutes'],
          ['pFBA', 'Same optimum, minimal total flux', 'Milliseconds'],
          ['Single deletion scan', 'Which genes are essential', 'Seconds'],
          ['Double deletion scan', 'Which pairs decouple growth from production', 'Millions of solves'],
          ['MOMA / ROOM', 'Flux after a knockout, not re-optimised', 'Moderate'],
        ],
      },
      {
        title: 'Solvers',
        cols: ['Solver', 'Licence', 'Note'],
        rows: [
          ['GLPK', 'GPL', 'The common default; slow on strain-design MILPs'],
          ['HiGHS', 'MIT', 'The intended replacement - permissive and far faster'],
          ['CBC', 'EPL', 'COIN-OR alternative'],
          ['Gurobi / CPLEX', 'Commercial', 'Fastest, not compatible with an open commons'],
        ],
      },
    ],
  },
  'fermos.design': {
    blurb: 'Strain design search methods.',
    tables: [
      {
        title: 'Methods',
        cols: ['Method', 'Searches for', 'Shape'],
        rows: [
          ['OptKnock', 'Knockouts coupling growth to production', 'Bilevel MILP'],
          ['RobustKnock', 'Knockouts robust to the cell re-optimising', 'Bilevel MILP'],
          ['OptGene', 'Knockout sets, heuristically', 'Evolutionary search'],
          ['OptForce', 'Which fluxes must change, and by how much', 'MILP'],
          ['FSEOF', 'Overexpression targets', 'Flux scanning under enforced objective'],
          ['GDLS', 'Knockouts by local search', 'Iterative'],
        ],
      },
      {
        title: 'Why this is the expensive stage',
        cols: ['Search', 'Approximate scale'],
        rows: [
          ['Single deletion', 'One solve per gene'],
          ['Double deletion', 'One solve per gene pair - millions on a mid-size model'],
          ['Triple and deeper', 'Combinatorial; often does not converge'],
          ['Bilevel MILP', 'Hard even at low depth; solver choice dominates runtime'],
        ],
      },
    ],
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
    ],
    note: 'A train of many high-yielding steps still ends low. The strategic move for a thermostable product is a heat step that removes most host protein in one operation.',
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
          ['Pre-GATT (filed before 8 June 1995)', 'The greater of 17 years from issue or 20 years from filing'],
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
};

export function referenceFor(subsystemId: string): ReferenceContent | null {
  return REFERENCE[subsystemId] ?? null;
}
