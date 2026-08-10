// openFerment corpus — Thread H (phosphorylation in heterologous hosts: what
// has actually been achieved). Transcribed from docs/OF-COR-001.md §9.
//
// REAL PAPERS, REAL AUTHORS. Every title, author string, year, venue, DOI,
// PMCID and patent number here is copied from OF-COR-001 §9. Nothing is
// invented: where the document gives no title, venue or year, the field says so
// or is 0 rather than carrying a guess.
//
// The full texts have NOT been ingested. Each paper carries exactly one section
// whose body is the curator's note from OF-COR-001 — the curator's words about
// the paper, never the paper's own prose — hence `textSource: 'curation-note'`
// and `ingest: 'catalogued'`. `abstract` is likewise the curator's summary of
// why the entry is in the corpus, not the publisher's abstract. Every record
// quotes that curation note verbatim, carries `provenance: 'curated'` and
// `status: 'unverified'`: real and attributable, but not yet checked against the
// source PDF.
//
// Thread-specific decisions, recorded so a reader can audit them:
//
//   * H1 (Mora Vásquez et al.) is a REVIEW whose Tables 1–3 recite other
//     groups' measurements. Its records are therefore `isPrimary: false`, and
//     the two plant figures cite the H15 records they are drawn from. Counting
//     H1's potato and soybean rows as independent of H15 would double-count the
//     only two plant studies that exist (OF-COR-001 §19, citation-of-a-citation).
//   * Where OF-COR-001 gives a titer without naming the compartment (H1's yeast
//     span, H5, H7, H14) the record is filed under `titer_intracellular` at
//     confidence 0.7 with the ambiguity stated in its audit trail. H2 and H3 are
//     at 0.9: their host is E. coli, which has no secretory compartment.
//   * H6, H9, H10, H11 and H16 carry NO records. Their curation notes state
//     mobility parity, thesis chapter scope, a biosensor design, a bare citation
//     and a one-line role — none of which is a value in any of the 24 ontology
//     fields. Forcing them in would fabricate numbers the document does not give.
//   * H17 in the document is a single landscape paragraph over six patent
//     families. It is split here into one `sourceType: 'patent'` Paper per
//     family (H17a–H17f) so that the ≥1% TSP claim attaches to the patent that
//     makes it (US12077798B2) rather than to a mixed bag. The entry-id sort in
//     data/papers.ts already carries a suffix group for exactly this shape.
//   * §9 marks no entry [verify], so no paper here sets `verifyNeeded`.
//   * check-seed emits exactly one warning against this file, deliberately:
//     r-H1-1 is non-primary and names no cited record, because H1's yeast span
//     runs across five tabulated studies and pointing it at any single one of
//     them would be a worse lie than leaving it unattributed. It is excluded
//     from aggregates by isPrimary either way.
import type { Paper, ExtractionRecord } from '../types';

const VENUE_UNSTATED = '(venue not stated in OF-COR-001)';
const PATENT_VENUE = 'Patent literature (OF-COR-001 §9 H17, from H1 Table 4)';

export const PAPERS_H: Paper[] = [
  {
    id: 'H1',
    title:
      'Heterologous Caseins: The Role of Phosphorylation in Their Functionality and How to Achieve It',
    authors: ['Mora Vásquez S', 'García-Jacobo S', 'Cardineau GA', 'García-Lara S'],
    year: 2025,
    venue: 'Biomolecules',
    doi: '10.3390/biom15071031',
    pmcid: 'PMC12292773',
    thread: 'H',
    sourceType: 'review',
    organisms: ['ecoli', 'bovine'],
    topics: [
      'heterologous casein expression',
      'prior-art benchmark',
      'phosphorylation analysis methods',
    ],
    abstract:
      'Corpus entry for the review that defines the shape of the prior art this programme is measured against: every reported heterologous casein study, tabulated by host, with the phosphorylation analysis method recorded — or recorded as never performed. It is the thread anchor because it is the source of the claim that no algal row exists; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `The keystone review. Systematic search of literature and patent databases for heterologous casein expression. Table 1 — 17 bacterial studies. Table 2 — 5 yeast studies, expression 0.6 mg/L to 1 g/L. Table 3 — 2 plant studies (potato 0.01%; soybean 0.1–0.4%, not phosphorylated). Table 4 — 12 patents, 2022–2024. Reviews four phosphorylation analysis methods (MALDI-MS / LC-ESI-MS; SDS-PAGE with Ethyl Stains-All; Urea-PAGE with phosphatase treatment; Phos-tag), and three enhancement strategies. Concludes that quantitative functional thresholds — how much calcium-binding is lost, what minimum phosphorylation supports curd formation — remain unestablished. Records "undetermined" for most bacterial studies because the analysis was never done.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The keystone review.',
  },
  {
    id: 'H2',
    title:
      'Expression and Characterization of Phosphorylated Recombinant Human Beta-Casein in Escherichia coli',
    authors: ['Thurmond JM', 'et al.'],
    year: 1997,
    venue: 'Protein Expr Purif',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['ecoli'],
    topics: ['human β-casein', 'ck2 co-expression', 'highest phosphorylated titer'],
    abstract:
      'Corpus entry for the highest-yield phosphorylated recombinant casein reported anywhere: human β-casein co-expressed in E. coli with both subunits of human CK2. It sets the titer bar the cw15 programme is compared against, and — read beside H3 — the limit of what CK2 can do for a bovine sequence.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Polycistronic construct encoding human β-casein with both α and β subunits of human CK2. Achieved high-level phosphorylated recombinant human β-casein at 500 mg/L, characterized by urea-PAGE, SDS-PAGE and negative-ion LC-ESI-MS. The highest-yield phosphorylated recombinant casein on record.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The highest-yield phosphorylated recombinant casein on record.',
  },
  {
    id: 'H3',
    title:
      'An E. coli over-expression system for multiply-phosphorylated proteins and its use in a study of calcium phosphate sequestration by novel recombinant phosphopeptides',
    authors: ['Clegg RA', 'Holt C'],
    year: 2009,
    venue: 'Protein Expr Purif',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['ecoli', 'bovine'],
    topics: ['bovine β-casein', 'ck2 consensus mismatch', 'partial phosphorylation'],
    abstract:
      'Corpus entry for the companion negative to H2: the same CK2 co-expression strategy applied to BOVINE β-casein reaches only partial phosphorylation, because only some bovine cluster serines sit in canonical CK2 sites. This pair is why the programme treats the kinase choice as a design decision rather than a detail.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `The companion negative result. Bovine β-casein co-expressed with CK2 achieved much lower phosphorylation than the native 5P state. In human β-casein the serine clusters align well with CK2 consensus sites; in bovine β-casein only some cluster serines sit in canonical CK2 sites. Yield 200 mg/L, partially phosphorylated (infusion MS of purified phosphopeptides). H2 and H3 together are the decisive argument for FAM20C over CK2 in a bovine program.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'H2 and H3 together are the decisive argument for FAM20C over CK2 in a bovine program.',
  },
  {
    id: 'H4',
    title:
      'Expression and Purification of Glycosylated Bovine β-Casein (L70S/P71S) in Pichia pastoris',
    authors: ['Choi BK', 'Jiménez-Flores R'],
    year: 2001,
    venue: 'J Agric Food Chem',
    doi: '10.1021/jf001298f',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['gs115', 'bovine'],
    topics: [
      'pichia β-casein',
      'signal peptide failure',
      'native-degree phosphorylation',
      'mannan glycosylation',
    ],
    abstract:
      'Corpus entry for the closest eukaryotic precedent to the cw15 programme: bovine β-casein at 15–18% of total soluble protein in a yeast, phosphorylated to the same degree as animal-derived protein, but almost entirely retained inside the cell behind a bovine signal peptide the host did not read. It carries the thread’s densest record set and its sharpest construct-design warning.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `The closest eukaryotic precedent. L70S/P71S mutations introduced an N-glycosylation site. Despite using the native bovine β-casein signal peptide for secretion, the protein localized mostly intracellularly at approximately 15–18% of total soluble protein, corresponding to 0.7–1.0 g/L; secreted protein reached only 0.005% of the intracellular level. Phosphorylation analysis (phosphatase treatment + Urea-PAGE) showed the recombinant protein carried the same degree of phosphorylation as animal-derived β-casein. The protein was N-glycosylated with mannan. The single most instructive paper for the cw15 program.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The single most instructive paper for the cw15 program.',
  },
  {
    id: 'H5',
    title:
      'Study of putative glycosylation sites in bovine β-casein introduced by PCR-based site-directed mutagenesis',
    authors: ['Choi BK', 'Jiménez-Flores R'],
    year: 1996,
    venue: 'J Agric Food Chem',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['glycosylation sites', 'site-directed mutagenesis', 'yeast titer'],
    abstract:
      'Corpus entry for the earlier of the two Choi & Jiménez-Flores papers, catalogued for a single number: 1 g/L, the top of the yeast expression span that H1 Table 2 reports. OF-COR-001 gives no further prose for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Reported at 1 g/L. OF-COR-001 gives no further curation prose for this entry, and does not name the expression host or say whether the figure is intracellular or secreted.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'H6',
    title: 'Expression of bovine β-casein in Saccharomyces cerevisiae',
    authors: ['Jimenez-Flores R', 'Richardson T', 'Bisson LF'],
    year: 1990,
    venue: 'J Agric Food Chem',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['saccharomyces expression', 'urea-gel mobility', 'periplasmic retention'],
    abstract:
      'Corpus entry for the first yeast casein study: matching urea-gel mobilities against bovine casein before and after dephosphorylation, with the product held in the periplasm. It carries no extraction records because the curation note states an observed parity, not a measured degree.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Yeast-produced and bovine casein showed the same urea-gel mobilities before and after dephosphorylation. Protein was retained in the periplasmic space.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'H7',
    title: 'Secretion of bovine β-casein by Saccharomyces cerevisiae',
    authors: ['Chung KS', 'Oh SS', 'Richardson T'],
    year: 1991,
    venue: 'J Microbiol Biotechnol',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['saccharomyces secretion', 'secreted fraction', 'bovine β-casein'],
    abstract:
      'Corpus entry for the yeast secretion attempt that supplies the platform’s S. cerevisiae secreted-fraction reference of 5–10%. Beside H4’s 0.005%, it frames how differently two yeasts handle the same cargo.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `10 mg/L; only 5–10% of total expressed casein reached the extracellular medium.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'H8',
    title: 'Production of phosphorylated and functional αs1-casein in Escherichia coli',
    authors: [
      'Balasubramanian S',
      'Mobasseri G',
      'Shi L',
      'Jers C',
      'Køhler JB',
      'Boire A',
      'Berton-Carabin C',
      'Mijakovic I',
      'Jensen PR',
    ],
    year: 2025,
    venue: 'Trends Biotechnol',
    doi: 'S0167779925001817',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['ecoli', 'bovine'],
    topics: ['kinase screen', 'fam20c in e. coli', 'phosphomimetic aspartate', 'αs1-casein'],
    abstract:
      'Corpus entry for the most recent bacterial attempt: five kinases screened for S-x-E/pS specificity, FAM20C expression in E. coli failing outright, and an eight-site Ser→Asp phosphomimetic built as the fallback. It is the strongest published argument for moving the whole problem into a host that has a secretory pathway.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Five kinases screened for S-x-E/pS specificity: three prokaryotic Hanks-type Ser/Thr kinases from Bacillus subtilis (PrkC, PrkD, YabT) and eukaryotic FAM20C from human and bovine. Attempts to express both FAM20C versions in E. coli failed — successful human FAM20C expression has to date been achieved only in human cell lines. A phosphomimetic route was built in parallel: all eight phosphoserine sites of αs1-casein variant B substituted with aspartate. The strongest single argument for a eukaryotic host with a secretory pathway.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The strongest single argument for a eukaryotic host with a secretory pathway.',
  },
  {
    id: 'H9',
    title: 'Precision fermentation of milk proteins',
    authors: ['Balasubramanian S'],
    year: 2025,
    venue: 'PhD thesis, DTU',
    thread: 'H',
    sourceType: 'thesis',
    organisms: ['ecoli'],
    topics: ['precision fermentation thesis', 'phosphomimetic proteins', 'milk protein hosts'],
    abstract:
      'Corpus entry for the thesis behind H8, catalogued for scope rather than for numbers: six chapters spanning C. glutamicum element optimization, phosphorylated and phosphomimetic caseins in E. coli, protein hybrids, and alfalfa whey. It carries no extraction records because the curation note states no measured value.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Six chapters covering C. glutamicum genetic element optimization, phosphorylated and phosphomimetic proteins in E. coli, recombinant caseins in plant–animal protein hybrids, and whey proteins from alfalfa. Includes a patent: Method to produce phosphorylated milk proteins in microbe (Jers, Shi, et al., 2023).`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'H10',
    title:
      'Biosensor-guided rapid screening for improved recombinant protein secretion in Pichia pastoris',
    authors: [
      'Navone L',
      'Moffitt K',
      'Behrendorff J',
      'Sadowski P',
      'Hartley C',
      'Speight R',
    ],
    year: 2023,
    venue: 'Microb Cell Fact',
    doi: '10.1186/s12934-023-02089-z',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['gs115', 'bovine'],
    topics: ['split-gfp biosensor', 'secretion screening', 'β-casein cargo'],
    abstract:
      'Corpus entry for a method rather than a result: a split-GFP secretion biosensor validated on β-casein among four cargoes, which the programme could transplant to screen cw15 secretion variants. It carries no extraction records — the curation note describes an assay design, not a value.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Split-GFP biosensor with a GFP1-10–TEV protease fusion in the ER; GFP11-tagged cargo complements on transit, so intracellular fluorescence tracks secretion. Validated on four cargoes including β-casein and β-lactoglobulin, with β-casein monitored under methanol induction at 72–130 h. A directly transplantable screening protocol.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'A directly transplantable screening protocol.',
  },
  {
    id: 'H11',
    title:
      'Overproduction of bovine β-casein in E. coli and engineering of its main chymosin cleavage site',
    authors: [
      'Simons G',
      'van den Heuvel W',
      'Reynen T',
      'Frijters A',
      'Rutten G',
      'Slangen CJ',
      'Groenen M',
      'de Vos WM',
      'Siezen RJ',
    ],
    year: 1993,
    venue: 'Protein Eng',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['ecoli', 'bovine'],
    topics: ['bovine β-casein', 'chymosin cleavage site', 'e. coli overproduction'],
    abstract:
      'Corpus entry catalogued as a bibliographic row in the bacterial prior art, with no curation prose attached. It carries no extraction records because OF-COR-001 states no value for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `OF-COR-001 lists this entry as a citation only, with no curation prose beyond the reference itself. The title records overproduction of bovine β-casein in E. coli and engineering of its main chymosin cleavage site; the corpus document gives no yield, no phosphorylation state and no analytical method for it.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'H12',
    title: 'Expression of human milk β-casein in E. coli',
    authors: [
      'Hansson L',
      'Bergström S',
      'Hernell O',
      'Lönnerdal B',
      'Nilsson AK',
      'Strömqvist M',
    ],
    year: 1993,
    venue: 'Protein Expr Purif',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['ecoli'],
    topics: ['human milk β-casein', 'unphosphorylated product', 'e. coli'],
    abstract:
      'Corpus entry for one of the seventeen bacterial studies, catalogued for its single stated outcome: the product was not phosphorylated. It is a reported negative, which the platform must hold apart from the many bacterial rows where the analysis was simply never done.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Not phosphorylated. OF-COR-001 gives no further curation prose for this entry and names no analytical method behind that negative.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'H13',
    title: 'Comparison of native and recombinant non-phosphorylated human β-casein',
    authors: ['Bu H', 'Hu Y', 'Sood SM', 'Slattery CW'],
    year: 2003,
    venue: 'Arch Biochem Biophys',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['non-phosphorylated β-casein', 'native versus recombinant comparison'],
    abstract:
      'Corpus entry catalogued as a citation only; its one extractable fact is in the title, which describes the recombinant material as non-phosphorylated. Recorded at reduced confidence for exactly that reason.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `OF-COR-001 lists this entry as a citation only, with no curation prose beyond the reference itself. The title records a comparison of native and recombinant non-phosphorylated human β-casein; the corpus document gives no yield and names no analytical method for it.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'H14',
    title:
      "Bioconversion of lignocellulosic 'waste' to high-value food proteins: recombinant production of bovine and human αs1-casein based on wheat straw lignocellulose",
    authors: [
      'Wang Y',
      'Kubiczek D',
      'Horlamus F',
      'Raber HF',
      'Hennecke T',
      'Einfalt D',
      'Henkel M',
      'Hausmann R',
      'Wittgens A',
      'Rosenau F',
    ],
    year: 2021,
    venue: 'GCB Bioenergy',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['lignocellulose feedstock', 'αs1-casein', 'highest bacterial titer'],
    abstract:
      'Corpus entry for the highest bacterial casein titer in the corpus, 1.45 g/L, produced on a wheat-straw lignocellulose feedstock. It is the number any algal titer will be held against, and OF-COR-001 gives it without naming the host strain.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `1.45 g/L — the highest bacterial casein titer in the corpus. OF-COR-001 records the figure as bacterial without naming the host strain.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The highest bacterial casein titer in the corpus.',
  },
  {
    id: 'H15',
    title:
      'Bovine β-casein in soybean and human β-casein in potato (title not stated in OF-COR-001)',
    authors: ['Philip R', 'et al.'],
    year: 2001,
    venue: VENUE_UNSTATED,
    thread: 'H',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['plant expression', 'soybean', 'potato', 'no phosphorylation'],
    abstract:
      'Corpus entry for both plant studies in the entire prior art — soybean at 0.1–0.4% TSP and potato at 0.01% — and for the finding that the plant-made casein was not phosphorylated. OF-COR-001 gives neither a title nor a journal for it, so both fields say so rather than carrying a guess.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `Bovine β-casein in soybean (Glycine max), 0.1–0.4% of total soluble protein, not phosphorylated by MALDI-MS. Enrichment used anti-casein antibody coupled to CNBr-activated Sepharose 4B. Also: human β-casein in Solanum tuberosum, 0.01%; migrated as a single ~30 kDa band, 1–1.5 kDa smaller than the phosphorylated control.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'H16',
    title: 'Expression of a biologically active GFP-αs1-casein fusion in Lactococcus lactis',
    authors: ['Shigemori S', 'et al.'],
    year: 2012,
    venue: 'Curr Microbiol',
    thread: 'H',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['lactococcus lactis', 'gfp fusion', 'food-grade host'],
    abstract:
      'Corpus entry catalogued for one reason OF-COR-001 states plainly: it is a food-grade host precedent for casein expression. No value accompanies it, so it carries no extraction records.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9)',
        text: `A food-grade host precedent.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    corpusRole: 'A food-grade host precedent.',
  },
  {
    id: 'H17a',
    title:
      'US12139737B2 (Nobell Foods) — host cells comprising a recombinant casein protein and a recombinant kinase protein',
    authors: [],
    year: 0,
    venue: PATENT_VENUE,
    thread: 'H',
    sourceType: 'patent',
    organisms: [],
    topics: ['patent landscape', 'casein plus kinase host cells', 'fam20c prior art'],
    abstract:
      'Corpus entry for the patent OF-COR-001 calls the closest prior art to the cw15 strategy: host cells carrying both a recombinant casein and a recombinant kinase, with Fam20C named explicitly. Split out of the §9 H17 landscape paragraph so the claim attaches to the patent that makes it; OF-COR-001 gives no inventor names or filing year.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9 H17)',
        text: `From the patent landscape of H1 Table 4: US12139737B2 (Nobell Foods) — host cells comprising a recombinant casein protein and a recombinant kinase protein; explicitly incorporates Fam20C. The closest prior art to the cw15 strategy.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The closest prior art to the cw15 strategy.',
  },
  {
    id: 'H17b',
    title:
      'WO2023092005A1 and WO2023197002A2 (Mozza Foods) — phosphorylation of proteins in plants',
    authors: [],
    year: 0,
    venue: PATENT_VENUE,
    thread: 'H',
    sourceType: 'patent',
    organisms: [],
    topics: ['patent landscape', 'phosphorylation in plants'],
    abstract:
      'Corpus entry for the two Mozza Foods applications on phosphorylating proteins in plants, split out of the §9 H17 landscape paragraph. OF-COR-001 states the subject only, with no value, inventor list or year, so the entry carries no records.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9 H17)',
        text: `From the patent landscape of H1 Table 4: WO2023092005A1 and WO2023197002A2 (Mozza Foods) — phosphorylation of proteins in plants.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 3,
  },
  {
    id: 'H17c',
    title:
      'WO2024013749A1 (Imagene Foods) — functional milk proteins in plant cells co-expressed with at least one kinase',
    authors: [],
    year: 0,
    venue: PATENT_VENUE,
    thread: 'H',
    sourceType: 'patent',
    organisms: [],
    topics: ['patent landscape', 'plant cell milk proteins', 'kinase co-expression'],
    abstract:
      'Corpus entry for the Imagene Foods application claiming functional milk proteins in plant cells with at least one co-expressed kinase, split out of the §9 H17 landscape paragraph. The kinase is left unnamed in OF-COR-001, so no kinase_identity record is created for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9 H17)',
        text: `From the patent landscape of H1 Table 4: WO2024013749A1 (Imagene Foods) — functional milk proteins in plant cells co-expressed with at least one kinase.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 3,
  },
  {
    id: 'H17d',
    title:
      'US12077798B2 (Nobell Foods) — transgenic plants stably expressing recombinant fusion milk proteins',
    authors: [],
    year: 0,
    venue: PATENT_VENUE,
    thread: 'H',
    sourceType: 'patent',
    organisms: [],
    topics: ['patent landscape', 'transgenic plants', 'expression threshold claim'],
    abstract:
      'Corpus entry for the one patent in the §9 H17 landscape that states an expression number: recombinant fusion milk proteins at or above 1% of total soluble protein in transgenic plants. Split out so that threshold sits on the patent that claims it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9 H17)',
        text: `From the patent landscape of H1 Table 4: US12077798B2 (Nobell Foods) — transgenic plants stably expressing recombinant fusion milk proteins at ≥1% of total soluble protein.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
  },
  {
    id: 'H17e',
    title:
      'WO2024015365A1 (Kiverdi) — recombinant food proteins in chemoautotrophic microorganisms',
    authors: [],
    year: 0,
    venue: PATENT_VENUE,
    thread: 'H',
    sourceType: 'patent',
    organisms: [],
    topics: ['patent landscape', 'chemoautotrophic hosts', 'algal claim'],
    abstract:
      'Corpus entry for the only document in the entire corpus that mentions algae as a casein host, and it does so generically in a host list rather than with data. It is the whitespace argument for the cw15 programme, stated as prior art.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9 H17)',
        text: `From the patent landscape of H1 Table 4: WO2024015365A1 (Kiverdi) — recombinant food proteins in chemoautotrophic microorganisms, host list includes algae; the only algal claim found.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The only algal claim found.',
  },
  {
    id: 'H17f',
    title: 'US12359212 — recombinant micelle and in vivo assembly',
    authors: [],
    year: 0,
    venue: PATENT_VENUE,
    thread: 'H',
    sourceType: 'patent',
    organisms: ['bovine'],
    topics: ['patent landscape', 'recombinant micelle', 'btfam20c co-infiltration'],
    abstract:
      'Corpus entry for the patent that pairs a casein with a bovine FAM20C construct in planta — the closest published statement of the co-expression architecture the cw15 programme is considering. Split out of the §9 H17 landscape paragraph.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §9 H17)',
        text: `From the patent landscape of H1 Table 4: US12359212 — recombinant micelle and in vivo assembly; co-infiltration of N. benthamiana with bovine κ-casein (pMOZ700) and BtFam20C (pMOZ14) constructs.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 3,
  },
];

export const RECORDS_H: ExtractionRecord[] = [
  // ── H1 — the benchmark tables. A review reciting other groups' numbers,
  //    so every record here is isPrimary: false (OF-COR-001 §19). ─────────
  {
    id: 'r-H1-1',
    paperId: 'H1',
    sectionId: 's1',
    quote: 'Table 2 — 5 yeast studies, expression 0.6 mg/L to 1 g/L',
    field: 'titer_intracellular',
    value: 500.3,
    unit: 'mg L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: false,
    range: { low: 0.6, high: 1000 },
    curationRef: '§9 H1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H1 — the span across five tabulated yeast studies, not one measurement; value is the midpoint of a three-order-of-magnitude range and should not be read as a central estimate. The review does not say whether the figures are intracellular or secreted; filed as intracellular at reduced confidence. isPrimary false: these are other groups’ measurements. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H1-2',
    paperId: 'H1',
    sectionId: 's1',
    quote: 'potato 0.01%',
    field: 'expression_pct_tsp',
    value: 0.01,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: false,
    citesRecordId: 'r-H15-3',
    curationRef: '§9 H1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H1 Table 3 — a citation of the H15 potato measurement, not an independent one; excluded from aggregates via isPrimary. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H1-3',
    paperId: 'H1',
    sectionId: 's1',
    quote: 'soybean 0.1–0.4%',
    field: 'expression_pct_tsp',
    value: 0.25,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: false,
    citesRecordId: 'r-H15-1',
    range: { low: 0.1, high: 0.4 },
    curationRef: '§9 H1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H1 Table 3 — a citation of the H15 soybean measurement; value is the midpoint of the stated range. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H1-4',
    paperId: 'H1',
    sectionId: 's1',
    quote: 'soybean 0.1–0.4%, not phosphorylated',
    field: 'phosphorylation_degree',
    value: 0,
    unit: '% of native sites',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: false,
    citesRecordId: 'r-H15-2',
    method: 'undetermined',
    negativeResult: true,
    curationRef: '§9 H1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H1 Table 3 — a reported negative, not an unperformed analysis. The review does not name the method behind the soybean row, so method is undetermined here even though H15 records MALDI-MS. Pending verification against source',
      },
    ],
  },

  // ── H2 — the titer ceiling for phosphorylated casein, and CK2 ─────────
  {
    id: 'r-H2-1',
    paperId: 'H2',
    sectionId: 's1',
    quote: 'phosphorylated recombinant human β-casein at 500 mg/L',
    field: 'titer_intracellular',
    value: 500,
    unit: 'mg L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'ecoli',
    isPrimary: true,
    curationRef: '§9 H2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H2 — filed as intracellular: the host is E. coli, which has no secretory compartment. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H2-2',
    paperId: 'H2',
    sectionId: 's1',
    quote:
      'Polycistronic construct encoding human β-casein with both α and β subunits of human CK2',
    field: 'kinase_identity',
    value: 'CK2',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'ecoli',
    isPrimary: true,
    method: 'LC-ESI-MS',
    curationRef: '§9 H2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H2 — human CK2, both α and β subunits, co-expressed polycistronically; phosphorylation characterized by negative-ion LC-ESI-MS. Pending verification against source',
      },
    ],
  },

  // ── H3 — the same kinase against a bovine sequence ────────────────────
  {
    id: 'r-H3-1',
    paperId: 'H3',
    sectionId: 's1',
    quote: 'Yield 200 mg/L',
    field: 'titer_intracellular',
    value: 200,
    unit: 'mg L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'ecoli',
    isPrimary: true,
    curationRef: '§9 H3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H3 — filed as intracellular: the host is E. coli, which has no secretory compartment. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H3-2',
    paperId: 'H3',
    sectionId: 's1',
    quote:
      'Bovine β-casein co-expressed with CK2 achieved much lower phosphorylation than the native 5P state',
    field: 'kinase_identity',
    value: 'CK2 (partial phosphorylation of bovine β-casein)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'ecoli',
    isPrimary: true,
    method: 'LC-ESI-MS',
    curationRef: '§9 H3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H3 — the curation note states partial phosphorylation by infusion MS of purified phosphopeptides but gives no percentage, so no phosphorylation_degree record is created; the shortfall against the native 5P state is carried in the kinase value. Pending verification against source',
      },
    ],
  },

  // ── H4 — the closest eukaryotic precedent ─────────────────────────────
  {
    id: 'r-H4-1',
    paperId: 'H4',
    sectionId: 's1',
    quote: 'approximately 15–18% of total soluble protein',
    field: 'expression_pct_tsp',
    value: 16.5,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'gs115',
    isPrimary: true,
    range: { low: 15, high: 18 },
    curationRef: '§9 H4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H4 — stated as a range; value is the midpoint. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H4-2',
    paperId: 'H4',
    sectionId: 's1',
    quote: 'corresponding to 0.7–1.0 g/L',
    field: 'titer_intracellular',
    value: 0.85,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'gs115',
    isPrimary: true,
    range: { low: 0.7, high: 1.0 },
    curationRef: '§9 H4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H4 — stated as a range; value is the midpoint. The paper supplies both this and the %TSP figure, which is why it is the one entry where the two are linked; ontology Rule 2 still forbids converting between them elsewhere. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H4-3',
    paperId: 'H4',
    sectionId: 's1',
    quote: 'secreted protein reached only 0.005% of the intracellular level',
    field: 'secreted_fraction',
    value: 0.005,
    unit: '% of total expressed',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'gs115',
    isPrimary: true,
    curationRef: '§9 H4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H4 — the note expresses this as a percentage of the INTRACELLULAR level rather than of total expressed protein; at 0.005% the two denominators are indistinguishable, but the wording should be checked against the paper. The construct used the native bovine signal peptide, which the yeast did not read. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H4-4',
    paperId: 'H4',
    sectionId: 's1',
    quote: 'carried the same degree of phosphorylation as animal-derived β-casein',
    field: 'phosphorylation_degree',
    value: 100,
    unit: '% of native sites',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'gs115',
    isPrimary: true,
    method: 'urea-PAGE + phosphatase',
    comparativeBaseline: 'animal-derived bovine β-casein',
    curationRef: '§9 H4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H4 — parity with animal-derived protein recorded as 100% of native sites; the claim is comparative, established by phosphatase treatment plus urea-PAGE, not by site-level mass spectrometry. Which enzyme did it is not stated anywhere in the corpus. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H4-5',
    paperId: 'H4',
    sectionId: 's1',
    quote: 'The protein was N-glycosylated with mannan',
    field: 'glycan_species',
    value: 'mannan',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'gs115',
    isPrimary: true,
    method: 'undetermined',
    curationRef: '§9 H4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H4 — the glycan is stated, the analysis behind it is not, so method is undetermined. β-casein is not natively glycosylated, so this is host-added and a product risk. Pending verification against source',
      },
    ],
  },

  // ── H5 ────────────────────────────────────────────────────────────────
  {
    id: 'r-H5-1',
    paperId: 'H5',
    sectionId: 's1',
    quote: 'Reported at 1 g/L',
    field: 'titer_intracellular',
    value: 1,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H5 — the document gives the figure with no host and no compartment; filed as intracellular at reduced confidence, and it is the upper end of the yeast span H1 Table 2 reports. Pending verification against source',
      },
    ],
  },

  // ── H7 — the S. cerevisiae secreted fraction ──────────────────────────
  {
    id: 'r-H7-1',
    paperId: 'H7',
    sectionId: 's1',
    quote: '10 mg/L',
    field: 'titer_intracellular',
    value: 10,
    unit: 'mg L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H7 — the note gives the figure without a compartment; the accompanying 5–10% secreted fraction is what makes intracellular the better reading, but it is a reading, hence reduced confidence. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H7-2',
    paperId: 'H7',
    sectionId: 's1',
    quote: 'only 5–10% of total expressed casein reached the extracellular medium',
    field: 'secreted_fraction',
    value: 7.5,
    unit: '% of total expressed',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    range: { low: 5, high: 10 },
    curationRef: '§9 H7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H7 — stated as a range; value is the midpoint. Three orders of magnitude above the P. pastoris figure in H4, which is the comparison that matters. Pending verification against source',
      },
    ],
  },

  // ── H8 — the kinase screen, the FAM20C failure, the phosphomimetic ────
  {
    id: 'r-H8-1',
    paperId: 'H8',
    sectionId: 's1',
    quote:
      'three prokaryotic Hanks-type Ser/Thr kinases from Bacillus subtilis (PrkC, PrkD, YabT)',
    field: 'kinase_identity',
    value: 'PrkC',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — one of five kinases screened for S-x-E/pS specificity; the note does not say which of them succeeded. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H8-2',
    paperId: 'H8',
    sectionId: 's1',
    quote:
      'three prokaryotic Hanks-type Ser/Thr kinases from Bacillus subtilis (PrkC, PrkD, YabT)',
    field: 'kinase_identity',
    value: 'PrkD',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — one of five kinases screened for S-x-E/pS specificity. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H8-3',
    paperId: 'H8',
    sectionId: 's1',
    quote:
      'three prokaryotic Hanks-type Ser/Thr kinases from Bacillus subtilis (PrkC, PrkD, YabT)',
    field: 'kinase_identity',
    value: 'YabT',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — one of five kinases screened for S-x-E/pS specificity. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H8-4',
    paperId: 'H8',
    sectionId: 's1',
    quote: 'eukaryotic FAM20C from human and bovine',
    field: 'kinase_identity',
    value: 'FAM20C (human)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — screened as one of the five, and the version that could not be expressed in E. coli (see r-H8-6). Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H8-5',
    paperId: 'H8',
    sectionId: 's1',
    quote: 'eukaryotic FAM20C from human and bovine',
    field: 'kinase_identity',
    value: 'FAM20C (bovine)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    isPrimary: true,
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — the bovine ortholog, screened alongside the human one. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H8-6',
    paperId: 'H8',
    sectionId: 's1',
    quote: 'Attempts to express both FAM20C versions in E. coli failed',
    field: 'kinase_identity',
    value: 'none — FAM20C not expressible in E. coli',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'ecoli',
    isPrimary: true,
    method: 'undetermined',
    negativeResult: true,
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — a reported negative, not an unattempted experiment: both human and bovine FAM20C failed to express, and successful human FAM20C expression is reported to date only in human cell lines. This is the record the eukaryotic-host argument rests on. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H8-7',
    paperId: 'H8',
    sectionId: 's1',
    quote: 'all eight phosphoserine sites of αs1-casein variant B substituted with aspartate',
    field: 'phosphate_count',
    value: 8,
    unit: 'mol mol⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'αs1-casein variant B',
    isPrimary: true,
    method: 'undetermined',
    curationRef: '§9 H8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H8 — eight is the phosphoserine SITE count of αs1-casein variant B, all of which were replaced by aspartate in the phosphomimetic construct; the phosphomimetic protein itself carries no phosphate. The note names no analysis behind the site count, so method is undetermined. Pending verification against source',
      },
    ],
  },

  // ── H12 — a reported negative, distinct from "never analysed" ─────────
  {
    id: 'r-H12-1',
    paperId: 'H12',
    sectionId: 's1',
    quote: 'Not phosphorylated',
    field: 'phosphorylation_degree',
    value: 0,
    unit: '% of native sites',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'ecoli',
    isPrimary: true,
    method: 'undetermined',
    negativeResult: true,
    curationRef: '§9 H12',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H12 — measurement of absence, not absence of measurement; the corpus document names no method for it. Pending verification against source',
      },
    ],
  },

  // ── H13 — the only fact the entry states is in its title ──────────────
  {
    id: 'r-H13-1',
    paperId: 'H13',
    sectionId: 's1',
    quote: 'recombinant non-phosphorylated human β-casein',
    field: 'phosphorylation_degree',
    value: 0,
    unit: '% of native sites',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'undetermined',
    negativeResult: true,
    curationRef: '§9 H13',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H13 — taken from the entry title rather than from curation prose, since the document supplies none; recorded at reduced confidence for that reason. Pending verification against source',
      },
    ],
  },

  // ── H14 — the bacterial titer ceiling ─────────────────────────────────
  {
    id: 'r-H14-1',
    paperId: 'H14',
    sectionId: 's1',
    quote: '1.45 g/L',
    field: 'titer_intracellular',
    value: 1.45,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H14',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H14 — the highest bacterial casein titer in the corpus. The document names neither the host strain nor the compartment; filed as intracellular at reduced confidence on the ground that the note calls it bacterial. Pending verification against source',
      },
    ],
  },

  // ── H15 — both plant studies in the entire prior art ──────────────────
  {
    id: 'r-H15-1',
    paperId: 'H15',
    sectionId: 's1',
    quote: 'Bovine β-casein in soybean (Glycine max), 0.1–0.4% of total soluble protein',
    field: 'expression_pct_tsp',
    value: 0.25,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    range: { low: 0.1, high: 0.4 },
    curationRef: '§9 H15',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H15 — stated as a range; value is the midpoint. The measurement H1 Table 3 recites. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H15-2',
    paperId: 'H15',
    sectionId: 's1',
    quote: 'not phosphorylated by MALDI-MS',
    field: 'phosphorylation_degree',
    value: 0,
    unit: '% of native sites',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'MALDI-MS',
    negativeResult: true,
    curationRef: '§9 H15',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H15 — a reported negative with the method named, which is what distinguishes it from the bacterial rows H1 records as undetermined. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H15-3',
    paperId: 'H15',
    sectionId: 's1',
    quote: 'human β-casein in Solanum tuberosum, 0.01%',
    field: 'expression_pct_tsp',
    value: 0.01,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H15',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H15 — the potato figure H1 Table 3 recites; the note reports the product migrating as a single band about 1–1.5 kDa smaller than the phosphorylated control, which the corpus does not convert into a phosphorylation value. Pending verification against source',
      },
    ],
  },

  // ── H17 — the patent landscape ────────────────────────────────────────
  {
    id: 'r-H17a-1',
    paperId: 'H17a',
    sectionId: 's1',
    quote: 'explicitly incorporates Fam20C',
    field: 'kinase_identity',
    value: 'FAM20C',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H17',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H17 — a patent claim, not a measurement: host cells comprising a recombinant casein and a recombinant kinase, with Fam20C named. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H17d-1',
    paperId: 'H17d',
    sectionId: 's1',
    quote: 'recombinant fusion milk proteins at ≥1% of total soluble protein',
    field: 'expression_pct_tsp',
    value: 1,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    curationRef: '§9 H17',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H17 — a claimed lower bound (≥1%), not a measured point value, and asserted in a patent rather than a peer-reviewed result; no range is set because the document gives no upper end. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-H17f-1',
    paperId: 'H17f',
    sectionId: 's1',
    quote:
      'co-infiltration of N. benthamiana with bovine κ-casein (pMOZ700) and BtFam20C (pMOZ14) constructs',
    field: 'kinase_identity',
    value: 'FAM20C (bovine, BtFam20C)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'pMOZ14',
    isPrimary: true,
    curationRef: '§9 H17',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §9 H17 — the bovine FAM20C construct co-infiltrated with κ-casein; the closest published statement of the co-expression architecture this programme is considering. Pending verification against source',
      },
    ],
  },
];
