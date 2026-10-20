# The tools

One registry (`core/openferment_core/tools/__init__.py`), three callers:
Postdoc's loop, `GET /api/tools` and `POST /api/tools/{name}`, and the MCP
server (`core/openferment_core/mcp_server.py`). A tool is in `WHITELIST` or
it does not exist. Every input carries ids and words: a JSON number anywhere
outside `k` and `limit` refuses the call, and every refusal is a result with
`error` set. A summary over 9,000 characters is replaced by an error.

The names below are the registry's. The build document writes `dominion.read`;
the Messages API refuses a dot in a tool name, so the registry uses an
underscore.

## The seven (OF-BLD-014)

| Tool | In | Out |
|---|---|---|
| `search_records` | words, a field id, a strain id, a limit | records Postdoc may cite |
| `convert_units` | a record id, a unit | a computed value, kept as an artifact |
| `search_passages` | words, k | up to six passages, each citable by a whole sentence |
| `yield_ceiling` | a model on geneOS's shelf, a product, a sugar | one evidence id, or a finding in words |
| `growth_forecast` | a kept kinetic fit's artifact id | one evidence id and the final values as intervals |
| `selling_price` | a scenario id | the kept run's price, or which inputs wait for a source; never runs a scenario |
| `draft_runbook` | a title, a product, a strain, items by evidence or field, measures | a draft whose numbers the service wrote |

## The read tools (OF-BLD-015 §7.2)

One a module: `dominion_read`, `runbooks_read`, `geneos_read`, `fermos_read`,
`pureos_read`, `proforma_read`, `biorepo_read`, `guild_read`, `primer_read`,
`intake_read`, `home_read`. One input for all: `ids` (ids or refs), `words`,
`kind` (one of the module's kinds, or empty), `state` (one of the enum, or
empty), `limit` (at most 20). One output, `ModuleRow`: `ref`
(`<module>/<kind>/<id>`, what a claim cites in `moduleRefs`), `label`,
`state`, `status` (the module's own word), `provenance` (the mark, or null),
`detail`. The count of every match by state rides on the summary, and a
module read in part says so. An artifact row's `provenance` is worked out
when the row is read, by `basis_provenance` over its inputs as they stand
then, never copied from the stored file: a record rejected since it was
computed brings the row, and a claim citing it, down with it.

Before round one, `module_stores.coverage` sweeps every module for what the
question names and hands the model the map. A follow-up is swept with the
earlier questions it reads (at most four), never with the earlier answers,
which are the model's words, and the map then says what the conversation
names.

`state` is one enum, computed by `module_stores.py` from the module's own
word and never by a model:

| State | Means | Computed from |
|---|---|---|
| `open` | free to use, read or make | a clearance of `clear-expired` or `clear-none`; a draft or running runbook; a host, pathway, model or unit operation in the catalogue; an artifact; an active person; a scheduled check |
| `fenced` | held back | a clearance of `watch-*`, `blocked` or `unknown` (Dominion's action for it is to run clearance first); a runbook `blocked_unverified`; a fetch that failed; a model not fetched |
| `approved` | a person or a source stands behind it | a record `measured`, `gold`, `verified` or `curated`; a protocol's current version; a lesson; a paper fetched with full text |
| `locked` | frozen for a test | a runbook with `lockedAt`; a check run |
| `proposed` | waits for a person | a candidate `unverified`; a runbook `needs_review` or `awaiting_budget`; a check proposed; a proposal at a gate; a paper waiting to be fetched |
| `retired` | withdrawn | a record rejected; a person inactive; a check dismissed |

Read in part: depositions, runbooks adopted or locked in a browser, and
review decisions not yet posted stay in that browser. The footer names the
modules it holds for.

## The program switch (OF-BLD-016 §2.3, §3.3)

Casein (threads A–O) and PHA (thread P) are archived programs; yeast ethanol
(thread Q) is active (`src/data/programs.ts`, `programs.py`). Whether a run
sees the archived two is not a tool input, and no model sets it. It rides in
`ToolContext.include_archived`, set by whatever started the run:

| Caller | Where the switch comes from |
|---|---|
| Postdoc's loop | `AskRequest.includeArchived` on `/api/ask` and `/api/ask/stream`; the browser sends Settings → Programs' switch with every question |
| `POST /api/tools/{name}` | the query parameter `?includeArchived=true`; the body is the tool's input, and no input carries the switch |
| the MCP server | `OPENFERMENT_INCLUDE_ARCHIVED` in its environment (unset: off), never a client |

Off is the default everywhere. A tool input that names `includeArchived`
(`geneos_read` sent it, say) is refused like any field the tool does not
take. With the switch off:

- `search_records` reads an evidence pool with every record and candidate
  on a thread A–P paper left out, counted in `EvidencePool.hidden`.
- `search_passages` drops archived passages from each ranking before
  fusion, reading past `DEPTH` so a ranking still holds `DEPTH`.
- Every read tool's rows are tagged in the store with the program they
  belong to (`module_stores.Row.program`, as the browser's `programOf`
  resolves it; an artifact by what its inputs name: a record's paper, a
  model's host, a product), and archived rows are left out. A row asked for
  by id says which archived program holds it.
- The coverage pass before round one fills `CoverageMap.archived` when the
  question names something archived; the trace reads *found in archived
  program PHA (hidden)*, no hidden row's ref reaches the model, and the
  code writes a gap naming the switch.
- With the switch off, `yield_ceiling`, `selling_price` and `draft_runbook`
  refuse an archived model, product, scenario or strain with *archived
  (hidden)* and name Settings → Programs, and no tool's description or schema
  names an archived model, product or scenario (`programs.archived_target`,
  `offered`; §2.R). `growth_forecast` reads the browser's run and the write
  tools are filtered by nothing beyond the pool they read.

**Examples.** A seed runbook, protocol, scenario or lesson that describes a
run nobody made carries `example: true` in its row's `detail`. The browser
hides examples with the archived programs, and so do the read tools: with the
switch off no read returns an example row (§4.R); with it on, a read returns
them marked, so it can say a runbook is an example. The coverage pass does not
count an example as an archived program's row.

## The write tools (OF-BLD-015 §7.3)

The pair of each read: `dominion_write` … `home_write`. One input for all:
`action`, `target` (an id), `fields` (names to words), `note` (why). A write
tool never touches a store: each action calls the module's own write
function, where the module's rules live, and `check:tools` fails when this
file reaches a file or a store function `ALLOWED_WRITES` does not name. It
reads `writes.py` as parsed Python and follows every name through its import,
aliases included, so `from ..biorepo import write as keep` is caught as
`biorepo.write`; a store module handed around bare, `getattr` on one, and
`importlib` or `__import__` fail too. Every write that goes through lands in the open lane
and is appended to the audit log (`core/data/audit.jsonl`, `GET /api/audit`)
with `agent: model`, the model id (the one answering the run, after any
fallback), the effort and the ask id. A call from `POST /api/tools/{name}` or
the MCP server belongs to no ask, and its line carries `askId: null`. A
person's carry-out or dismissal is appended the same way. A geneOS write that
ends in a finding (a feed the model cannot take up) keeps nothing and is
audited as `finding`.

| Tool | Action | What happens | Through |
|---|---|---|---|
| `geneos_write` | `ceiling`, `frontier`, `mix` | computes and keeps an artifact; returns an evidence id | `geneos.ceiling` and kin |
| `fermos_write` | `forecast` | forecasts from a kept fit and keeps it | `fermos.forecast_run` |
| `fermos_write` | `fit` | refused: a deposition's series lives in the browser | — |
| `proforma_write` | `run` | runs the BioSTEAM scenario on the bound inputs, or refuses naming what waits | `proforma.run` |
| `proforma_write` | `bind` | refused: an assumption is a named person's, in the Durable tier | — |
| `biorepo_write` | `candidate` | anchors a candidate to a sentence of a fetched paper, `unverified`, in the review queue; id `mw1-…`, kept in `candidates/hand/` apart from the extractor's file, so it never counts as an extraction; fields the action lists only, `negativeResult` and `isPrimary` as the word true or false | `extract.add_candidate` (§2.4's rules) |
| `biorepo_write` | `decide` | refused: a decision is a person's | — |
| `intake_write` | `fetch` | fetches and prepares a corpus paper's full text | `intake.fetch_paper` |
| `intake_write` | `extract` | extracts a fetched paper; at the budget, a `spend` proposal | `extract.extract_paper` |
| `intake_write` | `add` | refused: a source enters through a person's approval | — |
| `runbooks_write` | `draft` | refused: use `draft_runbook` | — |
| `runbooks_write` | `revise_protocol` | refused: protocols are seed, revised in the browser | — |
| `guild_write` | `record_check` | refused: an assessor runs a check at the bench, criterion by criterion | — |
| `guild_write`, `home_write`, `runbooks_write` | gated actions | a proposal (below) | `proposals.propose` |
| `dominion_write`, `pureos_write`, `primer_write` | any | refused: curated seed, no write function | — |

A refusal is a result Postdoc reports in `gaps`.

## The gates (OF-BLD-015 §7.4)

The table is `core/openferment_core/tools/gates.py`; this is the same table
for a person. An action here writes nothing: the call becomes a proposal
(`core/data/proposals.json`, `GET /api/proposals`) with `state: proposed`,
and Home shows it as a card with one button. Adding a gate is a row in both
places.

| Gate | Covers | Actions | The button |
|---|---|---|---|
| `publish` | publish to the commons | `biorepo publish`, `dominion publish`, `runbooks publish` | takes the person to the module to publish in their name |
| `spend` | spend past the ask or the daily budget | `intake extract` when the budget refuses | the server extracts when the budget allows |
| `lock` | lock a prediction a person will test | `runbooks lock` | takes the person to the runbook to press Lock predictions |
| `sign` | sign a Guild entry | `guild evidence`, `guild person`, `guild policy` | takes the person to Guild to record it in their name |
| `personnel` | mark a personnel check | `guild propose_check` | the server asks for the check in the person's name, by the Guild person the browser acts as (`checks.request`) |
| `bench` | send a protocol to the bench | `runbooks deposit`, `runbooks run` | takes the person to the protocols to start the deposition |
| `notebook` | write a note under a person's name | `home note` | the server keeps the note under the person's name (the notebook itself lands with OF-BLD-017 §5.3) |

A proposal is carried out or dismissed by a named person (the reviewer name
in Settings; placeholders are refused), and each carries their name and the
time. `POST /api/proposals/{id}/carry-out` and `/dismiss` take `{person,
reason, actingId}`: `actingId` is the Guild person the browser is acting as,
and a check is asked for by them, because Guild knows people by id and the
reviewer name is words; with none, a check proposal is refused in words. The
model may propose a check and may never record or sign one: no gate's server
action signs anything, and `guild record_check` is refused. A server gate is
marked done only when its server action ran; one with none is refused and
stays open to be dismissed. The store's locks are let go while the action
runs (the proposal is marked running in the service), so a long extraction
never holds up another proposal.

The rules a proposal holds to (OF-BLD-016 §1.R, as `proposals.propose`, `_held_to_rule_one` and
`shown` have them on 2026-10-20):

- **Rule 1.** Its note, target, field values, title and why hold no number
  (`validate.find_number`), and its target is one id or none. A write that
  breaks either is refused whole, never repaired, and the model reports the
  refusal in `gaps`. The title is the code's words and the target's id; a
  spend proposal's why is the code's words, not the budget's figures.
- **One of a kind.** One ask makes one open proposal per module, action and
  target; a second (a restart, a call worded otherwise) is refused naming
  the one waiting. Once it is carried out or dismissed, the ask may propose
  it again.
- **Who a check names is never shown before it is run.** A Guild proposal's
  title names nobody. `GET /api/proposals` (`proposals.listed`) and
  `home_read` serve it without its note, why and target, and keep its field
  ids, as Guild's checks serve theirs; the store keeps every word. Home shows
  it to the lead and assessors alone (`mayQueue`), never to the person it
  names (`shownTo`), through `shownProposals` in `src/lib/proposals.ts`.
- **Not filtered by program.** A proposal is work waiting for a person, so
  Home's card lists every open one whatever the program switch says (the
  service double's lock proposal names `rb-brazzein`, an example runbook).

## The MCP server

`core/openferment_core/mcp_server.py` lists `tools.infos()` and calls
`tools.run`, so every tool above, with its marks, refusals and gates, is what
Claude Desktop or Claude Code sees, plus `ask_postdoc` and `get_artifact`.
`test_mcp` counts them.
