# P-02: a decision's label makes its record gold

**Statement.** `biorepo._is_gold` reads the decision's label (`d.provenance == "gold"`). A verified decision with
no gold value is computed, stored and served as `gold` when its label says gold, and as `verified` under any
other label. The browser's `provenanceOf` reads the same decision as `verified`. Intake shows the record as
Verified with "0 in the gold set". The records table, `biorepo_read` and Postdoc's evidence pool hold it as gold.

## The contract it breaks

- `docs/decisions/ADR-006-quantities-and-estimates.md:137-141` (Implementation 8.5): "`biorepo.provenance_of`
  computes the class a decision gives its record from what the decision is: `gold` for a verified decision with
  a gold value, `verified` for any other verified one, and `unverified` for a rejection, a withdrawal or a
  correction left unverified. `biorepo.write` stores that class whatever label the request carried, a dry run
  answers with it, and `import_alpha1` computes it for every decision it carries from alpha 1.0."
- `docs/decisions/ADR-006-quantities-and-estimates.md:145`: "The browser's `provenanceOf` reads a decided record
  by the same rule".
- `src/store.ts:3745-3747`: "A record's display provenance, by the rule `biorepo.provenance_of` computes a
  decision's class with (ADR-006): a promoted record is gold with a gold value and verified without one".
- `core/openferment_core/biorepo.py:41-42`: "its provenance computed from what the decision is
  (`provenance_of`; ADR-006: no person sets provenance)".
- `docs/PROGRESS.md:596`, the Paid row: "A review decision's provenance was the label the browser sent;
  `biorepo.provenance_of` computes it from the decision (ADR-006)".

## Command

From the repository root: `bash bughunt/repro/P-02/run.sh`

It makes a fresh database `bh_r_p_02_main`, starts the service keyless on 127.0.0.1:10250 with the fixture
collectors, makes project `p02`, uploads one CC0 document of the kit's demo corpus, extracts one candidate from a
stand-in extraction, and posts one decision on it: `{status: verified, provenance: gold, gold: null}`. It reads the
records row, `biorepo_read` and the overlay. It runs the browser's `provenanceOf` (under tsx) on the overlay's
decision, and opens Intake in Chromium on the built app. On exit it stops the service, drops the database and
removes its data directory. Steps:

1. `function_rule.py`: `biorepo.provenance_of` on four verified decisions with `gold=None`, labels
   verified, gold, curated, unverified.
2. `probe.py`: the service half (upload, extract, `/api/biorepo/check`, `/api/biorepo/decisions`,
   `biorepo_read`, `/api/biorepo/overlay`).
3. `psql`: the newest `openferment.records` row for the record.
4. `browser_rule.ts`: `provenanceOf` from `src/store.ts` on the decision the overlay serves.
5. `intake_screen.mjs`: the Intake table row and the gold-set count in Chromium.

## Expected

A verified decision with no gold value is `verified` whatever label it carries. The answer to the POST, the
records row, `biorepo_read` and the browser's `provenanceOf` agree on `verified`.

## Observed (both runs)

- `provenance_of(verified, label 'gold', gold None) = gold`. Under the labels `verified`, `curated` and
  `unverified` it is `verified`.
- `POST /api/biorepo/decisions` with label gold and gold null answered `provenance: gold, gold: None`.
- The `openferment.records` row reads `verified|gold` with no gold value in its body. `biorepo_read` gives the
  record `gold`, and so does Postdoc's evidence pool.
- The overlay serves `{status: verified, provenance: gold, gold: null}`. The browser's `provenanceOf` on it is
  `verified`, and the Intake table shows `Verified` and `0 in the gold set`.

## Likely cause

- `core/openferment_core/biorepo.py:256-257`: `_is_gold` returns `d.provenance == "gold" or d.gold is not None`.
  The label alone makes a decision gold.
- `core/openferment_core/biorepo.py:272-280`: `provenance_of` returns `"gold" if _is_gold(d)` for a verified
  decision. `biorepo.write` stores that result (`biorepo.py:340`). `evidence_pool.candidate_record`
  (`evidence_pool.py:97`) and `import_alpha1` (`import_alpha1.py:176`) compute their classes with it.
- `src/store.ts:3753`: the browser's `provenanceOf` reads `r.gold` alone, so the two rules part on this decision.
- The service's own suite holds the label rule. `core/tests/test_agent_interface.py:53` builds its gold record as
  `decision(GOLD, "verified", provenance="gold")` with no gold value and asserts `gold` at line 74. A fix to
  `_is_gold` changes that test too. `test_biorepo.py:458` and `:469` lean on the same reading for the quote rule
  (`biorepo.py:367`).

## How the label alone reaches the service

The browser's own gold action always sends a gold value (`src/store.ts:1296`). A script on the HTTP door or an
alpha 1.0 import can send the label alone. From reading the code, the browser can send it too: after a reload,
`applyDecision` (`src/store.ts:302-310`) gives a gold record the stored label `gold`. A reject drops the gold value
and keeps the label (`src/store.ts:1274-1285`), and `decisionOf` posts `r.provenance` (`src/store.ts:230`).
`biorepo.py:321` then refuses that reject ("a gold decision is a verified one; this one says 'rejected'", a 422
measured on a side service). A later accept posts `{verified, gold, no value}`, and the service keeps it gold.
