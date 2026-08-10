// openFerment — real corpus, Thread A (host platform) and Thread B (expression
// optimization). Transcribed from docs/OF-COR-001.md §2 and §3.
//
// REAL PAPERS, REAL AUTHORS. Nothing in this file is invented. Every paper
// carries `textSource: 'curation-note'` and `ingest: 'catalogued'`: the full
// texts have NOT been ingested, so each paper holds exactly one section whose
// body is the curator's prose from OF-COR-001, not the paper's own words. The
// `abstract` on each entry is likewise the curator's summary, not the
// publisher's abstract. Extraction records quote the curation note verbatim and
// carry `provenance: 'curated'` — real and attributable, but not yet checked
// against the source PDF.
//
// Where OF-COR-001 gives no year, `year` is 0 rather than a guess.
// Where OF-COR-001 gives no journal, `venue` says so rather than inventing one.
import type { Paper, ExtractionRecord } from '../types';

const VENUE_UNSTATED = '(venue not stated in OF-COR-001)';

export const PAPERS_AB: Paper[] = [
  // ── §2 Thread A — Host platform: cw15 and its derivatives ───────────
  {
    id: 'A1',
    title:
      'Generation of Chlamydomonas strains that efficiently express nuclear transgenes',
    authors: ['Neupert J', 'Karcher D', 'Bock R'],
    year: 2009,
    venue: 'Plant J',
    doi: '10.1111/j.1365-313X.2008.03746.x',
    thread: 'A',
    sourceType: 'journal-article',
    organisms: ['cw15', 'uvm4'],
    topics: ['strain development', 'uvm4 and uvm11', 'nuclear transgene expression'],
    abstract:
      'Corpus entry A1: the strain-lineage paper that derived UVM4 and UVM11 by UV mutagenesis from the cell-wall-deficient, arginine-auxotrophic cw15-302 background. It is in the corpus because every expression figure the cw15 programme quotes traces back to this lineage and to the ~0.2% TSP reporter ceiling recorded here.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `The foundational strain paper. Arginine-auxotrophic cell-wall-deficient cw15-302 (= CC-4350, cwd mt+ arg7) was co-transformed with the CRY1-1 emetine resistance gene and ARG7 to give Elow47; UV mutagenesis of Elow47 followed by selection for high transgene expression yielded UVM4 and UVM11. Both reach ~0.2% of total soluble protein for intracellular GFP/YFP. Selection used paromomycin at 10 µg/mL and zeocin.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The foundational strain paper.',
  },
  {
    id: 'A2',
    title:
      'An epigenetic gene silencing pathway selectively acting on transgenic DNA in the green alga Chlamydomonas',
    authors: ['Neupert J'],
    year: 2020,
    venue: 'Nat Commun',
    doi: '10.1038/s41467-020-19983-4',
    thread: 'A',
    sourceType: 'journal-article',
    organisms: ['cw15', 'uvm4'],
    topics: ['transgene silencing', 'histone deacetylase', 'chromatin state'],
    abstract:
      'Corpus entry A2: the paper that names the causative lesion behind the UVM4/UVM11 phenotype as a Sir2-type histone deacetylase. It is in the corpus because whether the UVM advantage is silencing relief or a transcription gain decides whether a two-cassette CSN2 + FAM20C construct inherits it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Identifies the causative lesion in UVM4/UVM11 as a Sir2-type histone deacetylase (SRTA). ChIP against H3K9/K14ac and H4K5ac establishes the chromatin mechanism. Untransformed CC-4350 and Elow47 show no detectable YFP. If the mechanism is silencing relief rather than a transcription gain, a two-gene construct inherits the same benefit — an argument that needs testing.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'If the mechanism is silencing relief rather than a transcription gain, a two-gene construct inherits the same benefit — an argument that needs testing.',
  },
  {
    id: 'A3',
    title:
      'Efficient expression of nuclear transgenes in the green alga Chlamydomonas: synthesis of an HIV antigen and development of a new selectable marker',
    authors: ['Barahimipour R', 'Neupert J', 'Bock R'],
    year: 2016,
    venue: 'Plant Mol Biol',
    pmcid: 'PMC4766212',
    thread: 'A',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['hiv capsid p24', 'selectable marker', 'non-reporter cargo'],
    abstract:
      'Corpus entry A3: a case study expressing a non-reporter, biotechnologically relevant protein from a nuclear transgene in Chlamydomonas, plus rescue of nptII as a marker. It is catalogued as the closest published analogue to what a CSN2 construct would have to do.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Case study on expressing a non-reporter, biotechnologically relevant protein (HIV capsid P24) plus rescue of nptII as a marker. The closest published analogue to what a CSN2 construct would have to do.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The closest published analogue to what a CSN2 construct would have to do.',
  },
  {
    id: 'A4',
    title: 'Nuclear transformation of Chlamydomonas reinhardtii: A review',
    authors: ['Zhang MP', 'Wang M', 'Wang C'],
    year: 2021,
    venue: 'Biochimie',
    pmid: '33227342',
    thread: 'A',
    sourceType: 'review',
    organisms: [],
    topics: ['transformation methods', 'nhej integration', 'selection genes'],
    abstract:
      'Corpus entry A4: a systematic review of nuclear transformation methods, selection genes and efficiency factors in Chlamydomonas reinhardtii. It is in the corpus for the integration behaviour it summarises — non-homologous end joining at random loci, rare homologous recombination, and insertional damage near the integration site.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Systematic review of transformation methods, selection genes, and efficiency factors. Integration proceeds by non-homologous end joining at random loci; homologous recombination occurs at much lower frequency; insertional events can cause deletion, recombination, or translocation near the integration site.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'A5',
    title:
      'Molecular Advancements Establishing Chlamydomonas as a Host for Biotechnological Exploitation',
    authors: [],
    year: 2022,
    venue: VENUE_UNSTATED,
    pmcid: 'PMC9277225',
    thread: 'A',
    sourceType: 'review',
    organisms: ['uvm4'],
    topics: ['mating limitation', 'uvm4 and uvm11', 'multi-cassette strategy'],
    abstract:
      'Corpus entry A5: a platform review covering the UVM4/UVM11 mating limitation and a walled, mating-competent UVM11 derivative. It is in the corpus because a two-cassette CSN2 + FAM20C programme is exactly the case where that limitation bites.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Covers the UVM4/UVM11 mating limitation — the strains can hardly be crossed, so each transgene must be introduced by separate transformation with a distinct marker. Notes a walled, mating-competent UVM11 derivative. A two-cassette CSN2 + FAM20C program is exactly the case this limitation bites.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'A two-cassette CSN2 + FAM20C program is exactly the case this limitation bites.',
  },
  {
    id: 'A6',
    title:
      'Current Nuclear Engineering Strategies in the Green Microalga Chlamydomonas reinhardtii',
    authors: [],
    year: 0,
    venue: VENUE_UNSTATED,
    pmcid: 'PMC10381326',
    thread: 'A',
    sourceType: 'review',
    organisms: [],
    topics: ['nhej integration', 'position effects', 'crispr editing'],
    abstract:
      'Corpus entry A6: a consolidation of current nuclear engineering strategies for Chlamydomonas reinhardtii, spanning integration behaviour, position-effect variance, the known silencing routes and CRISPR status. It is catalogued as thread-A background rather than for any single number; OF-COR-001 states no publication year for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Consolidates NHEJ integration behavior, position-effect variance across transformants, the SRTA and met1 silencing routes, and CRISPR editing status.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
  },
  {
    id: 'A7',
    title:
      'Transcriptional gene fusions via targeted integration at safe harbors for high transgene expression in Chlamydomonas reinhardtii',
    authors: [],
    year: 0,
    venue: VENUE_UNSTATED,
    pmcid: 'PMC12371178',
    thread: 'A',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['safe harbor locus', 'targeted integration', 'expression boost'],
    abstract:
      'Corpus entry A7: the safe-harbor integration paper, identifying LHCBM1 as a locus that raises transgene accumulation well above random insertion. It is in the corpus as the single most actionable expression-boost result in thread A; OF-COR-001 states no publication year for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Identifies the LHCBM1 locus as a genetic safe harbor; reports an 8.6-fold increase in transgenic protein accumulation over random insertion, and a 60-fold increase in valencene production when a sesquiterpene synthase was co-expressed there. The single most actionable expression-boost result in the thread.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'The single most actionable expression-boost result in the thread.',
  },
  {
    id: 'A8',
    title:
      'Chlamydomonas reinhardtii as a viable platform for the production of recombinant proteins: current status and perspectives',
    authors: [],
    year: 2011,
    venue: 'Plant Cell Rep',
    doi: '10.1007/s00299-011-1186-8',
    pmid: '22080228',
    thread: 'A',
    sourceType: 'review',
    organisms: [],
    topics: ['expression limitations', 'codon dependency', 'protease sensitivity'],
    abstract:
      'Corpus entry A8: a platform review enumerating the factors that limit recombinant protein expression in Chlamydomonas reinhardtii. It is catalogued for that list of limitations rather than for any measured value.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Enumerates the factors limiting expression — enhancer elements, codon dependency, protease sensitivity, transformation-associated genotypic modification.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },
  {
    id: 'A9',
    title:
      'Chlamydomonas reinhardtii: a protein expression system for pharmaceutical and biotechnological proteins',
    authors: [],
    year: 2007,
    venue: VENUE_UNSTATED,
    pmid: '17172667',
    thread: 'A',
    sourceType: 'review',
    organisms: [],
    topics: ['platform review', 'pharmaceutical proteins', 'historical baseline'],
    abstract:
      'Corpus entry A9: the earliest platform review in thread A, describing Chlamydomonas reinhardtii as an expression system for pharmaceutical and biotechnological proteins. It is catalogued for the historical arc before UVM4.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §2)',
        text: `Earlier platform review; useful for the historical arc before UVM4.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
    corpusRole: 'Earlier platform review; useful for the historical arc before UVM4.',
  },

  // ── §3 Thread B — Expression optimization ───────────────────────────
  {
    id: 'B1',
    title:
      'Dissecting the contributions of GC content and codon usage to gene expression in the model alga Chlamydomonas reinhardtii',
    authors: [
      'Barahimipour R',
      'Strenkert D',
      'Neupert J',
      'Schroda M',
      'Merchant SS',
      'Bock R',
    ],
    year: 2015,
    venue: 'Plant J',
    doi: '10.1111/tpj.13033',
    pmcid: 'PMC4715772',
    thread: 'B',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['codon usage', 'gc content', 'heterochromatinization'],
    abstract:
      'Corpus entry B1: the experiment that separates GC content from codon usage by expressing YFP variants of identical amino acid sequence. It is in the corpus because β-casein is proline-rich and mammalian-codon-biased, which is precisely the case this paper predicts will fail without resynthesis.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §3)',
        text: `The decisive experiment: YFP variants encoding identical amino acid sequences but differing in GC content and/or codon usage. Codon usage is the key determinant of translational efficiency and, unexpectedly, of mRNA stability; unfavorable GC content acts at the chromatin level by triggering heterochromatinization. High-expressing mutant strains are less susceptible to epigenetic suppression. β-casein is proline-rich and mammalian-codon-biased — the exact case this paper predicts will fail without resynthesis.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'β-casein is proline-rich and mammalian-codon-biased — the exact case this paper predicts will fail without resynthesis.',
  },
  {
    id: 'B2',
    title:
      'Intron-containing algal transgenes mediate efficient recombinant gene expression in the green microalga Chlamydomonas reinhardtii',
    authors: [],
    year: 2018,
    venue: 'Nucleic Acids Res',
    thread: 'B',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['native introns', 'genome gc content', 'cargo length'],
    abstract:
      'Corpus entry B2: the native-intron insertion study, which also records the compositional context a CSN2 transgene has to sit in — a GC-rich nuclear genome with narrow codon bias. It is in the corpus because most robust engineering reports involve short reporter CDSs rather than the 627 nt cargo a mature β-casein construct requires.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §3)',
        text: `Establishes sequence-specific dynamics of native intron insertion into nuclear transgenes. Records the nuclear genome at ~64% GC overall and ~68% in coding regions with narrow codon bias, and notes that most robust engineering reports involve short reporter CDSs rather than long cargo. Mature β-casein CDS is 627 nt.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
  },
  {
    id: 'B3',
    title:
      'Enhancing heterologous expression in Chlamydomonas reinhardtii by transcript sequence optimization',
    authors: ['Weiner I', 'Atar S', 'Schweitzer S', 'Eilenberg H', 'Feldman Y', 'Avitan M'],
    year: 2018,
    venue: 'Plant J',
    pmid: '29383789',
    thread: 'B',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['transcript optimization', 'heterologous expression'],
    abstract:
      'Corpus entry B3: a transcript-sequence-optimization study for heterologous expression in Chlamydomonas reinhardtii. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §3)',
        text: `OF-COR-001 §3 lists this entry with authors, title, journal and identifier only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'B4',
    title:
      'Introns mediate post-transcriptional enhancement of nuclear gene expression in the green microalga Chlamydomonas reinhardtii',
    authors: [],
    year: 2020,
    venue: 'PLOS Genet',
    thread: 'B',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['introns', 'post-transcriptional enhancement'],
    abstract:
      'Corpus entry B4: an intron-mediated post-transcriptional enhancement study in Chlamydomonas reinhardtii. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §3)',
        text: `OF-COR-001 §3 lists this entry with title, journal and article number only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'B5',
    title:
      'Exploring the Impact of Terminators on Transgene Expression in Chlamydomonas reinhardtii with a Synthetic Biology Approach',
    authors: [],
    year: 2021,
    venue: 'Life',
    doi: '10.3390/life11090964',
    pmcid: 'PMC8471596',
    thread: 'B',
    sourceType: 'journal-article',
    organisms: ['cw15', 'uvm4'],
    topics: ['terminators', 'time to colony', 'shear sensitivity'],
    abstract:
      'Corpus entry B5: a synthetic-biology survey of nine terminators against a GFP reporter that also compares transformation of cw15, UVM4 and walled WT12 head to head. It is in the corpus for that time-to-colony comparison and for the shear- and osmotic-sensitivity trade-off it states plainly.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §3)',
        text: `Nine terminators across three size classes tested against a GFP reporter; optimal size tracked the median terminator length in the genome; PSAD and CA1 terminators gave significantly higher transformant counts than a no-3′UTR control (p<0.01). Directly compares transformation of cw15, UVM4, and walled WT12: colonies appear on selection in 7–10 days for cw15 and UVM4 versus 15–20 days for WT12. States the trade-off plainly — cell-wall-deficient strains have reduced motility and mating ability and are much more susceptible to shear and osmotic stress. The shear sensitivity is a bioreactor design constraint that propagates into the Simulate module's agitation and scale assumptions.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      "The shear sensitivity is a bioreactor design constraint that propagates into the Simulate module's agitation and scale assumptions.",
  },
];

export const RECORDS_AB: ExtractionRecord[] = [
  // ── A1 ──────────────────────────────────────────────────────────────
  {
    id: 'r-A1-1',
    paperId: 'A1',
    sectionId: 's1',
    quote: 'Both reach ~0.2% of total soluble protein for intracellular GFP/YFP',
    field: 'expression_pct_tsp',
    value: 0.2,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'uvm4',
    isPrimary: true,
    curationRef: '§2 A1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §2 A1 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-A1-2',
    paperId: 'A1',
    sectionId: 's1',
    quote: 'Selection used paromomycin at 10 µg/mL and zeocin',
    field: 'medium_component_conc',
    value: 10,
    unit: 'µg mL⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    componentTag: 'paromomycin',
    isPrimary: true,
    curationRef: '§2 A1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §2 A1 — pending verification against source',
      },
    ],
  },

  // ── A2 ──────────────────────────────────────────────────────────────
  {
    id: 'r-A2-1',
    paperId: 'A2',
    sectionId: 's1',
    quote: 'Untransformed CC-4350 and Elow47 show no detectable YFP',
    field: 'expression_pct_tsp',
    value: 0,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    negativeResult: true,
    curationRef: '§2 A2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §2 A2 — pending verification against source',
      },
    ],
  },

  // ── A7 ──────────────────────────────────────────────────────────────
  {
    id: 'r-A7-1',
    paperId: 'A7',
    sectionId: 's1',
    quote: 'an 8.6-fold increase in transgenic protein accumulation over random insertion',
    field: 'fold_improvement',
    value: 8.6,
    unit: '×',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    comparativeBaseline:
      'random insertion of the same transgene (vs targeted integration at the LHCBM1 safe harbor)',
    curationRef: '§2 A7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §2 A7 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-A7-2',
    paperId: 'A7',
    sectionId: 's1',
    quote:
      'a 60-fold increase in valencene production when a sesquiterpene synthase was co-expressed there',
    field: 'fold_improvement',
    value: 60,
    unit: '×',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    comparativeBaseline:
      'baseline not stated in OF-COR-001; the entry contrasts targeted integration at the LHCBM1 safe harbor with random insertion',
    curationRef: '§2 A7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §2 A7 — pending verification against source',
      },
    ],
  },

  // ── B5 — three strains, three records ───────────────────────────────
  {
    id: 'r-B5-1',
    paperId: 'B5',
    sectionId: 's1',
    quote: 'colonies appear on selection in 7–10 days for cw15 and UVM4',
    field: 'time_to_colony',
    value: 8.5,
    unit: 'd',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'cw15',
    isPrimary: true,
    range: { low: 7, high: 10 },
    curationRef: '§3 B5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §3 B5 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-B5-2',
    paperId: 'B5',
    sectionId: 's1',
    quote: 'colonies appear on selection in 7–10 days for cw15 and UVM4',
    field: 'time_to_colony',
    value: 8.5,
    unit: 'd',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'uvm4',
    isPrimary: true,
    range: { low: 7, high: 10 },
    curationRef: '§3 B5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §3 B5 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-B5-3',
    paperId: 'B5',
    sectionId: 's1',
    quote: 'versus 15–20 days for WT12',
    field: 'time_to_colony',
    value: 17.5,
    unit: 'd',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'creinhardtii-wt',
    isPrimary: true,
    range: { low: 15, high: 20 },
    comparativeBaseline: 'walled wild-type WT12, against cell-wall-deficient cw15 and UVM4',
    curationRef: '§3 B5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §3 B5 — pending verification against source',
      },
    ],
  },
];
