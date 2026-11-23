# The handoff by strangers, November 2026

The alpha 2.2 execution prompt (§6.6, stage D) holds the base to one claim: a person who never spoke
to the owner can build against it. Two builders with none of this build's context tested it, each
given a brief verbatim (the prompt's Appendix A and B) and a worktree, and nothing else. Both
finished in their first round with no file of the base changed. This report records what each
read, what each built, where each stalled and what the pages lacked.

## How the rounds ran

- **The core's commit.** `CORE=6f85338` (the D.0 commit, green on CI run 41865693107), recorded in
  `docs/PROGRESS.md` at D.1. A round counts when `git diff --stat 6f85338 -- core/openferment_core
  core/tests core/pyproject.toml src scripts` prints nothing.
- **The worktrees.** Each builder was started with the Agent tool and `isolation: "worktree"`. The
  harness cuts that isolated worktree from `origin/main` (`112eb8b`, alpha 2.1, which holds no
  `docs/api/engines.md`), so each brief's `<path>` named a worktree made at `CORE` instead
  (`git worktree add --detach .claude/worktrees/stranger-<a|b>1 6f85338`), as the appendices' own
  headers put it ("a fresh agent with a worktree path"). The harness held each builder's writes to
  its own isolated worktree: each read the pages at `CORE` in the named worktree, confirmed its own
  copies of the files it would build beside, and wrote its package in its own worktree, from which
  the base copied it into `examples/`. Each builder received this checkout's `CLAUDE.md` as house
  rules, the same as `CORE`'s.
- **Before the rounds (D.0).** Four readers confined to the briefs' files planned both
  deliverables from the pages alone and listed 65 gaps, two of them blocking (the time a run took
  against an identical replay; an MCP server with no way to reach a running service's project).
  Every gap was closed before the core's commit was recorded, on the page and in the core where
  the page revealed a gap the code had (`docs/PROGRESS.md`, stage D, D.0).

## Round 1, the engine builder (Appendix A)

**What it read.** `docs/api/engines.md` whole, `docs/api/workers.md` (lines 1 to 339 whole, the
rest searched for protocol words), `docs/api/runs.md` whole, and `docs/api/openapi.json` through
Python's `json` module (EngineThing, EnginePrecision, EngineParameter, ParameterSpec, EngineInput,
RunInput, Quantity, Origin and RunDiagnostic in full; the engine, runs and replay routes). It
hashed the four pages in both worktrees to confirm they matched `CORE`. It opened nothing under
`core/openferment_core/`, `core/tests/` or `src/`, and no `docs/PROGRESS.md`; the base checked its
transcript's every file read and shell command.

**What it built.** `examples/engines/openferment-engine-mirror/`, seven files: a `pyproject.toml`
registering `mirror = "openferment_engine_mirror.engine:ENGINE"` in the group
`openferment.engines`, with no licence and no dependency declared; a ten-line README; the entry
module holding a `WorkerEngine`; the worker module with its four ops through `serve`; and 30
tests that drive the worker as the service does, through `SimWorker`, and the engine object
through its entry point, with no database. Its one thing, `reflect`, takes two placeholder
parameters, each with a placeholder default in a placeholder unit; a run returns each value as the
run stands, then `values set` (their count, unit `""`); the time the run took is the diagnostic
`time taken` (ms) beside the outputs; its precision is `rtol` 0, `atol` 0, so a replay is
identical; it refuses its SFF file in words ("the mirror engine has no plant, so it writes no SFF
file").

**Where it stalled.** Nowhere in the contract. The harness refused its writes in the named
worktree and its shell's `<(…)`, so it built in its own worktree, moved to `CORE` once it had
confirmed the four pages there were the same blobs, and installed with the two-step form of the
page's command.

**The base's checks.** No core file changed in either worktree or in the main tree. Installed into
core's environment with the page's command (held to `core/uv.lock`), the registry lists
`biosteam`, `kinetics`, `mirror` and `train`; its own tests pass in core's environment (30 of 30);
`conform mirror` holds all eight checks (its diagnostic kept on the run's row and nowhere in its
artifact, its replay identical, its SFF refusal in words, its unknown thing kept as a receipt in
its words). `pnpm prove` with the package under `examples/engines/` holds 86 of 86 checks: it
installs the package, lists four engines, conforms `mirror` 8 of 8 in step 10, and its walk runs
`reflect` on the engine's own defaults from Studies' run card and reads the run's page with its 3
outputs and 1 diagnostic. Question 13, seeded with the mirror installed, expects a row for each of
biosteam, kinetics, mirror and train.

**What the contract should have said.** Six points, each now on `docs/api/engines.md`:

1. the install without process substitution, for a shell or harness that reads no `<(…)` (the
   two-step form beside the one-liner);
2. what a count is: a pure number, unit `""`, its meaning the engine's to name in the output;
3. how a request's "every example value a placeholder in a placeholder unit" meets the rule that a
   pure number's unit is `""` (a count keeps `""`);
4. that `WorkerError`'s words are the worker's `error` line exactly, `Refused: <the handler's
   words>`;
5. that a worker may check the values it receives again, the service's check standing either way;
6. that the models `ENGINE.things()` and `ENGINE.parameters()` answer carry the JSON's field names
   as attributes (`thing.id`, `parameter.origin.ref`).

## Round 1, the agent builder (Appendix B)

**What it read.** `.mcp.json`, `docs/TOOLS.md` whole (838 lines) and `docs/api/openapi.json`
through Python's `json` module (its description, the paths, `GET /api/audit`, `POST
/api/tools/{name}`, `GET /api/catalogues/{kind}/{entry_id}`, `GET /api/projects/{project_id}`, and
the schemas AuditEntry, ToolResult, CatalogueEntry, Refusal, ModuleRow and Usage), all in the
worktree at `CORE`. Beyond the brief's list it compared its own worktree's copies of those three
files with them and printed the first lines of the two `TOOLS.md` copies' difference, and read its
own worktree's `git log`, to learn why its own worktree could not serve the task: those copies are
alpha 2.1's, from `origin/main`. It opened no code of the base.

**What it built.** `examples/agents/record-reader/`: `record_reader.py` (`mcp` 2.3, a PEP 723
header naming `mcp>=2.3,<3`) and a six-line README. The script reads the `openferment` entry of
`.mcp.json`, appends `--project <id> --service <origin>`, starts the server from the repository's
root with its own environment (less `VIRTUAL_ENV`), connects as `clientInfo` `example-agent` /
`0.1`, lists the project's records with `biorepo_read`, keeps one placeholder skill with
`catalogue_write` (`example-agent.0.1-a-skill`), reads the entry back with `catalogue_read` and
its row with `GET /api/audit` (loopback, no proxy, no redirect), prints each, and exits 0 when the
entry and the audit row both name `example-agent/0.1`.

**Where it stalled.** Nowhere in the interface: its first run against the proof's kept service
worked. The harness held its writes to its own worktree, at alpha 2.1, so it gave the script a
`--root` option naming the checkout whose `.mcp.json` and `core` start the server; copied into
this repository the script needs none.

**The base's checks.** No core file changed. Run from the main tree against `pnpm prove --keep`'s
service (`uv run examples/agents/record-reader/record_reader.py --project proof --service
http://127.0.0.1:<port>`), it exits 0: the server lists 50 tools; the entry reads by
`example-agent/0.1`, agent `model`, via `http`, source "example-agent/0.1, at the HTTP endpoint";
and the newest audit row for `skill/example-agent.0.1-a-skill` reads who `example-agent/0.1`,
agent `model`, module `guild`, action `catalogue_write`, detail via `http`.

**What the interface should have said.** Five points:

1. "Record" reads two ways: `biorepo_read` with kind `record` lists none on the proof's project,
   where `search_records` returns the project's one record, which `biorepo_read` lists as an
   approved candidate. Neither says what makes a BioRepo row a `record`.
2. Nothing links a write to its audit row: the write's answer carries no audit id, so a client
   matches on action, target and who, and takes the newest row.
3. `GET /api/audit` takes `limit` alone (at most 500, newest last), so an older write cannot be
   found.
4. `docs/TOOLS.md` advises passing `env=dict(os.environ)`, and a client run by `uv run <script>`
   then hands the server a `VIRTUAL_ENV` that uv warns of at every start; the page should say to
   drop it.
5. Smaller: a module read's `partial` is a sentence, and its type unstated; what each kind puts in
   a ModuleRow's `detail` is undocumented; AuditEntry's `detail` promises a note the row did not
   carry; the HTTP audit sends explicit nulls where MCP answers leave them out; the client recipe
   sits at the end of an 84 KB `docs/TOOLS.md` with no pointer from its top.

`docs/TOOLS.md` is written from the code (`tools/reference.py` and the tools' descriptions), so
these five wait for the core to move again: they are Known debts in `docs/PROGRESS.md`, paid in
stage E, the first of them with the code it describes. Alpha 2.2 E.16 paid all five, each in the
code the pages are written from (ADR-008's Implementation 13).

## The gate

A round of each with no core edit: held, in round 1 of each. `pnpm verify` and `pnpm prove` on the
tree that holds both examples, and CI on the commit, are recorded in `docs/PROGRESS.md`'s Last
green runs.
