// openFerment corpus — Thread G (FAM20C biology: identity, motif, structure,
// regulation).
//
// REAL LITERATURE. Every title, author string, year, venue, DOI and PMCID in
// this file is transcribed from docs/OF-COR-001.md §8. Nothing is invented —
// where the corpus document gives no authors, `authors` is empty and
// `verifyNeeded` is set rather than a plausible name being supplied.
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
// Thread G is mechanistic rather than numeric. Most of what it establishes is
// categorical — which enzyme, which motif, which mutant is dead — so the
// records here are dominated by `kinase_identity`, and three entries (G5, G6,
// G8) carry no records at all because the corpus document states no extractable
// claim for them.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_G: Paper[] = [
  {
    id: 'G1',
    title:
      'Secreted kinase phosphorylates extracellular proteins that regulate biomineralization',
    authors: [
      'Tagliabracci VS',
      'Engel JL',
      'Wen J',
      'Wiley SE',
      'Worby CA',
      'Kinch LN',
      'Xiao J',
      'Grishin NV',
      'Dixon JE',
    ],
    year: 2012,
    venue: 'Science',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: [
      'fam20c identification',
      'golgi casein kinase',
      'd478a inactive control',
      'β-casein substrate',
    ],
    abstract:
      'Corpus entry for the paper OF-COR-001 records as the identification of Fam20C as the authentic Golgi casein kinase, with recombinant β-casein as the substrate of the original demonstration. It is catalogued here because the D478A catalytically-inactive mutant it establishes is the specificity control any openFerment FAM20C construct will have to reproduce; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `The identification paper. Fam20C is the authentic Golgi casein kinase. It phosphorylated recombinant β-casein in a time-dependent manner while the catalytically inactive D478A mutant, unable to coordinate Mn²⁺, did not. Co-expression of V5-tagged αs1-casein with FLAG-tagged Fam20C in U2OS cells produced a mobility shift absent with D478A and reversed by λ-phosphatase. The substrate in the original demonstration was β-casein specifically.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'The identification paper — and the substrate in the original demonstration was β-casein specifically.',
  },
  {
    id: 'G2',
    title: 'A Single Kinase Generates the Majority of the Secreted Phosphoproteome',
    authors: ['Tagliabracci VS', 'et al.'],
    year: 2015,
    venue: 'Cell',
    doi: '10.1016/j.cell.2015.04.028',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['s-x-e motif', 'secreted phosphoproteome', 'fam20c substrates'],
    abstract:
      'Corpus entry for the paper that fixes the motif openFerment must design around: Fam20C acts on S-x-E/pS sites in secreted proteins and accounts for most of the extracellular phosphoproteome. Catalogued from the curation note; the substrate census itself has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `Fam20C phosphorylates secreted proteins within S-x-E/pS motifs, including casein, FGF23, and the SIBLING family, and generates the majority of the extracellular phosphoproteome.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'Fam20C phosphorylates secreted proteins within S-x-E/pS motifs and generates the majority of the extracellular phosphoproteome.',
  },
  {
    id: 'G3',
    title: 'A secretory kinase complex regulates extracellular protein phosphorylation',
    authors: ['Cui J', 'Xiao J', 'Tagliabracci VS', 'Wen J', 'Rahdar M', 'Dixon JE'],
    year: 2015,
    venue: 'eLife',
    doi: '10.7554/eLife.06120',
    pmcid: 'PMC4421793',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['fam20a pseudokinase', 'allosteric activation', 'e306q mutant', 'construct design'],
    abstract:
      'Corpus entry for the paper that turns a one-gene design into a possible two-gene design: Fam20A is an allosteric activator of Fam20C, so co-expressing the kinase alone may not be enough. Summarised by the curator from OF-COR-001; the full text has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `Fam20A is a pseudokinase acting as an allosteric activator of Fam20C. The Fam20C E306Q mutant showed greatly reduced in vitro kinase activity toward casein and abolished intrinsic ATPase activity. A design warning: co-expressing Fam20C alone may be insufficient.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'A design warning: co-expressing Fam20C alone may be insufficient.',
  },
  {
    id: 'G4',
    title: 'Crystal structure of the Golgi casein kinase',
    authors: ['Xiao J', 'Tagliabracci VS', 'Wen J', 'Kim SA', 'Dixon JE'],
    year: 2013,
    venue: 'PNAS',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: [
      'kinase structure',
      'disulfide bridges',
      'n-linked glycosylation',
      'secretory pathway folding',
    ],
    abstract:
      'Corpus entry for the structural paper OF-COR-001 uses to argue that the kinase itself is a secretory-pathway protein — disulfide-bonded and N-glycosylated — and therefore cannot be folded in a bacterial cytoplasm. It is the structural half of the case for putting FAM20C in a Golgi-bearing host; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `The C. elegans ortholog structure: an atypical kinase-like fold with disulfide bridges, N-linked glycosylation, and a novel insertion domain conserved across Fam20 members. The disulfides and N-glycans mean the kinase itself must transit a secretory pathway to fold — why bacterial expression fails and why a Golgi-bearing host is credible.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'The disulfides and N-glycans mean the kinase itself must transit a secretory pathway to fold — why bacterial expression fails and why a Golgi-bearing host is credible.',
  },
  {
    id: 'G5',
    title: 'Structure and evolution of the Fam20 kinases',
    authors: ['Zhang H', 'et al.'],
    year: 2018,
    venue: 'Nat Commun',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['fam20 family', 'kinase evolution', 'open question d5'],
    abstract:
      'Corpus entry recorded by OF-COR-001 in a single line, as the priority read for closing the open D5 question of whether Chlamydomonas has a Fam20-family secretory kinase at all. It carries no extraction records because the corpus document states no extractable claim for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `Priority read for resolving D5.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'Priority read for resolving D5.',
  },
  {
    id: 'G6',
    title: 'The ABCs of the Atypical Fam20 Secretory Pathway Kinases',
    authors: ['Worby CA', 'Mayfield JE', 'Pollak AJ', 'Dixon JE', 'Banerjee S'],
    year: 2021,
    venue: 'J Biol Chem',
    pmcid: 'PMC7948968',
    thread: 'G',
    sourceType: 'review',
    organisms: [],
    topics: ['fam20 kinases', 'secretory pathway', 'background reading'],
    abstract:
      'Open-access background reading on the Fam20 kinase family, listed in OF-COR-001 §8 by citation alone. Nothing about its content has been transcribed, so it is catalogued as bibliography and carries no extraction records.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `OF-COR-001 §8 lists this entry by citation alone and records no curation prose for it. Nothing about its content has been transcribed, so there is nothing here to extract until the full text is ingested.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
  },
  {
    id: 'G7',
    title:
      'Proteolytic processing of secretory pathway kinase Fam20C by site-1 protease promotes biomineralization',
    authors: ['Chen X', 'Zhang J', 'Liu P', 'et al.'],
    year: 2021,
    venue: 'PNAS',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['site-1 protease', 'propeptide cleavage', 'golgi transmembrane form', 'construct design'],
    abstract:
      'Corpus entry for the paper behind what OF-COR-001 calls the third design fork: Fam20C sits in the Golgi as a transmembrane protein and is matured by site-1 protease, so a heterologous construct may need to be pre-cleaved. Catalogued from the curation note; the full text has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `Fam20C resides in the Golgi as a transmembrane protein; site-1 protease cleaves the propeptide and promotes secretion and activation. A third design fork: if S1P processing is required, a pre-cleaved or propeptide-free FAM20C construct may be necessary.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'A third design fork: if S1P processing is required, a pre-cleaved or propeptide-free FAM20C construct may be necessary.',
  },
  {
    id: 'G8',
    title:
      'Ancestral roles of the Fam20C family of secreted protein kinases revealed in C. elegans',
    authors: [],
    year: 2019,
    venue: 'J Cell Biol',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['fam20 evolution', 'ancestral function', 'c. elegans'],
    abstract:
      'Corpus entry listed in OF-COR-001 §8 by citation alone and marked [verify]: title, journal and year are recorded, the author string is not. It carries no extraction records because the corpus document states no claim for it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `OF-COR-001 §8 lists this entry by citation alone and marks it [verify]. No author string is given and no curation prose is recorded, so there is nothing here to extract until the entry is resolved and the full text ingested.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'G9',
    title:
      'Comprehensive Analysis of the Putative Substratome of FAM20C, the Master Serine Kinase of the Secretory Pathway',
    authors: [],
    year: 2025,
    venue: 'Not recorded in OF-COR-001',
    pmcid: 'PMC12650399',
    thread: 'G',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: [
      's/txe consensus',
      'ck1 and ck2 misnomer',
      'β(28–40) assay peptide',
      'fam20c substratome',
    ],
    abstract:
      'Corpus entry for the substratome survey OF-COR-001 mines for two things: the historical separation of CK1/CK2 from the real Golgi casein kinase, and the β(28–40) bovine β-casein peptide that gives openFerment a ready-made assay substrate for validating a FAM20C construct. Marked [verify] in the corpus document — the PMCID is the authoritative key, and no author string is recorded.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §8)',
        text: `CK1 and CK2 were named for casein but lack the correct localization and do not recognize the SxE motifs; a Golgi casein kinase activity was detected in lactating mammary gland in 1972; a synthetic peptide corresponding to a bovine β-casein phosphorylation site, β(28–40), was selectively phosphorylated by GCK but not CK1 or CK2; by 2010, 50–70% of secreted phosphosites in plasma and CSF matched the S/TxE consensus. β(28–40) is a ready-made assay substrate for validating any FAM20C construct.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'β(28–40) is a ready-made assay substrate for validating any FAM20C construct.',
  },
];

export const RECORDS_G: ExtractionRecord[] = [
  // ── G1 — the identification, and its catalytically dead control ───────
  {
    id: 'r-G1-1',
    paperId: 'G1',
    sectionId: 's1',
    quote: 'Fam20C is the authentic Golgi casein kinase',
    field: 'kinase_identity',
    value: 'FAM20C (the authentic Golgi casein kinase)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§8 G1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §8 G1 — pending verification against source',
      },
    ],
  },
  {
    id: 'r-G1-2',
    paperId: 'G1',
    sectionId: 's1',
    quote: 'the catalytically inactive D478A mutant, unable to coordinate Mn²⁺, did not',
    field: 'kinase_identity',
    value: 'none — FAM20C D478A, catalytically inactive and unable to coordinate Mn²⁺',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    negativeResult: true,
    componentTag: 'FAM20C D478A',
    curationRef: '§8 G1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G1 — the catalytically-dead specificity control; assay not named in the curation note, method recorded as undetermined; pending verification against source',
      },
    ],
  },
  {
    id: 'r-G1-3',
    paperId: 'G1',
    sectionId: 's1',
    quote: 'produced a mobility shift absent with D478A and reversed by λ-phosphatase',
    field: 'kinase_identity',
    value: 'FAM20C (αs1-casein mobility shift in U2OS cells, reversed by λ-phosphatase)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'SDS-PAGE mobility',
    curationRef: '§8 G1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §8 G1 — pending verification against source',
      },
    ],
  },

  // ── G2 — the motif ────────────────────────────────────────────────────
  {
    id: 'r-G2-1',
    paperId: 'G2',
    sectionId: 's1',
    quote: 'Fam20C phosphorylates secreted proteins within S-x-E/pS motifs',
    field: 'kinase_identity',
    value: 'FAM20C (S-x-E/pS motif specificity in secreted proteins)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§8 G2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action: 'curated from OF-COR-001 §8 G2 — pending verification against source',
      },
    ],
  },

  // ── G3 — the activator, and the dead-ATPase mutant ────────────────────
  {
    id: 'r-G3-1',
    paperId: 'G3',
    sectionId: 's1',
    quote: 'Fam20A is a pseudokinase acting as an allosteric activator of Fam20C',
    field: 'kinase_identity',
    value: 'FAM20A (pseudokinase; allosteric activator of FAM20C)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§8 G3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G3 — the two-gene design warning; pending verification against source',
      },
    ],
  },
  {
    id: 'r-G3-2',
    paperId: 'G3',
    sectionId: 's1',
    quote:
      'The Fam20C E306Q mutant showed greatly reduced in vitro kinase activity toward casein',
    field: 'kinase_identity',
    value:
      'FAM20C E306Q — greatly reduced in vitro kinase activity toward casein, intrinsic ATPase abolished',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    negativeResult: true,
    componentTag: 'FAM20C E306Q',
    curationRef: '§8 G3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G3 — "greatly reduced" is not quantified in the curation note, so confidence is held at 0.7; pending verification against source',
      },
    ],
  },

  // ── G4 — the kinase is itself a secretory-pathway glycoprotein ────────
  {
    id: 'r-G4-1',
    paperId: 'G4',
    sectionId: 's1',
    quote: 'an atypical kinase-like fold with disulfide bridges, N-linked glycosylation',
    field: 'glycan_species',
    value: 'N-linked glycosylation carried by the Fam20 kinase itself',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    componentTag: 'FAM20 kinase',
    curationRef: '§8 G4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G4 — glycan is on the kinase, not on the product; componentTag carries the distinction. Structure gives no glycan composition, so no species is recorded and method is undetermined; pending verification against source',
      },
    ],
  },

  // ── G7 — which form of the kinase is the active one ───────────────────
  {
    id: 'r-G7-1',
    paperId: 'G7',
    sectionId: 's1',
    quote: 'site-1 protease cleaves the propeptide and promotes secretion and activation',
    field: 'kinase_identity',
    value:
      'FAM20C (Golgi transmembrane form; activated by site-1 protease cleavage of the propeptide)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    curationRef: '§8 G7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G7 — bears on whether a heterologous construct must be pre-cleaved; pending verification against source',
      },
    ],
  },

  // ── G9 — CK1/CK2 are not it, and the β(28–40) assay peptide ───────────
  {
    id: 'r-G9-1',
    paperId: 'G9',
    sectionId: 's1',
    quote:
      'CK1 and CK2 were named for casein but lack the correct localization and do not recognize the SxE motifs',
    field: 'kinase_identity',
    value: 'CK1 and CK2 — wrong localization, no SxE recognition; not the Golgi casein kinase',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    negativeResult: true,
    curationRef: '§8 G9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G9 — the "casein kinase is three enzymes" trap of §19; pending verification against source',
      },
    ],
  },
  {
    id: 'r-G9-2',
    paperId: 'G9',
    sectionId: 's1',
    quote: 'was selectively phosphorylated by GCK but not CK1 or CK2',
    field: 'kinase_identity',
    value: 'GCK (Golgi casein kinase) — selective for the β(28–40) peptide over CK1 and CK2',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    curationRef: '§8 G9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G9 — the curation note names GCK, not FAM20C, for this assay; the equation of the two is G1’s claim, not this entry’s. Pending verification against source',
      },
    ],
  },
  {
    id: 'r-G9-3',
    paperId: 'G9',
    sectionId: 's1',
    quote:
      'a synthetic peptide corresponding to a bovine β-casein phosphorylation site, β(28–40)',
    field: 'phospho_site_position',
    value: 28,
    unit: 'residue',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    numbering: 'mature',
    componentTag: 'β(28–40) assay peptide, N-terminal bound',
    curationRef: '§8 G9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G9 — start of the β(28–40) assay peptide; mature numbering per the §19 numbering trap; pending verification against source',
      },
    ],
  },
  {
    id: 'r-G9-4',
    paperId: 'G9',
    sectionId: 's1',
    quote:
      'a synthetic peptide corresponding to a bovine β-casein phosphorylation site, β(28–40)',
    field: 'phospho_site_position',
    value: 40,
    unit: 'residue',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    organism: 'bovine',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    numbering: 'mature',
    componentTag: 'β(28–40) assay peptide, C-terminal bound',
    curationRef: '§8 G9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G9 — end of the β(28–40) assay peptide; mature numbering per the §19 numbering trap; pending verification against source',
      },
    ],
  },
  {
    id: 'r-G9-5',
    paperId: 'G9',
    sectionId: 's1',
    quote:
      'by 2010, 50–70% of secreted phosphosites in plasma and CSF matched the S/TxE consensus',
    field: 'phosphorylation_degree',
    value: 60,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: false,
    evidenceClass: 'literature',
    method: 'undetermined',
    range: { low: 50, high: 70 },
    curationRef: '§8 G9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §8 G9 — dated to 2010 in a ~2025 entry, so recorded as a recitation of prior literature rather than this entry’s own measurement; no corpus record exists yet to cite, so citesRecordId is unset. Denominator is secreted phosphosites matching the S/TxE consensus, NOT native site count — check the field mapping at verification',
      },
    ],
  },
];
