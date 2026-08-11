// openFerment corpus — Thread E (the molecule: β-casein structure and assembly)
// and Thread F (the gene: CSN2).
//
// REAL LITERATURE. Every title, author string, year, venue, DOI and PMCID in
// this file is transcribed from docs/OF-COR-001.md §6 and §7. Nothing is
// invented — where the corpus document gives no authors or no year, this file
// carries an empty author list and year 0 rather than a guess.
//
// The full texts have NOT been ingested. Each paper therefore carries exactly
// one section — the curator's note from OF-COR-001, in the curator's words,
// about the paper. `textSource: 'curation-note'` and `ingest: 'catalogued'` say
// so, and the reader labels it. No sentence in `sections[].text` is the paper's
// own prose, and every `quote` is a span of the curator's note rather than a
// source span. Records are provenance 'curated' and status 'unverified': the
// claim is real and attributable, but nothing here has yet been checked against
// the source PDF.
//
// Deliberate omissions, recorded so a reviewer does not mistake them for misses:
//
//   * E3 (209 aa; 23,946–24,097 Da; 15–60 molecules per micelle; CMC 0.05–0.2%),
//     F1 (10,338 bp; nine exons; 224-aa precursor; 209-residue mature protein;
//     fifteen variants) and F3 (35 of 209 residues proline) state real numbers
//     for which ontology v1 has no field. Residue counts, molecular masses,
//     aggregation numbers, gene lengths and critical micelle concentrations are
//     not among the 24 fields, and forcing them into a neighbouring field would
//     corrupt the field rather than capture the number. They stay in the section
//     text, where the reader can see them, and out of the record set.
//   * Codon 67 (F1, F2, F3) is NOT recorded as `phospho_site_position`. That
//     field means "residue index of a phosphorylation site"; position 67 is the
//     A1/A2 Pro→His SNP, not a phospho-site. Recording it would put a false
//     phospho-site into the very field OF-COR-001 §19 flags as the numbering
//     trap. There are consequently no `phospho_site_position` records here.
import type { Paper, ExtractionRecord } from '../types';

const VENUE_UNSTATED = '(venue not stated in OF-COR-001)';

export const PAPERS_EF: Paper[] = [
  // ── Thread E — the molecule: β-casein structure and assembly (§6) ─────
  {
    id: 'E1',
    title: 'Bovine β-casein: Isolation, properties and functionality. A review',
    authors: ['Atamer Z', 'Post AE', 'Schubert T', 'Holder A', 'Boom RM', 'Hinrichs J'],
    year: 2017,
    venue: 'Int Dairy J',
    doi: '10.1016/j.idairyj.2016.11.010',
    thread: 'E',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: [
      'reference values',
      'milk composition',
      'isoelectric precipitation',
      'fractionation',
    ],
    abstract:
      'Corpus entry for the β-casein review OF-COR-001 treats as its reference-value source: the milk concentration, the isoelectric pH and the casein share of milk protein that every recombinant target number is compared against. This is the curator’s summary of why the entry is in the corpus, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `Casein is ~80% of total bovine milk protein; β-casein is present at roughly 2.6 g/L; caseins are heat-stable but precipitate readily at their isoelectric point, pH 4.65, on acidification. Reviews fractionation technologies at technical scale. The single most useful reference-value source in the thread.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The single most useful reference-value source in the thread.',
  },
  {
    id: 'E2',
    title:
      'Are casein micelles extracellular condensates formed by liquid–liquid phase separation?',
    authors: ['Horvath A', 'et al.'],
    year: 2022,
    venue: 'FEBS Lett',
    doi: '10.1002/1873-3468.14449',
    thread: 'E',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['casein micelle', 'micelle geometry', 'liquid–liquid phase separation'],
    abstract:
      'Corpus entry for the paper OF-COR-001 nominates as the target specification for an assembled casein micelle — its size, its molecular count and its calcium phosphate nanoclusters. Summarised by the curator from the corpus document; the full text has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `Native casein micelle geometry: approximately spherical, radius ~70 nm, containing on the order of 10,000 casein molecules, with caseins bound to amorphous calcium phosphate nanoclusters and retaining hydration and conformational flexibility upon self-assembly. The target specification.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The target specification.',
  },
  {
    id: 'E3',
    title: 'Micellization of bovine β-casein',
    authors: ['Portnaya I', 'et al.'],
    year: 2006,
    venue: 'J Agric Food Chem',
    thread: 'E',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['micellization', 'critical micelle concentration', 'amphipathicity'],
    abstract:
      'Corpus entry for the physical-chemistry description of β-casein self-assembly: chain length, mass range, aggregation number and critical micelle concentration. Catalogued from the curation note; ontology v1 has no field for any of those quantities, so the entry carries text but no extraction records.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `209 amino acids; molecular mass 23,946–24,097 Da depending on genetic variant; the most hydrophobic casein by virtue of a large hydrophobic C-terminal domain, but strongly amphipathic because of a highly charged N-terminal domain carrying the phosphate center; self-assembles into micelles of roughly 15–60 molecules with a critical micelle concentration around 0.05–0.2% depending on temperature, pH, solvent composition and ionic strength.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'E4',
    title: "Nomenclature of the proteins of cows' milk — sixth revision",
    authors: ['Farrell HM Jr', 'et al.'],
    year: 2004,
    venue: 'J Dairy Sci',
    thread: 'E',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: ['nomenclature', 'casein variants', 'naming authority'],
    abstract:
      'Corpus entry for the milk-protein nomenclature revision OF-COR-001 designates as the naming and variant authority for the whole casein programme. The corpus document records one line about it, reproduced here as the curator’s note.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `The naming and variant authority.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    corpusRole: 'The naming and variant authority.',
  },
  {
    id: 'E5',
    title:
      'Caseins and the casein micelle: their biological functions, structures, and behavior in foods',
    authors: ['Holt C', 'Carver JA', 'Ecroyd H', 'Thorn DC'],
    year: 2013,
    venue: 'J Dairy Sci',
    thread: 'E',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: ['casein micelle', 'structure', 'behaviour in foods'],
    abstract:
      'Corpus entry E5: a review of casein and casein-micelle biology, structure and food behaviour. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `OF-COR-001 §6 lists this entry with authors, title, journal, volume and page range only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'E6',
    title:
      'Implications of kappa-casein evolutionary diversity for the self-assembly and aggregation of casein micelles',
    authors: ['Manguy J', 'Shields DC'],
    year: 2019,
    venue: 'R Soc Open Sci',
    doi: '10.1098/rsos.190939',
    pmcid: 'PMC6837221',
    thread: 'E',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['kappa-casein', 'intrinsic disorder', 'amyloid fibrils', 'micelle assembly'],
    abstract:
      'Corpus entry for the evolutionary and structural account of why caseins need a micelle at all: disorder inside, κ-casein at the surface, and the two failure modes — fibrils and calcium precipitation — that assembly prevents. Curator’s summary; the full text has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `Caseins in a micelle are substantially disordered — no fixed structure, free movement while the micelle keeps overall shape. α- and β-caseins sit mostly inside and bind calcium phosphate; κ-casein sits mostly at the surface. Alone at high concentration, caseins can form insoluble amyloid fibrils, and calcium at milk concentrations would precipitate; micelle formation prevents both.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
  },
  {
    id: 'E7',
    title:
      'Aggregation Behavior of Bovine κ- and β-Casein Studied with SANS, Light Scattering, and Cryo-TEM',
    authors: ['de Kruif CG', 'Huppertz T', 'et al.'],
    year: 2012,
    venue: 'Langmuir',
    doi: '10.1021/la302416p',
    thread: 'E',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['amyloid fibrils', 'calcium phosphate sequestration', 'micelle growth control'],
    abstract:
      'Corpus entry for the scattering and microscopy study of how κ- and β-casein aggregate: κ fibrillates, β inhibits it, and the calcium-sensitive caseins sequester calcium phosphate while κ caps micelle growth. Curator’s summary of why the entry is in the corpus, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `κ-casein forms amyloid-like fibrils at 25 °C under agitation; β-casein inhibits that fibrillation. Calcium-sensitive caseins sequester amorphous calcium phosphate in nanometer clusters while calcium-insensitive κ-casein limits micelle growth.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'E8',
    title: 'Self-Assembly of Bovine β-Casein below the Isoelectric pH',
    authors: [],
    year: 0,
    venue: 'J Agric Food Chem',
    doi: '10.1021/jf072630r',
    thread: 'E',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['saxs', 'premolten globule', 'disk micelles', 'low-pH self-assembly'],
    abstract:
      'Corpus entry E8: a SAXS study of β-casein self-assembly below its isoelectric pH, where the monomer is a premolten globule and the micelles are disk-shaped. OF-COR-001 gives no author string and no year for it; the DOI is the authoritative key.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `SAXS below the CMC indicates the monomer is in a premolten globule state at low pH; net charge is similarly high at acidic and neutral pH but charge distribution along the backbone differs considerably, producing disk micelles above the CMC at low pH.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'E9',
    title: 'Structural and dynamic characterization of intrinsically disordered β-casein',
    authors: [],
    year: 0,
    venue: 'Biophys J; Russ J Bioorg Chem',
    thread: 'E',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: [
      'intrinsic disorder',
      'neutron spectroscopy',
      'secondary structure',
      'success criterion',
    ],
    abstract:
      'Corpus entry E9: a composite of two structural studies of intrinsically disordered β-casein, gathered by OF-COR-001 under one heading with no single author string or year. It is here for the criterion it forces — for a disordered protein, "correct fold" is not the test.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §6)',
        text: `This entry gathers two studies. Nanosecond structural dynamics of intrinsically disordered β-casein micelles by neutron spectroscopy (Biophys J, 2021) — self-association does not reduce monomer chain flexibility. Self-assembly and secondary structure of beta-casein (Russ J Bioorg Chem, 2013) — micellization involves few residues in transition and is not driven by a large secondary-structure change. Because β-casein is intrinsically disordered, the usual recombinant-protein success criterion (correct fold) does not apply; the criterion is correct phosphorylation and assembly behavior.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
    corpusRole:
      'Because β-casein is intrinsically disordered, the usual recombinant-protein success criterion (correct fold) does not apply; the criterion is correct phosphorylation and assembly behavior.',
  },

  // ── Thread F — the gene: CSN2 (§7) ────────────────────────────────────
  {
    id: 'F1',
    title:
      'Does a Little Difference Make a Big Difference? Bovine β-Casein A1 and A2 Variants and Human Health — An Update',
    authors: [
      'Cieślińska A',
      'Fiedorowicz E',
      'Rozmus D',
      'Sienkiewicz-Szłapka E',
      'Jarmołowska B',
      'Kamiński S',
    ],
    year: 2022,
    venue: 'Int J Mol Sci',
    doi: '10.3390/ijms232415637',
    pmcid: 'PMC9779325',
    thread: 'F',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: ['csn2 architecture', 'a1/a2 variants', 'signal peptide', 'construct design'],
    abstract:
      'Corpus entry for the CSN2 architecture review: the gene, its exon structure, the 224-residue precursor and the 209-residue mature protein, and the codon-67 SNP that splits A1 from A2. Catalogued for the construct-design consequence OF-COR-001 draws from it; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §7)',
        text: `Bovine CSN2 spans 10,338 bp on chromosome 6, comprises nine exons and eight introns (GenBank M55158.1). The primary translation product is 224 amino acids (GenBank AAA30431.1) including a signal peptide removed during processing, giving a 209-residue mature protein. Fifteen coding-region variants are reported; most mutations fall in exon 7; variants classify as A2-type (10 variants, Pro67) or A1-type (5 variants, His67) by a single SNP at codon 67. Design consequence: the native 15-residue bovine signal peptide must be removed and replaced with an algal SP.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'Design consequence: the native 15-residue bovine signal peptide must be removed and replaced with an algal SP.',
  },
  {
    id: 'F2',
    title: 'A1/A2 variant selection evidence',
    authors: [],
    year: 2022,
    venue: 'bioRxiv',
    doi: '10.1101/2022.08.25.505361',
    thread: 'F',
    sourceType: 'preprint',
    organisms: ['bovine'],
    topics: ['a1/a2 selection', 'β-casomorphin-7', 'cheesemaking trade-off'],
    abstract:
      'Corpus entry F2: the evidence base OF-COR-001 assembles for choosing between the A1 and A2 variants, drawn from a 2022 bioRxiv preprint and two PMC sources. It is catalogued because the choice is a product decision with a stated cost, not because of any single measurement.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §7)',
        text: `The A1/A2 difference is a proline→histidine substitution at position 67 from a single nucleotide change; A2 is ancestral and A1 derived, with A1 at highest frequency in modern Holstein-Friesians; proteolytic cleavage at position 67 in A1 releases the seven-residue opioid peptide β-casomorphin-7 (Tyr-Pro-Phe-Pro-Gly-Pro-Ile), which A2 does not release. A1 is reported to improve curd consistency, milk coagulation, and micelle size relative to A2 — so choosing A2 is a marketing-and-health-positioning decision that costs cheesemaking performance. Sources: bioRxiv 2022 DOI 10.1101/2022.08.25.505361; PMC7070732; PMC12285589.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'Choosing A2 is a marketing-and-health-positioning decision that costs cheesemaking performance.',
  },
  {
    id: 'F3',
    title: 'Frequency of β-Casein Gene Polymorphisms in Jersey Cows in Western Japan',
    authors: [],
    year: 0,
    venue: VENUE_UNSTATED,
    pmcid: 'PMC9404981',
    thread: 'F',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['proline content', 'polymorphism frequency', 'codon optimization'],
    abstract:
      'Corpus entry F3: a polymorphism-frequency survey OF-COR-001 keeps for one structural fact — how much of the mature β-casein chain is proline, and what that implies for expressing it in a GC-rich algal host. OF-COR-001 gives no author string, venue or year; the PMCID is the authoritative key.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §7)',
        text: `Records that 35 of the 209 residues in the A2 variant are proline — a cyclic residue that complicates secondary structure formation, and the structural reason digestive enzymes cannot cleave at position 67 when proline is present. Proline content this high is a codon-optimization problem in a 68%-GC-coding-region host.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'Proline content this high is a codon-optimization problem in a 68%-GC-coding-region host.',
  },
  {
    id: 'F4',
    title:
      'Associations Between Polymorphisms of the CSN1S1, CSN1S2, CSN2 and CSN3 Genes and Milk Composition Traits in Holstein Cattle',
    authors: [],
    year: 0,
    venue: VENUE_UNSTATED,
    pmcid: 'PMC11970297',
    thread: 'F',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['casein proportions', 'kappa-casein', 'micelle composition'],
    abstract:
      'Corpus entry F4: the source of the casein-proportion reference values, and of the argument that a β-casein-only product cannot form a stable micelle without a calcium-insensitive κ-casein to cap growth. Curator’s summary; OF-COR-001 gives no author string, venue or year.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §7)',
        text: `Casein proportions: αs1 ≈ 38% of total caseins, β ≈ 36%, κ ≈ 13%, αs2 ≈ 10%. κ-casein is 169 residues, ~13 kb gene, 14 variants. If the product is an artificial casein micelle, β-casein alone is insufficient — a calcium-insensitive κ-casein is required to cap growth.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'If the product is an artificial casein micelle, β-casein alone is insufficient — a calcium-insensitive κ-casein is required to cap growth.',
  },
  {
    id: 'F5',
    title: 'UniProt accessions and phosphorylation-site distribution',
    authors: [],
    year: 2026,
    venue: 'UniProt (corpus reference entry, OF-COR-001 §7)',
    thread: 'F',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: [
      'phosphate distribution',
      'uniprot accessions',
      'success criterion',
      'phosphoserine clusters',
    ],
    abstract:
      'Not a publication: this is the corpus’s reference entry pinning the four bovine casein accessions to their phosphate counts, and stating the programme’s success criterion as a number — 5 phosphates on β-casein, clustered at the N-terminus. It carries the phosphate_count records the rest of the platform compares against.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §7)',
        text: `P02662 (αs1), P02663 (αs2), P02666 (β-casein), P02668 (κ). Phosphate distribution: αs1 ≈ 8 phosphates concentrated centrally; αs2 ≈ 10–13; β-casein ≈ 5 phosphates concentrated at the N-terminus; κ typically 1–3 near the C-terminus, and uniquely can be phosphorylated on threonine as well as serine. The success criterion stated numerically: "fully phosphorylated β-casein" means 5P, N-terminally clustered.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'The success criterion stated numerically: "fully phosphorylated β-casein" means 5P, N-terminally clustered.',
  },
];

export const RECORDS_EF: ExtractionRecord[] = [
  // ── E1 — the bovine reference values ──────────────────────────────────
  {
    id: 'r-E1-1',
    paperId: 'E1',
    sectionId: 's1',
    quote: 'β-casein is present at roughly 2.6 g/L',
    field: 'titer_secreted',
    value: 2.6,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'β-casein in bovine milk',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§6 E1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §6 E1 — native concentration in bovine milk, i.e. the reference the recombinant secreted titers are compared against, not a recombinant titer; pending verification against source',
      },
    ],
  },
  {
    id: 'r-E1-2',
    paperId: 'E1',
    sectionId: 's1',
    quote: 'precipitate readily at their isoelectric point, pH 4.65, on acidification',
    field: 'gelation_ph',
    value: 4.65,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'casein, isoelectric precipitation on acidification',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§6 E1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §6 E1 — the source states an isoelectric precipitation pH on acidification; ontology v1 carries acid destabilisation pH under gelation_ph. OF-COR-001 names no analytical method, so method is undetermined. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-E1-3',
    paperId: 'E1',
    sectionId: 's1',
    quote: 'Casein is ~80% of total bovine milk protein',
    field: 'expression_pct_tsp',
    value: 80,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'total casein, as % of total bovine milk protein',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§6 E1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §6 E1 — a native protein share of bovine milk protein, not a recombinant expression level; the denominator is carried in componentTag because it is not the total soluble protein of a host. 80 sits above the ontology range for expression_pct_tsp (0.001–40), which is the ontology correctly signalling that no host expresses at this share; the value is a reference composition, so the range warning is expected rather than a transcription error. Pending verification against source',
      },
    ],
  },

  // ── E2 — the target micelle specification ─────────────────────────────
  {
    id: 'r-E2-1',
    paperId: 'E2',
    sectionId: 's1',
    quote: 'approximately spherical, radius ~70 nm',
    field: 'micelle_diameter',
    value: 140,
    unit: 'nm',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'native bovine casein micelle',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§6 E2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §6 E2 — the source states a RADIUS of ~70 nm; micelle_diameter is a diameter field, so the value recorded is 2 × 70 = 140 nm and the quote is the radius statement it derives from. OF-COR-001 names no sizing method, so method is undetermined. Confidence 0.7 for the approximation and the derivation. Pending verification against source',
      },
    ],
  },

  // ── F4 — casein proportions (denominator: total caseins) ──────────────
  {
    id: 'r-F4-1',
    paperId: 'F4',
    sectionId: 's1',
    quote: 'αs1 ≈ 38% of total caseins',
    field: 'expression_pct_tsp',
    value: 38,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'αs1-casein, as % of total caseins',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§7 F4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F4 — native casein composition; denominator is total caseins, not total soluble protein, and is carried in componentTag. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-F4-2',
    paperId: 'F4',
    sectionId: 's1',
    quote: 'β ≈ 36%',
    field: 'expression_pct_tsp',
    value: 36,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'β-casein, as % of total caseins',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§7 F4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F4 — native casein composition; denominator is total caseins, not total soluble protein, and is carried in componentTag. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-F4-3',
    paperId: 'F4',
    sectionId: 's1',
    quote: 'κ ≈ 13%',
    field: 'expression_pct_tsp',
    value: 13,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'κ-casein, as % of total caseins',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§7 F4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F4 — native casein composition; denominator is total caseins, not total soluble protein, and is carried in componentTag. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-F4-4',
    paperId: 'F4',
    sectionId: 's1',
    quote: 'αs2 ≈ 10%',
    field: 'expression_pct_tsp',
    value: 10,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'αs2-casein, as % of total caseins',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§7 F4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F4 — native casein composition; denominator is total caseins, not total soluble protein, and is carried in componentTag. Pending verification against source',
      },
    ],
  },

  // ── F5 — phosphate counts, the numeric success criterion ──────────────
  {
    id: 'r-F5-1',
    paperId: 'F5',
    sectionId: 's1',
    quote: 'β-casein ≈ 5 phosphates concentrated at the N-terminus',
    field: 'phosphate_count',
    value: 5,
    unit: 'mol mol⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'β-casein (P02666)',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§7 F5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F5 — the native phosphate count that defines "fully phosphorylated" for this programme. OF-COR-001 names no analytical method for the accession annotation, so method is undetermined. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-F5-2',
    paperId: 'F5',
    sectionId: 's1',
    quote: 'αs1 ≈ 8 phosphates concentrated centrally',
    field: 'phosphate_count',
    value: 8,
    unit: 'mol mol⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'αs1-casein (P02662)',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§7 F5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F5 — OF-COR-001 names no analytical method for the accession annotation, so method is undetermined. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-F5-3',
    paperId: 'F5',
    sectionId: 's1',
    quote: 'αs2 ≈ 10–13',
    field: 'phosphate_count',
    value: 11.5,
    unit: 'mol mol⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'αs2-casein (P02663)',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    range: { low: 10, high: 13 },
    curationRef: '§7 F5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F5 — stated as a range 10–13; value is the midpoint and the range is carried explicitly. OF-COR-001 names no analytical method, so method is undetermined. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-F5-4',
    paperId: 'F5',
    sectionId: 's1',
    quote: 'κ typically 1–3 near the C-terminus',
    field: 'phosphate_count',
    value: 2,
    unit: 'mol mol⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    componentTag: 'κ-casein (P02668)',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    range: { low: 1, high: 3 },
    curationRef: '§7 F5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §7 F5 — stated as a range 1–3; value is the midpoint and the range is carried explicitly. κ-casein uniquely carries phospho-threonine as well as phospho-serine. OF-COR-001 names no analytical method, so method is undetermined. Pending verification against source',
      },
    ],
  },
];
