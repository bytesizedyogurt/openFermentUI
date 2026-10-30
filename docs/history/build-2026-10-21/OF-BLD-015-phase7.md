# OF-BLD-015 Phase 7 — Postdoc reaches everything

Committed for the length of the build (Part D of the session prompt); the closing truth pass deletes it.
Copied from the prompt Sean gave the session on 2026-10-19. Part C of the same prompt (OF-BLD-017
Phase 5, "Postdoc remembers") is committed beside it when that part starts.

## Part A — Read before touching anything

1. `CLAUDE.md`, `STATE.md`, `COMPONENTS.md`, `README.md`.
2. `docs/requests/` if it exists on the branch. Every file there is a finding to honour or to route.
3. These decisions are law for this session. A session that is offered something against one of them refuses it.
   - Every model call openFerment makes runs `claude-haiku-5-5` at effort medium: primary, fallback, index,
     eval. Nothing touches Opus pricing. The build session itself may run on any model; this rule is about
     calls the code makes.
   - The API key lives only in `core/.env` on the Mini and in the environment variable `OPENFERMENT_API_KEY`
     in cloud sessions. It is never pasted into a chat, never written to a log, never returned in a response.
   - Rule 1 stands: no quantity originates in model weights. Claims carry no numbers. Quotes are anchored to a
     sentence. Memory, history and notebook notes carry claims, record ids and named assumptions; every number
     on screen still comes from a source.
   - Provenance is computed, never chosen by a model.
   - Dual track (rule 13): the model researches, computes and writes freely into the open lane, marked as its
     own. Approval is asked at three gates only: spend past a budget, the physical world, the public record.
     Personnel data is a gate of its own: the model may propose a check and may never write a sign-off.
   - Writes by a model go through the module's own write function, carry the model as agent, land in the open
     lane, and are appended to the audit log like a person's write.
   - One commit per step, message `OF-BLD-015 §7.x: <what>` for Part B and `OF-BLD-017 §5.x: <what>` for
     Part C. `pnpm verify` is green before every commit.
4. Measure before you plan. Record in `STATE.md` the line counts and the exact contents of `WHITELIST` in
   `core/openferment_core/tools/__init__.py`, the tool files under `core/openferment_core/tools/`, the
   functions in `core/openferment_core/postdoc_agent.py`, the routes `/api/ask` and `/api/ask/stream` in
   `core/openferment_core/api.py`, `AskRequest` in `core/openferment_core/models.py`, the chat section of
   `src/store.ts` (`createSession`, `appendMessage`, `updateMessage`, `pinEvidence`), and `SEED_SESSIONS` in
   `src/data/misc.ts`. If a measurement disagrees with this prompt, the measurement wins, and the report says so.

## Part B — Postdoc reaches everything (OF-BLD-015 Phase 7)

Found in use on 2026-10-16: Postdoc was asked what is open in Dominion and answered that nothing was found in
the corpus, while the Dominion screen showed several open and fenced molecules. The registry holds seven names
(`search_records`, `convert_units`, `search_passages`, `yield_ceiling`, `growth_forecast`, `selling_price`,
`draft_runbook`); none reads Dominion, the protocols, the strains, the runbooks, the ledger, the depositions,
the artifacts or the Guild. This part gives every module a read tool and a write tool, in the same registry,
under the same rules the browser already obeys.

**§7.1 Coverage pass before the first turn.** A code-only step with no model call. Before round one of
`postdoc_agent.ask`, sweep every module store for the named entities in the question (molecule, strain,
protocol, runbook, record id, person, scenario, host, pathway) and build a coverage map: which modules hold a
match, how many, with ids and the `state` of each. Put the map in the context of round one, so Postdoc can
never say "not in the corpus" about something the app is showing. The answer footer reports it per module:
searched eleven, found in three. Add the map to the trace as its own step so the screen shows it line by line
like a tool call. Unit-test it against seeded data with a question that names a Dominion molecule, a runbook
and a strain.

**§7.2 Read tools, one per module, through `tools.run`.** Add to the registry and to `WHITELIST`:
`dominion.read` (molecules, clearance findings, fences), `runbooks.read` (runbooks, protocols, depositions,
ledger), `geneos.read` (hosts, pathways, models), `fermos.read` (runs, fits, forecasts), `pureos.read`,
`proforma.read` (scenarios, bindings, runs), `biorepo.read` (records, candidates, artifacts, Witness results),
`guild.read` (people, skills, checks, matrix, with personnel fields reduced to what the ledger shows),
`primer.read` (lessons, briefings), `intake.read` (sources and their preparation state), `home.read` (open
items, proposals awaiting a person). Each takes ids or words, never a number (the registry already refuses
numbers outside `COUNT_FIELDS`; keep that). Each returns typed rows with their provenance marks and a `state`
field drawn from one enum: `open`, `fenced`, `approved`, `locked`, `proposed`, `retired`. `validate_plan` and
`SeenSet` learn the new id families. Results obey `MAX_SUMMARY_CHARS`. The registry stays closed: a tool is in
`WHITELIST` or it does not exist. `_tool_defs` in `postdoc_agent.py` picks the new tools up with no special
case. Where a module's data lives only in the browser today (depositions, review decisions, runbook locks in
IndexedDB), the read tool reads what the service has and the footer says which module could only be read
partially; do not build a sync in this part.

**§7.3 Write tools, in symmetrical pairs.** `dominion.write`, `runbooks.write`, `geneos.write`,
`fermos.write`, `pureos.write`, `proforma.write`, `biorepo.write`, `guild.write`, `primer.write`,
`intake.write`, `home.write`. A write tool never touches a store directly; it calls the module's own write
function where the rules already live (`biorepo` candidate creation, the Guild rules in `guild.py` and
`checks.py`, `proforma` binding, the runbook lock, the deposition writer, `artifacts.py`). Every call carries
`agent: "model"`, the model id, the effort and the ask id, lands in the open lane, and is appended to the audit
log. Free writes, no approval: add and prepare an Intake source; create a candidate record anchored to a
sentence; draft a runbook; draft a protocol revision; run and store a simulation artifact; write a notebook
note; bind a Proforma assumption marked as the model's. Each is reversible and shows the model mark until a
person or a run promotes it. If a module has no write function yet, the write tool refuses in words with the
reason, and that refusal is a result Postdoc must report in `gaps`.

**§7.4 The gates.** A write that would publish to the commons, spend past the ask or daily budget, lock a
prediction a person will test, sign a Guild entry, mark a personnel check, or send a protocol to the bench
returns `state: proposed` instead of acting. The proposal is stored and appears as a card on Home with the one
button a person presses to carry it out. The gate list lives in one table, in
`core/openferment_core/tools/gates.py` and in `docs/TOOLS.md`, one row per gate, so adding a gate is a row and
never a special case.

**§7.5 The same registry serves the MCP server.** `core/openferment_core/mcp_server.py` already lists
`tools.infos()` and calls `tools.run`; confirm the new tools appear there with the same marks and gates and add
a test that counts them. Nothing in this part assumes the per-module agents of the Lanes plan; they are built
later from these pairs.

**§7.6 Verify.** Add `check:tools` to `package.json` and to the `verify` chain. It fails when a module store
has no read tool, when a write tool reaches a store without going through its module's write function, or when
a gated action can complete without a person's id on it. Negative-test each: plant the fault, watch it fail,
restore. Eval set O gains ten cross-module questions ("what is open in Dominion and which runbooks touch it")
with answer keys drawn from the stores by code, run on `claude-haiku-5-5` at medium, scored on whether the
right modules were searched and whether the footer names them.

**§7.R Review.** A fresh session that wrote none of this reads the audit log of a seeded Postdoc run and
confirms every write carries the model mark and no gated action went through. Record its findings in
`STATE.md`.

Done when the Dominion question above is answered from `dominion.read`, with the footer naming the modules
searched.

## Part D — How the work lands

- Commit the document for each part under `docs/build/` for the length of the build, as OF-BLD-014 did; the
  closing truth pass deletes it.
- Truth pass at the end of each part: `README.md`, `CLAUDE.md`, `COMPONENTS.md`, `STATE.md` and
  `docs/TOOLS.md` describe what the code does that day, every number measured that day.
- Open one pull request per part, unmerged, for Sean's review. Pull requests are squash-merged; the Mini runs
  `main` only, deployed by `scripts/host/deploy.sh`.
- When the context passes two thirds full, finish the step in hand, commit it and stop. The next "next phase"
  resumes at the first step whose id is missing from the commit log.

Stop and report when: `pnpm verify` goes red and the cause sits outside the step; a fact this prompt states
turns out false when measured; a write tool would reach a store with no write function and no clean way to
refuse; a key could reach a response, a log, the browser or git; a change would let a future second account
read the owner's private conversations with no visibility check in the way.
