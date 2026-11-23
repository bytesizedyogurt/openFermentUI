# H14: free use, as a new lab member

Commit 2047f5a, keyless, no model spend. Services on 8940 to 8945, test databases `bh_h14_*`, all stopped and dropped
at the end. Chromium through Playwright (headless, no proxy); screenshots and page text are in `shots/`, scripts in
`scripts/`. Nothing under core/, src/, scripts/ or examples/ was touched.

## What I did

- **A fresh project (8940, bh_h14_a).** Home with no reviewer name: Make it says in words to set the name first. Set
  the name in Settings, made "Lignin valorisation" from Home; the address stays `#/` after Make it while the project
  opens. Intake: OSTI 1013269 collected (190 passages); Europe PMC timed out once ("could not be reached; try again")
  and PMC5574463 came in on the next try; SGD S000203483 in; `12345` refused in words; a DOI with no open text refused
  in words; a pasted note stored. Extract with no key: a toast naming the missing key (`fresh1-3.mjs`).
- **The Ethanol copy (8941, bh_h14_full, pg_dump of openferment_dev).** Every rail entry toured (`tour.mjs`, `full.txt`).
  Search found titre passages and the reader opened at the passage; Answer with no key gave the kit's generic words
  (H14-03). Review queue from Intake: accept, reject with a reason, skip, accept, then gold; decisions held across a
  reload. Studies: cornstover's Run it answered at once with a three-day-old run (H14-09); corn ran in 17 s. Compared
  two cellulosic runs: the numbers agree with each run's page, and the comparison took my title over
  claude-sonnet-5-5's (H14-01). Made a runbook from a run, locked it, deposited a reading at the bench with the readings
  alone, read it back, reloaded; made a scenario on the reading from the run's page and ran it: provenance measured
  with the reading's origin and link, as ADR-006 states the rule. Kept a strain, a product and a skill on Catalogues;
  the strain page counted no record though 22 name its alias (H14-02). Guild, Primer, pureOS, fermOS, Flowsheets,
  Witness (H14-04), Artifacts, Compare, Settings, Architecture opened. Postdoc with no key says so in words. Exported
  the study package (zip with study.json, study.md, SFF files, versions). Palette found the strain by its alias.
- **Repros from fresh databases.** `repro_comparison_title.sh` (8943), `repro_strain_alias.sh` (8942),
  `repro_screens.sh` (8944: H14-03, H14-05, H14-06), `repro_witness.sh` (8945, a pg_dump copy, since a hand-written
  candidate is never scored and an extraction needs a model), `capture_comma.ts` (tsx over the tree's capture.ts).

## What I found

- H14-01 (S1): a second comparison of the same runs rewrites the kept title and leaves it in the first maker's name;
  the first title is gone with no audit row, and the export carries the new words under the old name.
- H14-02 (S2): `validate.vocabulary()` holds no strain, so anchoring never resolves an organism to a kept strain;
  strain pages, Hosts coverage and fermOS's strain filter find nothing for any strain. The tests that claim the
  resolution patch a vocabulary in (test_validate.py:160-169, test_fermos_bind.py:139-142).
- H14-03 (S3): the literature answer's no-key error says "generation failed (see server logs)"; the route promises it
  says there is no key, and the service has those words in its log.
- H14-04 (S3): Witness shows PRECISION 0.0% with no gold value under its own callout saying precision is undefined.
- H14-07 (S3): the bench capture strips commas, so "7,4 g/L" files as 74 g/L.
- H14-05, H14-06, H14-08 (S4): Home's destination lines are fixed words: "gold set not yet annotated" beside a gold set
  of one, Postdoc "live" with no key, pureOS "no process model".
- H14-09 (S4): Studies says "Ran" for a run the project already held, kept by someone else days before.

## What held

Intake's refusals in words; review decisions persisting; comparison arithmetic; pureOS recovery (0.99983 shown as
100.0%); the runbook lock and the deposition's read-back across reloads; the measured scenario's origin and link;
catalogue keeps read back in their screens; Postdoc's no-key words; `?q=` cleared after an ask; the export package;
not-found pages in words. No page or route I drove reached api.anthropic.com: llm.py refuses with no key before any call.

## Left

BenchCheck (needs a ledger and a check), ProtocolDetail and the editor's save path (no protocol made), runs of the
pureOS Builder and fermOS simulate/vessel, and the two-tab and outbox paths (H7's scripts cover them).
