# Hunt R2: the records the sessions wrote about their own work

Area: the 66 commit messages 112eb8b..2047f5a, `docs/reports/handoff-2026-11.md`, and the lines alpha 2.2 added
to `docs/decisions/`. Each sentence was read as a claim and held to the tree at 2047f5a with a grep, a `git show`,
a run on a service of my own (port 8970, database `bh_r2_svc`), or a mutation in a worktree of my own. 42 claims
held (listed in `candidates.json`, `held`); four did not (R2-01 to R2-04).

## What I did

- Read every message body in full (`git log --format='%H%n%B' 112eb8b..2047f5a`), the handoff report whole, and the
  ADR diffs. `scripts/adr_refs.py` held every backticked path and dotted name the ADR additions name to the tree;
  the names it flagged are deleted files the lines say are gone, or generated fixtures gitignored by design.
- The handoff report: the diff over the core paths between CORE and the D.4 commit is empty; the mirror's files,
  README lengths and 30 tests hold; installed with the page's own command into my worktree's venv, the registry
  lists four engines and `conform mirror` holds 8 of 8; the record-reader run against my service exits 0 with the
  50 tools, the entry and the audit row the report quotes. One count is off by one (R2-04).
- Behaviour the messages claim fixed, tried on my service: NaN and Infinity at five value doors
  (`scripts/nan_doors.py`), the engine request's refusals, the tool door's `by` rule, `auditIds`, the audit's
  filters, `GET /api/state`'s refused rows (a malformed row inserted into my own database), the override unit
  rules, the MCP server's `--service` refusals, `llm.routes()` with the four settings.
- Counts and sums: test:core collects 3061 of 3236 (175 deselected), test:sim 142, test:lit 10; CLAUDE.md 148 and
  149 lines; 39 standins importers; Known debts 33/11/18; the Spend table's sums; the routing report's arithmetic;
  the retrieval report's question counts; schema counts at E.0a; the TypeScript checks' counts in my worktree.
- Mutations (`scripts/mutate.py`, results in `mutations.json`): 21 changes to code a message says a test holds,
  each run against that test in my worktree after a green baseline (422 passed). 17 caught. M10 survived (the
  library's own `--limit` guard; the command's guard is tested, so no finding). M20 and M21 survived and change
  nothing (`scripts/proxy_mounts.py`: httpx reads no proxy once a client is handed a transport). M16 survived and
  is R2-03.

## Findings

- R2-01 (S3, Wrong number): the concept graph's dry run sums the 92 batches into one prompt and prices it at Haiku
  5.5's long-prompt tier; the records' 0.2199 and 2.3239 USD stand where the requests cost 0.0440 and 0.4648
  (`scripts/graph_dry_cost.py` drives the code's own branch and reproduces the recorded digits).
- R2-02 (S4, Inconsistency): `conform` against a database the server lacks runs the checks and exits 0 with a
  driver error for the verdict; migrations refuse it in words with exit 2 (`scripts/conform_missing_db.sh`,
  output in `conform_missing_db.out`).
- R2-03 (S4, Hollow test): the MCP relay's "no proxy" rule survives `trust_env=True`; its tests hand it a
  stand-in transport.
- R2-04 (S4, Drift): the handoff report's 838-line TOOLS.md held 837 lines at CORE.

## Rules kept, and one slip

- Nothing under core/, src/, scripts/ or examples/ of the main checkout changed (`git status` clean there; the
  mirror's bytecode under examples/ predates this hunt, 4 November). Every mutation, install and conform run with
  a scratch database ran in `$BH_WORK/R2/wt` (scratch prefix renamed to `bh_r2_conform`), removed at the end.
- Early on I ran `conform biosteam` twice from the main checkout against `bh_r2_missing`; each made and dropped
  its own scratch database under conform's prefix `openferment_conform_biosteam_<hex>` (none is left on the
  server). Every later conform run used the renamed prefix. `openferment_conform_kinetics_7b28ff7e` and
  `openferment_test_25359_*` on the server are not mine.
- The one test that binds an ephemeral port (`test_mcp_service.py`'s served-app test) was deselected from every run.
- No model call, no key read, no network beyond loopback. Databases `bh_r2_svc`, `bh_r2_conform_cfg` and the
  tests' `bh_r2_test_*` dropped; the service on 8970 stopped.
