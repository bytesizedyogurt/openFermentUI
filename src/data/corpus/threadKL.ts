// openFerment corpus — Thread K (comparable successes in other hosts) and
// Thread L (products: the plant-based gap that casein fills).
//
// REAL LITERATURE. Every title, author string, year, venue, DOI, PMCID and PII
// in this file is transcribed from docs/OF-COR-001.md §12 and §13. Nothing is
// invented. Where the corpus document gives no authors, `authors` is empty and
// `verifyNeeded` is set rather than a plausible name being supplied; where it
// gives no venue or no year, the house placeholders `'Not recorded in
// OF-COR-001'` and `year: 0` are used rather than a guess.
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
// Three authoring notes specific to these threads:
//
//   * Thread K carries the numeric weight. K1 is the cross-host benchmark the
//     whole platform is measured against, and K10 is the titer trajectory that
//     puts it in historical context. K3, K4 and K6–K9 are bibliographic or
//     purely qualitative and carry no records.
//
//   * K2's three life-cycle figures (≈70% lower greenhouse-gas impact, ≈80%
//     less water, ≈99% less arable land) have NO home in ontology v1. The 24
//     fields cover expression, PTM, function, cultivation and cost — there is
//     no environmental-impact family, and forcing an LCA percentage into
//     `fold_improvement` or any of the `%`-unit fields would be exactly the
//     category error OF-COR-001 §17 Rule 2 exists to prevent. The figures are
//     kept verbatim in the curation note (including the fact that K2 is
//     reciting Kossmann et al., 2025 rather than measuring them) so that a
//     future ontology v1.1 with an `lca_*` family can extract them without
//     re-reading the source. They are deliberately NOT records.
//
//   * Thread L carries no extraction records at all. Its numbers are food-
//     texture instrument readings (L3: hardness 126.8 N, firmness 98.81 N,
//     Young's modulus 953.3 kPa), a formulation protein share (L2: a zein/PPI
//     blend at 30% total protein) and review screening counts (L6: 1,553
//     articles and 155 patents screened). None of these fit ontology v1 —
//     `melt_stretch_length` is the only texture field and it is a length in mm,
//     not a force or a modulus. The thread earns its place as the product-side
//     argument for why phosphorylated casein matters, not as a source of
//     parameters, and the gap is recorded here rather than papered over.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_KL: Paper[] = [
  // ── Thread K — comparable successes in other hosts (§12) ─────────────
  {
    id: 'K1',
    title:
      'Production of bovine beta-lactoglobulin and hen egg ovalbumin by Trichoderma reesei using precision fermentation technology',
    authors: [
      'Aro N',
      'Ercili-Cura D',
      'Andberg M',
      'Silventoinen P',
      'Lille M',
      'Hosia W',
      'Nordlund E',
      'Landowski CP',
    ],
    year: 2023,
    venue: 'Food Res Int',
    doi: '10.1016/j.foodres.2022.112131',
    thread: 'K',
    sourceType: 'journal-article',
    organisms: ['treesei'],
    topics: [
      'precision fermentation',
      'secreted titer',
      'cross-host benchmark',
      'fungal n-glycosylation',
    ],
    abstract:
      'Corpus entry for the fungal precision-fermentation result OF-COR-001 uses as the yardstick for every openFerment scenario: gram-per-litre secreted milk and egg protein from a filamentous fungus, against milligram-per-litre from UVM4. This is the curator’s summary of why the entry is catalogued, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `1 g/L β-lactoglobulin and 2 g/L ovalbumin, at both 24-well plate and bioreactor scale. Circular dichroism confirmed the recombinant β-Lg matched native bovine secondary structure and showed comparable emulsification. The recombinant proteins were N-glycosylated with mannose-containing five-sugar-unit glycans typical of fungal hosts. The benchmark every openFerment scenario is measured against — 1 g/L secreted from a fungus vs 15 mg/L from UVM4 is a 65× gap.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'The benchmark every openFerment scenario is measured against — 1 g/L secreted from a fungus vs 15 mg/L from UVM4 is a 65× gap.',
  },
  {
    id: 'K2',
    title:
      'Omics-guided global rewiring of yeast metabolism enables high-level production of β-lactoglobulin',
    authors: [],
    year: 2026,
    venue: 'Not recorded in OF-COR-001',
    thread: 'K',
    sourceType: 'journal-article',
    organisms: ['gs115'],
    topics: [
      'methanol-free k. phaffii',
      'omics-guided rewiring',
      'secretion bottlenecks',
      'life-cycle assessment',
    ],
    abstract:
      'Corpus entry for the methanol-free Komagataella phaffii β-lactoglobulin platform, held both for its systems-level account of secretion bottlenecks and for the life-cycle figures it recites from Kossmann et al. (2025). Author string and venue are not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `Methanol-free K. phaffii β-Lg platform; transcriptomic and metabolomic identification of bottlenecks across energy supply, TCA-linked carbon and nitrogen metabolism, amino acid metabolism, redox homeostasis, and protein folding/secretion. Cites LCA figures for precision-fermented vs conventional dairy delivery of equivalent β-Lg: approximately 70% lower greenhouse-gas impact, around 80% less water use, and nearly 99% less arable land (Kossmann et al., 2025).`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },
  {
    id: 'K3',
    title: 'Expression of recombinant bovine β-lactoglobulin in Escherichia coli',
    authors: ['Batt CA', 'et al.'],
    year: 1990,
    venue: 'Agric Biol Chem',
    thread: 'K',
    sourceType: 'journal-article',
    organisms: ['ecoli'],
    topics: ['bacterial expression', 'inclusion bodies', 'β-lactoglobulin'],
    abstract:
      'Corpus entry for the earliest recombinant β-lactoglobulin attempt in the corpus, catalogued as the historical floor of the titer trajectory K10 describes. The curation note records only the aggregation outcome.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `Accumulated predominantly as insoluble inclusion bodies.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'K4',
    title: 'Secretory β-lactoglobulin production in P. pastoris',
    authors: ['Kim', 'et al.'],
    year: 1997,
    venue: 'Not recorded in OF-COR-001',
    thread: 'K',
    sourceType: 'journal-article',
    organisms: ['gs115'],
    topics: ['yeast secretion', 'β-lactoglobulin', 'commercial precedent'],
    abstract:
      'Corpus entry for the Pichia secretion precedent that several recombinant β-lactoglobulin businesses are built on. OF-COR-001 gives the entry as a one-line descriptive reference with no title, journal or DOI.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `Secretory β-lactoglobulin production in P. pastoris; the basis on which several companies now commercialize recombinant β-Lg.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    corpusRole:
      'The basis on which several companies now commercialize recombinant β-Lg.',
  },
  {
    id: 'K5',
    title:
      'Animal-free caseins by precision fermentation: technical challenges and perspectives',
    authors: [],
    year: 2026,
    venue: 'Trends Food Sci Technol',
    thread: 'K',
    sourceType: 'review',
    organisms: ['gs115', 'bovine'],
    topics: [
      'casein precision fermentation',
      'secretion advantage',
      'yeast o-glycosylation',
      'white-space check',
    ],
    abstract:
      'Corpus entry for the most current review of exactly this problem — animal-free casein by precision fermentation — held partly as a state-of-the-art summary and partly as an open verification task, since it may or may not already name microalgae as a candidate host. Author string is not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `The most current review of the exact problem. Secretion is highly advantageous for caseins because it avoids cell disruption and extensive purification; documents the yeast secretion failures; reiterates that phosphorylation is critical for micelle formation and for both acid and rennet coagulation; notes that when expressed in yeast, recombinant caseins can acquire O-glycosylation absent from the animal-derived protein. Publisher blocks automated retrieval. VERIFY AT INGEST whether this review already names microalgae as a candidate host — if so, the corpus white-space claim must be revised.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole: 'The most current review of the exact problem.',
  },
  {
    id: 'K6',
    title: 'Can recombinant milk proteins replace those produced by animals?',
    authors: ['Hettinga K', 'Bijl E'],
    year: 2022,
    venue: 'Curr Opin Biotechnol',
    thread: 'K',
    sourceType: 'review',
    organisms: [],
    topics: ['recombinant milk proteins', 'dairy replacement', 'opinion review'],
    abstract:
      'Corpus entry K6: a short opinion review on whether recombinant milk proteins can substitute for animal-derived ones. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `OF-COR-001 §12 lists this entry with authors, title, journal, volume and article number only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'K7',
    title: 'Cell factory-based milk protein biomanufacturing: advances and perspectives',
    authors: ['Deng M', 'Lv X', 'Liu L', 'Li J', 'Du G', 'Chen J', 'Liu Y'],
    year: 2023,
    venue: 'Int J Biol Macromol',
    thread: 'K',
    sourceType: 'review',
    organisms: [],
    topics: ['cell factories', 'milk protein biomanufacturing', 'review'],
    abstract:
      'Corpus entry K7: a survey of cell-factory routes to milk proteins. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `OF-COR-001 §12 lists this entry with authors, title, journal, volume and article number only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'K8',
    title:
      'Precision cellular agriculture: the future role of recombinantly expressed protein as food',
    authors: ['Dupuis JH', 'Cheung LKY', 'Newman L', 'Dee DR', 'Yada RY'],
    year: 2023,
    venue: 'Compr Rev Food Sci Food Saf',
    thread: 'K',
    sourceType: 'review',
    organisms: [],
    topics: ['cellular agriculture', 'recombinant food protein', 'review'],
    abstract:
      'Corpus entry K8: a comprehensive review of recombinantly expressed protein as food. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `OF-COR-001 §12 lists this entry with authors, title, journal, volume, issue and page range only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'K9',
    title:
      'From lab to table: the path of recombinant milk proteins in transforming dairy production',
    authors: ['Piazenski IN', 'et al.'],
    year: 2024,
    venue: 'Trends Food Sci Technol',
    thread: 'K',
    sourceType: 'review',
    organisms: [],
    topics: ['recombinant milk proteins', 'dairy transformation', 'review'],
    abstract:
      'Corpus entry K9: a review tracing recombinant milk proteins from laboratory expression to the dairy aisle. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `OF-COR-001 §12 lists this entry with authors, title, journal, volume and article number only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'K10',
    title:
      'Food production from air: gas precision fermentation with hydrogen-oxidising bacteria',
    authors: [],
    year: 2025,
    venue: 'Trends Biotechnol',
    thread: 'K',
    sourceType: 'review',
    organisms: ['ecoli', 'treesei', 'bovine'],
    topics: [
      'titer trajectory',
      'milk protein benchmark',
      'bacterial secretion yields',
      'gas fermentation',
    ],
    abstract:
      'Corpus entry for the review that supplies the historical scale of the problem: three decades of milk-protein titers, the natural bovine benchmark they are chasing, and the best reported bacterial secretion yields. Author string is not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §12)',
        text: `Milk protein titers from microbial fermentation have risen roughly a thousandfold over thirty years, from about 0.001 g/L in 1990 to about 1 g/L, against roughly 3 g/L β-lactoglobulin in bovine milk. Reported yields of at least 6 g/L for heterologous secretion via engineered E. coli secretion systems; the highest β-Lg levels have been achieved in T. reesei.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },

  // ── Thread L — products: the plant-based gap that casein fills (§13) ──
  {
    id: 'L1',
    title:
      'Title not recorded in OF-COR-001 — the canonical statement of plant-based cheese sensory shortfalls',
    authors: ['Grossmann L', 'McClements DJ'],
    year: 2021,
    venue: 'Trends Food Sci Technol',
    thread: 'L',
    sourceType: 'review',
    organisms: [],
    topics: ['plant-based cheese', 'sensory shortfall', 'review'],
    abstract:
      'Corpus entry L1: the reference OF-COR-001 treats as the canonical statement of what plant-based cheese fails to do. The document gives authors, year and journal but no title, so none is recorded here.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `OF-COR-001 §13 records this entry as the canonical statement of plant-based cheese sensory shortfalls. The corpus document gives no title and no further curation prose, so nothing beyond that role is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
    corpusRole: 'The canonical statement of plant-based cheese sensory shortfalls.',
  },
  {
    id: 'L2',
    title:
      'Overcoming the flavour and textural/rheological problems of plant-based cheese alternatives',
    authors: [],
    year: 2024,
    venue: 'Food Chem Adv',
    thread: 'L',
    sourceType: 'review',
    organisms: [],
    topics: ['starch structuring', 'meltability', 'zein', 'pea protein isolate'],
    abstract:
      'Corpus entry for the review of the starch-based structuring paradigm that dominates plant-based cheese formulation, and of the hardness-versus-melt trade-off it cannot escape. Author string is not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `Documents the starch-based structuring paradigm and its limits: increasing starch causes excessive hardening and reduced meltability; native starch prevents melting while oxidized starch improves it; pregelatinized starch as a casein and fat replacer improves softness, cohesiveness, and meltability; zein-containing analogues melt like cheese while pea-protein-isolate products do not, with a zein/PPI blend at 30% total protein showing melting potential.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'L3',
    title: 'Investigation of various plant protein ingredients for processed cheese analogues',
    authors: [],
    year: 2025,
    venue: 'Int J Food Sci Technol',
    thread: 'L',
    sourceType: 'journal-article',
    organisms: [],
    topics: [
      'processed cheese analogue',
      'texture benchmark',
      'meltability',
      'zein',
    ],
    abstract:
      'Corpus entry for the instrumented comparison that quantifies how far plant-protein cheese analogues sit from Cheddar on hardness, firmness and modulus, and attributes their poor melt to the absence of a continuous protein network. Author string is not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `Cheddar showed the highest hardness, firmness and Young's modulus (126.8 N, 98.81 N, 953.3 kPa); plant-based products displayed poor meltability attributed to the absence of a continuous protein network. Zein has melt-stretch and viscoelastic properties resembling Cheddar but suffers poor solubility, limited nutritional value, flavor issues, and processing difficulty. Ontology v1 has no home for any of these three numbers: hardness and firmness are forces in newtons and Young's modulus is a pressure, while the only texture field in the ontology, melt_stretch_length, is an extension in millimetres. The values are held in this note rather than forced into a field that does not fit.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole:
      'The instrumented texture benchmark against which plant-protein cheese analogues fall short.',
  },
  {
    id: 'L4',
    title: 'Plant-based cheese analogs: structure, texture, and functionality',
    authors: [],
    year: 2025,
    venue: 'Not recorded in OF-COR-001',
    thread: 'L',
    sourceType: 'review',
    organisms: [],
    topics: ['casein absence', 'brittle and gummy texture', 'phase separation'],
    abstract:
      'Corpus entry for the review that states the product-side thesis of the whole programme most directly: without casein, plant-based cheese has no structural network to build on. Author string and venue are not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `In the absence of casein, plant-based cheeses develop brittle or gummy textures, and plant protein/fat instability causes phase separation and poor structural cohesion.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'L5',
    title:
      'Sensory evaluation of plant-based cheese: a systematic review with a focus on texture and mouthfeel',
    authors: [],
    year: 2025,
    venue: 'Crit Rev Food Sci Nutr',
    doi: '10.1080/10408398.2025.2531220',
    thread: 'L',
    sourceType: 'review',
    organisms: [],
    topics: ['sensory evaluation', 'texture and mouthfeel', 'systematic review'],
    abstract:
      'Corpus entry L5: a systematic review of plant-based cheese sensory evaluation focused on texture and mouthfeel. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `OF-COR-001 §13 lists this entry with title, year, journal and DOI only. The corpus document records no authors and no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'L6',
    title: 'Cheese Analogues, an Alternative to Dietary Restrictions and Choices',
    authors: [],
    year: 0,
    venue: 'Not recorded in OF-COR-001',
    pmcid: 'PMC12294849',
    thread: 'L',
    sourceType: 'review',
    organisms: [],
    topics: ['prisma review', 'patent landscape', 'publication trend'],
    abstract:
      'Corpus entry for the PRISMA review that maps the size and trajectory of the cheese-analogue literature and patent landscape. Author string, year and venue are not given in the corpus document; the PMCID is the authoritative key.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `PRISMA review; 1,553 articles and 155 patents screened, 88 articles and 66 patents analyzed; interest rising since 2020 and peaking in 2024. These are bibliometric counts rather than process or product parameters, and ontology v1 has no field that holds them.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
  },
  {
    id: 'L7',
    title: 'Development of a Novel Robust Approach for Unveiling the Stretchiness of Cheese',
    authors: ['Andrigo', 'et al.'],
    year: 2025,
    venue: 'J Texture Stud',
    doi: '10.1111/jtxs.70012',
    thread: 'L',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['stretchiness', 'fork test', 'measurement standardisation'],
    abstract:
      'Corpus entry for the methods paper behind the ontology’s melt_stretch_length note: stretchiness is the attribute analogues most conspicuously lack and the one with the least standardised measurement.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `Stretchiness is among the hardest attributes to imitate and lacks standardized measurement, with the fork test still dominant.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'The measurement-standardisation problem behind the melt_stretch_length field.',
  },
  {
    id: 'L8',
    title:
      'Towards meltable plant-based cheese alternatives: processing oil and fat in zein-pea hybrids',
    authors: [],
    year: 2026,
    venue: 'Not recorded in OF-COR-001',
    thread: 'L',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['zein-pea hybrid', 'fat phase', 'commercial product composition'],
    abstract:
      'Corpus entry for the fat-phase study on zein-pea hybrids, held for its blunt characterisation of what is actually on shelves today. Author string and venue are not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §13)',
        text: `Commercially available alternatives contain little protein and are high in carbohydrates; coconut fat or sunflower oil produce waxy or oily textures.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
];

export const RECORDS_KL: ExtractionRecord[] = [
  // ── K1 — the cross-host benchmark ─────────────────────────────────────
  {
    id: 'r-K1-1',
    paperId: 'K1',
    sectionId: 's1',
    quote: '1 g/L β-lactoglobulin',
    field: 'titer_secreted',
    value: 1.0,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'HPLC',
    organism: 'treesei',
    componentTag: 'bovine β-lactoglobulin secreted by T. reesei',
    curationRef: '§12 K1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K1 — secreted β-lactoglobulin titer, reported at both 24-well plate and bioreactor scale; method recorded as HPLC, which the curation note does not itself name, so the qualifier must be confirmed at ingest; pending verification against source',
      },
    ],
  },
  {
    id: 'r-K1-2',
    paperId: 'K1',
    sectionId: 's1',
    quote: '2 g/L ovalbumin',
    field: 'titer_secreted',
    value: 2.0,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'HPLC',
    organism: 'treesei',
    componentTag: 'hen egg ovalbumin secreted by T. reesei',
    curationRef: '§12 K1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K1 — secreted ovalbumin titer, reported at both 24-well plate and bioreactor scale; method recorded as HPLC, which the curation note does not itself name, so the qualifier must be confirmed at ingest; pending verification against source',
      },
    ],
  },
  {
    id: 'r-K1-3',
    paperId: 'K1',
    sectionId: 's1',
    quote:
      'N-glycosylated with mannose-containing five-sugar-unit glycans typical of fungal hosts',
    field: 'glycan_species',
    value: 'mannose-containing five-sugar-unit N-glycan (fungal)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'treesei',
    componentTag: 'host N-glycosylation on recombinant β-Lg and ovalbumin',
    curationRef: '§12 K1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K1 — the host glycan structure carried by the recombinant proteins; the curation note names no analytical method, so method is undetermined; pending verification against source',
      },
    ],
  },

  // ── K5 — yeast O-glycosylation on recombinant casein ──────────────────
  {
    id: 'r-K5-1',
    paperId: 'K5',
    sectionId: 's1',
    quote:
      'recombinant caseins can acquire O-glycosylation absent from the animal-derived protein',
    field: 'glycan_species',
    value: 'O-glycosylation (yeast-added, absent from bovine casein)',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'gs115',
    componentTag: 'recombinant casein expressed in yeast',
    curationRef: '§12 K5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K5 — a host-added modification that the animal-derived protein does not carry, recorded because unwanted glycosylation is a product risk rather than a requirement for casein; the review names no analytical method, so method is undetermined; pending verification against source',
      },
    ],
  },

  // ── K10 — the titer trajectory and its benchmarks ─────────────────────
  {
    id: 'r-K10-1',
    paperId: 'K10',
    sectionId: 's1',
    quote: 'from about 0.001 g/L in 1990',
    field: 'titer_secreted',
    value: 0.001,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    componentTag: 'milk protein from microbial fermentation, 1990 — trajectory start',
    curationRef: '§12 K10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K10 — the 1990 end of the milk-protein titer trajectory; stated as "about" and not attributed to a named host or product, hence reduced confidence and no organism; pending verification against source',
      },
    ],
  },
  {
    id: 'r-K10-2',
    paperId: 'K10',
    sectionId: 's1',
    quote: 'to about 1 g/L',
    field: 'titer_secreted',
    value: 1.0,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    componentTag: 'milk protein from microbial fermentation, present day — trajectory end',
    curationRef: '§12 K10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K10 — the present-day end of the milk-protein titer trajectory; stated as "about" and not attributed to a named host, hence reduced confidence and no organism; note that it coincides with the K1 T. reesei measurement and must not be double-counted with it in aggregates until verification establishes whether it is that same result; pending verification against source',
      },
    ],
  },
  {
    id: 'r-K10-3',
    paperId: 'K10',
    sectionId: 's1',
    quote: 'roughly 3 g/L β-lactoglobulin in bovine milk',
    field: 'titer_secreted',
    value: 3.0,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    organism: 'bovine',
    componentTag:
      'natural β-lactoglobulin concentration in bovine milk — the biological benchmark, not a fermentation titer',
    curationRef: '§12 K10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K10 — the natural abundance of β-lactoglobulin in bovine milk, held in titer_secreted because it is the concentration every fermentation titer in the corpus is compared against; it is emphatically not a recombinant secretion measurement and the componentTag says so, so it must be excluded from host-performance aggregates; pending verification against source',
      },
    ],
  },
  {
    id: 'r-K10-4',
    paperId: 'K10',
    sectionId: 's1',
    quote: 'at least 6 g/L for heterologous secretion',
    field: 'titer_secreted',
    value: 6.0,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    organism: 'ecoli',
    componentTag: 'engineered E. coli secretion systems — reported floor, not a point value',
    curationRef: '§12 K10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §12 K10 — reported secretion yields via engineered E. coli secretion systems; the source states a lower bound ("at least 6 g/L") rather than a point or a closed range, so the value is entered as that floor and no `range` is set; pending verification against source',
      },
    ],
  },
];
