// Curriculum (OF-DES-001 §8.14, §14.8). Module 0 is fully built; modules 1–5
// carry one seeded lesson each plus an outline of what is not yet written.
//
// The embeds are live components, not screenshots — the pedagogy is the
// product. SYNTHETIC content; see BUILD-SPEC.md.
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
        minutes: 8,
        blocks: [
          {
            kind: 'prose',
            md: `## The problem is not that the numbers are missing

Open any bioprocess paper and the numbers you need are right there. A specific growth rate in the Results. A medium composition in the Methods. A protein content in a table. Nothing is hidden.

The problem is that they are in *prose*. A sentence like "regression over the interval from 6 h to 30 h gave a specific growth rate of 0.118 h⁻¹" is perfectly clear to you and completely opaque to a spreadsheet. To do anything computational with that number — compare it against nine other papers, feed it to a process model, decide a seed-train schedule — a human has to read the sentence, decide what the number means, decide what units it is in, and type it somewhere.

That transcription happens thousands of times a year, in every lab, into spreadsheets that die with the semester. It is slow, it is unrewarding, and it is where the errors come from.

## What gets lost in transcription

Three things, in increasing order of seriousness.

**The units.** Growth rates get published per hour and per day, and the difference is a factor of 24. A number typed into a column headed "mu" has already lost the information needed to catch that mistake.

**The conditions.** A growth rate means nothing without the light intensity, the temperature, and the carbon source that produced it. Spreadsheets flatten those into a comment cell, if they survive at all.

**The provenance.** This is the one that matters most. Once a number is in a spreadsheet, you cannot ask it where it came from. Six months later, looking at "0.118", you cannot tell whether that was measured, estimated, copied from a review article, or typed wrong. The number has been separated from its evidence, and there is no way back.`,
          },
          { kind: 'embed', embed: 'chip-demo', arg: 'SP-001' },
          {
            kind: 'prose',
            md: `## Extraction with provenance

An extraction record is a number that never loses its source. It carries the value, the unit as published, the SI-normalized twin, the exact span of text that supports it, the paper it came from, and a status saying whether a human has checked it.

That last part is what makes the whole thing usable. A verified record is evidence. An unverified one is a machine's guess, and the interface has to show you which is which without making you ask.`,
          },
          { kind: 'embed', embed: 'record-card', arg: 'ex-0001' },
          {
            kind: 'prose',
            md: `Look at what that card gives you that a spreadsheet cell cannot. The quote is the actual sentence from [[SP-001]]. The paper chip opens the source with the span highlighted in place. The status tells you a human has looked at it. If any of that turned out to be wrong, you could find out — which is the whole difference between a number and a claim.

## Why a machine, and why a human after it

Automation is the only way to get through a corpus of any size, and it is not reliable enough to trust unsupervised. Extraction models confuse a target with a result, attach a value to the wrong parameter, carry a per-day rate through as per-hour, or pick up a number from an introduction summarizing someone else's work.

So the design is not "automate extraction." It is **extract automatically, verify cheaply, and measure how often the machine was wrong.** The next three lessons are those three things: the ontology that makes verification possible, the review workflow that makes it fast, and the metrics that make the error rate visible instead of assumed.`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-1-1',
            prompt: 'What is the single most important thing an extraction record carries that a spreadsheet cell does not?',
            kind: 'mc',
            options: [
              'A link back to the exact source span that supports the value',
              'A larger number of decimal places',
              'The name of the person who typed it in',
              'An automatic unit conversion',
            ],
            answerIndex: 0,
            explanation:
              'Provenance is the spine of the whole platform. Unit conversion and precision matter, but they are recoverable if you have the source; a number separated from its evidence cannot be checked by anyone, ever, and so cannot be trusted.',
            evidenceChip: 'ex-0001',
          },
          {
            id: 'c0-1-2',
            prompt: 'A colleague reports that a paper gives a growth rate of 0.118. Why is this not yet a usable number?',
            kind: 'mc',
            options: [
              'It has no unit, so it could differ by a factor of 24 depending on whether it is per hour or per day',
              'It has too few significant figures',
              'Growth rates are never comparable between papers',
              'It has not been rounded to two decimal places',
            ],
            answerIndex: 0,
            explanation:
              'Rates are published both per hour and per day. Without the unit the value is ambiguous by a factor of 24 — which is exactly the class of error the ontology and the unit engine exist to catch.',
          },
        ],
      },

      {
        id: 'l0-2',
        title: 'The ontology and units',
        minutes: 10,
        blocks: [
          {
            kind: 'prose',
            md: `## Sixteen fields, deliberately

An ontology is a controlled list of the things you are willing to extract. This platform's is small on purpose: sixteen parameters, each with a definition, a canonical unit, and a validation range.

Smallness is a feature. A large ontology sounds more capable but makes every downstream job harder — reviewers have to remember more distinctions, extractors have more ways to pick the wrong field, and cross-paper comparison fragments across near-duplicate categories. Sixteen fields cover what a bioprocess model actually consumes.

Each field carries three things beyond its name:

- **A definition** precise enough to settle a disagreement. "Specific growth rate" is defined as the first-order rate constant of exponential biomass increase — the slope of ln(X) against time during unrestricted growth. That definition tells a reviewer whether a rate averaged over a whole batch qualifies. It does not.
- **A canonical unit** that every value is normalized to for comparison. For growth rate, h⁻¹.
- **A validation range** — for growth rate, 0.005 to 0.35 h⁻¹. Not a hard limit. A gate that makes you look twice.

## Units are sacred

The platform stores every quantity twice: as published, and SI-normalized. Both are kept, and the interface always says which one you are looking at.

This matters because both are true and they serve different purposes. The as-published value is what the paper says — the thing you would quote, the thing a reviewer checks against the source span. The normalized value is what you compute with. Throwing away the first makes verification impossible; throwing away the second makes comparison impossible.`,
          },
          { kind: 'embed', embed: 'unit-playground' },
          {
            kind: 'prose',
            md: `Try entering \`3.6 d⁻¹\` above and watch the SI twin appear as \`0.15 h⁻¹\`. Then try \`0.9 h⁻¹\` and watch the range warning. Then try something dimensionally wrong, like \`5 g L⁻¹\` for a growth rate — the field rejects it, because grams per litre cannot be a rate no matter what number you put in front.

That dimensional check is the highest-value validation in the system. It catches the error class that does the most damage, and it catches it without needing to know anything about biology.

## Why the range warns instead of blocking

A value outside the validation range is *suspicious*, not *wrong*. Sometimes a paper genuinely reports an anomalous number, and the reviewer's job is to record what the paper said — not to make it plausible.

So an out-of-range value shows a warning with the expected range, and saves anyway, marked as anomalous. Blocking it would force the reviewer to either falsify the record or abandon it, and both are worse than an honest outlier.

This is a general principle in the interface: validation that informs, rather than validation that obstructs. The reviewer knows things the schema does not.`,
          },
          { kind: 'embed', embed: 'strip-plot', arg: 'growth_rate_mu' },
          {
            kind: 'prose',
            md: `Normalization is what makes that plot possible. Every dot is a record from a different paper, some published per hour and some per day, all converted to h⁻¹ so they share an axis. Without a canonical unit there is no plot — just a list of incomparable numbers.`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-2-1',
            prompt: 'A paper reports a specific growth rate of 3.6 d⁻¹. What is this in the platform\'s canonical unit for that field?',
            kind: 'numeric',
            answer: { value: 0.15, unit: 'h⁻¹', tolerancePct: 3 },
            explanation:
              'Dividing by 24 gives 0.15 h⁻¹. The grader here is unit-aware, so answering 3.6 d⁻¹ is also accepted — they are the same quantity, and the platform stores both.',
          },
          {
            id: 'c0-2-2',
            prompt: 'A reviewer enters a growth rate of 0.9 h⁻¹, well outside the 0.005–0.35 range. What should the interface do?',
            kind: 'mc',
            options: [
              'Warn, show the expected range, and save it anyway marked as anomalous',
              'Refuse to save until the value is inside the range',
              'Silently clamp the value to 0.35',
              'Save it without comment',
            ],
            answerIndex: 0,
            explanation:
              'The reviewer may be recording a genuinely unusual published value, and their job is to record what the paper says. Blocking forces a choice between falsifying and abandoning the record; silent clamping is worse still, because it destroys data without telling anyone.',
          },
          {
            id: 'c0-2-3',
            prompt: 'Why does the platform keep the as-published value instead of storing only the SI-normalized one?',
            kind: 'mc',
            options: [
              'So a reviewer can check the record against the source span, which quotes the original unit',
              'Because SI units are less accurate',
              'To save storage space',
              'Because some fields have no canonical unit',
            ],
            answerIndex: 0,
            explanation:
              'Verification compares the record against what the paper actually printed. If only the converted value survived, every review would require redoing the conversion by hand — and any conversion error would become invisible.',
          },
        ],
      },

      {
        id: 'l0-3',
        title: 'Reviewing like a curator',
        minutes: 12,
        blocks: [
          {
            kind: 'prose',
            md: `## The job is narrower than it looks

Reviewing an extraction is not "is this a good number." It is one question: **does the quoted span support this value, in this field, in this unit?**

That narrowness is what makes review fast. You are not evaluating the paper's methods, not deciding whether the result is believable, not comparing it against other papers. You are checking a correspondence between a piece of text and a structured record. A trained reviewer does one in ten to fifteen seconds.

## The four failure modes

Extractors fail in recognizable ways, and naming them makes them fast to spot.

**Wrong value.** The span supports a number, but not this one. Often an adjacent number from the same sentence — a confidence interval bound, a time point, a different condition's result.

**Wrong unit.** The value is right and the unit is not. Usually a rate published per day recorded as per hour, or a compound unit that lost part of itself — a conversion factor of 0.42 g L⁻¹ OD⁻¹ recorded as 0.42 g L⁻¹, which is dimensionally a concentration rather than a factor.

**Wrong span.** The value may even be correct, but the quoted text does not support it. The classic case is a sentence containing several numbers, where the extractor attached the value to a neighbouring clause. A pH of 7.0 pulled from a sentence about temperature is wrong even if the culture really was at pH 7.0.

**Not this field.** The span supports a real quantity that belongs to a different parameter. Chlorophyll in mg g⁻¹ captured as protein content in % DW.

A fifth case is not an error at all: **duplicates**, where the same measurement appears in two sections. Reject one, keep the other, and do not agonize.`,
          },
          { kind: 'embed', embed: 'mini-queue' },
          {
            kind: 'prose',
            md: `Work that queue above. It is the real review interface with real records, and your decisions persist — verify something here and its dot changes colour on the strain page.

## Accept, reject, or fix

Three outcomes, and choosing between them is mostly about whether the *span* is good.

**Accept** when the record is right as it stands.

**Edit, then accept** when the span is right and the record misreads it. This is the highest-value action in the system, because it produces a corrected value *and* a labelled example of the extractor being wrong. The platform keeps both the original extraction and your correction, which is what makes extractor-error analysis possible later.

**Reject** when the span itself is wrong or the record belongs to another field. Do not repair a record by editing its value when the span does not support it — you would be manufacturing evidence, and the next reader would have no way to tell.

## Promoting to the gold set

Flagging a record for the gold set says something stronger than "this is correct." It says **this is a reference measurement worth scoring extractors against.**

Good gold entries are unambiguous, clearly stated in the source, and cover parameters that matter downstream. A value that required judgement to interpret makes a poor gold entry — if two careful curators could disagree, an extractor's disagreement tells you nothing about the extractor.

One caution the next lesson develops: a gold annotation created by *correcting an extraction* inherits that extraction's blind spots. The parameters an extractor never notices are exactly the ones that never enter a gold set built this way — and the recall number that results will be flattering and wrong.`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-3-1',
            prompt:
              'A record claims a pH setpoint of 7.0. The quoted span reads "cultures were maintained at 25 °C throughout the batch". The culture really was at pH 7.0, stated elsewhere in the paper. What should you do?',
            kind: 'mc',
            options: [
              'Reject it as a wrong span — the quoted text does not support the value',
              'Accept it, since the value is correct',
              'Edit the value to 25 and accept it',
              'Skip it and let another reviewer decide',
            ],
            answerIndex: 0,
            explanation:
              'A record is a value plus the evidence for it. Accepting a correct value on unsupporting evidence creates a record that cannot be checked — the next reader follows the chip, finds a sentence about temperature, and has no way to know whether the number was ever verified.',
          },
          {
            id: 'c0-3-2',
            prompt:
              'An extraction reads 0.038 d⁻¹ where the source prose says 0.038 h⁻¹. What is the most useful action?',
            kind: 'mc',
            options: [
              'Edit the unit to h⁻¹ and accept — this stores the correction and labels the extractor error',
              'Reject it and move on',
              'Accept it as published',
              'Skip it, since the number itself is right',
            ],
            answerIndex: 0,
            explanation:
              'Editing then accepting produces both a usable record and a labelled instance of unit-normalization failure. That label is what lets the validation dashboard show unit errors as a distinct, shrinking failure mode across extractor versions.',
            evidenceChip: 'ex-0071',
          },
          {
            id: 'c0-3-3',
            prompt: 'What makes a record a good candidate for the gold set?',
            kind: 'mc',
            options: [
              'It is unambiguous in the source and covers a parameter that matters downstream',
              'It was difficult to interpret and required expert judgement',
              'It has the highest extractor confidence score',
              'It comes from the most recently published paper',
            ],
            answerIndex: 0,
            explanation:
              'Gold entries are the yardstick. If two careful curators could disagree about a value, an extractor disagreeing with it tells you nothing about the extractor — the measurement is testing ambiguity rather than capability.',
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

An extractor can produce something wrong, or fail to produce something right. These are different failures with different consequences, and one number cannot describe both.

**Precision** answers: of everything the extractor produced, what fraction was correct? Low precision means the output is polluted — you cannot trust a record without checking it, so the automation has bought you nothing.

**Recall** answers: of everything that was there to find, what fraction did the extractor produce? Low recall means the corpus is under-mined. What you have may be perfectly reliable, and there is simply less of it than there should be.

Formally, with TP correct extractions, FP spurious ones, and FN things missed:

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)

**F1** is their harmonic mean: F1 = 2·P·R / (P + R). The harmonic mean, not the arithmetic one, because it refuses to let a strong score on one axis paper over a weak score on the other. An extractor with precision 1.0 and recall 0.1 has an arithmetic mean of 0.55 — respectable-sounding for something that found a tenth of the data. Its F1 is 0.18.`,
          },
          { kind: 'embed', embed: 'metrics-tiles' },
          {
            kind: 'prose',
            md: `Those tiles are computed live from this session's gold set and the seeded run outputs. Verify a record or promote one to gold in the review queue and they move.

## Read the shape, not just the headline

Look at the three runs on the validation dashboard and the interesting story is not that F1 went up. It is *which axis moved*.

Precision climbs steeply — most of that gain is unit-normalization failures disappearing between v0.4 and v0.4+rules. Recall barely moves at all.

The reason is visible in the gold set: **fifteen of the forty-one gold entries have never been produced by any run.** A curator read those parameters out of the papers; no extractor configuration has found them. No amount of precision tuning touches that, because precision only describes the things the extractor did produce.

That is an uncomfortable number to display, which is precisely why it is displayed. A dashboard that showed only F1 would let you feel good about a system that is missing over a third of what a human finds.

## Leave-one-out, and why small gold sets lie

Here is a trap. You build an extractor, tune it against your gold set until the numbers look good, and report those numbers. But you tuned on the answer key — the score measures how well the extractor learned *these particular papers*, not how well it will read the next one.

**Leave-one-out** evaluation fixes this: each gold paper is scored by a configuration tuned *without* it. Every paper is judged by a version that has never seen it. With a small gold set this is far more honest than a single held-out split, because a 41-entry set cannot spare a test partition large enough to mean anything.

Two limits worth stating. It is expensive — one configuration per held-out paper. And it does not rescue a gold set that is biased in the first place: if your annotations were built by correcting extractor output, then leave-one-out faithfully measures performance against a target the extractor helped define.

This simulation *describes* leave-one-out. It does not run it, because it does not train models. The dashboard says so rather than implying a rigour it does not have.`,
          },
        ],
        checkpoint: [
          {
            id: 'c0-4-1',
            prompt:
              'A run produces 30 correct extractions and 6 spurious ones, and misses 14 gold parameters entirely. What is its F1 score?',
            kind: 'numeric',
            answer: { value: 0.75, unit: '', tolerancePct: 3 },
            explanation:
              'Precision = 30/(30+6) = 0.833. Recall = 30/(30+14) = 0.682. F1 = 2·(0.833·0.682)/(0.833+0.682) = 0.75. Note how the 14 misses drag F1 well below precision — the harmonic mean will not let a strong precision hide a weak recall.',
          },
          {
            id: 'c0-4-2',
            prompt:
              'An extractor achieves precision 0.95 and recall 0.30. What is the most accurate description of it?',
            kind: 'mc',
            options: [
              'What it finds is trustworthy, but it is leaving most of the corpus unmined',
              'It performs well overall, since precision is high',
              'It is producing many spurious records',
              'It is well balanced across both axes',
            ],
            answerIndex: 0,
            explanation:
              'High precision with low recall means the output is reliable but sparse — its F1 is 0.46. Whether that is acceptable depends entirely on your purpose: for seeding a review queue it may be fine, but for claiming corpus coverage it is not.',
          },
          {
            id: 'c0-4-3',
            prompt: 'Why does leave-one-out evaluation matter more when the gold set is small?',
            kind: 'mc',
            options: [
              'A small gold set cannot spare a held-out test partition large enough to be meaningful',
              'Small gold sets contain more errors',
              'It makes evaluation run faster',
              'It increases the number of gold annotations',
            ],
            answerIndex: 0,
            explanation:
              'Holding out 20% of 41 entries leaves 8 papers to score against — far too few for a stable estimate. Leave-one-out uses every paper as a test case exactly once, at the cost of tuning one configuration per paper.',
          },
        ],
      },
    ],
  },

  {
    id: 'm1',
    index: 1,
    title: 'Strain and media',
    blurb:
      'What a strain designation actually commits you to, and how a medium recipe encodes a set of decisions about limitation.',
    lessons: [
      {
        id: 'l1-1',
        title: 'TAP, and why cw15 wants acetate',
        minutes: 9,
        blocks: [
          {
            kind: 'prose',
            md: `## A medium is a set of decisions

Tris-acetate-phosphate medium looks like a recipe. It is better understood as a set of decisions about what will run out first.

*Chlamydomonas reinhardtii* can grow three ways: photoautotrophically on dissolved inorganic carbon, heterotrophically on acetate in darkness, and mixotrophically on both at once. TAP is built for the third. The acetate is not a supplement — it is the primary carbon source, and it is what makes cw15 grow roughly twice as fast in TAP as in a mineral medium under the same light.

The components divide into three jobs:

- **Carbon.** Acetic acid, which also sets the starting pH.
- **Nitrogen.** Ammonium chloride at 0.375 g L⁻¹ in standard TAP ([[ex-0006]]).
- **Buffer.** Tris base at 2.42 g L⁻¹ ([[ex-0005]]), plus phosphate ([[ex-0010]]) doing double duty as buffer and nutrient.

## Why so much buffer

Acetate consumption is alkalinizing. As the culture eats its carbon source, pH climbs — and cw15 tolerates that poorly past about pH 8.5.

This is why TAP carries an unusually heavy buffer load and why [[SP-002]] tests doubling it to 4.84 g L⁻¹ ([[ex-0012]]). The trade is real in both directions: more buffer holds pH longer, but Tris is not free, it contributes nothing nutritionally, and at high concentration it is itself mildly inhibitory.

The deeper point is that the buffer concentration is a *design parameter tied to batch length*. A 48-hour flask batch and a week-long fed-batch need different answers, and copying a recipe without knowing which one it was written for is how cultures crash on day four.`,
          },
          { kind: 'embed', embed: 'protocol-card', arg: 'PR-TAP-01' },
          {
            kind: 'prose',
            md: `Open that protocol and change the batch size. Every quantity recomputes and rounds to a pipettable increment — which is the difference between a recipe you can read and one you can execute.`,
          },
        ],
        checkpoint: [
          {
            id: 'c1-1-1',
            prompt: 'Why does TAP medium carry such a heavy Tris buffer load?',
            kind: 'mc',
            options: [
              'Acetate consumption raises pH, and cw15 tolerates pH above about 8.5 poorly',
              'Tris is a nitrogen source for the culture',
              'It prevents contamination',
              'It increases the solubility of trace metals',
            ],
            answerIndex: 0,
            explanation:
              'Consuming acetate is alkalinizing, so pH drifts upward over the batch. The buffer concentration is effectively a decision about how long the batch can run before pH becomes the limitation.',
            evidenceChip: 'ex-0012',
          },
          {
            id: 'c1-1-2',
            prompt: 'Roughly what fold-advantage does mixotrophic growth give cw15 over photoautotrophic growth?',
            kind: 'numeric',
            answer: { value: 2.2, unit: '', tolerancePct: 12 },
            explanation:
              'SP-003 measures both modes under otherwise matched conditions: 0.132 h⁻¹ mixotrophic against 0.061 h⁻¹ photoautotrophic, a 2.2× advantage. The advantage is in rate, not necessarily in yield or cost.',
            evidenceChip: 'ex-0020',
          },
        ],
      },
    ],
    outline: [
      'Strain designations and what they commit you to',
      'Cell-wall mutants and downstream consequences',
      'Defined vs complex media',
      'Trace elements and chelation',
      'Sterilization and its effect on composition',
    ],
  },

  {
    id: 'm2',
    index: 2,
    title: 'Upstream: growth and control',
    blurb: 'What μ actually measures, why the growth curve has phases, and what you can control.',
    lessons: [
      {
        id: 'l2-1',
        title: 'What μ actually measures',
        minutes: 10,
        blocks: [
          {
            kind: 'prose',
            md: `## The rate constant, not the speed

The specific growth rate μ is the first-order rate constant of exponential biomass increase. Formally, dX/dt = μX — the rate of biomass production is proportional to how much biomass you already have.

The word doing the work is *specific*: per unit biomass. A culture at 4 g L⁻¹ produces four times as much biomass per hour as one at 1 g L⁻¹ at the same μ. μ describes how fast each gram of cells is making more cells, not how fast the tank is filling.

This is why μ is the parameter that propagates furthest into process design. It is the one growth quantity that is independent of scale and of how much you started with, so it is the only one that transfers between a flask and a 100 m³ vessel.

Doubling time is the same information in more intuitive units: t_d = ln(2)/μ. At 0.118 h⁻¹ ([[ex-0001]]), that is 5.9 hours.

## The phases, and why only one of them counts

A batch culture goes through lag, exponential, deceleration, and stationary phase. μ is defined on the exponential phase alone — the interval where growth is unrestricted and ln(X) against t is genuinely a straight line.

Which makes the measurement a judgement call, and this is where most cross-paper disagreement comes from. Regress over too wide a window and you pull in decelerating points, dragging the estimate down. Too narrow and you are fitting noise.

The careful convention is to regress over the interval where the residuals show no systematic trend, and to state that interval. Compare [[ex-0001]] at 0.118 h⁻¹, measured over a residual-checked window, with [[ex-0070]] at 0.094 h⁻¹, averaged over the first 36 hours of batch. These are not the same measurement, and most of the gap between them is method rather than biology.

When you see growth rates disagreeing across papers, suspect the regression window before you suspect the strain.`,
          },
          { kind: 'embed', embed: 'strip-plot', arg: 'growth_rate_mu' },
          {
            kind: 'prose',
            md: `## What actually limits the rate

Something is always limiting. The skill is knowing what.

**Light**, in photoautotrophic and mixotrophic culture, and it saturates — [[SP-005]] finds cw15 saturating near 150 µmol m⁻² s⁻¹ at 0.141 h⁻¹ ([[ex-0036]]), with photoinhibition above it. More light past saturation buys nothing and eventually costs.

**Carbon**, which announces itself by *how* growth stops: an abrupt halt rather than a taper is the signature of a carbon-limited culture.

**Nitrogen**, which does something more interesting — growth continues at a reduced rate while protein content collapses ([[ex-0028]] to [[ex-0029]], 38 % DW down to 17 % DW in 48 hours).

**pH**, the sneaky one, because it drifts rather than depletes.`,
          },
        ],
        checkpoint: [
          {
            id: 'c2-1-1',
            prompt: 'A culture grows with μ = 0.118 h⁻¹. What is its doubling time?',
            kind: 'numeric',
            answer: { value: 5.9, unit: 'h', tolerancePct: 4 },
            explanation:
              't_d = ln(2)/μ = 0.693/0.118 = 5.9 h. Answering in minutes or days is also accepted — the grader converts.',
            evidenceChip: 'ex-0001',
          },
          {
            id: 'c2-1-2',
            prompt: 'Growth stops abruptly rather than tapering off. What does this suggest?',
            kind: 'mc',
            options: [
              'A carbon source was exhausted — depletion of a consumed substrate stops growth sharply',
              'The culture became light limited',
              'The temperature control failed',
              'The culture was contaminated',
            ],
            answerIndex: 0,
            explanation:
              'Light limitation tightens gradually as cells shade each other, producing a taper. Substrate exhaustion removes the input entirely and stops growth sharply — the shape of the curve is diagnostic.',
          },
        ],
      },
    ],
    outline: [
      'Batch, fed-batch and continuous culture',
      'Oxygen transfer and kLa',
      'pH and temperature control',
      'Light delivery and photoinhibition',
      'Scale-up: what transfers and what does not',
    ],
  },

  {
    id: 'm3',
    index: 3,
    title: 'Harvest and downstream',
    blurb: 'Getting the product out of the cell, and why the cell wall decides how hard that is.',
    lessons: [
      {
        id: 'l3-1',
        title: 'Why cw15 changes the downstream problem',
        minutes: 9,
        blocks: [
          {
            kind: 'prose',
            md: `## The wall is the whole problem

For an intracellular product, downstream processing has one hard step: getting through the cell wall. Everything else — concentration, clarification, polishing — is comparatively routine engineering.

Microalgal walls are genuinely difficult. Bead milling and high-pressure homogenization work but are energy-intensive at scale, and the energy cost of disruption is often the largest single line in an algal process's operating budget.

This is why cw15 exists in bioprocess work at all. It is a cell-wall-deficient mutant: the glycoprotein wall is largely absent, so disruption takes far less specific energy. [[SP-006]] reaches **94.2 % disruption efficiency** ([[ex-0043]]) under conditions that leave a walled strain substantially intact.

## The trade you make

The wall was doing a job. Without it, cw15 is markedly shear-sensitive — it lyses under mild hydrodynamic stress that a walled strain shrugs off.

This shifts the difficulty upstream rather than removing it. Pump selection, impeller tip speed, and sparging rate all become constraints in cultivation. A centrifugal pump appropriate for a walled culture can cost you a meaningful fraction of your biomass before it reaches the disruption step.

The strain page carries a curator note to exactly this effect, because it is the kind of thing that is obvious in hindsight and expensive to learn.

## Recovery multiplies

Downstream yield is a product of stage efficiencies, and that arithmetic is unforgiving. [[SP-006]] reports harvest recovery of **96.4 %** ([[ex-0046]]) and disruption efficiency of 94.2 %. Chain those with a 90 % extraction and an 85 % polish:

0.964 × 0.942 × 0.90 × 0.85 = **0.69**

Four good stages, and nearly a third of the product is gone. This is why downstream yield dominates the economics of the fed-batch scenario, and why an apparently modest improvement at any one stage moves the minimum selling price more than most people expect.`,
          },
          { kind: 'embed', embed: 'protocol-card', arg: 'PR-HARV-01' },
        ],
        checkpoint: [
          {
            id: 'c3-1-1',
            prompt: 'What is the main downstream advantage of cw15 over a walled strain, and what does it cost?',
            kind: 'mc',
            options: [
              'Far lower disruption energy, at the cost of marked shear sensitivity during cultivation',
              'Higher protein content, at the cost of slower growth',
              'Better harvest recovery, at the cost of a longer batch',
              'Easier sterilization, at the cost of contamination risk',
            ],
            answerIndex: 0,
            explanation:
              'The absent glycoprotein wall makes disruption much cheaper but removes the cell\'s mechanical protection, moving the constraint upstream into pump and impeller selection.',
            evidenceChip: 'ex-0043',
          },
          {
            id: 'c3-1-2',
            prompt: 'Four downstream stages run at 96%, 94%, 90% and 85%. What is the overall recovery?',
            kind: 'numeric',
            answer: { value: 69, unit: '%', tolerancePct: 4 },
            explanation:
              '0.96 × 0.94 × 0.90 × 0.85 = 0.69, or about 69%. Stage efficiencies multiply, so four individually respectable stages still lose nearly a third of the product.',
          },
        ],
      },
    ],
    outline: [
      'Harvest: centrifugation, filtration, flocculation',
      'Disruption methods and their energy costs',
      'Extraction and fractionation',
      'Polishing and formulation',
      'Yield accounting across the train',
    ],
  },

  {
    id: 'm4',
    index: 4,
    title: 'Techno-economics with BioSTEAM',
    blurb: 'What a minimum selling price is, what dominates it, and how to read a sensitivity analysis.',
    lessons: [
      {
        id: 'l4-1',
        title: 'Reading a minimum selling price',
        minutes: 11,
        blocks: [
          {
            kind: 'prose',
            md: `## One number, and what it hides

The minimum selling price is the price per kilogram of product at which the process exactly breaks even over its lifetime — revenue covers operating costs and returns the capital at the required rate. Below it you lose money; above it you make some.

MSP is useful because it collapses a whole process into one comparable number. It is dangerous for exactly the same reason. Two processes with the same MSP can have completely different risk profiles: one dominated by capital, the other by a feedstock whose price moves 30% a year.

So the MSP is where you *start* reading, not where you stop. The cost breakdown is the actual content.

## The lines, and how they scale

**Capital, annualized.** Equipment cost scales sub-linearly with size — roughly as capacity to the power of about 0.6. Doubling scale costs about 52% more, not 100%. This is the single strongest argument for building big, and why capital per kilogram falls steeply along the scale axis.

**Media and feedstock.** You pay per litre processed and sell per kilogram produced, so this line is inversely proportional to titer or final biomass density. Doubling titer roughly halves media cost per kilogram — which is why titer dominates the fed-batch scenario at the low end.

**Utilities.** Mixing, aeration, lighting, heating. Also per-litre, so it also falls with concentration.

**Labor.** Broadly fixed against scale, so per-kilogram labor falls as you build bigger.

**Downstream.** Inversely proportional to recovery yield, and the reason the yield arithmetic from the previous module matters economically.

## Sensitivity, and reading a tornado

A tornado chart varies one assumption at a time — typically ±20% — and plots the resulting swing in MSP, sorted by magnitude.

Read it for two things. Which assumptions actually matter, so you know where to spend effort reducing uncertainty. And **asymmetry**: a bar longer on one side means the risk is not symmetric, which is usually more decision-relevant than the bar's length.

The honest caveat, stated on the chart itself: one-at-a-time sensitivity is evaluated at a reference point and ignores interactions. Titer and downstream yield are not independent in reality, and a tornado will not tell you that.

These models are illustrative. They are the right *shape* — the scaling laws and dependencies are real — but the absolute numbers are demonstration values, and every screen that shows them says so.`,
          },
          { kind: 'embed', embed: 'scenario-widget', arg: 'sc-s2' },
          {
            kind: 'prose',
            md: `Move the titer slider and watch the MSP fall steeply below about 12 g L⁻¹ and then flatten. That knee is the whole argument for strain and feed-strategy work in this process: below it, titer is the cheapest lever available; above it, capital and downstream take over and further titer gains buy progressively less.`,
          },
        ],
        checkpoint: [
          {
            id: 'c4-1-1',
            prompt: 'Capital cost scales with capacity to the power of about 0.6. Doubling the scale increases capital cost by roughly what percentage?',
            kind: 'numeric',
            answer: { value: 52, unit: '%', tolerancePct: 10 },
            explanation:
              '2^0.6 = 1.52, so capital rises about 52% for double the capacity — the economy-of-scale effect that makes capital per kilogram fall steeply with plant size.',
          },
          {
            id: 'c4-1-2',
            prompt: 'Why does media cost per kilogram of product fall as titer rises?',
            kind: 'mc',
            options: [
              'Media is consumed per litre processed while product is sold per kilogram, so higher titer spreads the same media cost over more product',
              'Higher titer cultures need less concentrated media',
              'Media becomes cheaper to buy at larger scale',
              'Higher titer reduces the number of batches per year',
            ],
            answerIndex: 0,
            explanation:
              'The denominator changes, not the numerator. You still pay for the same litre of medium; it simply yields more product — which is why titer is the dominant lever at the low end of the fed-batch scenario.',
          },
        ],
      },
    ],
    outline: [
      'Capital cost estimation and scaling exponents',
      'Operating cost structure',
      'Discounting and annualization',
      'Sensitivity and uncertainty analysis',
      'Interpreting a flowsheet',
    ],
  },

  {
    id: 'm5',
    index: 5,
    title: 'Agentic literature methods',
    blurb: 'Retrieval, grounding, and why "cite or decline" is the only workable contract.',
    lessons: [
      {
        id: 'l5-1',
        title: 'Cite or decline',
        minutes: 10,
        blocks: [
          {
            kind: 'prose',
            md: `## Retrieval before generation

A language model asked a bioprocess question will answer it. Whether it *knows* the answer is a separate matter, and from the outside the two cases look identical — same fluency, same confidence, same specific-sounding numbers.

Retrieval-augmented generation restructures the problem. Instead of asking the model what it knows, you retrieve passages from a corpus you control and ask it to answer *from those passages only*. The model's job shifts from recall to reading comprehension, which is a task it is far better at and, more importantly, one you can check.

The checkable part is what matters. If the answer must come from retrieved passages, and the passages are shown, then a reader can verify any claim by following it back. The system stops asking for trust and starts offering evidence.

## The contract

The instruction that makes this work is narrow and strict: **answer only from the provided passages; cite every quantitative claim; if the passages do not support an answer, say so.**

That last clause does the heavy lifting. Without it a model faced with insufficient evidence will produce a plausible answer anyway — not from malice but because producing text is what it does. An explicit decline has to be an available, legitimate, unpunished output.

You can see this in the demo: ask about CRISPR editing of cw15, which nothing in this corpus covers, and the agent declines and names what the corpus does contain. That decline is more valuable than a fluent paragraph, because a fluent paragraph would be indistinguishable from a real answer.

## Showing the work

Trust is earned by inspectability, not by tone. So the agent's plan, tool calls, and retrieved passages are all first-class interface elements — collapsed by default, one click away, never hidden.

An important design constraint follows: the trace must be *the actual data that produced the answer*, not a reconstruction generated afterward. A plausible-looking trace assembled after the fact would be worse than no trace at all, because it would look like evidence while being decoration.

## Where retrieval fails

Three ways, worth recognizing.

**The corpus does not contain it.** The honest case, handled by declining.

**Retrieval misses it.** The passage exists but scoring did not surface it. This produces a false decline — annoying, but safe.

**Retrieval surfaces something misleading.** The dangerous case. A passage from an introduction summarizing *other* work reads exactly like a result. This is the same failure the extractor makes, and it is why a paper's structure — which section a claim comes from — is information, not formatting.`,
          },
          { kind: 'embed', embed: 'ask-prompt', arg: 'How was the gold set built' },
        ],
        checkpoint: [
          {
            id: 'c5-1-1',
            prompt: 'Why is an explicit decline a valuable output from a retrieval-augmented agent?',
            kind: 'mc',
            options: [
              'Without it, a model facing insufficient evidence will produce a plausible answer indistinguishable from a real one',
              'It reduces the compute cost of answering',
              'It prevents the corpus from growing too large',
              'It is required by the retrieval algorithm',
            ],
            answerIndex: 0,
            explanation:
              'Generating text is what the model does, so a decline has to be an explicitly available and unpunished output. A fluent unsupported answer is more dangerous than no answer because nothing about its surface reveals the difference.',
          },
          {
            id: 'c5-1-2',
            prompt: 'Which retrieval failure is the most dangerous?',
            kind: 'mc',
            options: [
              'Surfacing a passage that reads like a result but actually summarizes other work',
              'Failing to find a passage that exists in the corpus',
              'Returning no passages at all',
              'Returning passages in the wrong order',
            ],
            answerIndex: 0,
            explanation:
              'A miss produces a false decline, which is safe. A misleading hit produces a confident, cited, wrong answer — and the citation makes it look more trustworthy, not less. This is the same failure mode the extractor has with introduction sections.',
          },
        ],
      },
    ],
    outline: [
      'Chunking strategies and their trade-offs',
      'Embeddings and hybrid retrieval',
      'Reranking and result diversity',
      'Grounding, attribution and citation validation',
      'Evaluating an agentic pipeline end to end',
    ],
  },
];
