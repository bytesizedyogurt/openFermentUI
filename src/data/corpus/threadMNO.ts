// openFerment corpus — Thread M (cultivation: cw15 growth and TAP medium),
// Thread N (food safety and regulatory position) and Thread O (techno-economic
// analysis and process modeling).
//
// REAL LITERATURE. Every title, author string, year, venue, DOI, PMCID and PMID
// in this file is transcribed from docs/OF-COR-001.md §14, §15 and §16. Nothing
// is invented — where the corpus document prints no authors, `authors` is empty
// and `verifyNeeded` is set rather than a plausible name being supplied, and
// where it prints no title the entry carries the document's own descriptive
// line, marked as such.
//
// The full texts have NOT been ingested. Each paper therefore carries exactly
// one section — the curator's note from OF-COR-001, in the curator's words,
// about the paper. `textSource: 'curation-note'` and `ingest: 'catalogued'` say
// so, and the reader labels it. No sentence in `sections[].text` is the paper's
// own prose, and every `quote` is a span of the curator's note rather than a
// source span. Records are status 'unverified': the claim is real and
// attributable, but nothing here has yet been checked against the source PDF.
//
// Four authoring notes specific to these threads:
//
//   * Thread N is regulatory and carries no numbers the ontology can hold. All
//     four entries are catalogued with zero records, which is the correct
//     outcome rather than a gap — a GRAS listing and an EFSA data-gap finding
//     are not quantities.
//
//   * M8 and O8m are composite entries. M8 gathers two sources under one
//     heading exactly as §14 does; O8m is split OUT of §16 O8 (see below). Each
//     opens with one curator sentence saying so, then the document's prose.
//
//   * O8 IS THE PROVENANCE SPLIT. §16 O8 deliberately mixes a peer-reviewed
//     anchor (Knychala et al. 2024, Fermentation) with a block of unattributed
//     market and vendor claims. They are two Paper objects here: 'O8' carries
//     the peer-reviewed cost trajectory at provenance 'curated', and 'O8m'
//     carries the market figures at provenance 'industry-estimate', sourceType
//     'industry-report', no authors, and no gold. §16's own handling rule
//     requires exactly this: ingest them, tick them differently, and never let
//     them into the gold set or default aggregates.
//
//   * Currency is NOT converted. §16 carries costs in both dollars and euros,
//     and units.ts keeps `costUSD` and `costEUR` in separate families on
//     purpose — converting would need an exchange rate with a date that no
//     unit engine has any business inventing. O4, O5, O6 and O7 therefore carry
//     'EUR kg⁻¹' verbatim.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_MNO: Paper[] = [
  // ── Thread M — cultivation: cw15 growth and TAP medium (§14) ──────────
  {
    id: 'M1',
    title: 'The Chlamydomonas Sourcebook',
    authors: ['Harris EH'],
    year: 1989,
    venue: 'Academic Press',
    thread: 'M',
    sourceType: 'book',
    organisms: [],
    topics: ['tap medium', 'standard cultivation', 'mixotrophic growth'],
    abstract:
      'Corpus entry for the reference work every TAP recipe in this programme ultimately descends from, catalogued as the cultivation baseline against which any modified medium is described. This is the curator’s summary of why the entry is in the corpus, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `TAP medium reference. Standard cultivation: liquid or agar-solidified TAP at 22 °C under continuous light at 50–100 µE m⁻² s⁻¹, mixotrophic.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'M2',
    title:
      'The original Tris-acetate-phosphate formulation — title not recorded in OF-COR-001',
    authors: ['Gorman DS', 'Levine RP'],
    year: 1965,
    venue: 'PNAS',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['tap medium', 'medium formulation', 'historical source'],
    abstract:
      'Corpus entry for the 1965 paper in which the Tris-acetate-phosphate formulation first appears; catalogued as the primary citation behind every later TAP variant. Curator’s summary, not the publisher’s abstract — OF-COR-001 records no title for this entry.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `The original Tris-acetate-phosphate formulation.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
  },
  {
    id: 'M3',
    title:
      'A revised mineral nutrient supplement increases biomass and growth rate in Chlamydomonas reinhardtii',
    authors: [
      'Kropat J',
      'Hong-Hermesdorf A',
      'Casero D',
      'Ent P',
      'Castruita M',
      'Pellegrini M',
      'Merchant SS',
      'Malasarn D',
    ],
    year: 2011,
    venue: 'Plant J',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['trace elements', 'medium formulation', 'biomass and growth rate'],
    abstract:
      'Corpus entry for the revised trace-element supplement that modern Chlamydomonas media use in place of the original Hutner formulation. Catalogued as a medium-design reference; the curator’s note states no numbers, so it carries no extraction records.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `The modern trace-element recipe.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },
  {
    id: 'M4',
    title:
      'Metabolic rewiring and biomass redistribution enable optimized mixotrophic growth in Chlamydomonas',
    authors: [],
    year: 2026,
    venue: 'PNAS',
    doi: '10.1073/pnas.2522572123',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['mixotrophy', 'flux analysis', 'acetate metabolism'],
    abstract:
      'Corpus entry for the ¹³C flux study explaining why mixotrophic Chlamydomonas outgrows both phototrophic and heterotrophic culture, and why partial suppression of photosynthesis may help rather than hurt. Catalogued as mechanism, not as a source of numbers; this is the curator’s summary rather than the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `¹³C flux analysis: mixotrophic cultures grow far faster than either phototrophic or heterotrophic cultures even though acetate partially suppresses photosynthesis. Acetate induced the glyoxylate cycle and suppressed gluconeogenesis while reducing photosynthetic flux; partial photosynthesis suppression may itself optimize growth by reducing the protein-synthesis burden — directly relevant to a host asked to overexpress two heterologous proteins.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole:
      'Partial photosynthesis suppression may itself optimize growth by reducing the protein-synthesis burden — directly relevant to a host asked to overexpress two heterologous proteins.',
  },
  {
    id: 'M5',
    title:
      'A Carbon Fixation Enhanced Chlamydomonas reinhardtii Strain for Achieving the Double-Win Between Growth and Biofuel Production',
    authors: [],
    year: 2020,
    venue: 'Front Bioeng Biotechnol',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['biomass density', 'biomass productivity', 'carbon fixation', 'cgapdh'],
    abstract:
      'Corpus entry for the paired wild-type and cGAPDH-overexpressing cultivation run that gives Thread M its cleanest density and productivity pair. Catalogued from the curation note; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `Wild-type CC-137c in TAP reached a maximum density of 1.23 ± 0.13 g/L within 96 h with maximum biomass productivity 24.30 ± 1.65 mg L⁻¹ h⁻¹; a cGAPDH-overexpressing strain reached 1.74 ± 0.09 g/L and 28.54 ± 1.43 mg L⁻¹ h⁻¹.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
  },
  {
    id: 'M6',
    title:
      'Mixotrophic growth with acetate or volatile fatty acids maximizes growth and lipid production in Chlamydomonas reinhardtii',
    authors: ['Moon M', 'et al.'],
    year: 2013,
    venue: 'Algal Res',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['mixotrophic growth', 'acetate', 'biomass density'],
    abstract:
      'Corpus entry for the mixotrophic acetate study that sets the upper end of the Chlamydomonas density band OF-COR-001 keeps returning to. Catalogued for one number — 2.15 g/L in five days; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `Greatest biomass production 2.15 g L⁻¹ in 5 days with FAME yield 16.41% of biomass, under mixotrophic cultivation with acetate.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },
  {
    id: 'M7',
    title:
      'Effect of the Light Regime and Phototrophic Conditions on Growth of C. reinhardtii',
    authors: [],
    year: 2012,
    venue: 'Energy Procedia',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['specific growth rate', 'light regime', 'co2 feed', 'acetate'],
    abstract:
      'Corpus entry for the light-regime study OF-COR-001 nominates as the corpus’s cleanest specific-growth-rate record, and as evidence that adding CO₂ to acetate-replete TAP makes growth worse rather than better. Curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `Strain cc124 in TAP showed its fastest growth rate, r = 0.087 h⁻¹, with 0% CO₂ feed — acetate is used far more effectively than CO₂, and adding CO₂ to acetate-replete TAP only reduces growth rate. Maximum final density was calculated at a CO₂ feed of 7.9%. The corpus's cleanest specific-growth-rate record.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole: "The corpus's cleanest specific-growth-rate record.",
  },
  {
    id: 'M8',
    title: 'Density and nutrient optimization',
    authors: [],
    year: 0,
    venue: 'PMC9549070; Process Biochem — composite entry, no single venue',
    pmcid: 'PMC9549070',
    thread: 'M',
    sourceType: 'journal-article',
    organisms: [],
    topics: [
      'medium optimization',
      'nitrogen limitation',
      'heterotrophic density',
      'density gap',
    ],
    abstract:
      'Composite corpus entry gathering the response-surface medium optimum, a 1996 heterotrophic chemostat benchmark, and the general algal density band — the cluster from which OF-COR-001 draws its harshest conclusion about the cw15 thesis. Curator’s summary, not any publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §14)',
        text: `This entry gathers two sources plus the general density band. Reducing culture medium nitrogen supply coupled with replenishing carbon nutrient (PMC9549070): response-surface optimum at 4.12 g/L sodium acetate and 0.20 g/L NH₄Cl, giving 32.14% total lipid, 1.68 g/L biomass, and 108.21 mg L⁻¹ d⁻¹ lipid productivity; standard TAP contains 0.38 g/L NH₄Cl. Chen F, Johns MR (1996), Process Biochem — heterotrophic growth on acetate in chemostat, highest cell concentration 1.5 g/L at 3.4 g/L feed acetate. Heterotrophic microalgal cultures can reach 50–100 g/L dry biomass versus a maximum around 30 g/L autotrophically. The density gap between 1–2 g/L mixotrophic Chlamydomonas and 100+ g/L Pichia fed-batch is the harshest number in the corpus for the cw15 thesis.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'The density gap between 1–2 g/L mixotrophic Chlamydomonas and 100+ g/L Pichia fed-batch is the harshest number in the corpus for the cw15 thesis.',
  },

  // ── Thread N — food safety and regulatory position (§15) ──────────────
  {
    id: 'N1',
    title:
      'C. reinhardtii GRAS status and human gastrointestinal-health study — title not recorded in OF-COR-001',
    authors: [
      'Fields FJ',
      'Lejzerowicz F',
      'Schroeder D',
      'Ngoi SM',
      'Tran M',
      'McDonald D',
      'Jiang L',
      'Chang JT',
      'Knight R',
      'Mayfield S',
    ],
    year: 2020,
    venue: 'J Funct Foods',
    thread: 'N',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['gras status', 'human trial', 'gastrointestinal health'],
    abstract:
      'Corpus entry for the human gastrointestinal-health study behind the claim that C. reinhardtii is safe to eat. Catalogued as the primary support for the GRAS pillar of the programme; the curator’s summary, not the publisher’s abstract, and OF-COR-001 records no title.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §15)',
        text: `C. reinhardtii GRAS status and human gastrointestinal-health study.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },
  {
    id: 'N2',
    title: 'Microalgae as a future food source',
    authors: [],
    year: 0,
    venue: 'OSTI 1822262',
    thread: 'N',
    sourceType: 'review',
    organisms: [],
    topics: ['gras list', 'regulatory scope', 'microalgal foods'],
    abstract:
      'Corpus entry for the report that enumerates which microalgae actually hold FDA GRAS status, and states the limit of that status — U.S. jurisdiction only. Catalogued as a regulatory reference; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §15)',
        text: `Records the short list of microalgae with FDA GRAS status: Arthrospira platensis, Chlamydomonas reinhardtii, Auxenochlorella protothecoides, Chlorella vulgaris, Dunaliella bardawil, Euglena gracilis. GRAS applies only in U.S. jurisdiction.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
  },
  {
    id: 'N3',
    title:
      'Safety of dried biomass powder of Chlamydomonas reinhardtii THN 6 as a novel food pursuant to Regulation (EU) 2015/2283',
    authors: ['EFSA NDA Panel'],
    year: 2025,
    venue: 'EFSA J',
    doi: '10.2903/j.efsa.2025.9413',
    pmcid: 'PMC12041885',
    thread: 'N',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['eu novel food', 'regulatory failure', 'data gaps'],
    abstract:
      'Corpus entry for the EFSA opinion in which an actual C. reinhardtii food application failed — on procedure and unanswered data requests rather than on any finding of harm. Catalogued as the programme’s regulatory cautionary tale; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §15)',
        text: `Triton Algae Innovations applied in April 2023. EFSA identified data gaps across identity, production process, composition, specifications, history of use, proposed uses and use levels, nutritional information, genotoxicity and allergenicity, requested additional information repeatedly, received no reply, and concluded that the safety of the novel food could not be established. The corpus's most important cautionary record: U.S. GRAS status does not transfer to the EU, an actual C. reinhardtii food application has failed on the record, and the failure was procedural rather than a finding of harm.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      "The corpus's most important cautionary record: U.S. GRAS status does not transfer to the EU, an actual C. reinhardtii food application has failed on the record, and the failure was procedural rather than a finding of harm.",
  },
  {
    id: 'N4',
    title:
      'Towards microalga-based superfoods: heterologous expression of zeolin in Chlamydomonas reinhardtii',
    authors: [],
    year: 2023,
    venue: 'Front Plant Sci',
    pmcid: 'PMC10203602',
    thread: 'N',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['heterologous food protein', 'zeolin', 'closest precedent'],
    abstract:
      'Corpus entry for the closest published precedent to this entire programme: a heterologous food protein expressed in C. reinhardtii for nutritional purposes. Marked priority ingest in OF-COR-001; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §15)',
        text: `A synthetic gene encoding zeolin, a chimera of γ-zein and phaseolin, introduced into the algal genome. The closest published precedent to the entire program — a heterologous food protein expressed in C. reinhardtii for nutritional purposes. Priority ingest.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole:
      'The closest published precedent to the entire program — a heterologous food protein expressed in C. reinhardtii for nutritional purposes.',
  },

  // ── Thread O — techno-economic analysis and process modeling (§16) ────
  {
    id: 'O1',
    title:
      'BioSTEAM: A Fast and Flexible Platform for the Design, Simulation, and Techno-Economic Analysis of Biorefineries under Uncertainty',
    authors: ['Cortes-Peña Y', 'Kumar D', 'Singh V', 'Guest JS'],
    year: 2020,
    venue: 'ACS Sustain Chem Eng',
    doi: '10.1021/acssuschemeng.9b07040',
    thread: 'O',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['process simulation', 'techno-economic engine', 'uncertainty analysis'],
    abstract:
      'Corpus entry for the open-source process simulator this platform’s own cost engine is modelled on. Catalogued as methodology rather than as a source of measured values; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `Open-source steady-state process simulator in Python; economic metrics closely match SuperPro Designer and Aspen Plus; evaluated 31,000 biorefinery designs in under 50 minutes. The platform's simulation engine — and Deepak Kumar is a co-author.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: "The platform's simulation engine — and Deepak Kumar is a co-author.",
  },
  {
    id: 'O2',
    title: 'Techno-economic insights on fermentation ingredients',
    authors: ['Good Food Institute'],
    year: 2025,
    venue: 'Good Food Institute',
    thread: 'O',
    sourceType: 'industry-report',
    organisms: [],
    topics: ['tea meta-analysis', 'fermentation protein cost', 'titer assumptions'],
    abstract:
      'Corpus entry for the meta-analysis of 55 published techno-economic models that OF-COR-001 calls its single richest TEA source, including the titer gap between published models and private benchmarks. Curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `Meta-analysis of 55 published techno-economic models. Biomass-fermentation protein costs converge around $4–6/kg, against beef and pork market prices of $6.0–15.0/kg. Microbial oils range $1.5–19.6/kg. Published models assume production volumes of 50–2,500 t/y and average titer around 24 g/L, while private-sector benchmarks span 2,500–25,000 t/y and average around 42 g/L — a gap wide enough that published models systematically overstate cost. Reported estimates span under $20/kg to about $15,000/kg with a conspicuous absence of models in the $20–200/kg band. The single richest TEA source in the corpus.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The single richest TEA source in the corpus.',
  },
  {
    id: 'O3',
    title:
      'Techno-economic analysis of industrial-scale fermentation for formate dehydrogenase production',
    authors: [],
    year: 2025,
    venue: 'Not recorded in OF-COR-001',
    pmcid: 'PMC12681506',
    thread: 'O',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['minimum selling price', 'crude versus purified', 'cell density sensitivity'],
    abstract:
      'Corpus entry for the four-scenario fermentation cost model OF-COR-001 calls the most directly transferable in the corpus — crude versus purified protein across a 30-fold price span, driven by cell density and target-protein content. Curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `Four scenarios all sized to deliver 80,000 kg pure protein per year. Minimum selling price for crude protein ranged $2,300/kg (1 L empirical) to $75/kg (optimistic); purified protein ranged $99,000/kg to $970/kg. A clear inverse relationship held between levelized protein cost and two upstream parameters: biomass cell density and target protein content — the 1 L case ran at 4.2 g/L biomass with target protein at 0.1% of cell mass. The most directly transferable cost model in the corpus.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'The most directly transferable cost model in the corpus.',
  },
  {
    id: 'O4',
    title:
      'Production cost of a real microalgae production plant and strategies to reduce it',
    authors: ['Acién FG', 'Fernández JM', 'Magán JJ', 'Molina E'],
    year: 2012,
    venue: 'Biotechnol Adv',
    pmid: '22361647',
    thread: 'O',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['real plant cost', 'photobioreactor', 'scale-up economics'],
    abstract:
      'Corpus entry for two years of operating data from a real tubular photobioreactor plant, and the only entry in Thread O whose cost figure comes from an operating facility rather than a model alone. Curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `Ten 3 m³ tubular photobioreactors, continuous mode, two years of data on Scenedesmus almeriensis in Almería. Annual capacity 3.8 t/y (90 t/ha·y), photosynthetic efficiency 3.6%, production cost 69 €/kg, dominated by labor and depreciation. Simplification plus scale-up to 200 t/y reduces cost to 12.6 €/kg.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'O5',
    title: 'Towards microalgal triglycerides in the commodity markets',
    authors: [],
    year: 2017,
    venue: 'Biotechnol Biofuels',
    pmcid: 'PMC5514516',
    thread: 'O',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['biomass cost', 'photosynthetic efficiency', 'sensitivity analysis'],
    abstract:
      'Corpus entry for the 100-hectare plant model whose parameter sensitivities OF-COR-001 describes as a ready-made tornado chart from real data. Catalogued for its two endpoint costs; curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `100-ha plant in southern Spain, vertically stacked tubular PBRs: 6.7 €/kg biomass at 24% TAG. Photosynthetic efficiency is the single most influential parameter (30% and 14% cost reduction from base case for stress and growth phases); avoiding active cooling gives 10%, raising the cooling setpoint 4.5%. All improvements together project 3.3 €/kg at 60% TAG. A ready-made tornado chart from real data.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    verifyNeeded: true,
    corpusRole: 'A ready-made tornado chart from real data.',
  },
  {
    id: 'O6',
    title:
      'Techno-economic assessment of microalgae cultivation in a tubular photobioreactor for food in a humid continental climate',
    authors: ['Schade S', 'Meier T'],
    year: 2021,
    venue: 'Clean Technol Environ Policy',
    doi: '10.1007/s10098-021-02042-x',
    thread: 'O',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['capital cost', 'co-product credit', 'photobioreactor for food'],
    abstract:
      'Corpus entry for the food-oriented photobioreactor assessment that prices the residual protein-rich biomass stream — the number that caps how much credit any process can claim for its leftovers. Curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `Borosilicate glass tubing is one of the largest single capital items; residual protein-rich biomass co-product was valued at only 0.44 EUR/kg DM.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'O7',
    title:
      'Techno-economic assessment of microalgae production, harvesting and drying',
    authors: [],
    year: 2022,
    venue: 'Not recorded in OF-COR-001',
    pmid: '35526636',
    thread: 'O',
    sourceType: 'journal-article',
    organisms: [],
    topics: ['harvesting cost', 'drying cost', 'biomass cost breakdown'],
    abstract:
      'Corpus entry for the production-plus-downstream assessment that itemises what harvesting and drying actually cost as a share of biomass price. Catalogued for its headline figure; the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `Nannochloropsis oceanica year-round cultivation: 53.32 €/kg DW at 27.61 t/y for 1 ha. Centrifugation contributed 10.65% of biomass cost and freeze-drying 20.15%; substituting ultrafiltration plus spray drying cut costs 7.03%, expanding to 10 ha cut 17.99%, and using fertilizers instead of commercial nutrient solutions cut 10.92%.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
  },
  {
    id: 'O8',
    title: 'Precision Fermentation as an Alternative to Animal Protein',
    authors: ['Knychala MM', 'Boing LA', 'Ienczak JL', 'Trichez D', 'Stambuk BU'],
    year: 2024,
    venue: 'Fermentation',
    doi: '10.3390/fermentation10060315',
    thread: 'O',
    sourceType: 'review',
    organisms: [],
    topics: ['cost trajectory', 'precision fermentation', 'peer-reviewed anchor'],
    abstract:
      'Corpus entry for the peer-reviewed anchor of the §16 cost-trajectory cluster: three decades of precision-fermentation cost, from about a million dollars a kilogram to a forecast below ten. Curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16)',
        text: `The peer-reviewed anchor of a deliberately mixed-quality cluster: cost falling from about USD 1 million/kg in 2000 to roughly USD 100/kg currently, forecast below USD 10/kg by 2030. The non-peer-reviewed market and vendor claims OF-COR-001 groups under the same heading are held separately, as entry O8m, so that they can never be mistaken for this one.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole:
      'The peer-reviewed anchor of the corpus cost trajectory — a deliberately mixed-quality cluster.',
  },
  {
    id: 'O8m',
    title: 'Precision fermentation market and vendor cost claims (non-peer-reviewed)',
    authors: [],
    year: 2025,
    venue: 'Market and vendor sources; none named in OF-COR-001',
    thread: 'O',
    sourceType: 'industry-report',
    organisms: [],
    topics: ['market claims', 'vendor forecasts', 'industry-estimate provenance'],
    abstract:
      'Corpus entry holding the non-peer-reviewed half of §16 O8, split out so that market and vendor claims can be read but never counted as evidence. Every record on this entry is provenance industry-estimate, none is gold, and OF-COR-001 names no source for any of the figures.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §16 O8, market half)',
        text: `Split out from entry O8 so that non-peer-reviewed numbers can never be mistaken for the peer-reviewed anchor. OF-COR-001 records, without naming any source: NON-PEER-REVIEWED market and vendor sources report precision-fermentation whey protein at $25–30/kg in 2025 targeting $8–12/kg by 2028, casein parity around 2028–2030, media at 35–50% of COGS, fermenters of 100,000–200,000 L needed for sub-$25/kg, and single-facility CAPEX of $150–400M. The document's handling rule is explicit: ingest these but assign provenance class industry-estimate, render with a distinct tick, and never allow them into the gold set or default aggregate statistics.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    corpusRole:
      'Ingest these but assign provenance class industry-estimate, render with a distinct tick, and never allow them into the gold set or default aggregate statistics.',
  },
];

// Every `quote` below is copied out of the section text above, character for
// character — the reader locates spans with indexOf(), so a quote that is not
// present loses its highlight silently rather than erroring.
//
// Deliberate non-extractions, so the gaps read as decisions rather than misses:
//
//   * M1's 22 °C and 50–100 µE m⁻² s⁻¹, M4's flux findings, M8's 32.14% lipid
//     and 108.21 mg L⁻¹ d⁻¹, O1's 31,000 designs, O4/O5/O7's percentage cost
//     breakdowns, O8m's media share of COGS and CAPEX band — the ontology has
//     no field that fits any of them, and inventing one to hold a number is
//     worse than leaving the number in the note where a reader can still see it.
//
//   * O2's "under $20/kg to about $15,000/kg" span describes the shape of a
//     literature distribution, not the cost of a process. Recorded as a range
//     its midpoint would be ~$7,500/kg, which would land in every strip plot as
//     a data point that no one ever estimated. Left unextracted on purpose.
//
//   * M8's closing "1–2 g/L mixotrophic Chlamydomonas and 100+ g/L Pichia"
//     restates figures already carried by M5, M6 and the heterotrophic band;
//     extracting it again would double-count the same evidence.
export const RECORDS_MNO: ExtractionRecord[] = [
  // ── M5 — the paired density / productivity run ────────────────────────
  {
    id: 'r-M5-1',
    paperId: 'M5',
    sectionId: 's1',
    quote: 'a maximum density of 1.23 ± 0.13 g/L within 96 h',
    field: 'final_biomass_density',
    value: 1.23,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    organism: 'creinhardtii-wt',
    componentTag: 'wild-type CC-137c in TAP, 96 h',
    curationRef: '§14 M5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M5 — wild-type baseline density; the ±0.13 g/L spread is a standard deviation rather than a stated range, so it is left in the quote rather than entered as `range` — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M5-2',
    paperId: 'M5',
    sectionId: 's1',
    quote: 'maximum biomass productivity 24.30 ± 1.65 mg L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 24.3,
    unit: 'mg L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    organism: 'creinhardtii-wt',
    componentTag: 'wild-type CC-137c in TAP — biomass, not product',
    curationRef: '§14 M5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M5 — the productivity figure the ontology cites as its worked example for this field; it is a biomass productivity, not a product productivity — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M5-3',
    paperId: 'M5',
    sectionId: 's1',
    quote: 'a cGAPDH-overexpressing strain reached 1.74 ± 0.09 g/L',
    field: 'final_biomass_density',
    value: 1.74,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    organism: 'creinhardtii-wt',
    componentTag: 'cGAPDH-overexpressing strain, CC-137c background',
    curationRef: '§14 M5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M5 — engineered arm of the same experiment; organism is recorded as the CC-137c wild-type background because the corpus has no id for the cGAPDH derivative — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M5-4',
    paperId: 'M5',
    sectionId: 's1',
    quote: '28.54 ± 1.43 mg L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 28.54,
    unit: 'mg L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    organism: 'creinhardtii-wt',
    componentTag: 'cGAPDH-overexpressing strain — biomass productivity',
    curationRef: '§14 M5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M5 — paired with r-M5-2; the two together are the only same-experiment productivity comparison in the corpus — pending verification against source',
      },
    ],
  },

  // ── M6 — the top of the mixotrophic density band ──────────────────────
  {
    id: 'r-M6-1',
    paperId: 'M6',
    sectionId: 's1',
    quote: 'Greatest biomass production 2.15 g L⁻¹ in 5 days',
    field: 'final_biomass_density',
    value: 2.15,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'mixotrophic cultivation with acetate, 5 days',
    curationRef: '§14 M6',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M6 — the upper end of the 1–2 g/L Chlamydomonas band; the curation note names no strain, so no organism id is asserted — pending verification against source',
      },
    ],
  },

  // ── M7 — the corpus's cleanest growth-rate record ─────────────────────
  {
    id: 'r-M7-1',
    paperId: 'M7',
    sectionId: 's1',
    quote: 'fastest growth rate, r = 0.087 h⁻¹, with 0% CO₂ feed',
    field: 'growth_rate_mu',
    value: 0.087,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    organism: 'creinhardtii-wt',
    componentTag: 'strain cc124 in TAP, 0% CO₂ feed',
    curationRef: '§14 M7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M7 — the value the ontology quotes for growth_rate_mu; the source writes it as r rather than μ, which must be confirmed to be a specific growth rate at verification',
      },
    ],
  },

  // ── M8 — medium optimum, chemostat benchmark, and the density gap ─────
  {
    id: 'r-M8-1',
    paperId: 'M8',
    sectionId: 's1',
    quote: 'response-surface optimum at 4.12 g/L sodium acetate',
    field: 'medium_component_conc',
    value: 4.12,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'sodium acetate',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — carbon-source optimum from the response-surface study (PMC9549070); the optimum was fitted for lipid productivity, not for recombinant protein, and must not be reused without that caveat — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-2',
    paperId: 'M8',
    sectionId: 's1',
    quote: '0.20 g/L NH₄Cl',
    field: 'medium_component_conc',
    value: 0.2,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'NH₄Cl (response-surface optimum, nitrogen-reduced)',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — the nitrogen-reduced optimum; paired with r-M8-3, which carries the standard TAP value it is reduced from — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-3',
    paperId: 'M8',
    sectionId: 's1',
    quote: 'standard TAP contains 0.38 g/L NH₄Cl',
    field: 'medium_component_conc',
    value: 0.38,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'NH₄Cl (standard TAP)',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — the standard TAP nitrogen concentration, recorded so that the reduced optimum in r-M8-2 has a baseline to be read against — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-4',
    paperId: 'M8',
    sectionId: 's1',
    quote: '1.68 g/L biomass',
    field: 'final_biomass_density',
    value: 1.68,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'response-surface optimum, nitrogen-reduced TAP',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — density achieved at the fitted medium optimum (PMC9549070) — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-5',
    paperId: 'M8',
    sectionId: 's1',
    quote: 'highest cell concentration 1.5 g/L at 3.4 g/L feed acetate',
    field: 'final_biomass_density',
    value: 1.5,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'heterotrophic chemostat on acetate (Chen & Johns 1996)',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — the chemostat half of the composite entry; it is a steady-state cell concentration rather than a batch harvest density, which the field name does not capture — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-6',
    paperId: 'M8',
    sectionId: 's1',
    quote: '3.4 g/L feed acetate',
    field: 'medium_component_conc',
    value: 3.4,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'acetate (chemostat feed concentration)',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — feed concentration, not a batch medium concentration; recorded because it is the carbon input the 1.5 g/L in r-M8-5 was obtained from — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-7',
    paperId: 'M8',
    sectionId: 's1',
    quote: 'Heterotrophic microalgal cultures can reach 50–100 g/L dry biomass',
    field: 'final_biomass_density',
    value: 75,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    range: { low: 50, high: 100 },
    componentTag: 'heterotrophic microalgae, general band (not Chlamydomonas)',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — a general claim about heterotrophic microalgae rather than a measurement on one strain; the point value is the midpoint of the stated range and carries no meaning on its own — pending verification against source',
      },
    ],
  },
  {
    id: 'r-M8-8',
    paperId: 'M8',
    sectionId: 's1',
    quote: 'a maximum around 30 g/L autotrophically',
    field: 'final_biomass_density',
    value: 30,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'autotrophic microalgae, general ceiling',
    curationRef: '§14 M8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §14 M8 — stated as "around 30 g/L", so confidence is reduced; it is the autotrophic counterpart to r-M8-7 and the ceiling the cw15 case has to argue against — pending verification against source',
      },
    ],
  },

  // ── Thread N — no records. GRAS listings, an EFSA data-gap finding and a
  // zeolin precedent are regulatory facts, not quantities; the ontology has no
  // field for any of them and forcing one would be worse than the silence.

  // ── O2 — the 55-model meta-analysis ───────────────────────────────────
  {
    id: 'r-O2-1',
    paperId: 'O2',
    sectionId: 's1',
    quote: 'Biomass-fermentation protein costs converge around $4–6/kg',
    field: 'minimum_selling_price',
    value: 5,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    range: { low: 4, high: 6 },
    componentTag: 'biomass-fermentation protein, convergence of 55 published models',
    curationRef: '§16 O2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O2 — the figure the ontology quotes for this field; it is a meta-analytic convergence across 55 models rather than one process estimate, and the same entry warns those models systematically overstate cost — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O2-2',
    paperId: 'O2',
    sectionId: 's1',
    quote: 'Microbial oils range $1.5–19.6/kg',
    field: 'minimum_selling_price',
    value: 10.55,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    range: { low: 1.5, high: 19.6 },
    componentTag: 'microbial oils (a different product to protein — not a comparator)',
    curationRef: '§16 O2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O2 — the point value is the arithmetic midpoint of a 13-fold span and should never be read as a central estimate; the range is the claim — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O2-3',
    paperId: 'O2',
    sectionId: 's1',
    quote: 'average titer around 24 g/L',
    field: 'titer_secreted',
    value: 24,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'mean assumed titer across published TEA models',
    curationRef: '§16 O2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O2 — field assignment is provisional: the note says only "titer" and does not distinguish secreted from intracellular, so titer_secreted is the closer of the two fields rather than a stated one. It is also a modelling assumption, not a measurement. Confidence reduced accordingly — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O2-4',
    paperId: 'O2',
    sectionId: 's1',
    quote: 'average around 42 g/L',
    field: 'titer_secreted',
    value: 42,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: 'mean titer across private-sector benchmarks',
    curationRef: '§16 O2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O2 — the private-sector counterpart to r-O2-3 and the reason the entry argues published models overstate cost; same provisional field assignment and same reduced confidence — pending verification against source',
      },
    ],
  },

  // ── O3 — the four-scenario fermentation cost model ────────────────────
  {
    id: 'r-O3-1',
    paperId: 'O3',
    sectionId: 's1',
    quote: 'crude protein ranged $2,300/kg (1 L empirical)',
    field: 'minimum_selling_price',
    value: 2300,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'crude protein, 1 L empirical scenario',
    curationRef: '§16 O3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O3 — worst-case crude MSP, from the scenario built on 1 L empirical data; the same scenario supplies r-O3-5 and r-O3-6, which are the two parameters the entry says drive it — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O3-2',
    paperId: 'O3',
    sectionId: 's1',
    quote: 'to $75/kg (optimistic)',
    field: 'minimum_selling_price',
    value: 75,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'crude protein, optimistic scenario',
    curationRef: '§16 O3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O3 — best-case crude MSP; the 30-fold spread against r-O3-1 comes from scenario assumptions alone, not from different measurements — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O3-3',
    paperId: 'O3',
    sectionId: 's1',
    quote: 'purified protein ranged $99,000/kg',
    field: 'minimum_selling_price',
    value: 99000,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'purified protein, high end of the four-scenario range',
    curationRef: '§16 O3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O3 — the note does not say which scenario the purified endpoints belong to, so the componentTag says "high end" rather than assuming it pairs with the 1 L empirical case — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O3-4',
    paperId: 'O3',
    sectionId: 's1',
    quote: '$99,000/kg to $970/kg',
    field: 'minimum_selling_price',
    value: 970,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'purified protein, low end of the four-scenario range',
    curationRef: '§16 O3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O3 — same caution as r-O3-3 about scenario attribution; the crude-to-purified step is roughly 13-fold at both ends, which is the transferable part of this model — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O3-5',
    paperId: 'O3',
    sectionId: 's1',
    quote: 'the 1 L case ran at 4.2 g/L biomass',
    field: 'final_biomass_density',
    value: 4.2,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: '1 L empirical scenario — the density driving r-O3-1',
    curationRef: '§16 O3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O3 — one of the two upstream parameters the entry identifies as inversely related to levelized protein cost; the host is not named in the note — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O3-6',
    paperId: 'O3',
    sectionId: 's1',
    quote: 'target protein at 0.1% of cell mass',
    field: 'expression_pct_tsp',
    value: 0.1,
    unit: '% TSP',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    componentTag: '1 L empirical scenario — source states % of cell mass, not % TSP',
    curationRef: '§16 O3',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O3 — recorded under the expression-share field with unit % TSP, but the note says "% of cell mass", which is a different denominator to total soluble protein. Confidence reduced and the discrepancy flagged for verification rather than silently normalised',
      },
    ],
  },

  // ── O4 — a real plant, in euros ───────────────────────────────────────
  {
    id: 'r-O4-1',
    paperId: 'O4',
    sectionId: 's1',
    quote: 'production cost 69 €/kg, dominated by labor and depreciation',
    field: 'minimum_selling_price',
    value: 69,
    unit: 'EUR kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'real 30 m³ tubular plant at 3.8 t/y — biomass, not protein',
    curationRef: '§16 O4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O4 — currency deliberately left in euros; units.ts keeps costEUR and costUSD in separate families because converting needs an exchange rate with a date. Cost of dried biomass, not of a purified protein — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O4-2',
    paperId: 'O4',
    sectionId: 's1',
    quote: 'Simplification plus scale-up to 200 t/y reduces cost to 12.6 €/kg',
    field: 'minimum_selling_price',
    value: 12.6,
    unit: 'EUR kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'same plant simplified and scaled to 200 t/y (projected)',
    curationRef: '§16 O4',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O4 — a projection rather than an operated cost, unlike r-O4-1; the 5.5-fold gap between the two is the scale argument this entry contributes — pending verification against source',
      },
    ],
  },

  // ── O5 — the ready-made tornado chart ─────────────────────────────────
  {
    id: 'r-O5-1',
    paperId: 'O5',
    sectionId: 's1',
    quote: '6.7 €/kg biomass at 24% TAG',
    field: 'minimum_selling_price',
    value: 6.7,
    unit: 'EUR kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: '100-ha plant, base case at 24% TAG',
    curationRef: '§16 O5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O5 — base-case biomass cost for a 100-ha modelled plant; currency left in euros by design — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O5-2',
    paperId: 'O5',
    sectionId: 's1',
    quote: 'All improvements together project 3.3 €/kg at 60% TAG',
    field: 'minimum_selling_price',
    value: 3.3,
    unit: 'EUR kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'all modelled improvements applied, 60% TAG (projected)',
    curationRef: '§16 O5',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O5 — a stacked best case, not an achieved cost: it assumes every sensitivity in the entry is realised at once and the TAG fraction more than doubles — pending verification against source',
      },
    ],
  },

  // ── O6 — what the leftovers are worth ─────────────────────────────────
  {
    id: 'r-O6-1',
    paperId: 'O6',
    sectionId: 's1',
    quote: 'residual protein-rich biomass co-product was valued at only 0.44 EUR/kg DM',
    field: 'minimum_selling_price',
    value: 0.44,
    unit: 'EUR kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag:
      'co-product credit inside the model — a valuation, not a product minimum selling price',
    curationRef: '§16 O6',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O6 — field assignment is a compromise: the ontology has one price-per-kilogram field and this is a co-product valuation rather than a break-even price, so the componentTag carries the distinction the field cannot. Must not be aggregated with product MSPs — pending verification against source',
      },
    ],
  },

  // ── O7 — production plus harvesting and drying ────────────────────────
  {
    id: 'r-O7-1',
    paperId: 'O7',
    sectionId: 's1',
    quote: '53.32 €/kg DW at 27.61 t/y for 1 ha',
    field: 'minimum_selling_price',
    value: 53.32,
    unit: 'EUR kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'process model',
    componentTag: 'Nannochloropsis oceanica, 1 ha year-round, dry weight basis',
    curationRef: '§16 O7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O7 — includes harvesting and drying, unlike the cultivation-only costs in O4 and O5, which is why it sits an order of magnitude above them; currency left in euros — pending verification against source',
      },
    ],
  },

  // ── O8 — the peer-reviewed cost trajectory ────────────────────────────
  {
    id: 'r-O8-1',
    paperId: 'O8',
    sectionId: 's1',
    quote: 'about USD 1 million/kg in 2000',
    field: 'minimum_selling_price',
    value: 1000000,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'undetermined',
    componentTag: 'precision-fermentation protein, year 2000',
    curationRef: '§16 O8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O8 — stated as "about", so confidence is reduced; the review names no costing method behind the trajectory, so method is undetermined rather than assumed to be a process model. Sits above the ontology plausibility ceiling on purpose — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O8-2',
    paperId: 'O8',
    sectionId: 's1',
    quote: 'roughly USD 100/kg currently',
    field: 'minimum_selling_price',
    value: 100,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'undetermined',
    componentTag: 'precision-fermentation protein, as of the 2024 review',
    curationRef: '§16 O8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O8 — the peer-reviewed present-day figure, and the one that should be compared against the O8m vendor claims rather than mixed with them — pending verification against source',
      },
    ],
  },
  {
    id: 'r-O8-3',
    paperId: 'O8',
    sectionId: 's1',
    quote: 'forecast below USD 10/kg by 2030',
    field: 'minimum_selling_price',
    value: 10,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    method: 'undetermined',
    componentTag: 'forecast ceiling for 2030 — the source states "below", not a point',
    curationRef: '§16 O8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O8 — a forecast, not a measurement, and an upper bound rather than an estimate: the value 10 is the stated ceiling and the true claim is "less than". Confidence reduced — pending verification against source',
      },
    ],
  },

  // ── O8m — market and vendor claims. provenance 'industry-estimate', and
  // never gold: §16's handling rule is that these are catalogued for framing
  // and are not evidence. `aggregateExclusion` in store.ts holds them out of
  // every median, range and count-based summary; they stay visible per record.
  {
    id: 'r-O8m-1',
    paperId: 'O8m',
    sectionId: 's1',
    quote: 'precision-fermentation whey protein at $25–30/kg in 2025',
    field: 'minimum_selling_price',
    value: 27.5,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'industry-estimate',
    isPrimary: true,
    method: 'undetermined',
    range: { low: 25, high: 30 },
    componentTag: 'precision-fermentation whey protein, 2025 — vendor claim',
    curationRef: '§16 O8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O8 market half — non-peer-reviewed. OF-COR-001 names no source, so there is nothing to verify against and the provenance class, not the confidence, carries the warning. Never gold; excluded from default aggregates',
      },
    ],
  },
  {
    id: 'r-O8m-2',
    paperId: 'O8m',
    sectionId: 's1',
    quote: 'targeting $8–12/kg by 2028',
    field: 'minimum_selling_price',
    value: 10,
    unit: 'USD kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'industry-estimate',
    isPrimary: true,
    method: 'undetermined',
    range: { low: 8, high: 12 },
    componentTag: 'precision-fermentation whey protein, 2028 vendor target',
    curationRef: '§16 O8',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §16 O8 market half — a vendor target rather than a forecast with a method behind it. It happens to coincide with the peer-reviewed 2030 ceiling in r-O8-3 two years earlier, which is precisely the kind of agreement the industry-estimate tick exists to keep from reading as corroboration',
      },
    ],
  },
];
