# P-03: Guild's review strip still names the retired identifier rule

**Statement.** Guild's review strip tells the reviewer that the records it hides sit "on papers with no
PMCID, DOI or PMID, which `biorepo.write` refuses"; the filter it describes hides records on
documents the project does not hold (`paperHeld`, `paper !== undefined`) and `biorepo.write` keeps a
decision on a held document with no identifier; two comments in `src/lib/review.ts` keep the same retired
rule.

**Contract.**

- `docs/PROGRESS.md:601`, a row of the Paid table:

  > The client's review path kept alpha 1.0's curated-record machinery (the extractor's best candidate
  > beside a curated record, the span carried on promotion) and its committed file's rule that a decision
  > needs a PMCID, DOI or PMID | alpha 2.0, 8.5 | `5287542`

- `docs/PROGRESS.md:1208-1212`, the stage 8.5 log the row points to:

  > The review queue's filter and the client's refusal rule kept alpha 1.0's committed-file rule: a
  > decision on a document with no PMCID, DOI or PMID was kept in the browser only, and such records were
  > hidden from the default queue, though `biorepo.write` keeps a decision on any document the project
  > holds (an upload, an OSTI report, an SGD entry). The rule is the service's now (`paperHeld`).

- `core/openferment_core/biorepo.py:26-27`, the rule `biorepo.write` refuses under:

  > paper      the record's paper is not a document the project holds — a decision stands on a text a
  > reader can look up (§7.4)

**Command** (from the repository root):

    bash bughunt/repro/P-03/run.sh

It greps the contract, the strip's words (`src/screens/Guild.tsx:621-629`), the filter they describe
(`Guild.tsx:208-216`), `paperHeld` (`src/lib/review.ts:215-217`), the service's `paper` refusal
(`biorepo.py:315-320`) and the two comments. Then it starts the head's own service on 127.0.0.1:10120
over a fresh database `bh_r_p_03_svc` (fixture mode, keyless, no model call, no network), makes the project
`p03`, uploads two of the kit's CC0 demo documents through Intake (`seed.py`), so the project holds two
documents with no DOI and no PMCID, writes a stand-in extraction for each, extracts one candidate from
each, and accepts one through `POST /api/biorepo/decisions`. `filter.ts` runs Guild's filter, with the
tree's own `paperHeld`, over the project's overlay, plus one waiting record on a paper with a DOI and a
PMCID that the project does not hold. The script stops the service and drops the database at the end.

**Expected.** The strip names the rule the filter applies: the hidden records sit on documents the project
does not hold, the rule `paperHeld` and `biorepo.write`'s `paper` share.

**Observed** (run1.log, run2.log, both `RESULT: DEFECT`).

- `src/screens/Guild.tsx:627-628` renders "— hiding N record(s) on papers with no PMCID, DOI or PMID,
  which `biorepo.write` refuses" whenever `hiddenByFilter > 0`. The box is on by default while the service
  answers (`keepableOnly = filterChoice ?? serviceUp === true`, `Guild.tsx:206`).
- `hiddenByFilter` counts waiting records whose paper `paperHeld` does not find, and `paperHeld` is
  `return paper !== undefined;`, reading no identifier.
- On the live service, `biorepo.write` kept a verified decision (HTTP 200) on an upload with
  `doi=None pmcid=None`. The filter shows the other upload's waiting record, a document with no PMCID or
  DOI, and hides the record on a paper carrying a DOI and a PMCID that the project does not hold. Both
  halves of the sentence name the wrong set: the hidden records may carry every identifier, and
  `biorepo.write` keeps decisions on documents that carry none.
- `src/lib/review.ts:224` ("a paper with no identifier can still be decided here") and `:310` ("A paper
  with no identifier is still reviewable here") describe the `paper` refusal by the retired rule.

The record on a paper the project does not hold is added to the filter's input by `filter.ts`; the
service made no such candidate here, and the strip itself was not drawn in Chromium. The words, the filter
and `paperHeld` are the tree's own, read and run unchanged.

**Likely cause.** `src/screens/Guild.tsx:621-629` and `src/lib/review.ts:221-227` and `:310` kept their
words when `5287542` moved the filter and the refusal rule to `paperHeld` (`src/lib/review.ts:210-217`).
The fix is the strip's sentence and the two comments, naming documents the project does not hold.
