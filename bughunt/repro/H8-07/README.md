# H8-07: the project report's kit rule credits another document's passage that shares the title

**Statement.** In `pnpm lit:report --project`, when two documents of a project carry the one title
("Strain report"), the question built from document A's candidate retrieves document B's passage first, and
the kit rule scores that passage relevant at rank 1 (MRR 1.0) while the passage rule scores A's passage at
rank 2 (MRR 0.5); B's passage is of another document and holds no quote of A's candidate.

**Contract.**
- `core/openferment_core/literature/report.py:760` (the words the report renders) and
  `docs/reports/literature-retrieval.md:57` (the committed report): "The kit's rule counts a passage of the
  question's document, or one holding a quote of its candidates; the passage rule counts the candidates' own
  passage alone."
- The kit's own docstring, `sci_rag/evals/retrieval_eval.py:5-6` (installed under `core/.venv`): "a retrieved
  item counts as relevant to a question if it comes from one of the question's reference documents, or its
  text contains one of the question's distinctive evidence phrases".

**Command.** From the repository root: `bash bughunt/repro/H8-07/run.sh`

It makes a fresh test database `bh_r_h8_07_title`, starts the head's service keyless on 127.0.0.1:10330,
creates the project `h8-07`, pastes two documents through `POST /api/intake/paste`, both titled
"Strain report" (A holds the quote "The batch fermentation reached an ethanol titre of 41 g/L after 48 h in
the H8 lane probe."; B is a short review paragraph that repeats the question's words), keeps one
`ethanol_titre` candidate on A's `p0` through `extract.add_candidate` (no model call), and runs
`python -m openferment_core.literature_live report --project h8-07 --configs interactive,vector_only,keyword_only`
(no judge, no `--render`: no model call, no committed file written, 0 USD). It reads the kept run file and,
for each kit-relevant rank, the chunk's document and text from the database. Then it stops the service,
drops the database and removes its data folder.

**Expected.** B's passage is neither of A nor holds A's quote, so the kit rule counts it irrelevant: the
kit rule's relevant ranks are `[2]`, its first relevant rank 2, as the passage rule's is (or the report says
the kit rule matches documents by title).

**Observed (both runs).** In `interactive`, `vector_only` and `keyword_only` alike: rank 1 is B's chunk
(the question's document: False; holds an evidence phrase: False); kit rule relevant ranks `[1, 2]`, first 1,
kit MRR 1.0; passage rule relevant ranks `[2]`, first 2, passage MRR 0.5. `RESULT: DEFECT` in `run1.log`
and `run2.log`.

**Likely cause.** `core/openferment_core/literature/report.py:364` builds each question's `SeedQuestion`
with `reference_titles=[titles[document_id]]`, the document's title alone, and
`core/openferment_core/literature/report.py:450` scores the kit column with the kit's `is_relevant`
(`sci_rag/evals/retrieval_eval.py:52-56`), which matches `item.title` against `reference_titles`. So every
document sharing the title counts as "the question's document". The `Asked` record already holds
`document_id` (report.py:366-367), so scoring by `i.document_id == a.document_id` or a quote match would hold
the rule as written. Fix size: small.
