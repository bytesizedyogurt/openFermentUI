// Scripted agent flows (OF-DES-001 §16.2, rewired onto OF-COR-001 §21).
//
// A flow is the complete data behind one turn: the plan, the tool calls with
// their retrieval sets, the answer, and the follow-ups. The Inspector renders
// this same object, so the trace a reviewer inspects is the literal data that
// produced the answer rather than a reconstruction ("honest by construction").
//
// WHAT IS REAL HERE AND WHAT IS NOT
// --------------------------------
// The papers, authors, ids and values referenced below are real: every chip
// resolves to a corpus entry (A1, C2, H4, H17e, O8m …) or an extraction record
// (r-H4-1 …) seeded from docs/OF-COR-001.md. Every retrieval snippet is a
// verbatim substring of the cited paper's section text.
//
// The answer PROSE is scripted — that is one of the two surfaces OF-COR-001 §0
// leaves modeled rather than measured. And because all 132 entries are
// `ingest: 'catalogued'` with `textSource: 'curation-note'`, the single section
// 's1' of each paper holds the CURATOR'S notes, not the paper's own words. No
// answer below may state anything OF-COR-001 does not state, quote a paper, or
// phrase a curator's summary as if the authors had written it. Where the corpus
// is silent the answer says so — the decline in F6 is the point of the demo,
// not a shortfall in it.
//
// Answers name their evidential standing where it changes how the answer should
// be read, rather than carrying an identical disclaimer everywhere.
import type { ChatFlow } from './types';

export const FLOWS: ChatFlow[] = [
  // ── F1 — the cross-host prior-art table ─────────────────────────────
  {
    id: 'F1',
    triggers: [
      'what titers have been achieved for recombinant β-casein',
      'what titers have been achieved for recombinant beta-casein and in which hosts',
      'recombinant casein titers by host',
      'how much beta-casein has anyone actually made',
      'best reported casein yields across hosts',
    ],
    plan: [
      'Parse question — target β-casein, all hosts, expression family',
      'Retrieve thread H prior-art entries',
      'Query records for titer and % TSP',
      'Split intracellular from secreted; attach the phospho method per row',
      'Assemble the cross-host table',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: {
          query: 'recombinant β-casein titer expression level host',
          k: 8,
          filters: { thread: 'H' },
        },
        durationMs: 940,
        retrieval: [
          {
            paperId: 'H2',
            sectionId: 's1',
            score: 0.95,
            snippet:
              'Achieved high-level phosphorylated recombinant human β-casein at 500 mg/L',
          },
          {
            paperId: 'H4',
            sectionId: 's1',
            score: 0.92,
            snippet:
              'the protein localized mostly intracellularly at approximately 15–18% of total soluble protein, corresponding to 0.7–1.0 g/L; secreted protein reached only 0.005% of the intracellular level',
          },
          {
            paperId: 'H3',
            sectionId: 's1',
            score: 0.88,
            snippet: 'Yield 200 mg/L, partially phosphorylated',
          },
          {
            paperId: 'H14',
            sectionId: 's1',
            score: 0.79,
            snippet: '1.45 g/L — the highest bacterial casein titer in the corpus',
          },
          {
            paperId: 'H7',
            sectionId: 's1',
            score: 0.71,
            snippet:
              '10 mg/L; only 5–10% of total expressed casein reached the extracellular medium',
          },
          {
            paperId: 'H15',
            sectionId: 's1',
            score: 0.63,
            snippet:
              'Bovine β-casein in soybean (Glycine max), 0.1–0.4% of total soluble protein, not phosphorylated by MALDI-MS',
          },
        ],
      },
      {
        name: 'records.query',
        args: {
          fields: ['titer_intracellular', 'titer_secreted', 'expression_pct_tsp', 'secreted_fraction'],
          provenance: 'curated',
          isPrimary: true,
        },
        durationMs: 560,
      },
      {
        name: 'records.query',
        args: { fields: ['phosphorylation_degree', 'kinase_identity'], requireMethod: true },
        durationMs: 470,
      },
    ],
    answerMd: `Twelve prior-art entries. **No host has both a high level and a secreted product.** An em dash below means the corpus states nothing.

| Entry | Host | Level | Location | Phosphorylated? | Method |
|---|---|---|---|---|---|
| [[H2]] | *E. coli* + CK2, human β | 500 mg/L [[r-H2-1]] | intracellular | yes | LC-ESI-MS [[r-H2-2]] |
| [[H3]] | *E. coli* + CK2, bovine β | 200 mg/L [[r-H3-1]] | intracellular | partial | LC-ESI-MS [[r-H3-2]] |
| [[H4]] | *P. pastoris*, bovine β | 15–18 % TSP [[r-H4-1]]; 0.7–1.0 g/L [[r-H4-2]] | 0.005 % secreted [[r-H4-3]] | native degree | urea-PAGE + phosphatase [[r-H4-4]] |
| [[H5]] | — | 1 g/L [[r-H5-1]] | — | — | — |
| [[H6]] | *S. cerevisiae* | — | periplasmic | urea-gel mobility matches bovine | urea-PAGE |
| [[H7]] | *S. cerevisiae* | 10 mg/L [[r-H7-1]] | 5–10 % secreted [[r-H7-2]] | — | — |
| [[H11]] | *E. coli* | — | — | — | — |
| [[H12]] | *E. coli*, human β | — | — | no [[r-H12-1]] | — |
| [[H13]] | — | — | — | non-phosphorylated [[r-H13-1]] | — |
| [[H14]] | bacterial, αs1 | 1.45 g/L [[r-H14-1]] | — | — | — |
| [[H15]] | soybean, bovine β | 0.1–0.4 % TSP [[r-H15-1]] | intracellular | no [[r-H15-2]] | MALDI-MS |
| [[H16]] | *L. lactis*, αs1 fusion | — | — | — | — |

[[H14]] and [[H16]] are αs1-casein, not β; they are kept in because they anchor the bacterial ceiling and the food-grade precedent.

Seven rows name no method at all. [[H1]] records "undetermined" for most bacterial studies because the analysis was never done [[r-H1-4]] — silence, not a negative result.

*Every cell is transcribed from curator notes, not read off a source PDF.*`,
    followups: [
      'flow:F2|Is any of it actually phosphorylated?',
      'flow:F9|Compare Chlamydomonas and Pichia',
      'flow:F6|Has anyone done this in an alga?',
    ],
  },

  // ── F2 — the CK2 pair, answered in three parts ──────────────────────
  {
    id: 'F2',
    triggers: [
      'is recombinant casein phosphorylated',
      'does recombinant beta-casein carry phosphate',
      'has anyone phosphorylated a recombinant casein',
      'can ck2 phosphorylate bovine casein',
      'phosphorylation status of recombinant casein',
    ],
    plan: [
      'Parse question — field phosphorylation_degree, kinase_identity',
      'Retrieve the H2/H3 co-expression pair',
      'Separate human from bovine β-casein',
      'Check whether FAM20C has been demonstrated in a heterologous host',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'casein co-expression kinase CK2 FAM20C phosphorylation achieved', k: 6 },
        durationMs: 880,
        retrieval: [
          {
            paperId: 'H3',
            sectionId: 's1',
            score: 0.94,
            snippet:
              'In human β-casein the serine clusters align well with CK2 consensus sites; in bovine β-casein only some cluster serines sit in canonical CK2 sites',
          },
          {
            paperId: 'H2',
            sectionId: 's1',
            score: 0.9,
            snippet:
              'Polycistronic construct encoding human β-casein with both α and β subunits of human CK2',
          },
          {
            paperId: 'H8',
            sectionId: 's1',
            score: 0.83,
            snippet:
              'Attempts to express both FAM20C versions in E. coli failed — successful human FAM20C expression has to date been achieved only in human cell lines',
          },
          {
            paperId: 'H4',
            sectionId: 's1',
            score: 0.68,
            snippet:
              'Phosphorylation analysis (phosphatase treatment + Urea-PAGE) showed the recombinant protein carried the same degree of phosphorylation as animal-derived β-casein',
          },
        ],
      },
      {
        name: 'records.query',
        args: { fields: ['kinase_identity', 'phosphorylation_degree'], organism: ['ecoli', 'bovine'] },
        durationMs: 520,
      },
    ],
    answerMd: `Three answers, and which one applies depends on the casein and the kinase.

**Human β-casein with CK2 — yes.** [[H2]] co-expressed human β-casein with both α and β subunits of human CK2 and reached **500 mg/L** of phosphorylated product [[r-H2-1]], characterised by urea-PAGE, SDS-PAGE and negative-ion LC-ESI-MS [[r-H2-2]]. That remains the highest-yield phosphorylated recombinant casein in the corpus.

**Bovine β-casein with CK2 — only partially.** [[H3]] is the companion result: **200 mg/L** [[r-H3-1]], at much lower phosphorylation than the native 5-phosphate state [[r-F5-1]]. The cause is sequence, not technique. In human β-casein the serine clusters align well with CK2 consensus sites; in bovine β-casein only some cluster serines sit in canonical CK2 sites [[r-H3-2]]. A bovine programme cannot borrow the human result.

**Bovine β-casein with FAM20C — not demonstrated at all.** [[H8]] screened five kinases and reports that expressing either human or bovine FAM20C in *E. coli* failed [[r-H8-6]]; success to date is only in human cell lines. No entry in this corpus reports FAM20C-phosphorylated casein from any heterologous production host.

One eukaryotic complication: [[H4]] reports bovine β-casein from *P. pastoris* carrying the same degree of phosphorylation as animal-derived protein [[r-H4-4]] — and does not name the enzyme that did it. The corpus records that gap rather than filling it.

*All four claims are curator transcriptions, not source-span extractions.*`,
    followups: [
      'flow:F11|What is FAM20C, exactly?',
      'flow:F8|How is phosphorylation measured?',
      'flow:F3|Does it matter for cheese?',
    ],
  },

  // ── F3 — the product fork (clarify) ─────────────────────────────────
  {
    id: 'F3',
    triggers: [
      'does phosphorylation actually matter for making cheese',
      'does phosphorylation matter for cheese',
      'do i need phosphorylated casein to make cheese',
      'why does casein phosphorylation matter',
      'can i make cheese with unphosphorylated casein',
    ],
    plan: [
      'Parse question — functional family, gelation and micellar fields',
      'Retrieve the dephosphorylation series',
      'Check for counter-evidence before answering',
      'Split the answer by product application',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'phosphorylation degree micelle reassembly gelation coagulation', k: 6 },
        durationMs: 900,
        retrieval: [
          {
            paperId: 'I1',
            sectionId: 's1',
            score: 0.96,
            snippet:
              'Gelation pH rose as phosphorylation fell, and fully dephosphorylated caseins failed to gel entirely, precipitating at their isoelectric point around pH 5.5',
          },
          {
            paperId: 'I1',
            sectionId: 's1',
            score: 0.91,
            snippet:
              'Across all three systems roughly 87% of total protein was sedimentable in the fully phosphorylated case',
          },
          {
            paperId: 'I2',
            sectionId: 's1',
            score: 0.77,
            snippet:
              'Artificial casein micelles composed predominantly of dephosphorylated casein form irregular structures roughly three times larger than normal',
          },
          {
            paperId: 'I9',
            sectionId: 's1',
            score: 0.72,
            snippet:
              'recombinant non-phosphorylated αs1-casein can stabilize emulsion and foam interfaces, indicating that for some food applications phosphorylation may be unnecessary',
          },
        ],
      },
      {
        name: 'records.query',
        args: { fields: ['micellar_fraction', 'gelation_ph', 'phosphorylation_degree'], requireMethod: true },
        durationMs: 500,
      },
    ],
    answerMd: `For cheese and yogurt, yes — and the failure mode is binary, not gradual.

[[I1]] dephosphorylated four bovine caseins into three pools and reassembled nine micelle systems. Reassembly tracked phosphorylation degree: roughly **87 % of protein was sedimentable** when fully phosphorylated [[r-I1-1]], while fully dephosphorylated caseins hardly formed micelles at all [[r-I1-3]] and failed to gel entirely, precipitating at their isoelectric point near **pH 5.5** [[r-I1-2]]. [[I2]] gives the structural version — artificial micelles built predominantly from dephosphorylated casein form irregular structures roughly **three times larger** than normal [[r-I2-1]].

Applied to this programme: an unphosphorylated cw15-derived β-casein does not make a weak curd. It makes no curd.

**But the product fork is real.** [[I9]] gathers the counter-evidence: recombinant non-phosphorylated αs1-casein has been reported to stabilise emulsion and foam interfaces [[r-I9-1]], and functional artificial micelles can be built from two or three caseins rather than all four. The same entry notes that artificial casein micelle formation from recombinant caseins has so far been unsuccessful, largely for PTM reasons.

So emulsifier and foaming applications are reachable **without** solving phosphorylation; cheese and yogurt are not. Those are two different programmes with two different risk profiles, and the corpus does not let you have both for one price.

*I1, I2 and I9 are catalogued entries — the numbers above come from curator notes pending source verification.*`,
    followups: [
      'flow:F2|Can we phosphorylate it at all?',
      'flow:F10|What does β-casein cost today?',
    ],
    clarify: {
      question: 'Which product are you designing against? The evidence forks here.',
      options: [
        { label: 'Cheese and yogurt — coagulation is required', flowId: 'F2' },
        { label: 'Emulsifier and foaming — phosphorylation may not be', flowId: 'F1' },
      ],
    },
  },

  // ── F4 — citation-of-a-citation ─────────────────────────────────────
  {
    id: 'F4',
    triggers: [
      'what is the maximum secreted protein yield from chlamydomonas',
      'max secreted yield from chlamydomonas',
      'how much protein can chlamydomonas secrete',
      'best secretion titer in c reinhardtii',
      'highest secreted protein from uvm4',
    ],
    plan: [
      'Parse question — organism uvm4, field titer_secreted',
      'Retrieve secretion entries from thread C',
      'Check isPrimary before counting any value twice',
      'Report the ceiling with its provenance chain',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'secreted yield mg/L Chlamydomonas glycomodule UVM4', k: 5, filters: { thread: 'C' } },
        durationMs: 870,
        retrieval: [
          {
            paperId: 'C2',
            sectionId: 's1',
            score: 0.96,
            snippet:
              'raised yields up to 12-fold, reaching a maximum of 15 mg/L, and conferred enhanced proteolytic stability',
          },
          {
            paperId: 'C6',
            sectionId: 's1',
            score: 0.84,
            snippet:
              'It recites the yield history: 0.2% TSP intracellular (Neupert 2009) → 12–15 mg/L secreted (Lauersen 2013; Ramos-Martinez 2017)',
          },
          {
            paperId: 'K1',
            sectionId: 's1',
            score: 0.59,
            snippet: '1 g/L secreted from a fungus vs 15 mg/L from UVM4 is a 65× gap',
          },
        ],
      },
      {
        name: 'records.query',
        args: { field: 'titer_secreted', organism: 'uvm4', includeNonPrimary: true },
        durationMs: 480,
      },
    ],
    answerMd: `**15 mg/L** — and it is one measurement, not two.

[[C2]] is the source. A C-terminal fusion of synthetic glycomodules of tandem Ser-Pro repeats, (SP)10 and (SP)20, to Venus secreted via the putative gametolysin signal sequence raised yields up to **12-fold** [[r-C2-2]], reaching a maximum of **15 mg/L** [[r-C2-1]] with enhanced proteolytic stability.

[[C6]] looks like independent corroboration and is not. It is the UVM4 secretome study, and its **12–15 mg/L** [[r-C6-1]] recites prior work — it cites Lauersen 2013 and Ramos-Martinez 2017 rather than measuring anything. That record is flagged non-primary and points back at [[r-C2-1]]. **Counting both would turn a single data point into a replicated consensus.** The same trap applies to the 0.2 % TSP figure in the same sentence [[r-C6-2]], which recites [[r-A1-1]].

So: one primary secretion measurement in the entire corpus, on a fluorescent reporter, not on a casein.

For scale, [[K1]] reports **1 g/L** secreted β-lactoglobulin from *T. reesei* [[r-K1-1]] — roughly 65× higher, and a whey protein rather than a casein.

*Both entries are catalogued. The citation relationship is recorded in OF-COR-001 and should be confirmed against both PDFs before it is quoted as fact.*`,
    followups: [
      'flow:F5|Why cw15 rather than a walled strain?',
      'flow:F7|Which signal peptide should I use?',
      'flow:F9|How does Pichia compare?',
    ],
  },

  // ── F5 — the chassis argument, with its counterweights ──────────────
  {
    id: 'F5',
    triggers: [
      'why cw15 rather than a walled strain',
      'why use cw15',
      'why a cell wall deficient strain',
      'what is the case for cw15 over wild type',
      'why not a walled chlamydomonas strain',
    ],
    plan: [
      'Parse question — organism cw15 vs creinhardtii-wt',
      'Retrieve transformation, expression and disruption evidence',
      'Retrieve the stated trade-offs, not only the case for',
      'Assemble reasons and counterweights side by side',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: {
          query: 'cell wall deficient cw15 transformation disruption shear trade-off',
          k: 6,
          filters: { organism: ['cw15', 'uvm4'] },
        },
        durationMs: 910,
        retrieval: [
          {
            paperId: 'J10',
            sectionId: 's1',
            score: 0.93,
            snippet:
              'PEF applied to a cell-wall-deficient mutant gave an average protein yield of 31 ± 6% versus 11 ± 3% for the walled wild type',
          },
          {
            paperId: 'B5',
            sectionId: 's1',
            score: 0.89,
            snippet:
              'colonies appear on selection in 7–10 days for cw15 and UVM4 versus 15–20 days for WT12',
          },
          {
            paperId: 'B5',
            sectionId: 's1',
            score: 0.81,
            snippet:
              'cell-wall-deficient strains have reduced motility and mating ability and are much more susceptible to shear and osmotic stress',
          },
          {
            paperId: 'A1',
            sectionId: 's1',
            score: 0.74,
            snippet: 'Both reach ~0.2% of total soluble protein for intracellular GFP/YFP',
          },
          {
            paperId: 'C6',
            sectionId: 's1',
            score: 0.66,
            snippet:
              'secreted recombinant proteins become trapped in a matrix of these aggregates, making isolation and purification difficult',
          },
        ],
      },
      {
        name: 'records.query',
        args: { fields: ['time_to_colony', 'disruption_protein_yield', 'expression_pct_tsp'] },
        durationMs: 510,
      },
    ],
    answerMd: `Three independent reasons, and two costs the corpus states just as plainly.

**1 — Transformability.** [[B5]] compares cw15, UVM4 and walled WT12 in one study: colonies appear on selection in **7–10 days** for the wall-deficient strains [[r-B5-1]] against **15–20 days** for WT12 [[r-B5-3]].

**2 — Expression lineage.** [[A1]] derived UVM4 and UVM11 from cw15-302 by UV mutagenesis and selection for high transgene expression; both reach ~**0.2 % of total soluble protein** for intracellular reporters [[r-A1-1]]. Every expression figure this programme quotes descends from that lineage.

**3 — Cheap disruption.** [[J10]] recovered **31 ± 6 %** of total protein from a wall-deficient mutant under pulsed electric field [[r-J10-1]] against **11 ± 3 %** from the walled wild type [[r-J10-2]] — roughly **three-fold** [[r-J10-3]], at mild conditions.

**Counterweight 1 — shear.** [[B5]] states it outright: wall-deficient strains have reduced motility and mating ability and are much more susceptible to shear and osmotic stress. That is an impeller-and-sparge constraint, not a footnote.

**Counterweight 2 — the secretome.** [[C6]] found UVM4 secretes unassembled cell wall glycoproteins whose aggregates trap recombinant product, making isolation genuinely hard. Read together with reason 3, that argues for accumulating intracellularly and disrupting mildly rather than secreting.

*Note what reason 2 does not say: 0.2 % TSP was measured on GFP/YFP reporters, never on a casein.*`,
    followups: [
      'flow:F4|What is the secretion ceiling here?',
      'flow:F12|Is it approved as food?',
      'flow:F9|Compare with Pichia',
    ],
  },

  // ── F6 — the substantive decline; the most important flow ───────────
  {
    id: 'F6',
    triggers: [
      'has anyone expressed a casein in an alga',
      'has casein been expressed in algae',
      'any algal casein papers',
      'is there prior art for casein in microalgae',
      'casein expression in chlamydomonas prior art',
    ],
    plan: [
      'Parse question — target casein, host class microalga',
      'Retrieve the systematic prior-art review and its tables',
      'Search the patent landscape for any algal claim',
      'Report the absence and what it rests on',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'casein expressed in algae microalga heterologous host survey', k: 8 },
        durationMs: 1020,
        retrieval: [
          {
            paperId: 'H1',
            sectionId: 's1',
            score: 0.9,
            snippet:
              'Table 1 — 17 bacterial studies. Table 2 — 5 yeast studies, expression 0.6 mg/L to 1 g/L. Table 3 — 2 plant studies',
          },
          {
            paperId: 'H17e',
            sectionId: 's1',
            score: 0.77,
            snippet:
              'WO2024015365A1 (Kiverdi) — recombinant food proteins in chemoautotrophic microorganisms, host list includes algae; the only algal claim found',
          },
          {
            paperId: 'N4',
            sectionId: 's1',
            score: 0.61,
            snippet:
              'a heterologous food protein expressed in C. reinhardtii for nutritional purposes',
          },
          {
            paperId: 'K5',
            sectionId: 's1',
            score: 0.52,
            snippet:
              'VERIFY AT INGEST whether this review already names microalgae as a candidate host',
          },
        ],
      },
      {
        name: 'records.query',
        args: { field: 'expression_pct_tsp', organism: ['cw15', 'uvm4'], componentTag: 'casein' },
        durationMs: 430,
      },
    ],
    answerMd: `**No.** And the absence is structural, not a retrieval failure.

[[H1]] is a systematic search of the literature and patent databases for heterologous casein expression. Its tables enumerate **17 bacterial studies**, **5 yeast studies** spanning 0.6 mg/L to 1 g/L [[r-H1-1]], and **2 plant studies** — potato at 0.01 % TSP [[r-H1-2]] and soybean at 0.1–0.4 % TSP, not phosphorylated [[r-H1-3]]. There is no algal row.

The only adjacent claim is a patent. [[H17e]] — WO2024015365A1, Kiverdi — covers recombinant food proteins in chemoautotrophic microorganisms and lists algae generically among possible hosts. It names no casein, no strain, and no yield.

The nearest published work in this actual host is [[N4]]: zeolin, a γ-zein/phaseolin chimera, expressed in *C. reinhardtii* as a nutritional protein. A heterologous food protein — not a casein.

**What the absence means.** This is the programme's white space, and it is defensible rather than accidental: caseins go into bacteria, yeast and plants because those hosts are cheap and well-tooled, and every one of them fails on the same kinase. Two caveats keep the claim honest. [[K5]] is behind a publisher block and is flagged for verification at ingest precisely because it may already name microalgae as a candidate host. And this corpus is a curated slice, not the whole literature.

*A search engine returns nothing here. Recording why nothing exists is the part that took curation.*`,
    followups: [
      'flow:F9|Compare Chlamydomonas and Pichia',
      'flow:F5|Why cw15 at all?',
      'flow:F1|What titers exist in other hosts?',
    ],
  },

  // ── F7 — signal peptide selection ───────────────────────────────────
  {
    id: 'F7',
    triggers: [
      'what signal peptide should i use',
      'which signal peptide for secretion in chlamydomonas',
      'best signal peptide for csn2',
      'compare secretory signal peptides',
      'which sp should i fuse to my transgene',
    ],
    plan: [
      'Parse question — localization, signal peptide selection',
      'Retrieve the thread C signal-peptide comparisons',
      'Rank by whether a working cassette is published',
      'Flag the negative result on native mammalian SPs',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'secretory signal peptide comparison ARS2 CAH1 BiP1 gametolysin', k: 6, filters: { thread: 'C' } },
        durationMs: 890,
        retrieval: [
          {
            paperId: 'C3',
            sectionId: 's1',
            score: 0.94,
            snippet:
              'Ten signal peptides evaluated, drawn from four classes of natively secreted protein: BiP1, ARS1, CAH1, and IBP1, plus newly identified sequences from unexplored regions of the genome — two of which outperformed the established set',
          },
          {
            paperId: 'C7',
            sectionId: 's1',
            score: 0.87,
            snippet:
              'the 21-amino-acid leader peptide of arylsulfatase ARS2 (Cre16.g671350, Phytozome v5.5) inserted upstream of the coding sequence, with APHVIII for selection, expressing VEGF-165',
          },
          {
            paperId: 'C8',
            sectionId: 's1',
            score: 0.8,
            snippet:
              'Carries a consolidated table of SPs used in Chlamydomonas reinhardtii: FEA1, ARS1/ARS2, CAH1, BiP1, gametolysin',
          },
          {
            paperId: 'C4',
            sectionId: 's1',
            score: 0.58,
            snippet:
              'LC-MS/MS confirms the ARS1 signal peptide is correctly cleaved during ER transit',
          },
        ],
      },
    ],
    answerMd: `Three entries carry the comparison, and none of them tested a casein.

| Rank | Entry | What it gives you |
|---|---|---|
| 1 | [[C7]] | The only complete published cassette in this host — the 21-amino-acid ARS2 leader (Cre16.g671350) upstream of the CDS, APHVIII selection, VEGF-165 in UVM4/UVM11. Start here because it is the one you can copy. |
| 2 | [[C3]] | The decision table: ten SPs across four classes of natively secreted protein (BiP1, ARS1, CAH1, IBP1) plus newly identified genomic sequences, two of which outperformed the established set. |
| 3 | [[C8]] | Evidence that a non-native SP works at all — one from a ~17 kDa secreted *Chlorella* protein — plus a consolidated table of SPs used in *C. reinhardtii*. |

[[C4]] is worth reading alongside them: LC-MS/MS confirmed the ARS1 signal peptide is correctly cleaved during ER transit, which is the check most SP comparisons skip.

**One thing the corpus settles negatively.** Do not use the native bovine β-casein signal peptide. [[H4]] did exactly that in *P. pastoris* and secreted **0.005 %** of the intracellular level [[r-H4-3]] — a non-mammalian eukaryote does not read it.

*The ranking is mine, built on which entry carries a working construct. The two high-performing sequences in [[C3]] are unnamed in the curation note — identifying them means reading the PDF.*`,
    followups: [
      'flow:F4|What is the secretion ceiling?',
      'flow:F5|Why cw15 rather than a walled strain?',
    ],
  },

  // ── F8 — methods, tied to the ontology's mandatory qualifier ────────
  {
    id: 'F8',
    triggers: [
      'how is casein phosphorylation measured',
      'how do you measure phosphorylation',
      'what methods detect casein phosphorylation',
      'phosphorylation analysis methods',
      'how do i assay phospho sites on casein',
    ],
    plan: [
      'Parse question — analytical method behind the PTM family',
      'Retrieve the review section that enumerates methods',
      'Map each method onto records that used it',
      'Connect to the ontology method qualifier',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'phosphorylation analysis methods MALDI Phos-tag urea-PAGE Stains-All', k: 5 },
        durationMs: 850,
        retrieval: [
          {
            paperId: 'H1',
            sectionId: 's1',
            score: 0.95,
            snippet:
              'Reviews four phosphorylation analysis methods (MALDI-MS / LC-ESI-MS; SDS-PAGE with Ethyl Stains-All; Urea-PAGE with phosphatase treatment; Phos-tag)',
          },
          {
            paperId: 'H1',
            sectionId: 's1',
            score: 0.86,
            snippet:
              'Records "undetermined" for most bacterial studies because the analysis was never done',
          },
          {
            paperId: 'H4',
            sectionId: 's1',
            score: 0.7,
            snippet: 'Phosphorylation analysis (phosphatase treatment + Urea-PAGE)',
          },
          {
            paperId: 'H15',
            sectionId: 's1',
            score: 0.62,
            snippet: 'not phosphorylated by MALDI-MS',
          },
        ],
      },
      {
        name: 'ontology.lookup',
        args: { fields: ['phosphorylation_degree', 'phosphate_count'], property: 'requiresMethod' },
        durationMs: 300,
      },
    ],
    answerMd: `[[H1]] reviews four, and the ontology makes naming one mandatory.

| Method | What it resolves | Trade-off |
|---|---|---|
| MALDI-MS / LC-ESI-MS | Mass-resolved, site-level | Most informative; [[H2]] used negative-ion LC-ESI-MS [[r-H2-2]], [[H15]] used MALDI-MS to report a negative [[r-H15-2]] |
| SDS-PAGE with Ethyl Stains-All | Phosphoprotein-selective stain | Qualitative — presence or absence, not stoichiometry |
| Urea-PAGE with phosphatase treatment | Mobility shift before and after dephosphorylation | Comparative, not absolute; [[H4]] used it for its native-degree claim [[r-H4-4]] |
| Phos-tag | Retardation of individual phospho-species | Resolves phospho-forms, still gel-based |

This is why \`phosphorylation_degree\`, \`phosphate_count\` and \`glycan_species\` all carry a mandatory \`method\` qualifier. "Phosphorylated: yes" is not interpretable without knowing whether it came from a mass spectrum or a gel mobility inference — and the platform refuses to store one without the other.

The qualifier also has to hold two states apart. \`undetermined\` means the analysis was never done: [[H1]] records exactly that for most bacterial studies [[r-H1-4]]. A measured negative — [[H15]]'s MALDI-MS result on soybean-expressed β-casein [[r-H15-2]] — is a finding. Collapsing the two would manufacture agreement out of silence.

*The method list is transcribed from the H1 curation note; the review's own comparison of their sensitivities has not been read.*`,
    followups: [
      'flow:F2|Is recombinant casein phosphorylated?',
      'flow:F11|What is FAM20C?',
      'flow:F3|Does phosphorylation matter for cheese?',
    ],
  },

  // ── F9 — the head-to-head ───────────────────────────────────────────
  {
    id: 'F9',
    triggers: [
      'compare chlamydomonas and pichia as casein hosts',
      'chlamydomonas vs pichia',
      'algae or yeast for casein',
      'which host is better for beta casein',
      'head to head chlamydomonas pichia',
    ],
    plan: [
      'Parse question — organism comparison cw15/uvm4 vs gs115',
      'Retrieve expression, density and precedent evidence for each',
      'Normalise units; refuse % TSP to g/L conversion',
      'Report the gaps without softening them',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'Chlamydomonas Pichia expression density casein host comparison', k: 8 },
        durationMs: 970,
        retrieval: [
          {
            paperId: 'H4',
            sectionId: 's1',
            score: 0.93,
            snippet:
              'approximately 15–18% of total soluble protein, corresponding to 0.7–1.0 g/L',
          },
          {
            paperId: 'M8',
            sectionId: 's1',
            score: 0.85,
            snippet:
              'The density gap between 1–2 g/L mixotrophic Chlamydomonas and 100+ g/L Pichia fed-batch is the harshest number in the corpus',
          },
          {
            paperId: 'A1',
            sectionId: 's1',
            score: 0.78,
            snippet: 'Both reach ~0.2% of total soluble protein for intracellular GFP/YFP',
          },
          {
            paperId: 'M5',
            sectionId: 's1',
            score: 0.7,
            snippet: 'Wild-type CC-137c in TAP reached a maximum density of 1.23 ± 0.13 g/L within 96 h',
          },
          {
            paperId: 'J10',
            sectionId: 's1',
            score: 0.61,
            snippet: 'comparable to mechanical disruption but under mild conditions',
          },
        ],
      },
      {
        name: 'records.query',
        args: {
          fields: ['expression_pct_tsp', 'titer_intracellular', 'titer_secreted', 'final_biomass_density'],
          organism: ['cw15', 'uvm4', 'gs115', 'creinhardtii-wt'],
        },
        durationMs: 620,
      },
    ],
    answerMd: `Not close on any number the corpus records.

| Axis | *C. reinhardtii* cw15 / UVM4 | *K. phaffii* GS115 |
|---|---|---|
| Intracellular level | ~0.2 % TSP, reporters only [[r-A1-1]] | 15–18 % TSP, β-casein [[r-H4-1]] |
| Intracellular titer | none recorded for any casein | 0.7–1.0 g/L [[r-H4-2]] |
| Best secreted titer | 15 mg/L, reporter + glycomodule [[r-C2-1]] | 0.005 % of intracellular [[r-H4-3]] |
| Cell density | 1.23 g/L [[r-M5-1]] to 2.15 g/L [[r-M6-1]] | 100+ g/L fed-batch, curation note only [[M8]] |
| Casein precedent | none [[H1]] | bovine β-casein at native-degree phosphorylation [[r-H4-4]] |

Roughly eighty-fold on expression level and two orders of magnitude on density — and [[O3]] finds minimum selling price inversely tied to exactly those two parameters, biomass density and target protein content.

What the alga has instead: cheap disruption ([[J10]], **31 ± 6 %** protein release under PEF [[r-J10-1]] versus **11 ± 3 %** walled [[r-J10-2]]), US GRAS standing [[N2]], and a secretory pathway the yeast also has.

**On published numbers, *Pichia* wins outright.** The algal case rests on downstream cost and regulatory position, not on titer, and it should be argued that way rather than on expression.

*Two honesty notes: the density figures were measured on walled wild-type cultures rather than cw15 [[M5]], and the 100+ g/L yeast figure has no extraction record behind it — OF-COR-001 states it in prose only.*`,
    followups: [
      'flow:F5|Why cw15 at all, then?',
      'flow:F10|What does it cost to produce?',
      'flow:F6|Is there any algal casein prior art?',
    ],
  },

  // ── F10 — cost, with the provenance firewall (clarify) ──────────────
  {
    id: 'F10',
    triggers: [
      'what does β-casein cost to produce today',
      'what does beta-casein cost to produce',
      'cost per kg of recombinant casein',
      'how much does precision fermentation casein cost',
      'production cost of recombinant milk protein',
    ],
    plan: [
      'Parse question — field minimum_selling_price',
      'Retrieve TEA entries from thread O',
      'Partition by provenance class before aggregating',
      'Report peer-reviewed and industry figures separately',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'techno-economic minimum selling price protein cost per kg', k: 6, filters: { thread: 'O' } },
        durationMs: 930,
        retrieval: [
          {
            paperId: 'O2',
            sectionId: 's1',
            score: 0.94,
            snippet:
              'Biomass-fermentation protein costs converge around $4–6/kg, against beef and pork market prices of $6.0–15.0/kg',
          },
          {
            paperId: 'O3',
            sectionId: 's1',
            score: 0.88,
            snippet:
              'Minimum selling price for crude protein ranged $2,300/kg (1 L empirical) to $75/kg (optimistic); purified protein ranged $99,000/kg to $970/kg',
          },
          {
            paperId: 'O8',
            sectionId: 's1',
            score: 0.81,
            snippet:
              'cost falling from about USD 1 million/kg in 2000 to roughly USD 100/kg currently, forecast below USD 10/kg by 2030',
          },
          {
            paperId: 'O8m',
            sectionId: 's1',
            score: 0.64,
            snippet:
              'NON-PEER-REVIEWED market and vendor sources report precision-fermentation whey protein at $25–30/kg in 2025',
          },
        ],
      },
      {
        name: 'records.query',
        args: { field: 'minimum_selling_price', groupBy: 'provenance', excludeFromAggregate: 'industry-estimate' },
        durationMs: 540,
      },
    ],
    answerMd: `There is no β-casein cost model in this corpus. There are three adjacent ones, and they must not be blended.

**Peer-reviewed process models.** [[O2]] meta-analyses 55 published TEAs: biomass-fermentation protein converges around **$4–6/kg** [[r-O2-1]], against beef and pork at $6.0–15.0/kg. [[O3]] sizes four scenarios to 80,000 kg/y and gets **$75–2,300/kg** crude [[r-O3-2]] and **$970–99,000/kg** purified [[r-O3-3]], with cost inversely tied to biomass density and target protein content.

**Peer-reviewed trajectory.** [[O8]] records the fall from about **$1,000,000/kg** in 2000 [[r-O8-1]] to roughly **$100/kg** now [[r-O8-2]], forecast below **$10/kg** by 2030 [[r-O8-3]].

**Industry estimates — quarantined.** [[O8m]] holds the vendor and market claims: whey protein at **$25–30/kg** in 2025 [[r-O8m-1]] targeting **$8–12/kg** by 2028 [[r-O8m-2]], casein parity around 2028–2030. Provenance class \`industry-estimate\`: never gold, never in a default aggregate, rendered with its own tick.

**Why the firewall matters.** [[O2]] shows published models assume ~**24 g/L** titer [[r-O2-3]] while private benchmarks average ~**42 g/L** [[r-O2-4]], over volumes ten times larger. The two literatures describe different plants, so a blended mean describes neither — and the vendor 2028 target happens to sit near the peer-reviewed 2030 ceiling, which reads as corroboration only if you let it.`,
    followups: [
      'flow:F9|Which host drives the cost?',
      'flow:F4|What secreted yield is reachable?',
    ],
    clarify: {
      question: 'Which cost driver do you want to chase? O3 says there are only two that matter.',
      options: [
        { label: 'Biomass density and % TSP — the host choice', flowId: 'F9' },
        { label: 'Secreted yield — skipping disruption entirely', flowId: 'F4' },
      ],
    },
  },

  // ── F11 — FAM20C and the compartment argument ───────────────────────
  {
    id: 'F11',
    triggers: [
      'what is fam20c and why cant e coli make it',
      'what is fam20c',
      'why cant e coli express fam20c',
      'why does fam20c need a secretory pathway',
      'fam20c expression failure in bacteria',
    ],
    plan: [
      'Parse question — kinase_identity, host capability',
      'Retrieve the identification and structure papers',
      'Retrieve the reported expression failure',
      'Separate the structural argument from the empirical one',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'FAM20C Golgi casein kinase structure disulfide glycosylation E. coli', k: 6 },
        durationMs: 900,
        retrieval: [
          {
            paperId: 'G1',
            sectionId: 's1',
            score: 0.96,
            snippet:
              'Fam20C is the authentic Golgi casein kinase. It phosphorylated recombinant β-casein in a time-dependent manner while the catalytically inactive D478A mutant, unable to coordinate Mn²⁺, did not',
          },
          {
            paperId: 'G4',
            sectionId: 's1',
            score: 0.9,
            snippet:
              'an atypical kinase-like fold with disulfide bridges, N-linked glycosylation, and a novel insertion domain conserved across Fam20 members',
          },
          {
            paperId: 'H8',
            sectionId: 's1',
            score: 0.84,
            snippet: 'Attempts to express both FAM20C versions in E. coli failed',
          },
          {
            paperId: 'G9',
            sectionId: 's1',
            score: 0.69,
            snippet:
              'CK1 and CK2 were named for casein but lack the correct localization and do not recognize the SxE motifs',
          },
        ],
      },
      {
        name: 'records.query',
        args: { field: 'kinase_identity', value: 'FAM20C' },
        durationMs: 460,
      },
    ],
    answerMd: `FAM20C is the authentic Golgi casein kinase — the enzyme that actually phosphorylates casein, as distinct from CK1 and CK2, which were named for casein and do not recognise the motif [[r-G9-1]].

[[G1]] is the identification paper: Fam20C phosphorylated recombinant β-casein in a time-dependent manner [[r-G1-1]] while the catalytically inactive D478A mutant, unable to coordinate Mn²⁺, did not [[r-G1-2]]. [[G2]] fixes the specificity — S-x-E/pS motifs in secreted proteins, generating the majority of the extracellular phosphoproteome [[r-G2-1]]. [[G9]] supplies the discriminating assay: a synthetic peptide spanning a bovine β-casein phosphorylation site, β(28–40) in mature numbering [[r-G9-3]] [[r-G9-4]], was phosphorylated by the Golgi casein kinase but not by CK1 or CK2 [[r-G9-2]].

**Why *E. coli* cannot make it.** [[G4]] solved the *C. elegans* ortholog: an atypical kinase-like fold carrying **disulfide bridges** and **N-linked glycosylation** [[r-G4-1]]. Both require transit through a secretory compartment to form. *E. coli* has none, so the kinase cannot fold there — a structural prediction, not a technique problem. [[H8]] is the empirical confirmation: attempts to express both human and bovine FAM20C in *E. coli* failed [[r-H8-6]], with success to date only in human cell lines.

That argument is what puts a Golgi-bearing host on the table at all. It does **not** show *Chlamydomonas* can host it — [[D5]] records that no retrieved source establishes whether this alga has a Fam20-family kinase, and the indirect evidence points toward absence.`,
    followups: [
      'flow:F2|Is recombinant casein phosphorylated?',
      'flow:F8|How would I measure it?',
      'flow:F-SIALYL|What glycans does the alga add?',
    ],
  },

  // ── F12 — regulatory position, stated precisely ─────────────────────
  {
    id: 'F12',
    triggers: [
      'what is the regulatory status of c reinhardtii as food',
      'is chlamydomonas approved as food',
      'regulatory status of chlamydomonas reinhardtii',
      'is c reinhardtii gras',
      'efsa opinion on chlamydomonas',
    ],
    plan: [
      'Parse question — regulatory thread, jurisdiction split',
      'Retrieve the GRAS listing and the EFSA opinion',
      'Check whether the EFSA outcome was procedural or substantive',
      'State each jurisdiction separately',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'GRAS EFSA novel food Chlamydomonas reinhardtii safety', k: 5, filters: { thread: 'N' } },
        durationMs: 860,
        retrieval: [
          {
            paperId: 'N2',
            sectionId: 's1',
            score: 0.95,
            snippet:
              'Records the short list of microalgae with FDA GRAS status: Arthrospira platensis, Chlamydomonas reinhardtii',
          },
          {
            paperId: 'N3',
            sectionId: 's1',
            score: 0.92,
            snippet:
              'requested additional information repeatedly, received no reply, and concluded that the safety of the novel food could not be established',
          },
          {
            paperId: 'N3',
            sectionId: 's1',
            score: 0.79,
            snippet:
              'the failure was procedural rather than a finding of harm',
          },
        ],
      },
    ],
    answerMd: `Split, and the split is jurisdictional rather than scientific.

**United States — GRAS.** [[N2]] records *C. reinhardtii* on the short list of microalgae with FDA GRAS status for human consumption, alongside *Arthrospira platensis*, *Auxenochlorella protothecoides*, *Chlorella vulgaris*, *Dunaliella bardawil* and *Euglena gracilis*. That status applies only in U.S. jurisdiction.

**European Union — not established.** [[N3]] is the 2025 EFSA NDA Panel opinion on dried biomass powder of *C. reinhardtii* THN 6, filed by Triton Algae Innovations in April 2023 under Regulation (EU) 2015/2283. EFSA concluded that the safety of the novel food could not be established.

**Read that conclusion precisely.** EFSA identified data gaps across identity, production process, composition, specifications, history of use, proposed uses and use levels, nutritional information, genotoxicity and allergenicity; it requested additional information repeatedly and received no reply. The outcome was **procedural** — the dossier was never completed. It is not a finding that the alga is unsafe, and [[N3]] reports no harm. Anyone summarising this as "EFSA found *C. reinhardtii* unsafe" has inverted it.

Two consequences. US GRAS does not transfer to the EU, so an EU route needs its own novel-food dossier built to the gaps [[N3]] lists. And a *C. reinhardtii* application has already failed on the public record, which is the sort of precedent a regulator remembers.

*Both entries are catalogued; the EFSA opinion is open access and is the one to read in full first.*`,
    followups: [
      'flow:F6|Has casein been made in an alga?',
      'flow:F5|Why cw15 rather than a walled strain?',
    ],
  },

  // ── F-SIALYL — the retained conflict, presented unresolved ──────────
  {
    id: 'F-SIALYL',
    triggers: [
      'does chlamydomonas sialylate n glycans',
      'algal glycosylation of recombinant proteins',
      'what glycans does chlamydomonas add',
      'are chlamydomonas n glycans sialylated',
      'sialylation in green algae',
    ],
    plan: [
      'Parse question — field glycan_species, organism cw15',
      'Retrieve all thread D glycosylation entries',
      'Detect disagreement before synthesising',
      'Present both positions; do not average them',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'Chlamydomonas N-glycosylation oligomannoside xylose sialylated', k: 6, filters: { thread: 'D' } },
        durationMs: 910,
        retrieval: [
          {
            paperId: 'D1',
            sectionId: 's1',
            score: 0.94,
            snippet:
              'oligomannosidic N-glycans account for nearly 70% of the total N-glycan population; minor complex N-glycans are partially 6-O-methylated Man-3 to Man-5 bearing one or two xylose residues',
          },
          {
            paperId: 'D2',
            sectionId: 's1',
            score: 0.89,
            snippet:
              'proteins carry a linear Man5GlcNAc2 rather than the branched eukaryotic structure, arising from a Glc3Man5GlcNAc2 precursor and GnTI-independent Golgi processing',
          },
          {
            paperId: 'D4',
            sectionId: 's1',
            score: 0.83,
            snippet:
              'Mass spectrometry of released N-linked oligosaccharides reports mammalian-like sialylated N-glycans in total extracts',
          },
          {
            paperId: 'D3',
            sectionId: 's1',
            score: 0.51,
            snippet:
              'Insertional and CRISPR knockouts of xylosyltransferase 1A',
          },
        ],
      },
      {
        name: 'records.query',
        args: { field: 'glycan_species', organism: 'cw15', detectConflicts: true },
        durationMs: 590,
      },
    ],
    answerMd: `The corpus disagrees with itself here, and I am not going to resolve it for you.

**Position A — oligomannosidic, xylose-decorated, no sialylation.** [[D1]] reports endogenous soluble and membrane-bound proteins carrying predominantly oligomannosides from Man-2 to Man-5 [[r-D1-1]], with oligomannosidic structures accounting for nearly **70 %** of the total N-glycan population [[r-D1-2]]; the minor complex glycans are partially 6-O-methylated Man-3 to Man-5 bearing one or two xylose residues. [[D2]] extends it — a **linear Man5GlcNAc2** from a Glc3Man5GlcNAc2 precursor, processed GnTI-independently [[r-D2-1]] — and reports that complementation with Arabidopsis or *Phaeodactylum* GnTI produced no glycan change at all [[r-D2-2]], only a stress phenotype.

**Position B — mammalian-like sialylated N-glycans.** [[D4]] reports, by mass spectrometry of released N-linked oligosaccharides, sialylated N-glycans in total extracts [[r-D4-1]].

**These are incompatible.** Sialylation sits downstream of branching that Position A says does not happen; a GnTI-independent pathway stopping at oligomannose cannot also produce sialylated complex glycans. One of them is wrong, or they measured different things.

I decline to adjudicate. Both records carry \`method: undetermined\`, both are curator transcriptions, and no third entry tests the question. [[D4]] is retained deliberately as a conflict case rather than averaged away.

For this programme the stake is bounded: β-casein is not natively N-glycosylated [[D1]], so algal glycosylation is a risk to characterise, not a capability to acquire.`,
    followups: [
      'flow:F11|What is FAM20C?',
      'flow:F9|Compare Chlamydomonas and Pichia',
      'flow:F5|Why cw15?',
    ],
  },
];

/**
 * Prompt chips on the empty Ask screen. Each string is one flow's trigger
 * verbatim, so clicking a chip is an exact match rather than a fuzzy one.
 */
export const SUGGESTED_PROMPTS: string[] = [
  'What titers have been achieved for recombinant β-casein?',
  'Has anyone expressed a casein in an alga?',
  'Compare Chlamydomonas and Pichia as casein hosts',
  'What is the maximum secreted protein yield from Chlamydomonas?',
  'Does phosphorylation actually matter for making cheese?',
  'What is the regulatory status of C. reinhardtii as food?',
];
