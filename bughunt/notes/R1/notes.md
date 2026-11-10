# Hunt R1: docs/PROGRESS.md and the alpha 2.2 reports, held to the tree at 2047f5a

Every sentence of PROGRESS.md's Resume, Current stage, both Spend tables, Decisions, Departures, Blockers, Owner
questions, Environment facts, Live owed and the alpha 2.2 Log was read as a claim; Known debts went to task P and
Last green runs to the baseline. The five reports alpha 2.2 added or changed were recomputed where their numbers
run offline. Keyless throughout; one service on 127.0.0.1:8960 over `bh_r1_main`, stopped and dropped. The
candidates are in `candidates.json`, the items in `coverage.jsonl`, and every script in `scripts/`.

## How

- Mechanical passes over the record at 2047f5a: `paths.py` (every backticked path), `pnpm_cmds.py` (every
  `pnpm <script>`), `idents.py` (every backticked identifier looked up in the code and docs), `routes.py` (every
  `METHOD /api/...` against openapi.json and api.py's decorators). Each flagged token was read in its line; most
  are deletions the record names as deletions, or concrete values of parametrized routes.
- Read against the code: the routing table and rooms, the spend table's holds, sff fetch, the eval CLI, the
  nightly's backup, has_key, basis_provenance, the departures' named functions and words.
- Run: `routing_tables.py` recomputes the routing report's one-row-a-table figures and its rule table from its
  own per-question rows; `litrun.py` recomputes the retrieval report from the kept run in the session's data
  folder; `warmup_ids.sh` runs the three warm-up plants on a fresh service; `dryrun_price.py` drives the graph dry
  run's own code; `stale_rows.sh` shows the two stale departures rows; check:state, check:guild, check:plan,
  test_host.py and test_guidance.py ran at the head; the mirror's tests were collected.

## What failed

- R1-03 (S3, Wrong number): the dry run prices all 92 batches as one prompt, which crosses Haiku's long-prompt
  threshold, so the recorded 0.2199 USD of input and 2.3239 USD at most are five times the per-call figures
  (0.0440 and 0.4648). The record, the report and the Known debts row carry the inflated figures.
- R1-01 (S4): a departures row names `GET /api/artifacts`, which the service never served.
- R1-02 (S4): a departures row still says no store holds a protocol; E.12a made one.
- R1-04 (S4): two departures rows disagree on whether the browser keeps the lessons finished.
- R1-05 (S4): the handoff report gives TOOLS.md at CORE 838 lines; it has 837.

## What held

The spend sums, the commit and tag state, the commands and flags of Resume item 5, the routing defaults, every
environment fact that can be re-measured, the owner questions' defaults, the warm-up run ids, every number in the
routing report's alpha 2.2 tables and rule, every number the retrieval report draws from its run, the live-questions
extraction table, the handoff report's claims about the base and the two examples, and H's counts (debts 33/11/18,
CLAUDE.md 149 lines, 39 standins importers, check:state 95, check:guild 146). The list is in `candidates.json`'s
`held`.

## Mishap

`python -m openferment_core.geneos fetch --help` was run to read its usage; the module takes no `--help` and
fetched Yeast9 and iMM904 from their public addresses into `core/data/models/` (gitignored; the folder did not exist
before). The folder was removed at once and `core/data`'s time set back to its last change (22:01:36); `git status`
over core/ is clean. Nothing from the repository was sent. The same mistake with `engine.sff fetch --help` printed
the docstring and fetched nothing. Later commands were read before they were run.

## Left

Known debts and Last green runs (by the brief); the spend tables against openferment_dev and its alpha 2.1 copy
(no leave to copy them); core/.env's budgets and routing lines (not read); historical counts that need a build at
their commit; ShellCheck (absent here); CI ids and the tag push. The live lanes the reports wait on are under
`needsLiveModel`.
