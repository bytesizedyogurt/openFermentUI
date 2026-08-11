// openFerment corpus — Thread I (functionality: does phosphorylation matter?)
// and Thread J (purification and downstream processing).
//
// REAL LITERATURE. Every title, author string, year, venue, DOI and PMCID in
// this file is transcribed from docs/OF-COR-001.md §10 and §11. Nothing is
// invented — where the corpus document gives no authors, `authors` is empty or
// carries only the fragment the document itself prints, and `verifyNeeded` is
// set rather than a plausible name being supplied.
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
// Two authoring notes specific to these threads:
//
//   * J2 is the same review as corpus entry E1; §11 prints only "Atamer Z, et
//     al. (2017). See E1." The author fragment is kept exactly as §11 gives it,
//     while the title, venue and DOI are taken from the E1 entry the document
//     points at. It is deliberately a second Paper object: it earns its place
//     in Thread J for a different reason than in Thread E.
//
//   * Thread J is mostly a bibliography of dairy-fractionation unit operations.
//     Eight entries (J1–J6, J8, plus I3–I8 in Thread I) state no quantitative or
//     categorical claim the ontology can hold, so they carry no records at all.
//     The numeric weight of the thread sits in J10 and J11.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_IJ: Paper[] = [
  // ── Thread I — functionality: does phosphorylation matter? (§10) ──────
  {
    id: 'I1',
    title:
      'Unravelling the dominant role of phosphorylation degree in governing the functionality of reassembled casein micelles',
    authors: [
      'Che J',
      'Fan Z',
      'Bijl E',
      'Thomsen JPS',
      'Mijakovic I',
      'Hettinga K',
      'Poulsen NA',
      'Larsen LB',
    ],
    year: 2025,
    venue: 'Food Hydrocolloids',
    doi: '10.1016/j.foodhyd.2024.110615',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: [
      'phosphorylation degree',
      'micelle reassembly',
      'gelation ph',
      'success criterion',
    ],
    abstract:
      'Corpus entry for the dephosphorylation-series experiment OF-COR-001 treats as the functional success criterion of the whole programme: micelle assembly, calcium binding and gelation all track phosphorylation degree, and fully dephosphorylated caseins simply precipitate. This is the curator’s summary of why the entry is catalogued, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `Four caseins purified from bovine milk and enzymatically dephosphorylated to three pools, then reassembled into nine micelle solutions across three systems. Micelle reassembly ability was proportional to phosphorylation degree; higher phosphorylation gave a higher micellar proportion and greater calcium-binding; fully dephosphorylated caseins hardly formed micelle structures at all and remained in serum. Gelation pH rose as phosphorylation fell, and fully dephosphorylated caseins failed to gel entirely, precipitating at their isoelectric point around pH 5.5. Across all three systems roughly 87% of total protein was sedimentable in the fully phosphorylated case. The success criterion, experimentally grounded: if a cw15-derived β-casein cannot be phosphorylated, it will not gel — it will precipitate.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'The success criterion, experimentally grounded: if a cw15-derived β-casein cannot be phosphorylated, it will not gel — it will precipitate.',
  },
  {
    id: 'I2',
    title:
      'Engineering artificial casein micelles for future food: Is casein phosphorylation necessary?',
    authors: ['Antuma LJ', 'Steiner I', 'Garamus VM', 'Boom RM', 'Keppler JK'],
    year: 2023,
    venue: 'Food Res Int',
    doi: '10.1016/j.foodres.2023.113315',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['artificial casein micelles', 'dephosphorylated casein', 'micelle size'],
    abstract:
      'Corpus entry for the artificial-micelle study that asks the programme’s question directly — whether phosphorylation is necessary at all — and reports that predominantly dephosphorylated casein assembles into irregular structures several times oversized. Catalogued from the curation note; the size distribution itself has not been ingested.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `Artificial casein micelles composed predominantly of dephosphorylated casein form irregular structures roughly three times larger than normal.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'I3',
    title:
      'Engineering artificial casein micelles for future food: Preparation rate and coagulation properties',
    authors: [
      'Antuma LJ',
      'Braitmaier SH',
      'Garamus VM',
      'Hinrichs J',
      'Boom RM',
      'Keppler JK',
    ],
    year: 2024,
    venue: 'J Food Eng',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['preparation rate', 'micelle diameter', 'coagulation'],
    abstract:
      'Corpus entry for the artificial-micelle paper OF-COR-001 records for one process fact: micellar diameter is set by how fast the micelle is assembled. Catalogued on a single line of curation prose, with no absolute diameter stated.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `Micellar diameter is controllable by preparation rate during assembly.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'I4',
    title: 'Casein micelle formation as a calcium phosphate phase separation process',
    authors: ['Antuma LJ', 'Stadler M', 'Garamus VM', 'Boom RM', 'Keppler JK'],
    year: 2024,
    venue: 'Innov Food Sci Emerg Technol',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['calcium phosphate', 'scalable assembly', 'membrane processing'],
    abstract:
      'Corpus entry for the paper that makes artificial micelle assembly a scalable unit operation rather than a bench trick, replacing dropwise mixing with vacuum evaporation and membrane routes. It is catalogued because that operation is what would sit immediately downstream of a cw15 fermentation.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `Replaces the unscalable dropwise-mixing method with vacuum evaporation and membrane routes — the unit operation that would sit downstream of a cw15 fermentation.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'Replaces the unscalable dropwise-mixing method with vacuum evaporation and membrane routes — the unit operation that would sit downstream of a cw15 fermentation.',
  },
  {
    id: 'I5',
    title: 'Artificial casein micelles and the road towards animal-free cheese',
    authors: ['Antuma LJ'],
    year: 2025,
    venue: 'Wageningen University',
    thread: 'I',
    sourceType: 'thesis',
    organisms: ['bovine'],
    topics: ['artificial casein micelles', 'animal-free cheese', 'doctoral thesis'],
    abstract:
      'Corpus entry I5: the doctoral thesis collecting the Antuma artificial-micelle series (I2–I4) into one 239-page account. OF-COR-001 lists it bibliographically with no curation prose, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `OF-COR-001 §10 lists this entry with author, year, title, degree-awarding institution and page count only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'I6',
    title:
      'Structure of biomimetic casein micelles: critical tests of the hydrophobic colloid and multivalent-binding models using recombinant deuterated and phosphorylated β-casein',
    authors: ['Raynes JK', 'Mata J', 'Wilde KL', 'Carver JA', 'Kelly SM', 'Holt C'],
    year: 2024,
    venue: 'J Struct Biol X',
    pmcid: 'PMC10840362',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: [
      'biomimetic micelles',
      'recombinant phosphorylated β-casein',
      'validation target',
    ],
    abstract:
      'Corpus entry for the structural study of biomimetic micelles built from recombinant, deuterated, phosphorylated β-casein — the closest published analogue of what a cw15 product would have to become. OF-COR-001 nominates it as the validation target; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `The most structurally rigorous validation target for a cw15-derived product.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 1,
    corpusRole: 'The most structurally rigorous validation target for a cw15-derived product.',
  },
  {
    id: 'I7',
    title:
      'Physicochemical properties of native and precision fermentation-derived bovine β-casein',
    authors: ['Chezan D', 'Fuhrmann PL', 'Bender D', 'Rennhofer H', 'Domig KJ', 'Dewi BPC'],
    year: 2026,
    venue: 'Food Hydrocolloids',
    doi: '10.1016/j.foodhyd.2025.111797',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['precision fermentation', 'head-to-head comparison', 'priority ingest'],
    abstract:
      'Corpus entry for the direct comparison of native against precision-fermentation-derived bovine β-casein. OF-COR-001 flags it as the head-to-head reference and marks it for priority ingest; nothing beyond that flag is held here.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `The head-to-head comparison. Priority ingest.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'The head-to-head comparison. Priority ingest.',
  },
  {
    id: 'I8',
    title: 'Dephosphorylation of αs- and β-caseins and its effect on chaperone activity',
    authors: ['Koudelka T', 'Hoffmann P', 'Carver JA'],
    year: 2009,
    venue: 'J Agric Food Chem',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['dephosphorylation', 'chaperone activity', 'structural flexibility'],
    abstract:
      'Corpus entry for the study of what dephosphorylation costs casein beyond assembly — its molecular-chaperone behaviour. It is catalogued as a second, independent functional consequence of failing to phosphorylate a recombinant casein.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `Phosphoserine-driven structural flexibility underpins casein's molecular-chaperone behavior — lost, not merely reduced, on dephosphorylation.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'I9',
    title: 'Counterweight — when phosphorylation may not be required',
    authors: ['Mortes', 'et al.'],
    year: 0,
    venue: 'Food Hydrocolloids; Crit Rev Food Sci Nutr',
    thread: 'I',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: [
      'emulsion and foam stabilisation',
      'casein composition',
      'product-strategy fork',
    ],
    abstract:
      'Corpus entry I9: a composite of three works OF-COR-001 gathers under one heading as the counterweight to Thread I, with no single author string or year. It is here for the fork it draws — emulsifier and foaming applications are reachable without solving FAM20C, cheese and yogurt are not.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §10)',
        text: `This entry gathers three works. Mortes et al. (2026) report that recombinant non-phosphorylated αs1-casein can stabilize emulsion and foam interfaces, indicating that for some food applications phosphorylation may be unnecessary. Tuning the structure and coagulation behaviour of artificial casein micelles by varying the casein composition (Food Hydrocolloids, 2025) shows functional artificial micelles can be built from two or three caseins rather than all four. Artificial and reformed casein micelles as encapsulation vehicles (Crit Rev Food Sci Nutr, 2025, DOI 10.1080/10408398.2025.2513522) notes ACM formation from recombinant caseins has so far been unsuccessful, largely for PTM reasons. The product-strategy fork: emulsifier/foaming applications are reachable without solving FAM20C; cheese and yogurt are not.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    verifyNeeded: true,
    corpusRole:
      'The product-strategy fork: emulsifier/foaming applications are reachable without solving FAM20C; cheese and yogurt are not.',
  },

  // ── Thread J — purification and downstream processing (§11) ───────────
  {
    id: 'J1',
    title: 'Downstream Processing of Food Proteins from Precision Fermentation',
    authors: ['Keppler JK', 'Boom RM'],
    year: 2026,
    venue: 'Annu Rev Food Sci Technol',
    doi: '10.1146/annurev-food-060424-091647',
    thread: 'J',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: ['downstream processing', 'functionality over purity', 'coacervation'],
    abstract:
      'Corpus entry for the review that reframes purification economics for bulk food proteins: chromatography is the wrong tool, and functionality rather than purity is the specification to hit. Catalogued from the curation note as the framing document for the whole thread.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `Conventional chromatography is designed for high-purity, high-value products and is too costly for bulk food proteins; cost-effective production requires prioritizing ingredient functionality — emulsifying, foaming, gelation — over purity. Discusses coacervation with food-grade polyanions, and notes the calcium sensitivity of α- and β-caseins can itself enable simplified extraction.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
  },
  {
    id: 'J2',
    title: 'Bovine β-casein: Isolation, properties and functionality. A review',
    authors: ['Atamer Z', 'et al.'],
    year: 2017,
    venue: 'Int Dairy J',
    doi: '10.1016/j.idairyj.2016.11.010',
    thread: 'J',
    sourceType: 'review',
    organisms: ['bovine'],
    topics: ['selective precipitation', 'cold membrane filtration', 'isolation technology'],
    abstract:
      'Corpus entry J2: the same review as entry E1, catalogued a second time under Thread J because it doubles as the isolation-technology survey. Title, venue and DOI are taken from the E1 entry the corpus document points at; the author fragment is as §11 prints it.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `See E1. Doubles as the isolation-technology review: selective precipitation exploiting calcium sensitivity by adding calcium chloride at alkaline pH, and cold membrane filtration at ≤4 °C exploiting β-casein dissociation from the micelle into the serum phase.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole: 'Doubles as the isolation-technology review.',
  },
  {
    id: 'J3',
    title:
      'Pilot-scale β-casein depletion from micellar casein via cold microfiltration in the diafiltration mode',
    authors: ['Schäfer J', 'Schubert T', 'Atamer Z'],
    year: 2019,
    venue: 'Int Dairy J',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['cold microfiltration', 'diafiltration', 'pilot scale'],
    abstract:
      'Corpus entry J3: pilot-scale cold microfiltration for β-casein depletion. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `OF-COR-001 §11 lists this entry with authors, title, journal, volume and page range only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'J4',
    title:
      'Application of a temperature-controlled decanter centrifuge for the fractionation of αS-, β- and κ-casein at pilot scale',
    authors: ['Schubert T', 'Ergin I', 'Panetta F', 'Hinrichs J', 'Atamer Z'],
    year: 2021,
    venue: 'Int Dairy J',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['decanter centrifuge', 'casein fractionation', 'pilot scale'],
    abstract:
      'Corpus entry J4: temperature-controlled decanter centrifugation as a pilot-scale casein fractionation route. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `OF-COR-001 §11 lists this entry with authors, title, journal, volume and article number only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'J5',
    title: 'β-casein as a bioactive precursor — processing for purification',
    authors: ['Post AE', 'Ebert M', 'Hinrichs J'],
    year: 2009,
    venue: 'Aust J Dairy Technol',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['bioactive precursor', 'purification processing'],
    abstract:
      'Corpus entry J5: β-casein purification processing framed around its bioactive-precursor role. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `OF-COR-001 §11 lists this entry with authors, title, journal, volume and page range only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'J6',
    title: 'Large-scale isolation of food-grade β-casein',
    authors: ['Post AE', 'Hinrichs J'],
    year: 2011,
    venue: 'Milchwissenschaft',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['large-scale isolation', 'food-grade β-casein'],
    abstract:
      'Corpus entry J6: large-scale, food-grade β-casein isolation. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `OF-COR-001 §11 lists this entry with authors, title, journal, volume and page range only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'J7',
    title: 'Effect of temperature and pH on the solubility of caseins',
    authors: ['Post A', 'Arnold B', 'Weiss J', 'Hinrichs J'],
    year: 2012,
    venue: 'J Dairy Sci',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['solubility surfaces', 'isoelectric precipitation', 'temperature and ph'],
    abstract:
      'Corpus entry for the casein solubility surfaces in temperature and pH that OF-COR-001 marks as directly usable for designing an isoelectric precipitation step on recombinant β-casein. This is the curator’s summary of the entry, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `Solubility surfaces in temperature × pH — directly usable for isoelectric precipitation of recombinant β-casein at pI 4.6.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'Solubility surfaces in temperature × pH — directly usable for isoelectric precipitation of recombinant β-casein at pI 4.6.',
  },
  {
    id: 'J8',
    title:
      'A novel approach to isolation of β-casein from micellar casein concentrate by cold microfiltration combined with chymosin treatment',
    authors: [
      'van der Schaaf JM',
      'Goulding DA',
      'Fuerer C',
      "O'Regan J",
      "O'Mahony JA",
      'Kelly AL',
    ],
    year: 2024,
    venue: 'Int Dairy J',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['bovine'],
    topics: ['cold microfiltration', 'chymosin treatment', 'micellar casein concentrate'],
    abstract:
      'Corpus entry J8: cold microfiltration combined with chymosin treatment as a β-casein isolation route. OF-COR-001 lists it bibliographically with no curation note, so it is catalogued on its citation alone.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `OF-COR-001 §11 lists this entry with authors, title, journal, volume and article number only. The corpus document records no curation prose for it, so nothing beyond the citation is held here.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
  },
  {
    id: 'J9',
    title:
      'Mannan interference and purification efficiency in downstream processing of precision-fermented milk proteins from Komagataella phaffii',
    authors: [],
    year: 0,
    venue: 'Not recorded in OF-COR-001',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['gs115'],
    topics: ['yeast mannan', 'purification interference', 'host glycoprotein burden'],
    abstract:
      'Corpus entry J9: an unresolved reference on mannan interference in yeast-derived milk-protein purification, held because it is the closest published analogue of the UVM4 cell-wall-glycoprotein problem a secreted cw15 product would face. Author string, year and venue are not given in the corpus document.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `Yeast mannan is the analogue of the UVM4 cell-wall-glycoprotein aggregate problem.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 3,
    verifyNeeded: true,
    corpusRole: 'Yeast mannan is the analogue of the UVM4 cell-wall-glycoprotein aggregate problem.',
  },
  {
    id: 'J10',
    title:
      'Mild and Selective Protein Release of Cell Wall Deficient Microalgae with Pulsed Electric Field',
    authors: ['Postma PR', 'et al.'],
    year: 2017,
    venue: 'ACS Sustain Chem Eng',
    doi: '10.1021/acssuschemeng.7b00892',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: ['cw15'],
    topics: ['pulsed electric field', 'cell wall deficiency', 'mild protein release'],
    abstract:
      'Corpus entry for the pulsed-electric-field study that measures what cell-wall deficiency is worth downstream: roughly three times the protein yield of a walled wild type, under mild conditions. OF-COR-001 treats it as the keystone of the cw15 processing case; this is the curator’s summary, not the publisher’s abstract.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `PEF applied to a cell-wall-deficient mutant gave an average protein yield of 31 ± 6% versus 11 ± 3% for the walled wild type (p < 0.05) — roughly three-fold, comparable to mechanical disruption but under mild conditions. The record that converts "cw15 is easy to transform" into "cw15 is cheap to process."`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: false,
    tranche: 2,
    corpusRole:
      'The record that converts "cw15 is easy to transform" into "cw15 is cheap to process."',
  },
  {
    id: 'J11',
    title: 'Mechanical disruption benchmarks for microalgae',
    authors: ['Safi C', 'et al.'],
    year: 0,
    venue: 'Encyclopedia (MDPI); primary journal not recorded in OF-COR-001',
    thread: 'J',
    sourceType: 'journal-article',
    organisms: [],
    topics: [
      'high-pressure homogenization',
      'bead milling',
      'disruption energy',
      'pef on walled cells',
    ],
    abstract:
      'Corpus entry J11: a composite of two disruption benchmarks OF-COR-001 gathers under one heading, giving the mechanical baseline (>95% disintegration, ~50% protein release, <0.5 kWh per kg) and the counter-case of PEF on walled cells. It is catalogued as the comparator that makes J10 mean something.',
    sections: [
      {
        id: 's1',
        heading: 'Curation note (OF-COR-001 §11)',
        text: `This entry gathers two sources. Safi C, et al. — Energy consumption and water-soluble protein release by cell wall disruption of Nannochloropsis gaditana: high-pressure homogenization and bead milling were most efficient, giving >95% cell disintegration, approximately 50% (w/w) release of total proteins, at low energy input (<0.5 kWh per kg biomass). Microalgae Cell Disruption Methods (Encyclopedia MDPI, 2021) records PEF released a maximum of 13% of protein from walled Chlorella vulgaris even at 10–100× the energy of bead milling, which released 45–50%. J10 and J11 read together: PEF on walled cells is bad; PEF on wall-deficient cells is competitive with bead milling at mild conditions.`,
      },
    ],
    ingest: 'catalogued',
    textSource: 'curation-note',
    openAccess: true,
    tranche: 2,
    verifyNeeded: true,
    corpusRole:
      'J10 and J11 read together: PEF on walled cells is bad; PEF on wall-deficient cells is competitive with bead milling at mild conditions.',
  },
];

export const RECORDS_IJ: ExtractionRecord[] = [
  // ── I1 — the functional success criterion ─────────────────────────────
  {
    id: 'r-I1-1',
    paperId: 'I1',
    sectionId: 's1',
    quote: 'roughly 87% of total protein was sedimentable in the fully phosphorylated case',
    field: 'micellar_fraction',
    value: 87,
    unit: '% sedimentable',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    organism: 'bovine',
    componentTag: 'fully phosphorylated reassembled micelles',
    curationRef: '§10 I1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §10 I1 — sedimentable fraction across all three reassembly systems; method recorded as gravimetric (sedimentation), pending verification against source',
      },
    ],
  },
  {
    id: 'r-I1-2',
    paperId: 'I1',
    sectionId: 's1',
    quote: 'precipitating at their isoelectric point around pH 5.5',
    field: 'gelation_ph',
    value: 5.5,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'bovine',
    componentTag: 'fully dephosphorylated caseins — precipitation, not gelation',
    curationRef: '§10 I1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §10 I1 — the pH at which fully dephosphorylated caseins precipitate instead of gelling; the curation note names no analytical method, so method is undetermined; pending verification against source',
      },
    ],
  },
  {
    id: 'r-I1-3',
    paperId: 'I1',
    sectionId: 's1',
    quote:
      'fully dephosphorylated caseins hardly formed micelle structures at all and remained in serum',
    field: 'micellar_fraction',
    value: 0,
    unit: '% sedimentable',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    organism: 'bovine',
    negativeResult: true,
    componentTag: 'fully dephosphorylated casein pool',
    curationRef: '§10 I1',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §10 I1 — a reported negative, not a missing measurement: the curation note states the effect qualitatively ("hardly formed micelle structures at all"), so the value is entered as zero at reduced confidence and must be replaced with the published figure at verification',
      },
    ],
  },

  // ── I2 — dephosphorylated artificial micelles are oversized ───────────
  {
    id: 'r-I2-1',
    paperId: 'I2',
    sectionId: 's1',
    quote: 'roughly three times larger than normal',
    field: 'fold_improvement',
    value: 3,
    unit: '×',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    organism: 'bovine',
    comparativeBaseline:
      'normally sized artificial casein micelles (predominantly dephosphorylated casein vs normal)',
    componentTag: 'artificial casein micelle size',
    curationRef: '§10 I2',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §10 I2 — recorded as a fold change rather than a micelle_diameter because the curation note gives no absolute size; the direction is a degradation, not an improvement, and the baseline carries that; pending verification against source',
      },
    ],
  },

  // ── I9 — the counterweight ────────────────────────────────────────────
  {
    id: 'r-I9-1',
    paperId: 'I9',
    sectionId: 's1',
    quote: 'recombinant non-phosphorylated αs1-casein can stabilize emulsion and foam interfaces',
    field: 'phosphorylation_degree',
    value: 0,
    unit: '% of native sites',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'bovine',
    negativeResult: true,
    componentTag: 'recombinant αs1-casein, emulsion and foam interfaces',
    curationRef: '§10 I9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §10 I9 — the material is described as non-phosphorylated and still interfacially functional; recorded as a reported zero rather than a missing measurement, with no analytical method named; pending verification against source',
      },
    ],
  },
  {
    id: 'r-I9-2',
    paperId: 'I9',
    sectionId: 's1',
    quote: 'ACM formation from recombinant caseins has so far been unsuccessful',
    field: 'micellar_fraction',
    value: 0,
    unit: '% sedimentable',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'bovine',
    negativeResult: true,
    componentTag: 'artificial casein micelles from recombinant caseins',
    curationRef: '§10 I9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §10 I9 — a field-level negative reported by a review ("unsuccessful, largely for PTM reasons") rather than a measured fraction; entered at reduced confidence and flagged as a negative result; pending verification against source',
      },
    ],
  },

  // ── J7 — the isoelectric point for a precipitation step ───────────────
  {
    id: 'r-J7-1',
    paperId: 'J7',
    sectionId: 's1',
    quote: 'isoelectric precipitation of recombinant β-casein at pI 4.6',
    field: 'gelation_ph',
    value: 4.6,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'bovine',
    componentTag: 'isoelectric point (pI) of β-casein',
    curationRef: '§11 J7',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J7 — the acid-precipitation pH of β-casein, held under gelation_ph because the ontology carries isoelectric precipitation there; no analytical method is named; pending verification against source',
      },
    ],
  },

  // ── J9 — the yeast glycan burden ──────────────────────────────────────
  {
    id: 'r-J9-1',
    paperId: 'J9',
    sectionId: 's1',
    quote: 'Yeast mannan is the analogue of the UVM4 cell-wall-glycoprotein aggregate problem',
    field: 'glycan_species',
    value: 'mannan',
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    organism: 'gs115',
    componentTag: 'host glycan interfering with purification',
    curationRef: '§11 J9',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J9 — the host glycan named as the purification interferent; the entry is [verify] and names no analytical method; pending verification against source',
      },
    ],
  },

  // ── J10 — the cw15 downstream keystone ────────────────────────────────
  {
    id: 'r-J10-1',
    paperId: 'J10',
    sectionId: 's1',
    quote: 'an average protein yield of 31 ± 6%',
    field: 'disruption_protein_yield',
    value: 31,
    unit: '% of total protein',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    organism: 'cw15',
    componentTag: 'pulsed electric field, cell-wall-deficient mutant',
    curationRef: '§11 J10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J10 — PEF on the cell-wall-deficient mutant; the curation note gives 31 ± 6% as a mean with a standard deviation, so the point value is entered and the spread is not encoded as a range; pending verification against source',
      },
    ],
  },
  {
    id: 'r-J10-2',
    paperId: 'J10',
    sectionId: 's1',
    quote: '11 ± 3% for the walled wild type',
    field: 'disruption_protein_yield',
    value: 11,
    unit: '% of total protein',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    componentTag: 'pulsed electric field, walled wild type',
    curationRef: '§11 J10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J10 — the walled wild-type control for r-J10-1, kept as its own record so the contrast survives aggregation; the walled strain is not one of the platform strain ids, so no organism is set; pending verification against source',
      },
    ],
  },
  {
    id: 'r-J10-3',
    paperId: 'J10',
    sectionId: 's1',
    quote: 'roughly three-fold',
    field: 'fold_improvement',
    value: 3,
    unit: '×',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    organism: 'cw15',
    comparativeBaseline:
      'PEF protein release from the walled wild type (11 ± 3% of total protein)',
    componentTag: 'pulsed electric field, wall-deficient vs walled',
    curationRef: '§11 J10',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J10 — the ratio the curation note draws between r-J10-1 and r-J10-2; not an independent measurement of either, and aggregation should treat it as the same observation viewed as a ratio; pending verification against source',
      },
    ],
  },

  // ── J11 — the mechanical benchmark and the walled-cell counter-case ───
  {
    id: 'r-J11-1',
    paperId: 'J11',
    sectionId: 's1',
    quote: 'giving >95% cell disintegration',
    field: 'disruption_protein_yield',
    value: 95,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'undetermined',
    componentTag: 'cell disintegration by HPH and bead milling (not protein release)',
    curationRef: '§11 J11',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J11 — a stated lower bound (>95%) entered as 95 at reduced confidence; the number counts disrupted cells rather than released protein, so the unit is a plain percentage and componentTag says so; re-field this record if the ontology gains a disintegration parameter',
      },
    ],
  },
  {
    id: 'r-J11-2',
    paperId: 'J11',
    sectionId: 's1',
    quote: 'approximately 50% (w/w) release of total proteins',
    field: 'disruption_protein_yield',
    value: 50,
    unit: '% of total protein',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    componentTag: 'high-pressure homogenization and bead milling, Nannochloropsis gaditana',
    curationRef: '§11 J11',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J11 — the mechanical-disruption protein-release benchmark; stated as approximate, so confidence is reduced; the organism is not one of the platform strain ids; pending verification against source',
      },
    ],
  },
  {
    id: 'r-J11-3',
    paperId: 'J11',
    sectionId: 's1',
    quote: 'at low energy input (<0.5 kWh per kg biomass)',
    field: 'disruption_energy',
    value: 0.5,
    unit: 'kWh kg⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    componentTag: 'high-pressure homogenization and bead milling',
    curationRef: '§11 J11',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J11 — a stated upper bound (<0.5 kWh per kg biomass) entered as 0.5 at reduced confidence; pending verification against source',
      },
    ],
  },
  {
    id: 'r-J11-4',
    paperId: 'J11',
    sectionId: 's1',
    quote: 'PEF released a maximum of 13% of protein from walled Chlorella vulgaris',
    field: 'disruption_protein_yield',
    value: 13,
    unit: '% of total protein',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    componentTag: 'pulsed electric field on walled Chlorella vulgaris',
    curationRef: '§11 J11',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J11 — the counter-case to J10: PEF on walled cells, at 10-100x the energy of bead milling; a stated maximum; pending verification against source',
      },
    ],
  },
  {
    id: 'r-J11-5',
    paperId: 'J11',
    sectionId: 's1',
    quote: 'which released 45–50%',
    field: 'disruption_protein_yield',
    value: 47.5,
    unit: '% of total protein',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    provenance: 'curated',
    isPrimary: true,
    evidenceClass: 'literature',
    method: 'gravimetric',
    range: { low: 45, high: 50 },
    componentTag: 'bead milling on walled Chlorella vulgaris',
    curationRef: '§11 J11',
    audit: [
      {
        at: '2026-08-10 09:00',
        who: 'S. Creighton',
        action:
          'curated from OF-COR-001 §11 J11 — the bead-milling comparator in the same sentence as r-J11-4; the source states a range, so the midpoint is the value and the range is carried explicitly; pending verification against source',
      },
    ],
  },
];
