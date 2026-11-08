<!-- Written by `pnpm lit:report` (core/openferment_core/literature/report.py); regenerate, do not edit. -->

# Literature retrieval report

Sci RAG Kit's retrieval evaluation over its demo corpus, as openFerment runs the kit (2026-10-30):
FastEmbed `BAAI/bge-small-en-v1.5` (384 dimensions), the project's scope, and the
configurations that ask no model. `interactive` is what BioRepo → Search runs. The kit's
note below compares rows with `full_deep`, which asks a model and is not run here: read
`interactive` as the baseline instead.

## The kit's retrieval evaluation

Corpus: 5 documents, 34 chunks, 0 entities, 0 communities.
Embedding versions: fastembed:BAAI/bge-small-en-v1.5@384.

| Config | hit@5 | hit@10 | MRR | nDCG@10 | questions |
|--------|------:|-------:|----:|--------:|----------:|
| interactive | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.94 [0.89, 0.98] | 9 |
| vector_only | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.94 [0.89, 0.98] | 9 |
| keyword_only | 0.33 [0.00, 0.67] | 0.33 [0.00, 0.67] | 0.33 [0.00, 0.67] | 0.33 [0.00, 0.67] | 9 |

Warning: n=9 questions is a small sample. The 95% intervals are
wide, and metric differences inside overlapping intervals are noise,
not findings.

Cells are mean [95% bootstrap CI], resampled per question.

Read this table by comparing rows against `full_deep`: a layer earns
its place when removing it drops hit rate or MRR. Misses by question
are in report.json.

## Missed questions

- `keyword_only`: rice-straw-generated
- `keyword_only`: rice-straw-baled
- `keyword_only`: rice-straw-ash
- `keyword_only`: almond-pruning-yield
- `keyword_only`: biogas-yield-pretreated
- `keyword_only`: chip-moisture-limit

<!-- The parts below are written by `pnpm lit:report --project <id> --render`. -->

## The project `ethanol`

Run 2026-11-08 08:17:27 UTC at `311990d`, configurations `interactive`, `vector_only`, `keyword_only`, with no judge. Written by `pnpm lit:report --project ethanol --render` from the run's public numbers; the run whole (its questions, answers and rationales) stays in the service's data folder, outside git.

### The corpus

22 documents, 814 passages and 381899 kit tokens (the kit's estimate, four characters a token where tiktoken is absent), embedded as fastembed:BAAI/bge-small-en-v1.5@384. The concept graph covers 0 of the 814 passages: 0 entities the project's passages name and 0 relationships they hold, 0 communities. Entities by type: none. Relationships by type: none.

### The ground truth

130 questions, built by code from 457 of the 457 candidates the project keeps, one a group of candidates by document, passage and field (130 groups), over 20 of its 22 documents. A candidate counts when its quote stands in the passage it cites; left out: none. Questions by field: biomass_yield_substrate 12, cake_moisture 2, ethanol_max_conc 2, ethanol_mesp 7, ethanol_productivity 5, ethanol_titre 13, ethanol_yield_substrate 14, final_biomass_density 4, fold_improvement 2, growth_rate_mu 29, medium_component_conc 22, monod_ks 10, product_purity 1, step_recovery 1, substrate_inhibition_ki 3, time_to_colony 1, titer_secreted 2. Each question is tagged `from-candidates`: its words and its evidence come from a model's extraction that no person has reviewed, so every number below is provisional.

### Retrieval

The kit's rule counts a passage of the question's document, or one holding a quote of its candidates; the passage rule counts the candidates' own passage alone. Each cell is the mean with its 95% bootstrap interval.

| Configuration | n | hit@5 kit | hit@10 kit | MRR kit | nDCG@10 kit | hit@5 passage | hit@10 passage | MRR passage | nDCG@10 passage |
|---|---|---|---|---|---|---|---|---|---|
| `interactive` | 130 | 0.42 [0.33, 0.50] | 0.54 [0.45, 0.62] | 0.30 [0.24, 0.36] | 0.36 [0.30, 0.42] | 0.12 [0.06, 0.17] | 0.17 [0.11, 0.24] | 0.09 [0.05, 0.13] | 0.11 [0.06, 0.15] |
| `vector_only` | 130 | 0.42 [0.33, 0.50] | 0.54 [0.45, 0.62] | 0.31 [0.25, 0.38] | 0.36 [0.30, 0.42] | 0.12 [0.06, 0.17] | 0.17 [0.11, 0.23] | 0.09 [0.05, 0.13] | 0.11 [0.06, 0.15] |
| `keyword_only` | 130 | 0.06 [0.02, 0.10] | 0.06 [0.02, 0.10] | 0.04 [0.01, 0.07] | 0.05 [0.02, 0.08] | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.01] |

| Configuration | graph stage | HyDE stage | calls | USD | seconds |
|---|---|---|---|---|---|
| `interactive` | disabled 130 | disabled 130 | 0 | 0.0000 | 2.7 |
| `vector_only` | disabled 130 | disabled 130 | 0 | 0.0000 | 1.9 |
| `keyword_only` | disabled 130 | disabled 130 | 0 | 0.0000 | 1.0 |

A layer earns its place when removing it moves a measure outside the overlap of the intervals: `full_deep` beside `no_graph` and `no_hyde`. Under a project's scope the graph seeds on exact names alone (ADR-002, Implementation F).

- `interactive` missed at ten under the passage rule: lq-001, lq-002, lq-003, lq-004, lq-005, lq-006, lq-007, lq-009, lq-010, lq-011, lq-013, lq-014, lq-015, lq-016, lq-017, lq-018, lq-019, lq-020, lq-021, lq-022, lq-026, lq-030, lq-031, lq-032, lq-034, lq-036, lq-038, lq-039, lq-041, lq-042, lq-043, lq-044, lq-045, lq-046, lq-048, lq-049, lq-050, lq-051, lq-052, lq-053, lq-054, lq-055, lq-056, lq-057, lq-058, lq-059, lq-060, lq-061, lq-062, lq-063, lq-064, lq-065, lq-066, lq-067, lq-068, lq-069, lq-070, lq-071, lq-072, lq-073, lq-074, lq-075, lq-076, lq-077, lq-078, lq-082, lq-083, lq-084, lq-085, lq-086, lq-088, lq-089, lq-090, lq-091, lq-093, lq-094, lq-095, lq-096, lq-097, lq-098, lq-099, lq-100, lq-101, lq-103, lq-104, lq-105, lq-106, lq-107, lq-108, lq-110, lq-111, lq-112, lq-113, lq-114, lq-116, lq-117, lq-118, lq-119, lq-120, lq-121, lq-122, lq-123, lq-124, lq-125, lq-126, lq-127, lq-129, lq-130.
- `vector_only` missed at ten under the passage rule: lq-001, lq-002, lq-003, lq-004, lq-005, lq-006, lq-007, lq-009, lq-010, lq-011, lq-013, lq-014, lq-015, lq-016, lq-017, lq-018, lq-019, lq-020, lq-021, lq-022, lq-026, lq-030, lq-031, lq-032, lq-034, lq-036, lq-038, lq-039, lq-041, lq-042, lq-043, lq-044, lq-045, lq-046, lq-048, lq-049, lq-050, lq-051, lq-052, lq-053, lq-054, lq-055, lq-056, lq-057, lq-058, lq-059, lq-060, lq-061, lq-062, lq-063, lq-064, lq-065, lq-066, lq-067, lq-068, lq-069, lq-070, lq-071, lq-072, lq-073, lq-074, lq-075, lq-076, lq-077, lq-078, lq-079, lq-082, lq-083, lq-084, lq-085, lq-086, lq-088, lq-089, lq-090, lq-091, lq-093, lq-094, lq-095, lq-096, lq-097, lq-098, lq-099, lq-100, lq-101, lq-103, lq-104, lq-105, lq-106, lq-107, lq-108, lq-110, lq-111, lq-112, lq-113, lq-114, lq-116, lq-117, lq-118, lq-119, lq-120, lq-121, lq-122, lq-123, lq-124, lq-125, lq-127, lq-129, lq-130.
- `keyword_only` missed at ten under the passage rule: lq-001, lq-002, lq-003, lq-004, lq-005, lq-006, lq-007, lq-008, lq-009, lq-010, lq-011, lq-012, lq-013, lq-014, lq-015, lq-016, lq-017, lq-018, lq-019, lq-020, lq-021, lq-022, lq-023, lq-024, lq-025, lq-026, lq-027, lq-028, lq-029, lq-030, lq-031, lq-032, lq-033, lq-034, lq-035, lq-036, lq-037, lq-038, lq-039, lq-040, lq-041, lq-042, lq-043, lq-044, lq-045, lq-046, lq-047, lq-048, lq-049, lq-050, lq-051, lq-052, lq-053, lq-054, lq-055, lq-056, lq-057, lq-058, lq-059, lq-060, lq-061, lq-062, lq-063, lq-064, lq-065, lq-066, lq-067, lq-068, lq-069, lq-070, lq-071, lq-072, lq-073, lq-074, lq-075, lq-076, lq-077, lq-078, lq-080, lq-081, lq-082, lq-083, lq-084, lq-085, lq-086, lq-087, lq-088, lq-089, lq-090, lq-091, lq-092, lq-093, lq-094, lq-095, lq-096, lq-097, lq-098, lq-099, lq-100, lq-101, lq-102, lq-103, lq-104, lq-105, lq-106, lq-107, lq-108, lq-109, lq-110, lq-111, lq-112, lq-113, lq-114, lq-115, lq-116, lq-117, lq-118, lq-119, lq-120, lq-121, lq-122, lq-123, lq-124, lq-125, lq-126, lq-127, lq-128, lq-129, lq-130.

### Routes

| Family | effort | models |
|---|---|---|
| `plan` | high | claude-opus-5-5, claude-sonnet-5-5 |
| `explain` | high | claude-opus-5-5, claude-sonnet-5-5 |
| `extract` | high | claude-opus-5-5, claude-sonnet-5-5 |
| `index` | low | claude-haiku-5-5 |
| `judge` | max | claude-opus-5-5, claude-sonnet-5-5 |

### Cost

Retrieval 0.0000 USD, the judge's relevance 0.0000 USD, answers and their grading 0.0000 USD: 0.0000 USD in all.

<!-- Added by hand at alpha 2.2 F.5 (docs/PROGRESS.md, stage F's log): the next `pnpm lit:report --project ethanol ... --render` writes this project's part whole from its own run, these two sections with it. -->

### What this run measured

The run above asked no model: 0 calls and 0 USD in its tally, 8.5 s for the command whole, each configuration's own
seconds in the table. The command:

    pnpm lit:report --project ethanol --by "Claude Code (build session)" --configs interactive,vector_only,keyword_only --render

Its run whole stays in the service's data folder, outside git. Its ground truth is built by code from the candidates the
project keeps (`report.truth`): 130 questions from the 457 candidates its 22 documents hold, 20 of them with candidates, extracted on 5 November, one
question a group by document, passage and field. Each question was asked of the retriever inside the project's scope in
the three configurations that ask no model: `interactive` (vectors and keywords together, as BioRepo → Search runs),
`vector_only` and `keyword_only`. Each configuration's top ten was scored under both relevance rules: the kit's rule (a
passage of the question's document, or one holding a quote of its candidates) and the passage rule (the candidates' own
passage). `keyword_only` returned no passage for 102 of the 130 questions, one for 22, four for one and ten for five, the
same under both rules; `interactive` and `vector_only` returned ten for every question.

### What waits on the account

The Anthropic account refuses every model call until 2026-12-01 00:00 UTC (`docs/PROGRESS.md`, Blockers). Each lane
below asks a model and runs once the account answers, in this order, `<name>` the person each run is audited under.

1. The concept graph, on the `index` route: `pnpm lit:graph --project ethanol --by <name>`. Its dry run (`pnpm lit:graph
   --project ethanol --dry-run`, which calls no model) measured 814 passages in 92 batches and 1,758,899 prompt
   characters (439,725 kit tokens): their input comes to 0.2199 USD on `claude-haiku-5-5`, and the most the build could
   cost, each batch's whole answer counted, to 2.3239 USD.
2. The configurations that ask a model, `full_deep`, `no_graph` and `no_hyde`, which measure the graph and HyDE layers
   each by its removal; the judge's grading of the top ten of `interactive` and `full_deep`, on the `judge` route; and
   the answer lane, the kit's answer through `interactive` and `full_deep` on the `explain` route, graded blind for
   grounding on the `judge` route. One run gives them all and renders this part again: `pnpm lit:report --project
   ethanol --by <name> --judge --render`.
3. The answer lane is the measure `explain`'s default rests on: the routing table holds `explain` at the `extract`
   route's models and effort until that lane's live run sets the family's default (ADR-008, Implementations 17 and 18).
   The same run's count of the kit's judgements that stopped at their ceiling measures the kit's room at max
   (`llm.KIT_ROOM`, Implementation 18).
