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

