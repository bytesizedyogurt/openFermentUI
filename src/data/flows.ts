// Scripted agent flows (OF-DES-001 §14.7, §16.2).
//
// A flow is the complete data behind one turn: the plan, the tool calls with
// their retrieval sets, the answer, and the follow-ups. The Inspector renders
// this same object, so the trace a reviewer inspects is the literal data that
// produced the answer rather than a reconstruction (§16.2, "honest by
// construction").
//
// Every retrieval snippet is copied verbatim out of the seeded section text.
// SYNTHETIC — see BUILD-SPEC.md content rules.
import type { ChatFlow } from './types';

const DEMO_FOOTER = '';

export const FLOWS: ChatFlow[] = [
  // ── F1 — the flagship demo answer ────────────────────────────────────
  {
    id: 'F1',
    triggers: [
      'what growth rates are reported for cw15 in tap',
      'growth rates for cw15 in tap',
      'reported mu for cw15',
      'how fast does cw15 grow in tap',
      'specific growth rate cw15 tap medium',
      'mu values cw15',
    ],
    plan: [
      'Parse question — organism cw15, field growth_rate_mu, medium TAP',
      'Retrieve passages (filter: organism=cw15)',
      'Query extraction records for growth_rate_mu',
      'Rank and deduplicate by paper',
      'Synthesize and attach citations',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'cw15 specific growth rate TAP mixotrophic', k: 5, filters: { organism: 'cw15' } },
        durationMs: 840,
        retrieval: [
          { paperId: 'SP-001', sectionId: 's3', score: 0.94, snippet: 'a specific growth rate of 0.118 h⁻¹' },
          { paperId: 'SP-005', sectionId: 's3', score: 0.89, snippet: 'the maximum specific growth rate of 0.141 h⁻¹ was reached at 150 µmol m⁻² s⁻¹' },
          { paperId: 'SP-003', sectionId: 's3', score: 0.85, snippet: 'cw15 grew at 0.132 h⁻¹ in mixotrophic culture' },
          { paperId: 'SP-004', sectionId: 's3', score: 0.78, snippet: 'The replete cultures grew at 0.112 h⁻¹' },
          { paperId: 'SP-002', sectionId: 's3', score: 0.74, snippet: 'the cultures grew with a specific growth rate of 0.104 h⁻¹' },
          { paperId: 'SP-009', sectionId: 's3', score: 0.71, snippet: 'Mixotrophic batch cultures grew at 0.094 h⁻¹ during the first 36 h' },
        ],
      },
      {
        name: 'records.query',
        args: { field: 'growth_rate_mu', organism: 'cw15', status: ['verified', 'unverified'] },
        durationMs: 610,
      },
    ],
    answerMd: `Six papers in this corpus report a specific growth rate for cw15 under mixotrophic conditions in TAP or a TAP variant. The verified values span **0.094–0.141 h⁻¹**, a factor of 1.5.

| Paper | μ (h⁻¹) | Condition | Record |
|---|---:|---|---|
| [[SP-005]] | 0.141 | 150 µmol m⁻² s⁻¹, light-saturated | [[ex-0036]] |
| [[SP-003]] | 0.132 | mixotrophic, standard TAP | [[ex-0020]] |
| [[SP-001]] | 0.118 | acetate-limited flask | [[ex-0001]] |
| [[SP-004]] | 0.112 | nitrogen-replete | [[ex-0030]] |
| [[SP-002]] | 0.104 | standard-buffer TAP | [[ex-0011]] |
| [[SP-009]] | 0.094 | first 36 h of batch | [[ex-0070]] |

The spread tracks illumination more than medium composition. [[SP-005]] resolves the light response directly and puts saturation near 150 µmol m⁻² s⁻¹ — the two highest rates come from the two best-lit configurations, and the lowest from a study reporting the rate averaged over the first 36 h rather than over the exponential window alone.

One caution on comparability: [[SP-009]] regresses over a fixed time window while the others regress over the interval where residuals are unstructured. That is not the same measurement, and it plausibly accounts for most of the gap between 0.094 and 0.118 h⁻¹.

A seventh value, 0.109 h⁻¹ from the high-buffer variant in [[SP-002]] ([[ex-0015]]), is extracted but **not yet verified**.`,
    followups: [
      'flow:F3|Compare mixotrophic vs photoautotrophic',
      'flow:F2|Which media are used for cw15?',
      'What does light intensity do to the rate?',
    ],
  },

  // ── F2 — media, leading to recipes ───────────────────────────────────
  {
    id: 'F2',
    triggers: [
      'which media are used for cw15',
      'what media does cw15 grow in',
      'tap medium composition',
      'media for cw15',
      'what is in tap medium',
      'medium recipe cw15',
    ],
    plan: [
      'Parse question — organism cw15, field medium_component_conc',
      'Retrieve Materials and Methods passages',
      'Group components by medium',
      'Cross-reference the protocol library',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'cw15 medium composition TAP tris acetate phosphate', k: 4, filters: { organism: 'cw15', section: 'methods' } },
        durationMs: 910,
        retrieval: [
          { paperId: 'SP-001', sectionId: 's2', score: 0.96, snippet: 'Each litre contained 2.42 g L⁻¹ Tris base' },
          { paperId: 'SP-002', sectionId: 's2', score: 0.88, snippet: 'contained 4.84 g L⁻¹ Tris base' },
          { paperId: 'SP-001', sectionId: 's2', score: 0.82, snippet: 'a final potassium phosphate concentration of 1.61 g L⁻¹' },
          { paperId: 'SP-009', sectionId: 's2', score: 0.66, snippet: 'The feed reservoir contained sodium acetate at 30.0 g L⁻¹' },
        ],
      },
      {
        name: 'protocol.lookup',
        args: { organism: 'cw15', category: 'media' },
        durationMs: 480,
      },
    ],
    answerMd: `Tris-acetate-phosphate (TAP) is the only medium used for cw15 anywhere in this corpus. Every study is either standard TAP or a declared variant of it.

**Standard TAP, per litre** — as reported in [[SP-001]]:

| Component | Concentration | Record |
|---|---:|---|
| Tris base | 2.42 g L⁻¹ | [[ex-0005]] |
| Ammonium chloride | 0.375 g L⁻¹ | [[ex-0006]] |
| Potassium phosphate | 1.61 g L⁻¹ | [[ex-0010]] |
| Magnesium sulfate heptahydrate | 0.100 g L⁻¹ | [[ex-0019]] |
| Calcium chloride dihydrate | 0.050 g L⁻¹ | [[ex-0017]] |

Two variants appear. [[SP-002]] doubles the buffer to 4.84 g L⁻¹ Tris ([[ex-0012]]) and doubles nitrogen to 0.750 g L⁻¹ ammonium chloride ([[ex-0013]]) to hold pH over a longer batch. [[SP-004]] runs the opposite direction, cutting ammonium chloride to induce nitrogen limitation.

For fed-batch work, [[SP-009]] feeds sodium acetate separately at 30.0 g L⁻¹ ([[ex-0077]]) rather than raising it in the basal medium.

The platform's **TAP medium preparation** protocol (PR-TAP-01) is built from the [[SP-001]] formulation, with its acetate concentration revised in v1.1.`,
    followups: [
      'flow:F1|What growth rates come out of these media?',
      'Open the TAP protocol',
      'Why buffer TAP so heavily?',
    ],
  },

  // ── F3 — clarifying-question showcase ────────────────────────────────
  {
    id: 'F3',
    triggers: [
      'compare mixotrophic and photoautotrophic growth',
      'mixotrophic vs photoautotrophic',
      'how much faster is mixotrophic growth',
      'difference between mixotrophic and photoautotrophic cw15',
      'does acetate speed up growth',
    ],
    plan: [
      'Parse question — comparison across two trophic modes',
      'Detect ambiguity in the comparison basis',
      'Request disambiguation',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'mixotrophic photoautotrophic comparison cw15', k: 3 },
        durationMs: 720,
        retrieval: [
          { paperId: 'SP-003', sectionId: 's3', score: 0.93, snippet: 'cw15 grew at 0.132 h⁻¹ in mixotrophic culture' },
          { paperId: 'SP-003', sectionId: 's3', score: 0.91, snippet: 'the photoautotrophic rate for cw15 was 0.061 h⁻¹' },
          { paperId: 'SP-009', sectionId: 's3', score: 0.68, snippet: 'photoautotrophic controls grew at 0.038 h⁻¹ under the same illumination' },
        ],
      },
    ],
    answerMd: `Two papers compare the trophic modes directly, but they answer different questions. Before I give you a number — which comparison do you want?`,
    clarify: {
      question: 'Which basis should I compare on?',
      options: [
        { label: 'Growth rate (μ)', flowId: 'F3A' },
        { label: 'Protein content', flowId: 'F8' },
        { label: 'Either — show me both', flowId: 'F3A' },
      ],
    },
    followups: [],
  },

  // ── F3A — the resolved comparison ────────────────────────────────────
  {
    id: 'F3A',
    triggers: [
      'compare growth rate mixotrophic photoautotrophic',
      'mixotrophic photoautotrophic growth rate difference',
      'show me both trophic modes',
    ],
    plan: [
      'Retrieve paired measurements from the same study',
      'Compute the ratio within each study',
      'Flag cross-study comparability',
    ],
    toolCalls: [
      {
        name: 'records.query',
        args: { field: 'growth_rate_mu', organism: 'cw15', paired: true },
        durationMs: 660,
        retrieval: [
          { paperId: 'SP-003', sectionId: 's3', score: 0.95, snippet: 'cw15 grew at 0.132 h⁻¹ in mixotrophic culture' },
          { paperId: 'SP-003', sectionId: 's3', score: 0.94, snippet: 'the photoautotrophic rate for cw15 was 0.061 h⁻¹' },
          { paperId: 'SP-009', sectionId: 's3', score: 0.72, snippet: 'Mixotrophic batch cultures grew at 0.094 h⁻¹ during the first 36 h' },
        ],
      },
    ],
    answerMd: `Only [[SP-003]] measures both modes on the same strain under otherwise matched conditions, which makes it the one comparison worth quoting.

- Mixotrophic: **0.132 h⁻¹** ([[ex-0020]])
- Photoautotrophic: **0.061 h⁻¹** ([[ex-0021]])

That is a **2.2× advantage** for acetate supplementation, which is the number to use if you need one.

[[SP-009]] also runs photoautotrophic controls, reporting 0.094 h⁻¹ mixotrophic ([[ex-0070]]) against a photoautotrophic control ([[ex-0071]]) — but that second record is **unverified and carries a unit error**: the source prose reads 0.038 h⁻¹ while the extraction recorded d⁻¹. Until it is reviewed I would not use it, and the review queue has it flagged.

Worth noting for process design: the advantage is in rate, not necessarily in yield. Mixotrophic culture buys you a shorter seed train, but it also buys you an organic carbon bill and a contamination risk that photoautotrophic culture does not have.`,
    followups: [
      'flow:F1|Show all reported growth rates',
      'flow:F5|What about K. phaffii titers?',
      'Model the economics of each route',
    ],
  },

  // ── F4 — single-record answer with calculator handoff ────────────────
  {
    id: 'F4',
    triggers: [
      'what is the od to dcw conversion',
      'od750 dcw factor',
      'how do i convert od to dry cell weight',
      'od dcw conversion factor cw15',
      'optical density to biomass',
    ],
    plan: [
      'Parse question — field od_dcw_factor',
      'Retrieve the calibration methods paper',
      'Check strain and wavelength tags',
    ],
    toolCalls: [
      {
        name: 'records.query',
        args: { field: 'od_dcw_factor', organism: 'cw15' },
        durationMs: 540,
        retrieval: [
          { paperId: 'SP-010', sectionId: 's3', score: 0.97, snippet: 'For cw15 the OD750-to-DCW factor was 0.42 g L⁻¹ OD⁻¹ over the linear range' },
          { paperId: 'SP-010', sectionId: 's3', score: 0.83, snippet: 'Stationary-phase cw15 cells required 0.55 g L⁻¹ OD⁻¹' },
          { paperId: 'SP-010', sectionId: 's3', score: 0.79, snippet: 'cc1690 required a higher factor of 0.47 g L⁻¹ OD⁻¹ over the same optical range' },
        ],
      },
    ],
    answerMd: `For exponential-phase cw15 at 750 nm, the factor is **0.42 g L⁻¹ per OD unit** ([[ex-0080]], from [[SP-010]]) — verified and in the gold set.

Three qualifications matter more than the number itself:

- **Growth phase.** Stationary-phase cells need **0.55 g L⁻¹ OD⁻¹** ([[ex-0086]]) — a 31% difference. Using the exponential factor at harvest will under-report your biomass.
- **Strain.** cc1690 requires 0.47 g L⁻¹ OD⁻¹ ([[ex-0081]]). [[SP-010]] states explicitly that the cw15 factor should not be transferred between strains.
- **Wavelength.** The 750 nm figure is the calibrated one. A 680 nm reading on the same biomass gives a different coefficient, and that record ([[ex-0082]]) is unverified with a unit problem — the OD basis was dropped in extraction.

The **OD₇₅₀ and dry cell weight SOP** (PR-OD-01) has this coefficient bound to its calculator step, so the protocol stays consistent with the record if the record is ever corrected.`,
    followups: [
      'Open the OD SOP',
      'flow:F1|What growth rates use this conversion?',
      'Why does phase change the factor?',
    ],
  },

  // ── F5 — titers, segueing to the S2 scenario ─────────────────────────
  {
    id: 'F5',
    triggers: [
      'what titers are reported for k phaffii',
      'pichia titers',
      'komagataella phaffii product titer',
      'recombinant protein titer gs115',
      'how much protein does k phaffii make',
      'fed batch titers',
    ],
    plan: [
      'Parse question — organism gs115, field product_titer',
      'Retrieve fed-batch passages',
      'Separate measured results from cited claims',
      'Attach citations',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'K. phaffii fed-batch titre methanol induction', k: 5, filters: { organism: 'gs115' } },
        durationMs: 1020,
        retrieval: [
          { paperId: 'SP-014', sectionId: 's3', score: 0.96, snippet: 'a titre of 25.8 g L⁻¹ of rALB-7' },
          { paperId: 'SP-012', sectionId: 's3', score: 0.9, snippet: 'reached a final titre of 12.4 g L⁻¹ of RlpB-3 after 72 h of induction' },
          { paperId: 'SP-014', sectionId: 's3', score: 0.87, snippet: 'reached 22.3 g L⁻¹ over the same induction period' },
          { paperId: 'SP-013', sectionId: 's3', score: 0.8, snippet: 'raised the final titre to 10.8 g L⁻¹' },
          { paperId: 'SP-013', sectionId: 's3', score: 0.75, snippet: 'Methanol-only induction gave 6.2 g L⁻¹ of PhyG-1 after 94 h' },
        ],
      },
    ],
    answerMd: `Three papers report fed-batch titers for *K. phaffii* GS115, spanning **6.2–25.8 g L⁻¹** across three different recombinant products.

| Paper | Titer (g L⁻¹) | Product · strategy | Record |
|---|---:|---|---|
| [[SP-014]] | 25.8 | rALB-7, high cell density | [[ex-0109]] |
| [[SP-014]] | 22.3 | rALB-7, alternate feed | [[ex-0110]] |
| [[SP-012]] | 14.9 | RlpB-3, hybrid feed policy | [[ex-0093]] |
| [[SP-012]] | 12.4 | RlpB-3, DO-stat feed | [[ex-0091]] |
| [[SP-013]] | 10.8 | PhyG-1, mixed glycerol/methanol | [[ex-0100]] |
| [[SP-012]] | 8.7 | RlpB-3, fixed exponential feed | [[ex-0092]] |
| [[SP-013]] | 6.2 | PhyG-1, methanol-only | [[ex-0101]] |

The dominant variable is feed strategy, not product. Within [[SP-012]] alone — one product, one strain, one vessel — moving from a fixed exponential feed to a hybrid policy takes 8.7 to 14.9 g L⁻¹, a 71% gain from control strategy alone.

Treat the range's top end with care: these are three different proteins, and secretion titer is strongly product-dependent. A claim of ">20 g L⁻¹" also appears in [[SP-013]]'s introduction ([[ex-0107]]), but it describes prior work under a constitutive promoter and has been **rejected** as an extraction — it is not this study's result.

Titer is the single most influential input in the **K. phaffii fed-batch** economic scenario (S2), where it dominates minimum selling price below roughly 12 g L⁻¹.`,
    followups: [
      'Open the S2 scenario',
      'flow:F11|Compare two of these papers',
      'What drives the titer differences?',
    ],
  },

  // ── F6 — scoped inside one paper ─────────────────────────────────────
  {
    id: 'F6',
    triggers: [
      'what does sp-004 report',
      'summarize sp-004',
      'nitrogen limitation protein content',
      'what happens to protein under nitrogen starvation',
      'tell me about sp-004',
    ],
    plan: [
      'Scope retrieval to SP-004',
      'Extract the reported parameters',
      'Summarize within scope only',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'nitrogen limitation protein content growth rate', k: 4, filters: { paperId: 'SP-004' } },
        durationMs: 690,
        retrieval: [
          { paperId: 'SP-004', sectionId: 's3', score: 0.95, snippet: 'a protein content of 38 % DW in nitrogen-replete cultures' },
          { paperId: 'SP-004', sectionId: 's3', score: 0.92, snippet: 'protein had fallen to 17 % DW after 48 h of nitrogen starvation' },
          { paperId: 'SP-004', sectionId: 's3', score: 0.84, snippet: 'an intermediate value of 24 % DW at 24 h' },
          { paperId: 'SP-004', sectionId: 's3', score: 0.8, snippet: 'The replete cultures grew at 0.112 h⁻¹' },
        ],
      },
    ],
    answerMd: `Answering from [[SP-004]] only.

The paper tracks what nitrogen starvation does to cw15 protein content over 48 hours. Protein falls steeply and monotonically:

- Nitrogen-replete: **38 % DW** ([[ex-0028]])
- After 24 h of starvation: **24 % DW** ([[ex-0035]])
- After 48 h: **17 % DW** ([[ex-0029]])

That is a **55% relative loss** in two days. Growth does not stop when nitrogen runs out — replete cultures grow at 0.112 h⁻¹ ([[ex-0030]]) and a residual rate persists under limitation ([[ex-0033]], currently unverified with a unit discrepancy) — so the cells keep accumulating biomass while diluting their protein, which is the mechanism behind the drop.

The process implication is direct and slightly uncomfortable: if protein is your product, harvest timing is not a scheduling convenience. Waiting two days past nitrogen exhaustion for more biomass costs you more than half your protein fraction.`,
    followups: [
      'flow:F8|What is the protein content range across the corpus?',
      'Open SP-004',
      'flow:F1|Growth rates for cw15',
    ],
  },

  // ── F7 — methodology ─────────────────────────────────────────────────
  {
    id: 'F7',
    triggers: [
      'how was the gold set built',
      'what is the gold set',
      'how do you know the extractions are right',
      'how is extraction quality measured',
      'explain leave one out',
      'what is phycoextract validation',
    ],
    plan: [
      'Recognize a methodology question',
      'Retrieve the evaluation configuration',
      'Answer from platform state, not the corpus',
    ],
    toolCalls: [
      {
        name: 'platform.describe',
        args: { topic: 'validation', scheme: 'leave-one-out' },
        durationMs: 520,
      },
    ],
    answerMd: `The gold set is **41 hand-curated annotations across 16 papers**, concentrated on the parameters that carry the most weight downstream: specific growth rate, product titer, protein content, and medium composition.

Each entry is a human reading of a source span — the curator records what the paper actually says, independently of what any extractor produced. That independence is the whole point: an annotation created by correcting an extraction inherits the extraction's blind spots.

Quality is scored by comparing each extractor run against those annotations. A run's output for a gold parameter is a match, a value mismatch, a unit error, a span error, or a miss. Precision, recall and F1 follow from the counts, and the per-field table shows which parameters are hardest.

**Leave-one-out** is the evaluation scheme: each gold paper is scored by a configuration tuned without it, so the reported number is not measuring the extractor's ability to memorize the papers it was built against. This build *describes* the scheme rather than executing it — the simulation does not train models, and the validation dashboard says so.

One number is worth reading honestly before the headline F1: **15 of the 41 gold entries have never been produced by any run**. Recall is the platform's weak axis, and no amount of precision tuning has moved it.`,
    followups: [
      'Open the validation dashboard',
      'flow:F8|Show me a parameter with high spread',
      'What are the common failure modes?',
    ],
  },

  // ── F8 — uncertainty-phrasing showcase ───────────────────────────────
  {
    id: 'F8',
    triggers: [
      'what is the protein content of cw15',
      'protein content ranges',
      'how much protein does cw15 have',
      'protein percentage dry weight',
      'algal protein content',
    ],
    plan: [
      'Parse question — field protein_content',
      'Retrieve across organisms and methods',
      'Group by assay method',
      'Report spread rather than a point estimate',
    ],
    toolCalls: [
      {
        name: 'records.query',
        args: { field: 'protein_content', groupBy: 'method' },
        durationMs: 780,
        retrieval: [
          { paperId: 'SP-008', sectionId: 's3', score: 0.94, snippet: 'Nitrogen-replete cw15 contained 38.4 % DW protein by the Lowry assay' },
          { paperId: 'SP-008', sectionId: 's3', score: 0.92, snippet: 'the same biomass returned 46.1 % DW by Kjeldahl digestion' },
          { paperId: 'SP-008', sectionId: 's3', score: 0.86, snippet: 'cc1690 was consistently richer, at 42.7 % DW by Lowry' },
          { paperId: 'SP-004', sectionId: 's3', score: 0.81, snippet: 'a protein content of 38 % DW in nitrogen-replete cultures' },
        ],
      },
    ],
    answerMd: `I would not give you a single number here, because the spread is mostly methodological rather than biological.

For nitrogen-replete cw15 the corpus reports **31–41 % DW**, and the assay accounts for much of that. [[SP-008]] measures the *same freeze-dried biomass* two ways and gets **38.4 % DW by Lowry** ([[ex-0062]]) against **46.1 % DW by Kjeldahl** ([[ex-0063]]) — a 20% relative difference with zero biological variation between them. Kjeldahl reads total nitrogen and multiplies by a factor of 6.25, which counts nucleic acids and free amino acids as protein; Lowry responds to peptide bonds and specific residues.

Three further sources of spread, in rough order of size:

- **Nitrogen status.** Starvation drives cw15 from 38 to 17 % DW in 48 hours ([[ex-0028]], [[ex-0029]]).
- **Growth phase.** Mid-exponential biomass reads 31.2 % DW ([[ex-0069]]) against 38.4 % at replete harvest.
- **Strain.** cc1690 runs consistently richer than cw15 — 42.7 % DW by Lowry ([[ex-0064]]).

*Arthrospira platensis* sits far higher, at **62.4 % DW by Kjeldahl** ([[ex-0126]]), which is why it is the reference organism for food-grade protein.

Practically: quote the method with the number, or the number does not mean much. With n this small and two assays in play, treating 38 % and 46 % as a disagreement to be resolved would be a mistake — they are two different measurements.`,
    followups: [
      'flow:F6|What does nitrogen starvation do?',
      'flow:F7|How was the gold set built?',
      'Open the cw15 strain page',
    ],
  },

  // ── F9 — the honest decline ──────────────────────────────────────────
  {
    id: 'F9',
    triggers: [
      'crispr editing of cw15',
      'how do i knock out a gene in cw15',
      'genetic engineering chlamydomonas',
      'crispr cas9 protocol',
      'transformation efficiency cw15',
      'what vectors work in chlamydomonas',
    ],
    plan: [
      'Parse question — topic: genome editing',
      'Retrieve candidate passages',
      'Assess support — none found above threshold',
      'Decline rather than infer',
    ],
    toolCalls: [
      {
        name: 'corpus.search',
        args: { query: 'CRISPR Cas9 genome editing transformation knockout', k: 6 },
        durationMs: 940,
        retrieval: [],
      },
    ],
    answerMd: `That's outside this demo corpus — nothing in it addresses genome editing, transformation, or vector design, so anything I told you about CRISPR in cw15 would be invention rather than retrieval.

What the corpus does cover:

- **cw15 growth kinetics** — specific growth rates, doubling times, and light response across six papers
- **TAP media** — standard composition and buffer/nitrogen variants
- ***K. phaffii* fed-batch** — methanol induction strategies and recombinant protein titers
- **Downstream processing** — bead-mill disruption, harvest recovery, OD-to-DCW calibration
- **Extraction methodology** — the gold set and how quality is measured

Three questions it can answer well:`,
    followups: [
      'flow:F1|What growth rates are reported for cw15 in TAP?',
      'flow:F4|What is the OD₇₅₀-to-DCW conversion?',
      'flow:F5|What titers are reported for K. phaffii?',
    ],
  },

  // ── F10 — ambiguous units, clarify ───────────────────────────────────
  {
    id: 'F10',
    triggers: [
      'how fast does it grow per day',
      'what is the growth rate in per day',
      'convert the growth rate',
      'growth rate per day',
      'whats the rate in days',
    ],
    plan: [
      'Parse question — field growth_rate_mu, requested unit d⁻¹',
      'Detect an unresolved referent',
      'Request disambiguation',
    ],
    toolCalls: [
      {
        name: 'records.query',
        args: { field: 'growth_rate_mu', unit: 'd⁻¹' },
        durationMs: 600,
        retrieval: [
          { paperId: 'SP-001', sectionId: 's3', score: 0.72, snippet: 'a specific growth rate of 0.118 h⁻¹' },
          { paperId: 'SP-015', sectionId: 's3', score: 0.69, snippet: 'averaged 0.62 d⁻¹ in the summer quarter' },
        ],
      },
    ],
    answerMd: `I can convert any of these — the platform stores both the as-published value and its SI twin, so per-day and per-hour are the same record viewed two ways.

But "it" is ambiguous here, and the organisms differ by more than an order of magnitude. Which did you mean?`,
    clarify: {
      question: 'Which organism and condition?',
      options: [
        { label: 'cw15, mixotrophic', flowId: 'F1' },
        { label: 'cw15, photoautotrophic', flowId: 'F3A' },
        { label: 'A. platensis, outdoor', flowId: 'F10A' },
      ],
    },
    followups: [],
  },

  // ── F10A — the resolved unit answer ──────────────────────────────────
  {
    id: 'F10A',
    triggers: [
      'arthrospira platensis growth rate outdoor',
      'spirulina growth rate per day',
      'a platensis raceway productivity',
    ],
    plan: [
      'Retrieve outdoor raceway measurements',
      'Report in the published unit and its SI twin',
    ],
    toolCalls: [
      {
        name: 'records.query',
        args: { field: 'growth_rate_mu', organism: 'aplat' },
        durationMs: 580,
        retrieval: [
          { paperId: 'SP-015', sectionId: 's3', score: 0.93, snippet: 'averaged 0.62 d⁻¹ in the summer quarter' },
        ],
      },
    ],
    answerMd: `*Arthrospira platensis* in an outdoor raceway averaged **0.62 d⁻¹** over the summer quarter ([[ex-0123]]), which is **0.026 h⁻¹** in the platform's canonical unit.

Two caveats worth stating plainly. First, that record is **unverified** — it has not been through review. Second, and more importantly, an outdoor seasonal average is not the same kind of quantity as a controlled laboratory μ: it folds in day length, temperature swing, and night-time biomass loss. Comparing it directly against cw15's 0.132 h⁻¹ from a temperature-controlled flask would be comparing a field average against a laboratory maximum.

Corpus coverage for this organism is thin — two papers — and the strain page says so rather than implying otherwise.`,
    followups: [
      'flow:F1|Compare against cw15',
      'Open the A. platensis strain page',
      'flow:F8|Protein content of A. platensis',
    ],
  },

  // ── F11 — paper comparison (slash command) ───────────────────────────
  {
    id: 'F11',
    triggers: [
      '/compare sp-002 sp-011',
      'compare sp-002 and sp-011',
      'difference between sp-002 and sp-011',
      'compare two papers',
    ],
    plan: [
      'Parse comparison targets — SP-002, SP-011',
      'Retrieve both papers’ parameter sets',
      'Align on shared fields',
      'Report overlaps and gaps',
    ],
    toolCalls: [
      {
        name: 'corpus.compare',
        args: { papers: ['SP-002', 'SP-011'], align: 'fields' },
        durationMs: 1180,
        retrieval: [
          { paperId: 'SP-002', sectionId: 's3', score: 0.88, snippet: 'the cultures grew with a specific growth rate of 0.104 h⁻¹' },
          { paperId: 'SP-002', sectionId: 's2', score: 0.81, snippet: 'contained 4.84 g L⁻¹ Tris base' },
        ],
      },
    ],
    answerMd: `These two papers barely overlap, which is itself the useful finding.

[[SP-002]] is an experimental study of TAP buffer and nitrogen variants. It reports what you would expect from a bench paper: a growth rate of 0.104 h⁻¹ under standard buffer ([[ex-0011]]), 0.109 h⁻¹ for the high-buffer variant ([[ex-0015]], unverified), and full medium compositions for both — 4.84 g L⁻¹ Tris in the doubled-buffer formulation ([[ex-0012]]) against 2.42 g L⁻¹ in standard TAP.

[[SP-011]] is a techno-economic methodology paper. It reports no growth rates at all. What it contributes is the downstream and yield side — harvest recovery ([[ex-0090]]) and the yield assumptions a process model needs.

**Shared fields: effectively none.** SP-002 has no economics; SP-011 has no kinetics.

That complementarity is exactly why they are useful together rather than individually: SP-002 supplies measured inputs and SP-011 supplies the framework that consumes them. The S1 scenario draws on both — kinetics from the experimental papers, cost structure from the methodology one — and its assumptions table shows which rows come from which.`,
    followups: [
      'Open the S1 scenario',
      'flow:F2|What media does SP-002 use?',
      'flow:F7|How is the corpus curated?',
    ],
  },

  // ── F12 — insert-into handoff ────────────────────────────────────────
  {
    id: 'F12',
    triggers: [
      'draft a protocol reference list for pr-pbr-01',
      'what should pr-pbr-01 cite',
      'references for the photobioreactor protocol',
      'build a reference list for a protocol',
      '/protocol pr-pbr-01',
    ],
    plan: [
      'Resolve protocol PR-PBR-01',
      'Map its parameters onto corpus records',
      'Rank candidate references by directness',
      'Format for insertion',
    ],
    toolCalls: [
      {
        name: 'protocol.lookup',
        args: { protocolId: 'PR-PBR-01' },
        durationMs: 490,
      },
      {
        name: 'records.query',
        args: { organism: 'cw15', fields: ['growth_rate_mu', 'light_intensity', 'medium_component_conc'], status: 'verified' },
        durationMs: 830,
        retrieval: [
          { paperId: 'SP-005', sectionId: 's3', score: 0.9, snippet: 'the maximum specific growth rate of 0.141 h⁻¹ was reached at 150 µmol m⁻² s⁻¹' },
          { paperId: 'SP-003', sectionId: 's3', score: 0.85, snippet: 'cw15 grew at 0.132 h⁻¹ in mixotrophic culture' },
          { paperId: 'SP-001', sectionId: 's2', score: 0.77, snippet: 'Each litre contained 2.42 g L⁻¹ Tris base' },
        ],
      },
    ],
    answerMd: `Here is a reference list for the mixotrophic batch protocol, ordered by how directly each source supports a decision the protocol actually makes.

**Primary — parameters the protocol sets**

- [[SP-005]] — light intensity. The 150 µmol m⁻² s⁻¹ setpoint and the saturating rate of 0.141 h⁻¹ ([[ex-0036]]) are why the protocol specifies this irradiance rather than a higher one.
- [[SP-003]] — the mixotrophic growth rate of 0.132 h⁻¹ ([[ex-0020]]) that sets the expected batch duration.
- [[SP-001]] — the TAP formulation the medium step builds on ([[ex-0005]], [[ex-0006]]).

**Supporting — sampling and analysis**

- [[SP-010]] — the OD₇₅₀-to-DCW factor of 0.42 g L⁻¹ OD⁻¹ ([[ex-0080]]) used to convert the sampling schedule's readings into biomass.
- [[SP-004]] — nitrogen status and its effect on protein content ([[ex-0028]]), relevant to harvest timing.

**Deliberately excluded**

[[SP-009]] reports a comparable mixotrophic rate, but its photoautotrophic companion record is unverified with a unit error. I have left it out rather than cite a paper on the strength of a record that is still in the review queue.

Use **Insert into…** to attach these to PR-PBR-01's reference list.`,
    followups: [
      'Open PR-PBR-01',
      'flow:F1|Show all cw15 growth rates',
      'flow:F4|Explain the OD conversion',
    ],
  },
];

/** Composer starter chips — each matches a flow trigger exactly (§14.7). */
export const SUGGESTED_PROMPTS: string[] = [
  'What growth rates are reported for cw15 in TAP',
  'Which media are used for cw15',
  'What titers are reported for K. phaffii',
  'What is the OD to DCW conversion',
  'How was the gold set built',
  'What is the protein content of cw15',
];

export { DEMO_FOOTER };
