// openFerment corpus — Thread C (localization: intracellular vs secretion) and
// Thread D (host post-translational modification capability).
//
// REAL LITERATURE. Every title, author string, year, venue, DOI, PMCID and PMID
// in this file is transcribed from docs/OF-COR-001.md §4 and §5. Nothing is
// invented.
//
// The full texts have NOT been ingested. Each paper therefore carries exactly
// one section — the curator's note from OF-COR-001, in the curator's words,
// about the paper. `textSource: 'curation-note'` and `ingest: 'catalogued'` say
// so, and the reader labels it. No sentence in `sections[].text` is the paper's
// own prose, and every `quote` is a span of the curator's note rather than a
// source span. Records are provenance 'curated' and status 'unverified': the
// claim is real and attributable, but nothing here has yet been checked against
// the source PDF.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_CD: Paper[] = [
  // ── Thread C — localization: intracellular versus secretion (§4) ──────
  {
    id: 'C1',
    title:
      'Efficient recombinant protein production and secretion from nuclear transgenes in Chlamydomonas reinhardtii',
    authors: ['Lauersen KJ', 'Berger H', 'Mussgnug JH', 'Kruse O'],
    year: 2013,
    venue: 'J Biotechnol',
    doi: '10.1016/j.jbiotec.2012.10.010',
    pmid: '23099045',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['secretion', 'cah1 signal peptide', 'nuclear transgenes'],
    abstract:
      'Corpus entry for the study OF-COR-001 credits with establishing the CAH1 signal peptide as a route to heterologous secretion from Chlamydomonas nuclear transgenes. It is catalogued here as the origin point of the secretion architecture the rest of Thread C builds on; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `Establishes the CAH1 (carbonic anhydrase 1) signal peptide for heterologous secretion.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'Establishes the CAH1 (carbonic anhydrase 1) signal peptide for heterologous secretion.',
  },
  {
    id: 'C2',
    title:
      'High-yield secretion of recombinant proteins from the microalga Chlamydomonas reinhardtii',
    authors: ['Ramos-Martinez EM', 'Fimognari L', 'Sakuragi Y'],
    year: 2017,
    venue: 'Plant Biotechnol J',
    doi: '10.1111/pbi.12710',
    pmcid: 'PMC5552477',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15', 'uvm4'],
    topics: [
      'secretion benchmark',
      'glycomodule fusion',
      'gametolysin signal peptide',
      'secreted titer',
    ],
    abstract:
      'Corpus entry for the paper OF-COR-001 designates the current secretion benchmark for Chlamydomonas: the 15 mg/L against which every openFerment secretion scenario is scored. Summarised by the curator from the corpus document; the full text has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `The current secretion benchmark. The putative gametolysin signal sequence directs Venus into the medium; C-terminal fusion to synthetic glycomodules of tandem Ser-Pro repeats — (SP)10 and (SP)20 — raised yields up to 12-fold, reaching a maximum of 15 mg/L, and conferred enhanced proteolytic stability. This is the number every openFerment secretion scenario is measured against, and the number that makes the honest case that algal secretion is currently ~65× below Trichoderma β-lactoglobulin.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'The number every openFerment secretion scenario is measured against, and the number that makes the honest case that algal secretion is currently ~65× below Trichoderma β-lactoglobulin.',
  },
  {
    id: 'C3',
    title:
      'Comparison of secretory signal peptides for heterologous protein expression in microalgae',
    authors: ['Molino JVD', 'et al.'],
    year: 2018,
    venue: 'PLoS ONE',
    pmcid: 'PMC5800701',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['signal peptide screen', 'secretion', 'construct design'],
    abstract:
      'Corpus entry for the head-to-head signal-peptide comparison OF-COR-001 calls the decision table for which leader to fuse to CSN2. Catalogued from the curation note; the ten peptides and their ranking are not reproduced here because the full text has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `Ten signal peptides evaluated, drawn from four classes of natively secreted protein: BiP1, ARS1, CAH1, and IBP1, plus newly identified sequences from unexplored regions of the genome — two of which outperformed the established set. The decision table for which SP to fuse to CSN2.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The decision table for which SP to fuse to CSN2.',
  },
  {
    id: 'C4',
    title:
      'Robust Expression and Secretion of Xylanase1 in Chlamydomonas reinhardtii by Fusion to a Selection Gene and Processing with the FMDV 2A Peptide',
    authors: ['Rasala BA', 'et al.'],
    year: 2012,
    venue: 'PLoS ONE',
    pmcid: 'PMC3427385',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['2a peptide', 'secretion', 'signal peptide cleavage'],
    abstract:
      'Corpus entry for the self-cleaving 2A strategy that couples a secreted cargo to its selection marker on one transcript. OF-COR-001 keeps it as the most direct published answer to the two-cassette problem a CSN2 plus FAM20C program would face; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `Xylanase linked directly to an antibiotic resistance gene via the FMDV self-cleaving 2A sequence. LC-MS/MS confirms the ARS1 signal peptide is correctly cleaved during ER transit — peptides covering 97% of the cytoplasmic and 89% of the secreted sequence were identified, with no ARS1 peptides detected. The 2A strategy is the most direct published answer to A5's two-cassette problem: a single transcript could carry CSN2-2A-FAM20C.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      "The 2A strategy is the most direct published answer to A5's two-cassette problem: a single transcript could carry CSN2-2A-FAM20C.",
  },
  {
    id: 'C5',
    title: 'Strategies to facilitate transgene expression in Chlamydomonas reinhardtii',
    authors: ['Eichler-Stahlberg A', 'Weisheit W', 'Ruecker O', 'Heitzer M'],
    year: 2009,
    venue: 'Planta',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['ars2 signal peptide', 'transgene expression'],
    abstract:
      'Corpus entry for the source OF-COR-001 credits with the ARS2 signal peptide approach that the C7 secretion cassette later uses. The corpus document records the entry in a single line and marks the author string for verification.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `Source of the ARS2 signal peptide approach.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole: 'Source of the ARS2 signal peptide approach.',
  },
  {
    id: 'C6',
    title:
      'Unassembled cell wall proteins form aggregates in the extracellular space of Chlamydomonas reinhardtii strain UVM4',
    authors: [],
    year: 2022,
    venue: 'Appl Microbiol Biotechnol',
    doi: '10.1007/s00253-022-11960-9',
    pmcid: 'PMC9200674',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15', 'uvm4'],
    topics: ['secretome', 'cell wall glycoprotein aggregates', 'purification risk'],
    abstract:
      'Corpus entry for what OF-COR-001 calls the most important cautionary paper in the corpus: the UVM4 secretome is loaded with unassembled cell wall glycoprotein, and secreted product is trapped in it. It also recites the host yield history, which is why two of its records are marked non-primary.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `The most important cautionary paper in the corpus. Compares the extracellular proteome of UVM4 to its walled ancestor 137c under matched conditions. UVM4 produces a distinct extracellular proteomic profile with higher abundance of secreted cell wall glycoproteins; secreted recombinant proteins become trapped in a matrix of these aggregates, making isolation and purification difficult. It recites the yield history: 0.2% TSP intracellular (Neupert 2009) → 12–15 mg/L secreted (Lauersen 2013; Ramos-Martinez 2017). Note that its 12–15 mg/L is a citation of C2, not an independent measurement.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'The most important cautionary paper in the corpus.',
  },
  {
    id: 'C7',
    title:
      'Towards a biotechnological platform for the production of human pro-angiogenic growth factors in the green alga Chlamydomonas reinhardtii',
    authors: [],
    year: 2020,
    venue: 'Not recorded in OF-COR-001',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['uvm4'],
    topics: ['secretion cassette', 'ars2 leader peptide', 'vegf-165'],
    abstract:
      'Corpus entry for a worked example of the full UVM4/UVM11 secretion architecture — ARS2 leader, APHVIII selection, a human growth factor as cargo. OF-COR-001 keeps it as the construct template a CSN2 secretion cassette would be modelled on.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `Working example of the full secretion architecture in UVM4/UVM11: the 21-amino-acid leader peptide of arylsulfatase ARS2 (Cre16.g671350, Phytozome v5.5) inserted upstream of the coding sequence, with APHVIII for selection, expressing VEGF-165. The construct template a CSN2 secretion cassette would be modeled on.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole: 'The construct template a CSN2 secretion cassette would be modeled on.',
  },
  {
    id: 'C8',
    title:
      'Efficient secretory production of recombinant proteins in microalgae using an exogenous signal peptide',
    authors: [],
    year: 2025,
    venue: 'Front Microbiol',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['exogenous signal peptide', 'secretion', 'signal peptide table'],
    abstract:
      'Corpus entry for the demonstration that a signal peptide taken from another alga can drive secretion in a microalgal host, plus the consolidated table of Chlamydomonas signal peptides OF-COR-001 draws on. Catalogued from the curation note only.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `Novel SP from a ~17 kDa highly secreted protein in Chlorella sp. HS2; demonstrates non-native signal sequences can work in microalgae. Carries a consolidated table of SPs used in Chlamydomonas reinhardtii: FEA1, ARS1/ARS2, CAH1, BiP1, gametolysin.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'Demonstrates non-native signal sequences can work in microalgae.',
  },
  {
    id: 'C9',
    title:
      'Comparing the Ability of Secretory Signal Peptides for Heterologous Expression of Anti-Lipopolysaccharide Factor 3 in Chlamydomonas reinhardtii',
    authors: [],
    year: 2023,
    venue: 'Not recorded in OF-COR-001',
    pmid: '37367671',
    thread: 'C',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['signal peptide comparison', 'heterologous expression'],
    abstract:
      'Corpus entry held on its bibliographic line alone: OF-COR-001 lists the title, year and PMID for this signal-peptide comparison and writes no curation prose about it. Nothing is extractable until the source is retrieved.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §4)',
        text: `OF-COR-001 records this entry as a bibliographic line only, with no curation prose: a comparison of the ability of secretory signal peptides for heterologous expression of anti-lipopolysaccharide factor 3 in Chlamydomonas reinhardtii.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },

  // ── Thread D — host post-translational modification capability (§5) ────
  {
    id: 'D1',
    title:
      'Exploring the N-glycosylation Pathway in Chlamydomonas reinhardtii Unravels Novel Complex Structures',
    authors: ['Mathieu-Rivet E', 'et al.'],
    year: 2013,
    venue: 'Mol Cell Proteomics',
    pmcid: 'PMC3820931',
    thread: 'D',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['n-glycosylation', 'oligomannosides', 'glycan structures'],
    abstract:
      'Corpus entry for the survey of what Chlamydomonas actually puts on its own glycoproteins — predominantly oligomannosidic N-glycans, with a minor methylated and xylosylated complex fraction. It sets the baseline against which any host glycosylation risk to β-casein is judged.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §5)',
        text: `Endogenous soluble and membrane-bound proteins carry predominantly oligomannosides from Man-2 to Man-5; oligomannosidic N-glycans account for nearly 70% of the total N-glycan population; minor complex N-glycans are partially 6-O-methylated Man-3 to Man-5 bearing one or two xylose residues. β-casein is not natively N-glycosylated, so algal N-glycosylation is a risk rather than a requirement.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'β-casein is not natively N-glycosylated, so algal N-glycosylation is a risk rather than a requirement.',
  },
  {
    id: 'D2',
    title:
      'Heterologous expression of the N-acetylglucosaminyltransferase I dictates a reinvestigation of the N-glycosylation pathway in Chlamydomonas reinhardtii',
    authors: [],
    year: 2017,
    venue: 'Sci Rep',
    doi: '10.1038/s41598-017-10698-z',
    pmcid: 'PMC5578997',
    thread: 'D',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['n-glycosylation', 'gnti complementation', 'golgi perturbation'],
    abstract:
      'Corpus entry for the reinvestigation that recast the Chlamydomonas N-glycan as a linear, GnTI-independent structure, and for the failed attempt to redirect it with plant and diatom GnTI. OF-COR-001 keeps it as the standing warning against importing mammalian Golgi machinery into this host.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §5)',
        text: `Chlamydomonas reinhardtii proteins carry a linear Man5GlcNAc2 rather than the branched eukaryotic structure, arising from a Glc3Man5GlcNAc2 precursor and GnTI-independent Golgi processing. Complementation with Arabidopsis or Phaeodactylum GnTI produced no glycan change but did produce a stress phenotype: enlarged vacuoles, increased ROS, starch accumulation — read as Golgi perturbation. A direct warning that forcing mammalian-type Golgi machinery into this host has produced cellular stress before.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'A direct warning that forcing mammalian-type Golgi machinery into this host has produced cellular stress before.',
  },
  {
    id: 'D3',
    title:
      'Altered N-glycan composition impacts flagella-mediated adhesion in Chlamydomonas reinhardtii',
    authors: [],
    year: 2020,
    venue: 'eLife',
    thread: 'D',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['n-glycan engineering', 'xylosyltransferase', 'crispr knockouts'],
    abstract:
      'Corpus entry for the knockout work that supplies the genetic tools for changing algal N-glycan composition. Catalogued from a two-clause curation note; no quantitative claim is recorded there.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §5)',
        text: `Insertional and CRISPR knockouts of xylosyltransferase 1A; establishes tools for manipulating algal N-glycan composition.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'Establishes tools for manipulating algal N-glycan composition.',
  },
  {
    id: 'D4',
    title: 'Green algae Chlamydomonas reinhardtii possess endogenous sialylated N-glycans',
    authors: [],
    year: 2011,
    venue: 'Not recorded in OF-COR-001',
    thread: 'D',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['sialylated n-glycans', 'evidence conflict', 'mass spectrometry'],
    abstract:
      'Corpus entry retained deliberately as a conflict case: it reports mammalian-like sialylated N-glycans in the same host that D1 and D2 describe as oligomannosidic and free of sialylation. The platform is expected to surface the disagreement rather than average the two.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §5)',
        text: `Mass spectrometry of released N-linked oligosaccharides reports mammalian-like sialylated N-glycans in total extracts. This contradicts D1 and D2, which describe an oligomannosidic, xylose-decorated, GnTI-independent pathway with no sialylation. The entry is deliberately retained as a conflict case — the agent must surface the disagreement rather than average it.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole:
      'Deliberately retained as a conflict case — the agent must surface the disagreement rather than average it.',
  },
  {
    id: 'D5',
    title: 'The FAM20C-in-algae gap — OPEN',
    authors: [],
    year: 2026,
    venue: 'OF-COR-001 (corpus open question)',
    thread: 'D',
    sourceType: 'review',
    organisms: ['cw15'],
    topics: ['fam20c', 'secretory kinase', 'evidence gap', 'open question'],
    abstract:
      'Not a publication: this is the corpus’s record of a question the literature does not answer — whether Chlamydomonas has a Fam20-family secretory kinase at all. It carries no extraction records on purpose, because there is nothing published to extract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §5)',
        text: `No retrieved source establishes whether Chlamydomonas reinhardtii possesses a Fam20-family secretory kinase. Evidence is indirect and points toward absence: Fam20 kinases are described as conserved across the animal kingdom from sponges to mammals, and plants do not express FAM20C and have never successfully phosphorylated recombinant caseins with endogenous machinery. Chlamydomonas sits outside the animal lineage. The action recorded is an HMM search of the Chlamydomonas reinhardtii v6.1 proteome against Pfam PF03881, plus a search of the algal secretory-pathway kinase literature. This is the canonical known-unknown — a demonstration that the platform records what the literature does not say.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
    corpusRole:
      'The canonical known-unknown — a demonstration that the platform records what the literature does not say.',
  },
];

export const RECORDS_CD: ExtractionRecord[] = [
  // ── C2 — the secretion benchmark ──────────────────────────────────────
  {
    id: 'r-C2-1',
    paperId: 'C2',
    sectionId: 's1',
    quote: 'reaching a maximum of 15 mg/L',
    field: 'titer_secreted',
    value: 0.015,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'uvm4',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§4 C2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §4 C2 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-C2-2',
    paperId: 'C2',
    sectionId: 's1',
    quote: 'raised yields up to 12-fold',
    field: 'fold_improvement',
    value: 12,
    unit: '×',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'uvm4',
    isPrimary: true,
    evidenceClass: 'literature',
    comparativeBaseline: '(SP)10/(SP)20 glycomodule fusion vs unfused Venus',
    curationRef: '§4 C2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §4 C2 — pending verification against source',
      },
    ],
  },

  // ── C6 — recited yield history, both non-primary ──────────────────────
  {
    id: 'r-C6-1',
    paperId: 'C6',
    sectionId: 's1',
    quote: '12–15 mg/L secreted',
    field: 'titer_secreted',
    value: 0.0135,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'uvm4',
    isPrimary: false,
    evidenceClass: 'literature',
    citesRecordId: 'r-C2-1',
    range: { low: 0.012, high: 0.015 },
    curationRef: '§4 C6',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §4 C6 — recitation of C2, not an independent measurement; pending verification against source',
      },
    ],
  },
  {
    id: 'r-C6-2',
    paperId: 'C6',
    sectionId: 's1',
    quote: '0.2% TSP intracellular',
    field: 'expression_pct_tsp',
    value: 0.2,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'uvm4',
    isPrimary: false,
    evidenceClass: 'literature',
    citesRecordId: 'r-A1-1',
    curationRef: '§4 C6',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §4 C6 — recitation of A1 (Neupert 2009), not an independent measurement; pending verification against source',
      },
    ],
  },

  // ── D1 — endogenous N-glycan population ───────────────────────────────
  {
    id: 'r-D1-1',
    paperId: 'D1',
    sectionId: 's1',
    quote:
      'Endogenous soluble and membrane-bound proteins carry predominantly oligomannosides from Man-2 to Man-5',
    field: 'glycan_species',
    value: 'predominantly oligomannosides, Man-2 to Man-5',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§5 D1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §5 D1 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-D1-2',
    paperId: 'D1',
    sectionId: 's1',
    quote: 'oligomannosidic N-glycans account for nearly 70% of the total N-glycan population',
    field: 'glycan_species',
    value: 'oligomannosidic N-glycans, ~70% of the total N-glycan population',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§5 D1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §5 D1 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-D1-3',
    paperId: 'D1',
    sectionId: 's1',
    quote:
      'minor complex N-glycans are partially 6-O-methylated Man-3 to Man-5 bearing one or two xylose residues',
    field: 'glycan_species',
    value:
      'minor complex N-glycans: partially 6-O-methylated Man-3 to Man-5 with one or two xylose residues',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§5 D1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §5 D1 — pending verification against source',
      },
    ],
  },

  // ── D2 — linear Man5GlcNAc2, and the GnTI complementation negative ────
  {
    id: 'r-D2-1',
    paperId: 'D2',
    sectionId: 's1',
    quote: 'proteins carry a linear Man5GlcNAc2 rather than the branched eukaryotic structure',
    field: 'glycan_species',
    value: 'linear Man5GlcNAc2 (from a Glc3Man5GlcNAc2 precursor, GnTI-independent Golgi processing)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§5 D2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §5 D2 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-D2-2',
    paperId: 'D2',
    sectionId: 's1',
    quote: 'Complementation with Arabidopsis or Phaeodactylum GnTI produced no glycan change',
    field: 'glycan_species',
    value: 'unchanged — no glycan change after heterologous GnTI complementation',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    negativeResult: true,
    curationRef: '§5 D2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §5 D2 — pending verification against source',
      },
    ],
  },

  // ── D4 — the sialylation conflict ─────────────────────────────────────
  {
    id: 'r-D4-1',
    paperId: 'D4',
    sectionId: 's1',
    quote: 'reports mammalian-like sialylated N-glycans in total extracts',
    field: 'glycan_species',
    value: 'mammalian-like sialylated N-glycans in total extracts',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§5 D4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §5 D4 — conflicts with D1/D2; mass spectrometry named but not specified; pending verification against source',
      },
    ],
  },
];
