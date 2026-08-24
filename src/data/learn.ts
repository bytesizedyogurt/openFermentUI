// Curriculum (OF-DES-001 §8.14, §14.8), rebuilt on the real corpus of
// OF-COR-001. Module 0 is fully built; modules 1–5 carry one seeded lesson
// each plus an outline of what is not yet written.
//
// HONESTY CONTRACT FOR THIS FILE. The papers chipped here are real papers by
// real authors, and the platform does NOT hold their full texts — every entry
// is `catalogued`, its single section (id 's1') carrying the curator's note
// from OF-COR-001 rather than the paper's own words. So every claim in this
// curriculum is traceable to the curation document, no sentence is written as
// though the paper said it, and where the corpus does not settle a question
// the lesson says so instead of filling the gap. That refusal is teachable
// material, not a shortfall: lessons 0.4 and 5.1 are built on it.
//
// The embeds are live components, not screenshots — the pedagogy is the
// product. Two of them will render empty states against this corpus
// ('metrics-tiles' certainly, 'mini-queue' once a session's records are all
// decided), and the surrounding prose is written so that the empty state is
// the lesson rather than an accident.
import type { LearnModule } from './types';

export const MODULES: LearnModule[] = [
  {
    id: 'm0',
    index: 0,
    title: 'PhycoExtract: reading the literature like a machine',
    blurb:
      'How quantitative parameters get out of prose and into a database you can compute with — and how you know whether the machine got them right.',
    lessons: [
      {
        id: 'l0-1',
        title: 'Why extraction',
        minutes: 9,
        blocks: [
          {
            kind: 'prose',
            md: `## The numbers are not missing. They are stuck.

This platform carries one argument: that a cell-wall-deficient *Chlamydomonas reinhardtii* strain could be made to produce phosphorylated bovine β-casein. It is assembled from 125 catalogued entries across fifteen threads, running from host platform and expression through the molecule, the kinase, prior art in other hosts, downstream processing and techno-economics.

Not one of those threads gives you a number you can compute with. They give you sentences.

Two sentences in particular decide the whole architecture of the programme. The strain-lineage paper [[A1]] records that the UVM4 and UVM11 expression mutants reach about 0.2% of total soluble protein for intracellular reporters. The secretion benchmark [[C2]] records a maximum secreted yield of 15 mg/L. Whether you build an intracellular process with a disruption step or a secreted process with a clarification step turns on how those two numbers relate.

You cannot subtract them, divide them, or put them on the same axis — lesson 0.2 is about exactly why not. But before any of that, somebody has to get them out of the prose.

## What transcription destroys

Type "0.2" and "15" into a spreadsheet and four things die on the way in.

**The unit.** 0.2% of total soluble protein is not a concentration at all, and a column headed "yield" has already lost the information needed to notice.

**The organism.** [[A1]]'s 0.2% is measured on UVM4, a UV-mutagenised derivative selected for high transgene expression — not on cw15, and the corpus keeps them separate for that reason.

**The method.** The keystone review [[H1]] records "undetermined" for most of the bacterial studies it tabulates, because nobody ran the analysis, and a spreadsheet cell cannot hold the difference between *measured to be absent* and *never measured*.

**The provenance.** The one that ruins corpora. Six months later, looking at "15", you cannot tell whether it was measured here, quoted from elsewhere, estimated by a vendor, or typed wrong. The number has been separated from its evidence and there is no road back.

## A chip is a road back

Everywhere the platform prints a claim, it prints the route to the source alongside it.`,
          },
          { kind: 'embed', embed: 'chip-demo', arg: 'M7' },
          {
            kind: 'prose',
            md: `The chip is real: hover it for the source, click through to the entry with the span highlighted. The sentence *around* it is component boilerplate — illustrative framing supplied by the widget, not a quotation from [[M7]]. Which is exactly the habit this module is trying to build: **the rendered sentence is never the evidence; the resolved record is.**

## Anatomy of an extraction record

An extraction record is a number that cannot lose its source: the value and unit as published, an SI-normalised twin for computation, the exact span that supports it, the entry it came from, the organism it was measured on, the analytical method where one is required, whether this source measured it or repeated someone else's measurement, and a provenance class saying how far it has been checked.`,
          },
          { kind: 'embed', embed: 'record-card', arg: 'r-C2-1' },
          {
            kind: 'prose',
            md: `Look at what that card gives you that a cell in a spreadsheet cannot.

The value appears as published *and* normalised, so comparison arithmetic and verification arithmetic are both available without redoing either. The quote is the span that supports it. The chip opens the entry. And the provenance tick says **curated** — a precise, deliberately modest claim: the value was transcribed from the curation document OF-COR-001, not read off the source PDF. It is real and attributable, it has not been checked against the paper itself, and the interface refuses to let it pass as if it had.

That distinction exists because of the state this corpus is in. Every entry is *catalogued*: bibliographically real, full text not yet ingested, each holding a single section whose body is the curator's note. The spans you can highlight today are spans of the curation document — and none of that is hidden anywhere in this build. It is printed on every record.

So the design is not "automate extraction" — extractors attach values to the wrong parameter, carry a per-day rate through as per-hour, and quietly merge measurements on strains that share a nickname. It is **extract automatically, verify cheaply, and measure how often the machine was wrong.**`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-1-1',
            prompt:
              'A record on this platform carries the provenance class "curated". What does that claim, and what does it deliberately not claim?',
            kind: 'mc',
            options: [
              'The value was transcribed from the curation document — real and attributable, but not yet checked against the source paper',
              'The value was checked against the source PDF by two independent reviewers',
              'The value was invented for demonstration purposes',
              'The value is a reference measurement suitable for scoring extractors',
            ],
            answerIndex: 0,
            explanation:
              'Curated sits between unverified machine output and verified human-checked evidence. It says a real curator wrote this down about a real paper, and it says nothing at all about whether the paper actually contains it in that form. Collapsing that distinction is how a literature database quietly becomes fiction: the claim is transitively sourced, and until someone opens the PDF it has to be rendered as such.',
            evidenceChip: 'r-C2-1',
          },
          {
            id: 'c0-1-2',
            prompt:
              'A spreadsheet column headed "yield" contains 0.015 and 0.85, both from casein-programme papers. What is the most consequential thing that column has already lost?',
            kind: 'mc',
            options: [
              'Whether each number is a secreted or an intracellular quantity, and which host it was measured in',
              'The number of significant figures the authors reported',
              'The publication year of each paper',
              'The alphabetical ordering of the sources',
            ],
            answerIndex: 0,
            explanation:
              'Both numbers are in grams per litre and neither is comparable to the other: 0.015 g/L is protein that reached the medium of an algal culture, and 0.85 g/L is protein that stayed inside a yeast cell and needs disruption to recover. The ontology splits secreted and intracellular titer into separate fields precisely so that a column heading cannot fuse two different process architectures into one average.',
            evidenceChip: 'r-H4-2',
          },
          {
            id: 'c0-1-3',
            prompt:
              'Why does the platform store both the as-published value and its SI-normalised twin, rather than only the normalised one?',
            kind: 'mc',
            options: [
              'Verification compares the record against the span, which quotes the original unit; keeping only the conversion would make conversion errors invisible',
              'SI units are less precise than the units papers publish in',
              'Because the corpus contains fields that have no canonical unit',
              'To reduce the storage footprint of the corpus',
            ],
            answerIndex: 0,
            explanation:
              'The two values serve different jobs. As-published is what a reviewer checks against the source span; normalised is what a strip plot or a cost model consumes. Discard the first and every review has to redo the arithmetic by hand — at which point a conversion error is no longer detectable, because the only surviving witness to it has been deleted.',
          },
        ],
      },

      {
        id: 'l0-2',
        title: 'The ontology and units',
        minutes: 12,
        blocks: [
          {
            kind: 'prose',
            md: `## Twenty-four fields, in five families

An ontology is a controlled list of the things you are willing to extract. Version 1 has twenty-four parameters in five families — **expression performance** (share of total soluble protein, intracellular and secreted titer, secreted fraction, fold improvement, transformation efficiency, time to colony), **post-translational modification** (phosphate count, phosphorylation degree, phospho-site position, glycan species, kinase identity), **functional performance** (micelle diameter, micellar fraction, gelation pH, calcium binding, melt–stretch length), **cultivation** (growth rate, final biomass density, volumetric productivity, medium component concentration) and **downstream and economics** (disruption protein yield, disruption energy, minimum selling price). Each carries a definition precise enough to settle an argument, a canonical unit, and a validation range.

Two fields are categorical rather than numeric, and both are enums on purpose: glycan species, and kinase identity — the latter for a reason lesson 0.3 returns to, that "casein kinase" is the common name of three different enzymes.

The validation range warns rather than blocks. A value outside it is *suspicious*, not *wrong*; sometimes a source really does report an anomalous number, and the reviewer's job is to record what the source says. Blocking would force a choice between falsifying and abandoning the record, and both are worse than an honest outlier.

## Rule 1 — a PTM value without its method is not a value

Every field in the post-translational-modification and functional families carries a mandatory method qualifier. "Phosphorylated: yes" means one thing from LC-ESI-MS, another from Phos-tag or urea-PAGE with phosphatase treatment, and something considerably weaker from an SDS-PAGE mobility inference.

The value \`undetermined\` is first-class and legitimate: *the analysis was never done*, which is a completely different statement from *the analysis was done and the answer was no*. The keystone review [[H1]] records undetermined for most of the bacterial casein studies it tabulates, and an ontology that could not express that would have to drop those rows or misrepresent them as negatives.


## Rule 2 — % TSP and g/L are not interconvertible

This is the single most important thing in the ontology, and this corpus contains the exact trap it exists to catch.

[[A1]] reports that UVM4 and UVM11 reach roughly 0.2% of total soluble protein for intracellular reporters ([[r-A1-1]]). [[C2]] reports secreted yields reaching a maximum of 15 mg/L ([[r-C2-1]]). Every student who meets these two numbers wants to compare them. It is the obvious question — is secretion better than intracellular accumulation in this host?

You cannot do it, and the engine will not let you.

A percentage of total soluble protein is a *share of a mixture*. A concentration is *mass per unit volume of broth*. Converting the first into the second needs two quantities neither paper supplies at that point: the biomass concentration of the culture, and the total-protein fraction of that biomass. Guess either and you have not performed a conversion — you have fabricated a titer and given it a provenance it did not earn.

So the unit engine puts \`% TSP\` in its own family, structurally separate from mass concentration, and refuses with an explanation rather than a bare dimension error. The refusal is the feature: a silent failure teaches nothing, while one naming the two missing quantities tells you what to go and measure.

Note the subtler barrier underneath. Even with those quantities in hand the comparison would still be wrong, because the measurements are not of the same thing: one is an intracellular reporter, the other a secreted protein carrying a synthetic glycomodule. Unit compatibility is necessary for a comparison, not sufficient.

The same discipline applies inside the percent sign. This ontology carries \`% TSP\`, \`% of native sites\`, \`% sedimentable\`, \`% of total expressed\` and \`% of total protein\`, all with different denominators: 87% sedimentable ([[r-I1-1]]) and 0.005% secreted ([[r-H4-3]]) are both percentages and share nothing else. Currency is separated for the same reason — 69 €/kg ([[r-O4-1]]) does not become $5/kg ([[r-O2-1]]) without an exchange rate carrying a date, and a unit converter has no business inventing one.`,
          },
          { kind: 'embed', embed: 'unit-playground' },
          {
            kind: 'prose',
            md: `Work that field. Enter a per-day growth rate and watch the SI twin appear in per-hour. Push a value past the validation range and watch it warn without blocking. Then switch the parameter to expression level and try to type a concentration into it — the refusal you get back is the one this lesson is about, and it arrives with its reason rather than an error code. Dimensional checking is the highest-value validation in the system: it catches the error class that does the most damage, without needing to know any biology at all.`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-2-1',
            prompt:
              'The corpus’s cleanest specific-growth-rate record is 0.087 h⁻¹. Suppose a second source reported the same kind of quantity as 3.6 d⁻¹. Express that in the ontology’s canonical unit for growth rate.',
            kind: 'numeric',
            answer: { value: 0.15, unit: 'h⁻¹', tolerancePct: 3 },
            explanation:
              'Divide by 24: 3.6 d⁻¹ = 0.15 h⁻¹. The grader is unit-aware, so answering 3.6 d⁻¹ is accepted too — they are the same quantity and the platform stores both. This is the cheapest of all the unit traps, and also the most common: rates are published both ways, and the two differ by a factor of 24 with no change in how the number looks.',
            evidenceChip: 'r-M7-1',
          },
          {
            id: 'c0-2-2',
            prompt:
              'UVM4 reporters reach about 0.2% TSP intracellularly; the best secreted yield reported from this host is 15 mg/L. A student divides one by the other and concludes secretion is the better route. What is wrong?',
            kind: 'mc',
            options: [
              'A share of total soluble protein and a concentration are not interconvertible without biomass concentration and the total-protein fraction of that biomass',
              'The two numbers were published in different decades',
              'Nothing is wrong, provided both are converted to SI first',
              '15 mg/L should first be rounded to 0.02 g/L',
            ],
            answerIndex: 0,
            explanation:
              'Rule 2. The conversion needs two quantities neither source supplies, and inventing them manufactures a titer out of a percentage. The engine refuses and names the missing quantities, which turns a dead end into a measurement plan. There is a second problem underneath the first: an intracellular reporter and a secreted glycomodule fusion are not the same measured quantity, so even a licensed conversion would not license that conclusion.',
            evidenceChip: 'r-C2-1',
          },
          {
            id: 'c0-2-3',
            prompt:
              'What two additional quantities would have to be recorded before a % TSP value could legitimately be turned into a titer?',
            kind: 'mc',
            options: [
              'Biomass concentration of the culture, and the total-protein fraction of that biomass',
              'Culture temperature, and the length of the batch',
              'Optical density, and the specific growth rate',
              'The molecular weight of the product, and the pH of the medium',
            ],
            answerIndex: 0,
            explanation:
              'A percentage of total soluble protein tells you the product’s share of a mixture. To get to grams per litre of broth you need how many grams of biomass are in a litre, and what fraction of that biomass is soluble protein. Record those and the conversion becomes arithmetic; omit either and it becomes fiction. This is why refusals in the unit engine are phrased as instructions rather than errors.',
          },
          {
            id: 'c0-2-4',
            prompt:
              'A record reads: phosphorylation degree = 0% of native sites. Which field decides whether this is a measured negative or an analysis that was never run?',
            kind: 'mc',
            options: [
              'The method qualifier — "MALDI-MS" means measured and absent, "undetermined" means never assessed',
              'The confidence score assigned by the extractor',
              'The publication year of the source',
              'The organism the record was measured on',
            ],
            answerIndex: 0,
            explanation:
              'Rule 1 exists for this exact ambiguity. Measurement of absence is a finding; absence of measurement is a gap in the literature. Both render as a zero, and only the method distinguishes them. Aggregate a corpus that has lost that distinction and you will report a consensus that no one ever measured.',
            evidenceChip: 'r-H15-2',
          },
        ],
      },

      {
        id: 'l0-3',
        title: 'Reviewing like a curator',
        minutes: 13,
        blocks: [
          {
            kind: 'prose',
            md: `## The question is narrower than it looks

Reviewing an extraction is not "is this a good paper" or "is this number believable." It is one question, asked mechanically:

> Does the quoted span support **this value**, in **this field**, in **this unit**, for **this organism**, by **this method**, as **this source's own measurement**?

Six clauses, one span. That narrowness makes review fast enough to be worth doing — a trained reviewer clears a record in fifteen seconds — and it makes the result auditable, because every clause has a visible witness.

One thing this corpus changes. Because every entry is catalogued rather than ingested, the span you check today belongs to the *curation document*, not the paper. Review at this stage establishes transcription fidelity, and a record surviving it stays **curated**; promotion to **verified** is a separate, later act requiring somebody to open the PDF. Conflating the two would be the largest single lie this interface could tell, so it does not offer the option.

## Four failure modes this literature actually produces

Generic extraction-error taxonomies are not much use. These four are the ones the curator flagged here.

### 1. Precursor versus mature numbering

Bovine β-casein is **224 residues as translated** and **209 after the signal peptide is removed** ([[F1]]). Every residue position that matters here is quoted in mature numbering: the codon-67 SNP separating the A1 and A2 variants, the N-terminal phosphate cluster, and the β(28–40) kinase-assay peptide ([[G9]], [[r-G9-3]] and [[r-G9-4]]). A position without its convention mislocates every site by fifteen residues, which is why the field carries a mandatory convention flag and the seed checker fails the build if one is missing: 224 and 209 are both correct answers to "how long is β-casein", and they answer different questions.

### 2. "Casein kinase" names three different enzymes

CK1, CK2 and FAM20C. CK1 and CK2 were named for casein in the 1960s and do not have the right localisation; the substratome analysis [[G9]] records that they do not recognise the S-x-E motifs at all ([[r-G9-1]]), and that a peptide corresponding to a bovine β-casein phosphorylation site was selectively phosphorylated by the Golgi casein kinase activity but not by CK1 or CK2 ([[r-G9-2]]). FAM20C is the authentic Golgi casein kinase ([[G1]], [[r-G1-1]]), phosphorylating within S-x-E/pS motifs ([[r-G2-1]]).

The consequences are not academic. [[H2]] co-expressed **human** β-casein with CK2 in *E. coli* and reached 500 mg/L of phosphorylated product ([[r-H2-1]]); [[H3]] co-expressed **bovine** β-casein with CK2 and got much less phosphorylation than the native five-phosphate state ([[r-H3-2]]), because human serine clusters align well with CK2 consensus sites and bovine ones mostly do not. Flatten all three enzymes into "casein kinase" and that decisive pair of results becomes a contradiction. Hence the enum.

### 3. Strain aliases

cw15, cw15-302, CC-4350, "cwd mt+ arg7", Elow47, UVM4 and UVM11 are related and **not interchangeable**. The first four name one lineage; Elow47 is a transformant of it; UVM4 and UVM11 are UV-mutagenised derivatives selected for high transgene expression, the lesion behind that phenotype being a Sir2-type histone deacetylase ([[A2]]).

So the 0.2% TSP figure ([[r-A1-1]]) belongs to the expression mutants, not the parental strain — filing it under cw15 credits a strain with a phenotype it was selected against, and the reverse error is as easy, since walled wild-type isolates carry most of the corpus's growth measurements. Every record therefore normalises its organism string through an explicit alias table on ingest.

### 4. Citation of a citation

The most common false-independence error in literature aggregation, and this corpus contains a textbook instance. The 15 mg/L secretion figure appears twice: in [[C2]] as the measurement ([[r-C2-1]]), and in [[C6]] as part of that paper's summary of prior work ([[r-C6-1]]). The 0.2% TSP figure appears the same way, in [[A1]] and again recited by [[C6]] ([[r-C6-2]]).

Count both and a strip plot shows two independent sources agreeing. There is one measurement. Records therefore carry a primacy flag and, when non-primary, the identifier of the record they quote, and aggregates filter on it — the same rule that quarantines market and vendor figures ([[r-O8m-1]]).

## Accept, edit, or reject

**Accept** when the record is right as it stands. **Edit, then accept** when the span is right and the record misreads it — the highest-value action available, because it yields a corrected value *and* a labelled example of the extractor being wrong, and both are kept. **Reject** when the span does not support the value, or the value belongs in another field. Never repair a record by editing its value when the span is wrong: you would be manufacturing evidence, and the next reader would have no way to tell.`,
          },
          { kind: 'embed', embed: 'mini-queue' },
          {
            kind: 'prose',
            md: `Whatever you decide there is real. The queue calls the same store actions the Guild review screen does, and the consequences propagate — organism pages, strip plots and Witness all read the records you just changed.
`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-3-1',
            prompt:
              'A record gives a phospho-site position of 35 but carries no numbering convention. Why is the seed checker right to fail the build over it?',
            kind: 'mc',
            options: [
              'β-casein is 224 residues as translated and 209 after signal-peptide removal, so a position without its convention is ambiguous by fifteen residues',
              'Position 35 is outside the validation range for that field',
              'Residue positions must always be recorded as ranges',
              'The field requires an organism, and none was given',
            ],
            answerIndex: 0,
            explanation:
              'The literature quotes mature numbering — the codon-67 variant SNP and the β(28–40) assay peptide both do — but precursor numbering appears too, and the two differ by exactly the fifteen-residue signal peptide. A site recorded without its convention will be silently mislocated by any downstream consumer, and the error is invisible because both numbers are plausible residue indices.',
            evidenceChip: 'r-G9-3',
          },
          {
            id: 'c0-3-2',
            prompt:
              'The UVM4 secretome paper states 12–15 mg/L in its summary of prior work. The secretion benchmark paper reports 15 mg/L as its own result. How should the first of these be recorded?',
            kind: 'mc',
            options: [
              'As non-primary, naming the record it is quoting, so aggregate statistics exclude it',
              'As a second independent measurement, strengthening the consensus around 15 mg/L',
              'It should not be recorded at all',
              'As an average of the two, at 13.5 mg/L',
            ],
            answerIndex: 0,
            explanation:
              'Citation of a citation is how a single measurement becomes an apparent consensus. Counting both would put two dots on a strip plot where the literature contains one measurement, and the visual impression of agreement is exactly the thing a reader will take away without checking. Marking it non-primary and naming its source keeps the claim readable while removing it from every aggregate.',
            evidenceChip: 'r-C6-1',
          },
          {
            id: 'c0-3-3',
            prompt:
              'Why is kinase identity a categorical enum in this ontology rather than a free-text field?',
            kind: 'mc',
            options: [
              '"Casein kinase" names three distinct enzymes, and CK1 and CK2 do not recognise the S-x-E motifs that FAM20C does',
              'Free-text fields cannot be indexed for retrieval',
              'The corpus contains only one kinase, so a controlled list is trivial',
              'Enums render more compactly in the review queue',
            ],
            answerIndex: 0,
            explanation:
              'The naming collision is historical and the biology is not forgiving of it. CK2 co-expression phosphorylates human β-casein well and bovine β-casein only partially, because the bovine serine clusters mostly sit outside canonical CK2 sites. Merge the enzymes under one label and that decisive comparison collapses into an unexplained disagreement between two papers.',
            evidenceChip: 'r-G9-1',
          },
          {
            id: 'c0-3-4',
            prompt:
              'An extraction reports 0.2% TSP and tags the organism as cw15, based on a span describing UVM4 and UVM11. What should the reviewer do?',
            kind: 'mc',
            options: [
              'Correct the organism to the expression mutant — UVM4 is a selected derivative, and filing its expression phenotype under the parental strain misattributes it',
              'Accept it, since UVM4 was derived from the cw15 lineage',
              'Reject the record entirely, since the span mentions two strains',
              'Leave the organism blank, since the lineage is shared',
            ],
            answerIndex: 0,
            explanation:
              'The alias table normalises names that genuinely denote the same organism; it does not merge a lineage with a mutant selected out of it. The entire point of UVM4 is that it expresses transgenes better than its parent, so crediting the parent with the figure asserts the opposite of what the strain paper reports. Blanking the organism is no better — an expression figure with no organism is not interpretable at all.',
            evidenceChip: 'r-A1-1',
          },
        ],
      },

      {
        id: 'l0-4',
        title: 'Measuring quality: P/R/F1 and leave-one-out',
        minutes: 14,
        blocks: [
          {
            kind: 'prose',
            md: `## Two ways to be wrong

An extractor can produce something wrong, or fail to produce something right. Different failures, different consequences, and no single number describes both.

**Precision** asks: of everything produced, what fraction was correct? Low precision means the output is polluted — you cannot use a record without checking it, so the automation has bought you nothing. **Recall** asks: of everything there was to find, what fraction did it produce? Low recall means the corpus is under-mined: what you have may be reliable, there is simply less of it than there should be.

With TP correct extractions, FP spurious ones and FN things missed:

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2·P·R / (P + R)

F1 is the *harmonic* mean, not the arithmetic one, because it refuses to let a strong score on one axis paper over a weak score on the other. An extractor with precision 1.0 and recall 0.1 has an arithmetic mean of 0.55, respectable-sounding for something that found a tenth of the data. Its F1 is 0.18.

## Now look at what the platform shows you`,
          },
          { kind: 'embed', embed: 'metrics-tiles' },
          {
            kind: 'prose',
            md: `That empty state is the lesson.

There is no precision, recall or F1 to display, because **no extractor has been run against this corpus and no gold set has been annotated from it.** Both follow from the state described in lesson 0.1: every entry is catalogued rather than ingested, and the only text the platform holds is the curator's note. A gold annotation is a value anchored to a span of the *paper*, and there are no such spans yet. Annotating against the curation document instead would produce an answer key measuring transcription of a summary.

So the dashboard shows nothing, and says why. This is not modesty for its own sake. A fabricated F1 is worse than an absent one in a specific way: it is *load-bearing*. Somebody reads 0.82 and stops checking. Refusing to print a number the system has not earned is the same discipline as the unit engine refusing to convert % TSP into g/L, applied one level up — and if you take one habit from this module, take that one.

## What the numbers will mean when they exist

**Precision will describe pollution**: if it is low, the review queue is doing the extractor's job and the throughput argument collapses. **Recall will describe coverage**, and this corpus makes it the harder number, because so much of what matters is not in running prose — the keystone review [[H1]] carries its prior art in three tables. So read which axis moved, not the headline: a parameter no configuration ever produced will never enter a gold set built by correcting extractor output.

The planned gold set spans fourteen papers, chosen so the difficult cases are deliberately included rather than avoided:

- a value stated only as a range — $4–6/kg ([[r-O2-1]]) — where the correct output is a range, not an invented midpoint;
- a comparative claim, up to 12-fold ([[r-C2-2]]), meaningless unless the extractor also captures the baseline;
- a negative result, "not phosphorylated" ([[r-H15-2]]), recorded as a value rather than dropped as an empty cell, and an "undetermined" table cell, where the correct extraction is a null **with a reason**;
- and a genuine disagreement about whether this host carries sialylated N-glycans ([[D1]] versus [[D4]]).

That last deserves emphasis. The conflict is real. An extractor faithfully reproducing both claims has done its job, and a metric scoring it as making one error has misdefined the task. Aggregation must surface disagreement, not average it away.

## Leave-one-out, and why small gold sets lie

Here is the trap. You build an extractor, tune it against your gold set until the numbers look good, and report those numbers. But you tuned on the answer key: the score measures how well the extractor learned *these particular papers*, not how well it will read the next one.

**Leave-one-out** fixes this — each gold paper is scored by a configuration tuned *without* it, so every paper is judged by a version that has never seen it. With a few dozen records across fourteen papers this beats a single held-out split, because a set that size cannot spare a test partition large enough to mean anything: hold out a fifth and you are estimating performance from two or three papers.

Two limits: it costs one configuration per held-out paper, and it does not rescue a gold set biased to begin with. This build *describes* leave-one-out; it does not run it, because it does not train models, and the dashboard says so rather than implying a rigour it does not have.`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-4-1',
            prompt:
              'A run produces 24 correct extractions and 8 spurious ones, and misses 16 gold parameters entirely. What is its F1 score?',
            kind: 'numeric',
            answer: { value: 0.667, unit: '', tolerancePct: 3 },
            explanation:
              'Precision = 24/(24+8) = 0.75. Recall = 24/(24+16) = 0.60. F1 = 2·(0.75·0.60)/(0.75+0.60) = 0.90/1.35 = 0.667. Notice that the sixteen misses drag F1 well below precision: the harmonic mean will not let a strong precision hide a weak recall, which is precisely why it is used instead of an average.',
          },
          {
            id: 'c0-4-2',
            prompt:
              'Why does Witness show an empty state rather than a precision, recall and F1 figure?',
            kind: 'mc',
            options: [
              'No extractor has been run and no gold set annotated, because the corpus is catalogued rather than ingested — so any number would describe nothing',
              'The metrics engine has not been implemented in this build',
              'The gold set is too small for the metrics to be statistically meaningful',
              'The papers are behind publisher access controls, so metrics cannot be computed legally',
            ],
            answerIndex: 0,
            explanation:
              'A gold annotation anchors a value to a span of the source paper, and no source paper has been parsed yet — the only text held is the curator’s note. Scoring now would mean scoring an extractor that never ran, against an answer key nobody wrote. The empty state tells a reader exactly where the project stands, which is more useful and considerably more honest than a plausible-looking number.',
            evidenceChip: 'H1',
          },
          {
            id: 'c0-4-3',
            prompt:
              'Two papers in the corpus disagree about whether this host carries sialylated N-glycans. An extractor reproduces both claims faithfully. How should the metric treat it?',
            kind: 'mc',
            options: [
              'As correct on both — the disagreement is real, and a metric that penalises reproducing it has misdefined the task',
              'As one true positive and one false positive, since only one claim can be true',
              'As two false positives, since contradictory records cannot both be extracted',
              'As a miss, since the extractor failed to resolve the conflict',
            ],
            answerIndex: 0,
            explanation:
              'The extractor’s job is to report what each source says, not to adjudicate between sources. Resolving the conflict is a curation decision that needs evidence the extractor does not have. A scoring scheme that rewards picking a side would train the system to hide genuine disagreement — the single most damaging thing a literature aggregator can do.',
            evidenceChip: 'r-D4-1',
          },
          {
            id: 'c0-4-4',
            prompt:
              'Why does leave-one-out evaluation matter more when the gold set is small?',
            kind: 'mc',
            options: [
              'A small set cannot spare a held-out partition large enough to give a stable estimate, so every item has to serve as a test case exactly once',
              'Small gold sets contain proportionally more annotation errors',
              'It reduces the compute cost of evaluating an extractor',
              'It increases the number of gold annotations available for tuning',
            ],
            answerIndex: 0,
            explanation:
              'Hold out a fifth of a few dozen records and you are estimating performance from two or three papers, which is noise. Leave-one-out uses every item as a test case once, at the cost of tuning one configuration per held-out paper. It does not, however, fix a gold set whose contents were chosen by the extractor — that bias survives any resampling scheme you apply on top of it.',
          },
        ],
      },
    ],
  },

  {
    id: 'm1',
    index: 1,
    title: 'Host and chassis',
    blurb:
      'Why a cell-wall-deficient green alga is a defensible chassis for a milk protein — and the numbers that argue against it just as hard.',
    lessons: [
      {
        id: 'l1-1',
        title: 'Why cw15, and what it costs',
        minutes: 11,
        blocks: [
          {
            kind: 'prose',
            md: `## The case is assembled, not inherited

Caseins have been expressed in bacteria, in yeast and in plants. The keystone review [[H1]] searched literature and patent databases systematically and tabulates every reported attempt — seventeen bacterial studies, five yeast, two plant. There is no algal row. The only algal mention anywhere in the corpus is a patent application that lists algae generically among possible hosts ([[H17e]]).

So there is no precedent to inherit. The case for a cell-wall-deficient *Chlamydomonas* chassis has to be assembled out of adjacent results, and it rests on four established facts: this host has a **real secretory pathway**, routing proteins through ER and Golgi, cleaving signal peptides and N-glycosylating, with secretion established at 12–15 mg/L ([[C2]]); it holds **US GRAS status** for human consumption, one of a short list of microalgae that do ([[N2]]); **cell-wall deficiency is a downstream asset**, releasing roughly three times the protein of walled cells under pulsed electric field ([[J10]]); and **the hard problem is the same everywhere**, since no yeast, plant or bacterial host natively phosphorylates bovine β-casein either. Nobody has an easy route. The question is which host makes the hard route survivable.

## The lineage, and why the names matter

The strain-lineage paper [[A1]] is where the chassis comes from. The arginine-auxotrophic, cell-wall-deficient parent — cw15-302, also called CC-4350 and "cwd mt+ arg7" — was co-transformed to give Elow47, and UV mutagenesis of Elow47 followed by selection for high transgene expression yielded UVM4 and UVM11. Both reach about 0.2% of total soluble protein for intracellular reporters ([[r-A1-1]]).

The follow-up [[A2]] identifies the lesion behind that phenotype as a Sir2-type histone deacetylase, making the mechanism relief from epigenetic silencing rather than a gain in transcription. That has a direct design consequence: if the benefit is silencing relief, a two-gene construct plausibly inherits it — recorded as an argument needing testing, not as a result. Two constraints come with the lineage: integration is by random non-homologous end joining ([[A4]]), though safe-harbour targeting reportedly gave an 8.6-fold increase ([[r-A7-1]]); and the mutants can hardly be crossed ([[A5]]), so a two-cassette build needs two markers or a self-cleaving 2A linker ([[C4]]).

## Transformability, measured against a walled strain

The terminator study [[B5]] is the one place in the corpus where wall-deficient and walled strains are compared side by side under matched conditions. Colonies appear on selection in 7–10 days for cw15 and UVM4 ([[r-B5-1]]) against 15–20 days for the walled WT12 ([[r-B5-3]]).

That paper also states the trade plainly: cell-wall-deficient strains have reduced motility and mating ability, and are much more susceptible to shear and osmotic stress. That last clause is not a footnote — it propagates directly into bioreactor design, where impeller tip speed, pump selection and sparge rate become process variables rather than details.

## The economic keystone

The pulsed-electric-field study [[J10]] converts "easy to transform" into "cheap to process." Applied to a cell-wall-deficient mutant, PEF gave an average protein yield of 31 ± 6% of total protein against 11 ± 3% for the walled wild type ([[r-J10-1]], [[r-J10-2]]) — roughly three-fold ([[r-J10-3]]), comparable to mechanical disruption but under mild conditions. Read it alongside the mechanical benchmarks in [[J11]]: homogenisation and bead milling reach over 95% disintegration and release around 50% of total protein ([[r-J11-2]]) at under 0.5 kWh per kg biomass ([[r-J11-3]]), while PEF on *walled* cells released at most 13% ([[r-J11-4]]) even at many times that energy. Together they say something sharper than either alone — PEF is a bad technique on walled cells and a competitive one on wall-deficient cells, so the chassis choice is what makes the mild process available.

## The honest counterweight

A curriculum that stopped there would be advocacy. The same corpus supplies the case against.

Expression is historically weak: 0.2% TSP for intracellular reporters is the known ceiling for this lineage, and since no casein has been expressed in any alga, every point above it is extrapolation. Secreted yield of 15 mg/L ([[r-C2-1]]) sits roughly sixty-five-fold below the 1 g/L of β-lactoglobulin secreted from a filamentous fungus ([[r-K1-1]]). Culture density is the harshest number: mixotrophic *Chlamydomonas* reaches about 1.23 g/L ([[r-M5-1]]), against 50–100 g/L for heterotrophic microalgal cultures ([[r-M8-7]]) and far higher for yeast fed-batch. And the expression mutants secrete unassembled cell wall glycoproteins that form extracellular aggregates in which recombinant product becomes trapped ([[C6]]).

A methodological caveat sits underneath all of it: most growth and density figures were measured on walled wild-type isolates, not cw15, and whether they transfer is an assumption no retrieved source tests. The regulatory position is likewise split — US GRAS does not transfer to the EU, and a *C. reinhardtii* novel-food application failed on the EFSA record in 2025 after the applicant did not answer repeated data requests ([[N3]]), a procedural failure rather than a finding of harm.

This is a research bet. The corpus supports calling it a defensible one. It does not support calling it an engineering exercise.`,
          },
        ],
        checkpoint: [
          {
            id: 'c1-1-1',
            prompt:
              'Pulsed electric field released 31% of total protein from a cell-wall-deficient mutant against 11% from the walled wild type. What does that license you to claim?',
            kind: 'mc',
            options: [
              'That mild PEF recovers roughly three times more protein from wall-deficient cells than from walled ones — a statement about disruption, not about product yield',
              'That the cell-wall-deficient strain produces three times more protein overall',
              'That PEF is the best available disruption method for microalgae',
              'That the wall-deficient strain will give three times the casein titer',
            ],
            answerIndex: 0,
            explanation:
              'The measurement is protein *released by a given disruption method*, expressed as a share of total cellular protein. It says nothing about how much protein the cells contained, and nothing at all about a recombinant product neither strain was expressing. Read alongside the mechanical benchmarks, its real claim is narrower and more interesting: PEF is a poor technique on walled cells and a competitive one here, so the chassis is what makes the mild route available.',
            evidenceChip: 'r-J10-1',
          },
          {
            id: 'c1-1-2',
            prompt:
              'Using the midpoints of the reported ranges, how many days sooner do colonies appear for cw15 than for the walled WT12 after transformation?',
            kind: 'numeric',
            answer: { value: 9, unit: 'd', tolerancePct: 15 },
            explanation:
              'Colonies appear in 7–10 days for cw15 and UVM4, and 15–20 days for WT12: midpoints 8.5 and 17.5 days, a difference of 9 days. Note what the record has to preserve to make this subtraction legitimate — both figures come from one study under matched conditions, and both carry their organism. Two time-to-colony numbers from different papers would not be subtractable at all.',
            evidenceChip: 'r-B5-3',
          },
          {
            id: 'c1-1-3',
            prompt:
              'Which statement about algal casein expression is actually supported by this corpus?',
            kind: 'mc',
            options: [
              'No casein expression in a microalga has been published; the only algal mention is a patent listing algae generically among possible hosts',
              'Algal casein expression has been attempted and failed',
              'Casein has been expressed in microalgae but at low yield',
              'The question has not been investigated by anyone',
            ],
            answerIndex: 0,
            explanation:
              'A systematic search of literature and patent databases produced seventeen bacterial, five yeast and two plant studies, and no algal row. That is a surveyed absence — it is evidence, and it is what makes the whitespace claim defensible. It is not the same as a failed attempt, which would be a result, nor the same as nobody having looked, which would be no information at all. Lesson 5.1 turns that three-way distinction into a rule for grounded answering.',
            evidenceChip: 'H1',
          },
        ],
      },
    ],
    outline: [
      'Reading a strain designation: what cw15, Elow47, UVM4 and UVM11 each commit you to',
      'Silencing, position effects and why transformants vary',
      'Safe-harbour integration and the routes upward from 0.2% TSP',
      'Codon usage, GC content and a proline-rich mammalian gene',
      'Two cassettes in a strain that cannot be crossed',
      'Shear sensitivity as a bioreactor design constraint',
    ],
  },

  {
    id: 'm2',
    index: 2,
    title: 'Expression and localisation',
    blurb:
      'Keep the product inside the cell or push it into the medium — the fork that decides the whole downstream process.',
    lessons: [
      {
        id: 'l2-1',
        title: 'The intracellular–secretion fork',
        minutes: 11,
        blocks: [
          {
            kind: 'prose',
            md: `## Why secretion is attractive for a casein

Secretion looks like the obvious answer. It avoids cell disruption and much of the purification train, which for a bulk food protein is where the cost lives — the most current review of the problem [[K5]] says exactly that.

The corpus contains a strong demonstration that secretion works in this host, a strong warning about what the secreted material lands in, and a precedent from a different eukaryote showing how badly the obvious construct can fail. Together they define a fork, and it is a genuinely open decision.

## The benchmark

[[C2]] is the number every secretion scenario in this platform is measured against. A putative gametolysin signal sequence directed a fluorescent reporter into the medium; C-terminal fusion to synthetic glycomodules of tandem Ser-Pro repeats raised yields up to twelve-fold ([[r-C2-2]]), reaching a maximum of 15 mg/L ([[r-C2-1]]), and conferred enhanced proteolytic stability.

Two things about that record deserve a curator's attention. The twelve-fold figure is a *comparative* claim, and a fold-improvement value without its baseline is not interpretable. And the 15 mg/L is a maximum achieved with a glycomodule fusion, not a generic expectation for any cargo.

Around it sits a decision table: [[C3]] evaluated ten signal peptides, two newly identified ones outperforming the established set, and [[C7]] is a working example of the full architecture in the expression mutants.

## The warning

[[C6]] is the most important cautionary entry in the corpus. Comparing the extracellular proteome of the UVM4 expression mutant with its walled ancestor under matched conditions, it reports a distinct profile with higher abundance of secreted cell wall glycoproteins — and the consequence that secreted recombinant proteins become trapped in a matrix of these aggregates, making isolation and purification difficult.

So secretion in this host does not deliver product into clean medium. It delivers product into a glycoprotein sludge. The nearest analogue elsewhere is yeast mannan interference in downstream processing ([[J9]]) — a recognised problem rather than an exotic one, though recognising it does not make it free.

That paper also supplies the corpus's cleanest lesson in provenance discipline. Its recital of the yield history — 0.2% TSP intracellular, then 12–15 mg/L secreted — reads exactly like a result and is not one. Both figures are citations of earlier work ([[r-C6-1]] citing [[r-C2-1]], and [[r-C6-2]] citing [[r-A1-1]]). An aggregate counting them as independent shows a consensus that does not exist.

## The precedent that failed instructively

[[H4]] is the closest eukaryotic precedent to this programme and the sharpest warning in it. Bovine β-casein was expressed in a methylotrophic yeast, carrying mutations that introduced an N-glycosylation site. Despite using the **native bovine signal peptide** for secretion, the protein localised mostly intracellularly at roughly 15–18% of total soluble protein ([[r-H4-1]]), corresponding to 0.7–1.0 g/L ([[r-H4-2]]) — while secreted protein reached only 0.005% of the intracellular level ([[r-H4-3]]).

Read that number twice. It is not a modest secretion yield; it is a secretion signal that essentially did not function in a non-mammalian eukaryote. Any casein construct for an algal host has to carry a host-native signal peptide, which is why the signal-peptide comparison work matters as much as it does.

Two further findings carry forward. Phosphorylation matched animal-derived β-casein by phosphatase treatment plus urea-PAGE ([[r-H4-4]]) — a striking result whose mechanism the corpus does not explain, since no kinase in that host is named. And the protein was N-glycosylated with mannan ([[r-H4-5]]), a modification bovine β-casein does not natively carry: host glycosylation here is a risk, not a requirement.

## Naming the fork

**Intracellular.** Accept the 0.2%-TSP-class expression ceiling and recover the product with mild pulsed-electric-field disruption, which is the one place the wall-deficient chassis has a measured, three-fold advantage.

**Secreted.** Take the 15 mg/L benchmark and the glycomodule and signal-peptide toolkit, and inherit a purification problem in an aggregate-loaded medium.

The corpus does not settle this. What it does is state the comparison honestly: nobody has reported a recombinant casein in this host by either route, so the choice sits between one measured secretion benchmark for a different cargo and one measured disruption advantage for no cargo at all.`,
          },
        ],
        checkpoint: [
          {
            id: 'c2-1-1',
            prompt:
              'In the closest eukaryotic precedent, secreted β-casein reached only 0.005% of the intracellular level despite using a secretion signal. What is the design lesson?',
            kind: 'mc',
            options: [
              'The construct used the native bovine signal peptide, which a non-mammalian eukaryote does not recognise — a casein cassette needs a host-native signal peptide',
              'β-casein cannot be secreted by any eukaryotic host',
              'The culture was harvested too early for secretion to be detected',
              'Secretion always requires a glycomodule fusion to work',
            ],
            answerIndex: 0,
            explanation:
              'A signal peptide is read by the host’s own targeting machinery, and a mammalian secretion signal carries no guarantee of being recognised elsewhere. This is why the corpus keeps a whole thread on signal-peptide comparison rather than treating the choice as a formality — and why a two-thousandth-of-a-percent secretion figure is best read as a construct failure rather than as a property of the protein.',
            evidenceChip: 'r-H4-3',
          },
          {
            id: 'c2-1-2',
            prompt:
              'The 15 mg/L secretion figure appears in two different papers. Why is that not two independent measurements?',
            kind: 'mc',
            options: [
              'The second paper is reciting the first in its summary of prior work — one measurement, quoted twice',
              'The two papers used different strains, so the figures are not comparable',
              'The second measurement was made under different conditions',
              'The second paper reports a range rather than a point value',
            ],
            answerIndex: 0,
            explanation:
              'The secretome paper’s yield history reads like a result and is a citation. Records therefore carry a primacy flag and name the record being quoted, so aggregates count the measurement once. The visual consequence of getting this wrong is a strip plot showing two agreeing sources where the literature contains one — and agreement is exactly what a reader takes away from a plot without checking.',
            evidenceChip: 'r-C6-1',
          },
          {
            id: 'c2-1-3',
            prompt:
              'A filamentous fungus secretes β-lactoglobulin at 1 g/L; the best secreted titer reported from the algal expression mutants is 15 mg/L. What is the ratio?',
            kind: 'numeric',
            answer: { value: 67, unit: '', tolerancePct: 8 },
            explanation:
              '1.0 / 0.015 ≈ 67, which the corpus rounds to roughly 65-fold. Two caveats keep this from being a like-for-like comparison: the fungal figure is for a whey protein, not a casein, and the algal figure is for a fluorescent reporter carrying a glycomodule. The gap is real and worth stating plainly; what it compares is two different cargoes in two different hosts.',
            evidenceChip: 'r-C2-1',
          },
        ],
      },
    ],
    outline: [
      'Signal peptides: the comparison table and how to read it',
      'Glycomodules, proteolytic stability and what fold-improvement claims require',
      'Codon usage and GC content in a 68%-GC coding-region host',
      'Introns, terminators and untranslated regions as expression levers',
      'One transcript or two: 2A peptides against separate markers',
      'What the UVM4 secretome does to a purification train',
    ],
  },

  {
    id: 'm3',
    index: 3,
    title: 'The molecule and its modification',
    blurb:
      'β-casein is disordered, so folding is not the success criterion. Five phosphates in the right place is.',
    lessons: [
      {
        id: 'l3-1',
        title: 'Five phosphates, N-terminally clustered',
        minutes: 12,
        blocks: [
          {
            kind: 'prose',
            md: `## The usual success criterion does not apply

For most recombinant proteins, success means the chain folded correctly. β-casein does not fold. It is intrinsically disordered and stays disordered even when it self-assembles: the structural work collected in [[E9]] reports that self-association does not reduce monomer chain flexibility, and that micellisation involves few residues in transition rather than a large secondary-structure change.

So the criterion has to be something else, and the corpus states it numerically. Fully phosphorylated bovine β-casein carries **about five phosphates, clustered at the N-terminus** ([[F5]], [[r-F5-1]]). That is the target specification. For comparison, αs1-casein carries about eight, concentrated centrally ([[r-F5-2]]), αs2 ten to thirteen, and κ typically one to three near the C-terminus — κ uniquely being able to carry phospho-threonine as well.

## Why the clustering, not just the count, matters

The mature protein is 209 residues ([[E3]]): the most hydrophobic of the caseins by virtue of a large hydrophobic C-terminal domain, yet strongly amphipathic, because of a highly charged N-terminal domain carrying the phosphate centre.

That is the whole architecture in one sentence. The phosphates are not decoration; they are a charge block at one end of an amphipathic chain, and that block binds amorphous calcium phosphate. Native micelles are approximately spherical with a radius around 70 nm, holding on the order of ten thousand casein molecules bound to calcium phosphate nanoclusters ([[E2]], [[r-E2-1]]) — an assembly that prevents both the amyloid fibrils caseins otherwise form at high concentration and the precipitation calcium at milk concentrations would cause ([[E6]]).

So "five phosphates" is the count and "N-terminally clustered" is what makes the count do work. Any record carrying a phospho-site position must also carry its numbering convention, because the protein is 224 residues as translated and 209 after the signal peptide is removed, and the literature quotes mature numbering ([[F1]]).

## The kinase

[[G1]] is the identification paper: Fam20C is the authentic Golgi casein kinase ([[r-G1-1]]). It phosphorylated recombinant β-casein in a time-dependent manner while a catalytically inactive mutant, unable to coordinate manganese, did not ([[r-G1-2]]), and [[G2]] establishes the motif — S-x-E/pS, generating the majority of the extracellular phosphoproteome ([[r-G2-1]]).

Three design complications follow, each a fork rather than a detail.

**It may need a partner.** Fam20A is a pseudokinase acting as an allosteric activator of Fam20C ([[G3]], [[r-G3-1]]), and a Fam20C point mutant showed greatly reduced kinase activity toward casein. Co-expressing the kinase alone may not be enough.

**It may need processing.** The kinase resides in the Golgi as a transmembrane protein, and site-1 protease cleaves its propeptide to promote secretion and activation ([[G7]]). A pre-cleaved construct may be necessary.

**It needs a secretory pathway to fold at all.** The crystal structure shows an atypical kinase-like fold with disulfide bridges and N-linked glycosylation ([[G4]]) — which is why bacterial expression fails: attempts in *E. coli* failed outright for both human and bovine versions ([[H8]], [[r-H8-6]]), with success reported to date only in human cell lines. This is the strongest argument in the corpus for a eukaryotic host with a Golgi. The alternative built in parallel changes the target rather than solving it — a phosphomimetic route substituting all eight phosphoserine sites of an αs1-casein variant with aspartate ([[r-H8-7]]).

And the honest gap: whether *Chlamydomonas* possesses a Fam20-family secretory kinase at all is **open** ([[D5]]). The indirect evidence points toward absence — Fam20 kinases are described as conserved across the animal kingdom, plants do not express FAM20C, and this host sits outside the animal lineage — but indirect evidence is what it is, and the corpus records the question rather than the guess.

## Why any of it matters: the functional evidence

[[I1]] is where the success criterion stops being a specification and becomes a measurement. Caseins purified from milk were enzymatically dephosphorylated to different degrees and reassembled into micelles across three systems. Reassembly ability was proportional to phosphorylation degree, with higher phosphorylation giving a greater micellar proportion and more calcium binding; roughly 87% of total protein was sedimentable in the fully phosphorylated case ([[r-I1-1]]), while fully dephosphorylated caseins hardly formed micelle structures at all and remained in serum ([[r-I1-3]]).

The coagulation result is the one to remember. Gelation pH rose as phosphorylation fell, and fully dephosphorylated caseins **failed to gel entirely**, precipitating at their isoelectric point around pH 5.5 ([[r-I1-2]]). That is a binary product failure, not a quality gradient: an unphosphorylated β-casein does not make a slightly worse cheese, it makes a precipitate. Artificial micelles built predominantly from dephosphorylated casein likewise form irregular structures roughly three times larger than normal ([[I2]], [[r-I2-1]]).

## The counterweight, and the product fork it creates

The corpus also records evidence that phosphorylation is not universally required. [[I9]] collects the counter-case: recombinant non-phosphorylated αs1-casein can stabilise emulsion and foam interfaces ([[r-I9-1]]); functional artificial micelles can be built from two or three caseins rather than all four; and micelle formation from recombinant caseins has so far been unsuccessful, largely for post-translational-modification reasons. That produces a genuine product-strategy fork, cleaner than most technical arguments here — emulsifier and foaming applications appear reachable without solving the kinase problem, and cheese and yogurt are not.`,
          },
        ],
        checkpoint: [
          {
            id: 'c3-1-1',
            prompt:
              'How many phosphates does fully phosphorylated bovine β-casein carry?',
            kind: 'numeric',
            answer: { value: 5, unit: 'mol mol⁻¹', tolerancePct: 5 },
            explanation:
              'About five, clustered at the N-terminus — against roughly eight for αs1 concentrated centrally, ten to thirteen for αs2, and one to three for κ. The count alone is not the specification: the clustering is what forms the charged block that binds calcium phosphate, so a construct achieving five phosphates in the wrong positions would satisfy the number and miss the target.',
            evidenceChip: 'r-F5-1',
          },
          {
            id: 'c3-1-2',
            prompt:
              'Why is "the protein folded correctly" not a usable success criterion for recombinant β-casein?',
            kind: 'mc',
            options: [
              'β-casein is intrinsically disordered and stays flexible even on self-assembly, so the criterion is correct phosphorylation and assembly behaviour instead',
              'Folding cannot be measured for proteins of this size',
              'The protein folds only in the presence of calcium, which is absent in fermentation',
              'Folding is guaranteed by any eukaryotic host with a Golgi',
            ],
            answerIndex: 0,
            explanation:
              'Neutron and spectroscopic work reports that self-association does not reduce chain flexibility and that micellisation involves few residues in transition. There is no native fold to reproduce or to fail to reproduce. The consequence for the analytics plan is concrete: circular dichroism, the standard structural check for a recombinant protein, is answering a question this molecule does not pose.',
            evidenceChip: 'E9',
          },
          {
            id: 'c3-1-3',
            prompt:
              'What is the main risk in a design that co-expresses FAM20C on its own alongside the casein gene?',
            kind: 'mc',
            options: [
              'A pseudokinase partner acts as an allosteric activator, and the kinase is a Golgi transmembrane protein requiring protease processing — the kinase alone may be inactive or mislocalised',
              'FAM20C would phosphorylate every host protein indiscriminately',
              'FAM20C cannot be expressed in any eukaryotic host',
              'The casein would be phosphorylated at too many sites',
            ],
            answerIndex: 0,
            explanation:
              'Three published complications stack: an allosteric activator partner, propeptide cleavage by site-1 protease promoting secretion and activation, and a fold that depends on disulfide bridges and N-glycans — which is why bacterial expression of the kinase failed and why a Golgi-bearing host is the credible route. Each of these is a construct decision, and the corpus records them as forks rather than as solved parameters.',
            evidenceChip: 'r-G3-1',
          },
          {
            id: 'c3-1-4',
            prompt:
              'What does the reassembly study license you to predict about an unphosphorylated cw15-derived β-casein?',
            kind: 'mc',
            options: [
              'It would largely fail to form micelles and would not gel — it would precipitate near its isoelectric point',
              'It would form micelles of normal size but with reduced calcium binding',
              'It would gel at a slightly lower pH than native casein',
              'It would behave identically to native casein in acid coagulation',
            ],
            answerIndex: 0,
            explanation:
              'Fully dephosphorylated caseins hardly formed micelles at all, remained in serum, and failed to gel entirely, precipitating around pH 5.5. This is a threshold, not a slope: the product either assembles or it does not. That is why phosphorylation is treated as the programme’s central success metric rather than as one performance attribute among several — and why the emulsifier applications, which do not depend on assembly, form a separate product path.',
            evidenceChip: 'r-I1-3',
          },
        ],
      },
    ],
    outline: [
      'CSN2: exons, variants and the A1/A2 decision as a product choice',
      'Precursor and mature numbering, and why every position record carries a convention',
      'Analytical methods for phosphorylation, and what each one can and cannot show',
      'The β(28–40) peptide as a construct-validation assay',
      'Micelle assembly: calcium phosphate nanoclusters and the role of κ-casein',
      'Host glycosylation as a risk rather than a requirement',
    ],
  },

  {
    id: 'm4',
    index: 4,
    title: 'Techno-economics',
    blurb:
      'What a minimum selling price is, which two upstream parameters dominate it, and how to read a sensitivity chart without being misled by it.',
    lessons: [
      {
        id: 'l4-1',
        title: 'Reading a minimum selling price',
        minutes: 12,
        blocks: [
          {
            kind: 'prose',
            md: `## One number, and what it hides

A minimum selling price is the price per kilogram at which a process exactly breaks even over its lifetime — revenue covers operating costs and returns the capital at the required rate. Below it you lose money; above it you make some.

MSP is useful because it collapses a whole process into one comparable number, and dangerous for the same reason: two processes with the same MSP can have completely different risk profiles, and an MSP quoted without its assumption set is a rumour with a decimal point.

The corpus makes that vivid. A techno-economic analysis of industrial-scale protein production ([[O3]]) sized four scenarios to deliver the same 80,000 kg of pure protein per year and produced minimum selling prices for crude protein ranging from $2,300/kg in the small empirical case ([[r-O3-1]]) down to $75/kg in the optimistic case ([[r-O3-2]]) — and for purified protein, from $99,000/kg ([[r-O3-3]]) down to $970/kg ([[r-O3-4]]). Same product, same annual output, three orders of magnitude.

## The two parameters that dominate

That analysis is the most transferable cost model in the corpus because it says *why* the spread is so wide. A clear inverse relationship held between levelised protein cost and two upstream parameters: **biomass cell density** and **target protein content**. The expensive case ran at 4.2 g/L biomass ([[r-O3-5]]) with target protein at 0.1% of cell mass ([[r-O3-6]]).

Hold that pair in mind and read it against the algal case. Mixotrophic *Chlamydomonas* reaches about 1.23 g/L ([[r-M5-1]]); intracellular reporter expression in the expression mutants reaches about 0.2% TSP ([[r-A1-1]]). Both sit below the expensive case on both dominant axes. That is not a reason to abandon the chassis, but it is the honest starting position — and it is why this platform's algal cost surface sweeps exactly those two variables plus recovery yield, rather than a longer and more impressive list.

## What the wider literature converges on

The richest source in the thread is a meta-analysis of 55 published techno-economic models ([[O2]]). Biomass-fermentation protein costs converge around $4–6/kg ([[r-O2-1]]), against beef and pork market prices of $6–15/kg.

Then comes the finding that should change how you read any single model. Published models assume 50–2,500 t/y and an average titer around 24 g/L ([[r-O2-3]]), while private-sector benchmarks span 2,500–25,000 t/y and average around 42 g/L ([[r-O2-4]]) — a gap wide enough that the analysis concludes published models systematically overstate cost. Note those titers for scale: 24 g/L is an *assumption*, while the best secreted milk-protein titer reported is 1 g/L ([[r-K1-1]]) and the best from the algal mutants is 15 mg/L ([[r-C2-1]]).

## A real plant, and how to read a tornado

For an algal process specifically, the anchor is two years of operating data from an actual production plant ([[O4]]): ten 3 m³ tubular photobioreactors in continuous mode, 3.8 t/y capacity, photosynthetic efficiency 3.6%, production cost 69 €/kg ([[r-O4-1]]) — **dominated by labour and depreciation**. Simplification plus scale-up to 200 t/y reduces that to 12.6 €/kg ([[r-O4-2]]).

That is a factor of 5.5 from scale and simplification alone, with no biological improvement whatever, and it is measured rather than modelled. It is also a warning about which lever you are pulling: at 3.8 t/y the cost was dominated by two lines with almost nothing to do with the strain. A companion 100-hectare study ([[O5]]) adds a sensitivity analysis from real data — 6.7 €/kg at base case ([[r-O5-1]]), photosynthetic efficiency the most influential parameter, all improvements together projecting 3.3 €/kg ([[r-O5-2]]).

Read a tornado chart for two things. **Which assumptions actually matter**, so you know where to spend effort reducing uncertainty. And **asymmetry** — a bar longer on one side means the risk is not symmetric, which is usually more decision-relevant than its length. The standing caveat is that one-at-a-time sensitivity is evaluated at a reference point and ignores interactions: biomass density and product share are not independent in reality, and no tornado will tell you that.

One rule of hygiene closes the lesson: **market figures are not evidence.** Vendor sources put precision-fermentation whey protein at $25–30/kg in 2025 ([[r-O8m-1]]). These are ingested, rendered with a distinct provenance tick, and excluded from the gold set and default aggregates by construction — useful for framing, useless for supporting a claim. The peer-reviewed anchor in the same cluster ([[O8]]) is a different object and is treated differently.`,
          },
          { kind: 'embed', embed: 'scenario-widget', arg: 'sc-s1' },
          {
            kind: 'prose',
            md: `Move the biomass density slider and watch the minimum selling price fall steeply at the low end and then flatten. The knee is the argument: while density is the binding constraint it is the cheapest lever available, and past it capital and downstream take over and further gains buy progressively less.

Two things to keep in view. The reference point sits at 2 g/L — already optimistic against the 1.23 g/L actually measured for this organism in this medium. And the cost engine is an authored demonstration model: the scaling laws and dependencies are real and traceable, the absolute values are illustrative, and every screen that shows them says so. Literature-derived assumptions carry source chips; modelling conventions carry a demo tick. Check which is which before quoting anything from it.`,
          },
        ],
        checkpoint: [
          {
            id: 'c4-1-1',
            prompt:
              'A real algal plant reported 69 €/kg at 3.8 t/y and 12.6 €/kg after simplification and scale-up to 200 t/y. What fold reduction is that?',
            kind: 'numeric',
            answer: { value: 5.5, unit: '×', tolerancePct: 6 },
            explanation:
              '69 / 12.6 ≈ 5.5×. What makes this figure valuable is that it comes from two years of operating data on a real plant rather than from a model, and that the original cost was dominated by labour and depreciation — so the improvement is a scale-and-simplification result, not a biological one. Any strain improvement would be multiplicative on top of it.',
            evidenceChip: 'r-O4-2',
          },
          {
            id: 'c4-1-2',
            prompt:
              'Which two upstream parameters did the industrial-scale fermentation analysis identify as inversely related to levelised protein cost?',
            kind: 'mc',
            options: [
              'Biomass cell density and target protein content as a share of cell mass',
              'Fermenter volume and annual operating days',
              'Downstream recovery yield and labour rate',
              'Feedstock price and capital charge factor',
            ],
            answerIndex: 0,
            explanation:
              'Both are upstream and both are where the algal case is currently weakest — about 1.23 g/L density and about 0.2% TSP expression. That is exactly why this platform’s algal cost surface sweeps those two axes plus recovery yield, rather than a longer list: a model whose dominant variables are not the ones the literature identifies will produce confident answers about the wrong things.',
            evidenceChip: 'r-O3-5',
          },
          {
            id: 'c4-1-3',
            prompt:
              'Why does the platform refuse to express a 69 €/kg production cost in dollars per kilogram?',
            kind: 'mc',
            options: [
              'Currency conversion requires an exchange rate with a date attached, and a unit engine has no business inventing one',
              'Euro-denominated costs are less reliable than dollar-denominated ones',
              'The two figures were computed for different products',
              'Currency is a categorical field and cannot be converted at all',
            ],
            answerIndex: 0,
            explanation:
              'Currencies are separate unit families for the same reason % TSP and g/L are: the conversion needs information the record does not carry. Silently applying a rate would embed an undated, unattributed assumption inside a number that then looks like a measurement. If the comparison is needed, record the rate and its date as an explicit, citable assumption — which is a visible act rather than a hidden one.',
            evidenceChip: 'r-O4-1',
          },
          {
            id: 'c4-1-4',
            prompt:
              'Published techno-economic models average around 24 g/L titer and 50–2,500 t/y; private-sector benchmarks average around 42 g/L and 2,500–25,000 t/y. What did the meta-analysis conclude from that gap?',
            kind: 'mc',
            options: [
              'That published models systematically overstate cost, because they assume lower titers and smaller plants than industry actually runs',
              'That private-sector benchmarks are unreliable and should be discarded',
              'That titer has no meaningful effect on production cost at scale',
              'That the two populations are measuring different products',
            ],
            answerIndex: 0,
            explanation:
              'Both dominant cost drivers — output scale and titer — sit higher in the private benchmarks, so the published population is biased toward expensive configurations. The practical consequence is that a published MSP should be read as conditional on its titer and volume assumptions rather than as a property of the technology, and the first question to ask of any cost figure is what it assumed rather than what it concluded.',
            evidenceChip: 'r-O2-4',
          },
        ],
      },
    ],
    outline: [
      'Capital cost estimation and the six-tenths scaling rule',
      'Operating cost structure: where labour and depreciation dominate',
      'Discounting, annualisation and what a capital charge factor hides',
      'Building a sensitivity analysis that survives interaction effects',
      'Life-cycle claims and how to keep them separate from cost claims',
      'Grading a cost source: peer-reviewed model, real plant data, or vendor estimate',
    ],
  },

  {
    id: 'm5',
    index: 5,
    title: 'Agentic literature methods',
    blurb:
      'Retrieval, grounding, and why "cite or decline" is the only contract worth offering a reader.',
    lessons: [
      {
        id: 'l5-1',
        title: 'Cite or decline',
        minutes: 11,
        blocks: [
          {
            kind: 'prose',
            md: `## Retrieval before generation

A language model asked a bioprocess question will answer it. Whether it *knows* the answer is a separate matter, and from the outside the two cases look identical — same fluency, same confidence, same specific-sounding numbers.

Retrieval-augmented generation restructures the problem. Instead of asking a model what it knows, you retrieve passages from a corpus you control and ask it to answer from those passages only. The job shifts from recall to reading comprehension, and — this is the part that matters — a reader can verify any claim by following it back. The system stops asking for trust and starts offering evidence.

## The contract

**Answer only from the provided passages. Cite every quantitative claim. If the passages do not support an answer, say so.**

The last clause does the heavy lifting. Without it, a model facing insufficient evidence will produce a plausible answer anyway — not from malice but because producing text is what it does. An explicit decline has to be an available, legitimate and unpunished output, and the interface has to make declining look like competence rather than failure.

## The worked example: has anyone done this in an alga?

Ask this corpus whether a casein has ever been expressed in a microalga and the honest answer is unusually instructive, because it contains three different kinds of "no" and they are not interchangeable.

**A surveyed absence.** The keystone review [[H1]] searched literature and patent databases systematically and tabulates every reported attempt: seventeen bacterial studies, five yeast, two plant. There is no algal row. That absence was *looked for*, so it is evidence, and an agent may assert it — provided it cites the survey that licenses it. "No casein expression in a microalga has been published, per a 2025 systematic review" is a claim about the literature, and it is supported.

**A generic prior-art mention.** The single algal appearance anywhere in the corpus is a patent application listing algae among possible hosts ([[H17e]]) — a claim, not data. Omitting it overstates the whitespace; presenting it as a precedent overstates the prior art. Both errors are easy and only one looks like caution.

**An unresolved question.** Whether this host even possesses a Fam20-family secretory kinase is recorded as open ([[D5]]). No retrieved source establishes it either way. The indirect evidence points toward absence, and the corpus says so while explicitly declining to convert that into a finding — it records the resolving experiment instead. An agent answering "*Chlamydomonas* lacks FAM20C" has invented a result. The correct output is the open question, plus what would close it.

That three-way distinction — *surveyed absence*, *weak prior art*, *unresolved* — is the substance of grounding. Everything else is formatting.

## What catalogued text does to retrieval

One limitation this build states rather than papers over. Because every entry is catalogued rather than ingested, retrieval scores against the curator's notes, not the papers. So false declines are likelier — a fact present in a paper but absent from its summary is unfindable, and the system will correctly report it cannot support a claim that is nonetheless true. Every answer inherits the curator's compression, and nothing retrieved is verified: a curated span is a transcription, not a check against the source PDF.

## Three ways retrieval fails

**The corpus does not contain it.** The honest case, handled by declining and naming what the corpus does cover instead.

**Retrieval misses it.** The passage exists but scoring did not surface it. This produces a false decline — annoying, and safe.

**Retrieval surfaces something misleading.** The dangerous case, and this corpus has a perfect specimen. The secretome paper's recital of prior yields ([[r-C6-1]]) reads exactly like a measurement and is a citation of someone else's. A retrieval system that surfaces it, and an agent that cites it, produce a confident, sourced, chip-decorated answer double-counting a single measurement — and the citation makes it look *more* trustworthy, not less.

That is why the primacy flag is not bookkeeping. It stands between a grounded answer and a well-dressed error, and it is why an agent here should check whether a record is a source's own measurement before repeating the number.

## Showing the work

Trust is earned by inspectability, not by tone, so the agent's plan, tool calls and retrieved passages are first-class interface elements — and the trace must be *the actual data that produced the answer*, never a reconstruction assembled afterwards. A plausible after-the-fact trace would be worse than none: it would look like evidence while being decoration, the same failure as a fabricated F1 in lesson 0.4.`,
          },
          {
            kind: 'embed',
            embed: 'ask-prompt',
            arg: 'Has a casein ever been expressed in a microalga',
          },
          {
            kind: 'prose',
            md: `Ask it, then read the trace rather than the answer. Check which entries were retrieved, whether each cited number is that source's own measurement or a recital of someone else's, and whether any sentence in the reply asserts something no retrieved passage supports. That review — not the fluency of the prose — is the skill this module exists to build.`,
          },
        ],
        checkpoint: [
          {
            id: 'c5-1-1',
            prompt:
              'A systematic review found no algal row among reported casein expression studies. The corpus separately records that whether this host has a Fam20-family kinase is unresolved. Why must an agent treat these two "no" answers differently?',
            kind: 'mc',
            options: [
              'The first is a surveyed absence and counts as evidence; the second is an unanswered question and counts as evidence for nothing',
              'The first concerns patents and the second concerns papers',
              'The second is older and therefore less reliable',
              'They are equivalent, and both should be reported as negative findings',
            ],
            answerIndex: 0,
            explanation:
              'Someone looked for algal casein studies and found none, so the absence is informative and citable. Nobody has established whether the kinase exists, so the honest output is the open question plus the experiment that would settle it — an HMM search of the proteome against the relevant Pfam family. Converting the second into a finding is the exact failure mode grounding is meant to prevent, and it is tempting precisely because the indirect evidence leans one way.',
            evidenceChip: 'D5',
          },
          {
            id: 'c5-1-2',
            prompt:
              'Which retrieval failure is the most dangerous for a citing agent?',
            kind: 'mc',
            options: [
              'Surfacing a passage that reads like a measurement but is a paper reciting someone else’s result',
              'Failing to surface a passage that exists in the corpus',
              'Returning no passages at all for a question',
              'Returning passages ranked in a suboptimal order',
            ],
            answerIndex: 0,
            explanation:
              'A miss produces a false decline, which is safe and visible. A recital surfaced as a result produces a confident answer with a chip on it, and the chip makes it look better sourced rather than worse. This corpus contains the specimen: a secretome paper’s summary of prior yields reads exactly like its own data. The primacy flag exists for this, and an agent that repeats a number without checking it has skipped the only step that would catch the error.',
            evidenceChip: 'r-C6-1',
          },
          {
            id: 'c5-1-3',
            prompt:
              'Why does the agent state that retrieval currently runs over curators’ notes rather than paper full texts?',
            kind: 'mc',
            options: [
              'Because it changes how the answers should be read — misses are likelier, and every answer inherits the curator’s compression',
              'Because full-text retrieval is technically impossible for this corpus',
              'Because the notes are more accurate than the papers',
              'Because it reduces the number of citations each answer needs',
            ],
            answerIndex: 0,
            explanation:
              'A fact present in a paper but absent from its summary is unfindable, so a decline may be correct about the corpus and wrong about the literature. Stating the limitation costs one sentence and lets the reader calibrate; omitting it lets a decline read as a finding about the world. This is the same discipline as the empty Witness screen — describe the state you are actually in, and let the reader decide what it is worth.',
          },
        ],
      },
    ],
    outline: [
      'Chunking a catalogued corpus, and what changes after full-text ingest',
      'Embeddings, lexical matching and hybrid retrieval',
      'Reranking, result diversity and scoped retrieval within one entry',
      'Citation validation: checking that every chip supports its sentence',
      'Surfacing conflicts instead of averaging them',
      'Evaluating an agentic pipeline end to end',
    ],
  },
];
