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
module read in part says so.

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

## The write tools (OF-BLD-015 §7.3)

The pair of each read: `dominion_write` … `home_write`. One input for all:
`action`, `target` (an id), `fields` (names to words), `note` (why). A write
tool never touches a store: each action calls the module's own write
function, where the module's rules live, and `check:tools` fails when this
file reaches a file. Every write that goes through lands in the open lane
and is appended to the audit log (`core/data/audit.jsonl`, `GET /api/audit`)
with `agent: model`, the model id, the effort and the ask id. A person's
carry-out or dismissal is appended the same way.

| Tool | Action | What happens | Through |
|---|---|---|---|
| `geneos_write` | `ceiling`, `frontier`, `mix` | computes and keeps an artifact; returns an evidence id | `geneos.ceiling` and kin |
| `fermos_write` | `forecast` | forecasts from a kept fit and keeps it | `fermos.forecast_run` |
| `fermos_write` | `fit` | refused: a deposition's series lives in the browser | — |
| `proforma_write` | `run` | runs the BioSTEAM scenario on the bound inputs, or refuses naming what waits | `proforma.run` |
| `proforma_write` | `bind` | refused: an assumption is a named person's, in the Durable tier | — |
| `biorepo_write` | `candidate` | anchors a candidate to a sentence of a fetched paper, `unverified`, in the review queue; id `mw1-…` | `extract.add_candidate` (§2.4's rules) |
| `biorepo_write` | `decide` | refused: a decision is a person's | — |
| `intake_write` | `fetch` | fetches and prepares a corpus paper's full text | `intake.fetch_paper` |
| `intake_write` | `extract` | extracts a fetched paper; at the budget, a `spend` proposal | `extract.extract_paper` |
| `intake_write` | `add` | refused: a source enters through a person's approval | — |
| `runbooks_write` | `draft` | refused: use `draft_runbook` | — |
| `runbooks_write` | `revise_protocol` | refused: protocols are seed, revised in the browser | — |
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
| `personnel` | mark a personnel check | `guild propose_check`, `guild record_check` | the server asks for the check in the person's name (`checks.request`) |
| `bench` | send a protocol to the bench | `runbooks deposit`, `runbooks run` | takes the person to the protocols to start the deposition |
| `notebook` | write a note under a person's name | `home note` | the server keeps the note under the person's name (the notebook itself lands with OF-BLD-017 §5.3) |

A proposal is carried out or dismissed by a named person (the reviewer name
in Settings; placeholders are refused), and each carries their name and the
time. `POST /api/proposals/{id}/carry-out` and `/dismiss` take `{person,
reason}`. The model may propose a check and may never write a sign-off: no
gate's server action signs anything.

## The MCP server

`core/openferment_core/mcp_server.py` lists `tools.infos()` and calls
`tools.run`, so every tool above, with its marks, refusals and gates, is what
Claude Desktop or Claude Code sees, plus `ask_postdoc` and `get_artifact`.
`test_mcp` counts them.
