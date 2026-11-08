# ADR-008 — Postdoc: one loop, one registry, server-side memory, routed models

- **Status**: accepted (provisional choice; stage 6 implements it)
- **Date**: 2026-10-30

## Context

At `alpha-1.0` the loop (`postdoc_agent.py`) is bounded (6 rounds, 12 tool calls, 180 s, an ask
budget) and validated. Conversation history exists only in the browser. Model access is
`llm.call`/`llm.converse` with a primary and a fallback model from the environment, prices in
`llm.PRICES` and budgets in `spend.py`. The registry holds thirty-six tools; the old guidance said
thirty-four.

## Decision

- Keep the loop's bounds and its validator, revised for typed values (ADR-006).
- Conversations, turns, tool traces and the artifacts each turn produced are tables under a
  project; a follow-up reads the server's history.
- `llm.ROUTES` maps task families (`plan`, `explain`, `extract`, `index`, `judge`) to ordered model
  specs and effort, in the kit's `provider:model` syntax, so Anthropic, OpenAI-compatible and local
  models route the same way. A per-request key override reaches both openFerment and the kit.
- Streaming: every tool call, worker job and artifact emits an SSE event the UI renders as a card.
- `tools/__init__.py` stays the one place a tool exists; `docs/TOOLS.md` is generated from it
  (`pnpm gen:tools`).
- Specialist agents wait for an evaluation that shows the single loop failing.

## Implementation

### 6.1 (2026-10-30)

- `postdoc/` is a package: `single.py` (the one-call path, the old `postdoc.py`) and
  `conversations.py`, the store. A conversation is a row of `conversations`, each turn a row of
  `turns` in order, each tool call a row of `tool_calls` under its turn with what it answered the
  model and what it offered to cite (migration 0005 split the conversations the page kept whole,
  turn by turn, and puts them back on a downgrade). A turn names the artifacts its calls produced
  and its plan cites. `docs/api/postdoc.md`.
- `POST /api/ask` and `/api/ask/stream` take `conversationId`, `turnId` and `by`; `api._answer`
  keeps the question as a turn, reads a follow-up's history from the store (the request's own
  `history` only when it names no conversation), keeps each call through the loop's new
  `on_call` and `on_result`, and ends the turn `answered`, `stopped` or `failed`. A turn is asked
  once. The stream's first event is `turn`.
- The page's writes through `project_state` land on the same store: a turn the service lacks is
  kept as the page wrote it, and one the service holds stays as it kept it. A turn the page
  writes `running` before its ask arrives is taken over by the ask, in its place. A turn kept
  `running` that this process is not answering reads `interrupted`; the screen follows a turn the
  service is still answering after a reload (`fetchConversation`), and the page no longer marks a
  running turn interrupted itself.
- `events.py` and `GET /api/events`: `job.*` from engine runs, `artifact.kept` from
  `artifacts.compute`, `tool.call/result` and `turn.started/delta/plan/decline` from `_answer`. An
  event's id counts up in the process; a page resumes with `Last-Event-ID`, a page that names no
  event is sent what happens from then on, and one that falls behind is closed and reconnects.
  The stream waits on the event loop and holds no thread. The UI's cards over these events are
  stage 7's.

### 6.2 (2026-10-30)

- Nine tools join the registry, forty-three in all: `engine_plants`, `engine_parameters`,
  `engine_run` and `engine_report` over the library shelf and the project's engine runs (a run's
  numbers are evidence ids on its artifact, `<artifact id>:<block>.<key>`); `study_scenario`,
  `study_compare` and `study_read` over its studies (a comparison's changes are evidence ids on
  its artifact); `literature_sources` and `literature_document` over the documents it holds (a
  section's passages are quoted as `search_passages`' are). The writes go through
  `tools/writes.py` (`run_engine`, `make_scenario`, `make_comparison`), audited as their caller's.
- Every tool carries a project scope and `tools.run` runs it in `ToolContext.project` when one is
  named (A5). The MCP server acts in the project `--project` names, else `OPENFERMENT_PROJECT`, and
  a server started in none answers every call with the words to start it in one.
- `docs/TOOLS.md` is written from the registry by `pnpm gen:tools` (`tools/reference.py`): each
  tool's family, whether it writes, its scope, its description and its fields, the gate table and
  the MCP server's two names. `check:tools` fails when the file differs from what the registry
  writes (rule 5), holds every schema's numbers to quantities and counts (rule 6), holds every
  tool to a project scope (rule 7), and counts an engine run, a scenario and a comparison among
  what only `tools/writes.py` keeps.
- The loop's rules name the new tools (18 to 20), drop the module read the Dominion deletion
  left in rule 11, and its trace says what each new tool did.

### 6.3 (2026-10-30)

- `llm.ROUTES` and `llm.routes()`: the families `plan` (Postdoc's loop), `explain` (an answer in
  one call, the kit's cited answers), `extract`, `index` (OPENFERMENT_INDEX_MODEL first) and
  `judge`, each an ordered list of model specs and an effort. The table core/.env leaves alone is
  `ROUTES`; the models and effort it names still set the defaults, and `OPENFERMENT_ROUTES` (a
  JSON object of family to `{"models", "effort"}`) lays a route over a family, refused in words
  when it cannot route (`RoutesInvalid`, and `pnpm ready` fails on it). Every caller names its
  family: the loop `plan`, the single call `explain`, extraction `extract`, and the kit's answer,
  extraction and judge roles `explain`, `index` and `judge`. The day's spend keeps its two roles
  (`SPEND_ROLES`).
- A model is a spec in Sci RAG Kit's syntax, `provider:model` (`anthropic`, `openai-compatible`,
  `google`), a bare id being Anthropic's. The service serves Anthropic's models; a route's model
  of another provider is passed over in words and the next one answers, because calling it
  through the kit reads that provider's key from the kit's settings, a change to how keys are read
  (execution prompt §11.1). `pnpm ready` names such a route. Serving it is the owner's call,
  asked in `docs/PROGRESS.md`'s owner questions with the per-request key override below.
- The per-request key override (§4.8) changes how a key is read, and waits for the owner
  (§11.1). The design it would take: a request names a key for its own calls in a header the
  guard reads on loopback alone; `llm` holds it in a context variable for the request, its
  clients use it in place of `core/.env`'s, and the kit's calls reach it through `llm.call` (the
  kit's client already calls there), so the key reaches both and never a log, a response or a
  row.
- The ask budget keeps back the final turn's worst case before another round is asked
  (`postdoc_agent._final_turn_usd`: the conversation so far read as input, and every output token
  the turn allows): the loop stops asking for tools when what it spent and what the answer could
  cost reach the question's budget, so the answer is paid for within it.

### 6.4 (2026-10-30)

- The evaluation set is two tables of the project (migration 0006): `eval_questions`, each
  question with the tool groups a good answer reaches for, what its claims cite and whether it
  states a labelled estimate, and `eval_runs`, each scored run (`postdoc/evaluate.py`). A run asks
  every question through the service's answer path, as a turn of a conversation (a question that
  follows another is asked in that one's conversation and reads its history from the service),
  and scores it by code: the share of tool groups reached, the share of claims citing what the
  question expects, whether a labelled estimate stands exactly where one is asked for (every claim
  stating one `assumed`), and whether a claim was dropped for a number, with the count.
- Offline, the evaluation's stand-in answers (`evaluate.StandIn`, named `openferment-standin`
  wherever a model is named, the `plan` route pointed at it): each default question's script of
  tool calls and a plan written from what the tools returned; its follow-up drops a claim with a
  bare number on purpose. Live (`--live`), the routing table answers. `pnpm eval seed | run
  [--live]` (`openferment_core/evaluation.py`, outside the `postdoc` package because it reaches
  the API's answer path, which `postdoc` may not import).
- `scripts/prove.py` step 6 runs it offline against the proof's project and checks it through
  the service: the selling price cited by evidence id, the scenario of a labelled estimate run and
  `assumed` and its price read by the run's artifact id, the bare number dropped and counted, the
  follow-up's history read from the service, each turn and its tool calls kept.
- Specialist agents still wait for an evaluation that shows the single loop failing: two
  questions offline say nothing of a model, and the live set grows with the projects that run it.

## Revisit condition

That evaluation (development plan §8, "Let the simple system compete").

## Implementation 8 (found by the live proof)

`pnpm prove --live` asked Postdoc's evaluation set of the routed model (2026-10-30, `claude-haiku-5-5`)
and every request came back HTTP 400: "The compiled grammar is too large, which would cause
performance issues." The API compiles one grammar for a request's answer schema and its strict tools.
Measured with one request each: the plan schema, with each claim's typed values (stage 6.2), beside
the registry's seven strict tools was refused; the same schema with every tool loose was accepted, as
were the seven strict tools with no answer schema. `llm.converse` now sends such a request again
with its tools loose and its answer schema strict, and remembers its shape, so the next turn goes
loose at once (`GrammarTooLarge`; `test_llm.py`). `tools.run` validates every tool's input alike,
strict or not. The offline suites could not see it: the API compiles the grammar.

## Implementation 9 (alpha 2.1 stage B: the owner's questions on Opus)

The owner's twelve questions, asked live on `claude-opus-5-5` through the Postdoc screen
(`docs/reports/live-questions-2026-11.md`), found the loop's bounds too tight for real work: four
answers spent their 12 tool calls before they covered the project's 22 documents, and two spent
their 6 rounds before a scenario ran or a draft was written. The bounds are now 10 rounds, 24 tool
calls and 360 s (`postdoc_agent.MAX_ROUNDS`, `MAX_TOOL_CALLS`, `MAX_SECONDS`); the tests derive
their budgets from the constants. The ask's cost cap (`OPENFERMENT_ASK_BUDGET_USD`) bounds what one
question spends, and its reservation for the final turn stands as 6.3 built it. The same asking
added `flowsheet_library`, `flowsheet_import` and `flowsheet_read` to the registry (46 names), and
the plan prompt now names ordinals, fractions and table labels as the numbers they are.

Asked again, the answer over the project's 22 documents ran out of room: a turn's ceiling of 8,000
tokens holds the model's thinking as well as its plan. A turn now writes as much as the question's
budget has left to pay for, between `MIN_TOKENS` (8,000) and `MAX_TOKENS` (32,000)
(`postdoc_agent._turn_tokens`), and the loop holds back a `MIN_TOKENS` answer before it asks
another round, as 6.3 held back the whole ceiling. On the owner's default ask budget (0.75 USD,
D8's figure) a turn on Opus still gets what the budget left pays for; on the 6 USD core/.env names
for real work, every turn gets the whole ceiling.

## Implementation 10 (alpha 2.1 stage D: the key a request names)

The owner authorized the per-request key override on 2 November 2026 (question 10), within these
rules: a key sent on a request is used for that request's model calls and never stored, logged or
echoed; it reaches openFerment's client and the kit's; a request with none uses core/.env's; the
audit row records that an override was used, never the key. Built as 6.3 designed it:

- A request names its key in `X-OpenFerment-Key` (`llm.KEY_HEADER`). The API's middleware reads
  it after the guard and the project's middleware: `guard.key_refusal` refuses a request through
  Tailscale Funnel, from the public internet, and one under a name the service does not answer
  to, in words that never repeat the key; an empty header is refused with a 422.
- `llm.request_key` holds the key in a context variable for the request. `_default_client` builds
  every client on it in place of core/.env's; the kit's calls reach it through `llm.call` on
  asyncio's worker thread, and the ask stream's thread through `contextvars.copy_context`, both
  of which carry the context. A key the API rejects is said to be the one the request named.
- The project's audit table keeps one row for the request (`home`, `key_override`, its method and
  path, `{"override": true}`), and nothing of the key.
- `test_key_override.py` is the negative test: an ask on a named key reaches a stand-in client
  built on that key and no other, an ask with none on core/.env's, and the key appears in no log
  line, no response body or header, and no row of any table of either schema.

## Implementation 11 (alpha 2.1 stage D: a local model in a route)

The owner allowed a local model behind an OpenAI-compatible endpoint named in core/.env to stand
in a route through the kit's adapter (2 November 2026). `OPENFERMENT_LOCAL_BASE_URL` names the
endpoint and `OPENFERMENT_LOCAL_API_KEY` its key (many local servers take any); a route's
`openai-compatible:<model>` is then served (`llm.served_providers`). `llm.call` asks it through
Sci RAG Kit's `OpenAICompatLLM` (the `openai` extra of the kit, Apache-2.0, now in `uv.lock`), at
no charge on the day's cap, and passes to the next model in words when the endpoint does not
answer. Postdoc's loop needs a model that calls tools, so `converse` passes a local model over in
words. With no endpoint named, a local model in a route is passed over and `pnpm ready` names the
setting; another provider's model still waits for the owner.

## Implementation 12 (alpha 2.2 D.0: an assistant named at the tool door)

- `POST /api/tools/{name}` reads `X-OpenFerment-Assistant` (`tools.ASSISTANT_HEADER`): with it the
  call runs in the model's lane under that name, `ToolContext(model=<name>, via="http")` in the
  request's project, the name read as UTF-8 text, whitespace-collapsed, its control, format and
  surrogate characters dropped and cut to `tools.MAX_CALLER` characters (`tools.caller_name`,
  which an MCP client's declared name and a person's `?by=` pass through too). A number it types
  is that name's estimate, a write is marked with that name (`by`), its audit row names it as
  `who` with agent `model`, and a catalogue entry's source reads `<name>, at the HTTP endpoint`. A
  call naming both `?by=` and the header is a 422 in words, and so is a writing tool's call naming
  neither.
- Every write of the model's lane names the door it came in by: `detail.via` on its audit row and
  `via` on a catalogue entry it keeps, `postdoc` for Postdoc's loop, `mcp` for the MCP server in
  its own process, `http` for the header. Only Postdoc's row carries an `effort`, the one its
  model ran at, since no model of the service runs for an outside assistant's write.
- The header gives an HTTP caller the model's lane under the name it declares. A number it types
  is that name's estimate, which every record store refuses (ADR-006); its `catalogue_write`
  replaces only an entry that name kept in the model's lane through an assistant's door, so it
  replaces neither a person's entry nor Postdoc's; and it writes the stores that hold a model's
  work alone, pureOS's kept trains among them, where a `?by=` call is refused. A gated action
  becomes a proposal in either lane, since `writes._runner` checks the gate before the lane, and
  what a write at the tool door makes lands in the open lane whoever calls (THE MARK,
  `tools/writes.py`). A caller on loopback reaches the model's lane already through
  `POST /api/ask`, and an MCP client in the server's own process reaches it with the database's
  address; the header is one more door to it, `guard.py` holds it as it holds every POST, and no
  listener, host or CORS rule is added. The MCP server's `--service` mode sends its client's name
  here (ADR-005).
- `docs/TOOLS.md` says how the server starts, both ways it reaches a project, and what a client
  reads: the SDK's names, the shape of an answer over MCP, and where the audit row is read.

## Implementation 13 (alpha 2.2 E.16: the agent builder's interface points)

The agent builder of stage D (`docs/reports/handoff-2026-11.md`, round 1) finished with no core
edit and named five points the interface left a client to guess. Each is paid in the code the page
is written from:

- **What a BioRepo record is.** One rule, `module_stores.RECORD`, which both readers' descriptions
  quote: a record is an extraction a reviewer verified against its document's own words
  (provenance verified, or gold), and a candidate is one no reviewer has verified yet
  (unverified); one a reviewer rejected leaves every read. `biorepo_read` lists the two as its
  kinds `record` and `candidate` (`module_stores.record_kind`, from the row's state), and
  `search_records` names each hit's kind by the same rule. A candidate a reviewer accepted, which
  `biorepo_read` listed as kind `candidate` in the approved state, is now kind `record`; a
  fixture's curated row was a record already and stays one. The row `biorepo_write`'s candidate
  action answers with is the row the read lists (`module_stores.record_row`).
- **A write's answer names its audit row.** An audit row's id is its place in the table (`seq`),
  served as a string of digits. `tools.run` opens `audit.written()` around the tool, and
  `audit.add` adds each new row's id to it, so the result's `auditIds` names every row the call
  wrote, oldest first: a kept entry's, a run's, a refused run's receipt, and a gated write's
  proposal, whose row its own transaction writes on the database's thread (a coroutine sent there
  runs in a copy of its sender's context, so the list reaches it). Over MCP the answer carries the
  field as every other.
- **The audit read by what a write was.** `GET /api/audit` takes `action`, `target` and `who`
  beside `limit`, each matched exactly as a row names it, and serves the newest `limit` of the
  matching rows, so a write older than the newest 500 rows is found by what it was. Each row is an
  `AuditRow`, the entry under its `id`.
- **The HTTP audit leaves null fields out**, as the MCP server writes every model it answers
  (`response_model_exclude_none`): a row with no target, ask or effort holds no such key.
  `AuditRow` joins `api.AS_KEPT`, so the document lists the fields a row may leave out as
  optional, and `test_route_models.py` serves the route as kept.
- **What a row holds.** `AuditEntry.detail` says what it holds, and every write whose call takes a
  note keeps it there (`catalogue_write` and `study_scenario` join the writes that did). A module
  read's summary is a `ModuleRead`, its `partial` a sentence, and `module_stores.DETAIL` names
  each kind's `detail` field by field; `docs/TOOLS.md` renders both under Module reads, and
  `test_agent_interface.py` builds a row of every kind and holds its fields to its kind's words.
- **The client recipe** hands the server its client's environment with `VIRTUAL_ENV` taken out,
  which a client run by `uv run <script>` holds and the server's `uv run --project core` warns of
  at every start, and the page's top points at the recipe, at the MCP server's section and at what
  a module read answers.

## Implementation 14 (alpha 2.2 F.2a: the evaluation the model comparison reads)

Stage F compares four route tables for `plan` and `explain` on the fourteen, each answer judged by
two judge models; F.2a lands the evaluation code that comparison reads before the ethanol suite is
seeded (`postdoc/evaluate.py`, `openferment_core/evaluation.py`, `docs/api/postdoc.md`):

- **The judge pass reads core/.env as a run does.** `pnpm eval judge` copied the database address
  and the project from `core/.env` and imported nothing more, so it read no key, no routes and the
  default cap of 25 USD, and each judgement it kept was a decline naming a missing key. Its branch
  now imports the service module first, as the run branch does, whose import loads `core/.env`
  through the same loader with `override=False` (`api.py`): the same file, the same names, read
  the same way, and no new place a key is read from. A judge none of whose route's models answers
  (no key, the account's usage limit, the day's cap) now stops `run --judge` and `judge` in words
  with exit 1 and keeps no judgement for the run it was judging (`evaluate.JudgeUnavailable`); a
  judge that declines is kept as a judgement with no score.
- **A model's write carries the plan route's effort.** A write's audit row named the single effort
  setting (`llm.effort()`), so a write asked on a route table at `high` was labelled with
  `core/.env`'s `max`. It now names the effort of the route Postdoc's loop answers on,
  `llm.routes()["plan"].effort` (`tools/writes._plan_effort`), so a table's writes carry the
  table's effort; the single setting stands where the table names no effort for the route, as
  `routes()` builds it, and where the table cannot be read.
- **What a run and a judgement keep.** A run keeps the seconds to the loop's first step (the code's
  module sweep), to its first step of another kind (the model's first) and to the answer, timed
  through the answer path's `on_step`, with the loop's stop, its restart steps and the validator's
  reasons. A judgement keeps the models its route tried and the route itself, so one Sonnet gave
  after Opus declined says so. The summary counts each run once for each judge model, by that
  model's newest judgement of it, and says how far the two judges' scores of the same answers lie
  apart, per tag and pooled; `rows` gives each tag's newest run of each question; `run --only`
  asks some questions alone under a tag, a follow-up in the conversation of its question's newest
  run there, so a table stopped part way is finished where it stopped. Question 4 follows question
  3, as the owner's screen asked it in alpha 2.1.
- `JUDGE_TOKENS` and the loop's bounds stay as they are: the comparison measures them first.
- **The review (F.2a review).** The account's limit most often lands on one of an answer's plan
  calls before its judge call, so a stop's answer is itself unanswered: a plan with no claim whose
  final step reads `No answer: …`, its decline no refusal (`evaluate.unanswered`). The stop's words
  then say to ask that question again with the rest, beside the questions a full asking asks in
  its conversation before it when it is a follow-up, and name no judge command for it. `--only`
  asks a follow-up in its question's conversation when that conversation holds what a full asking
  has it read before it; a follow-up that would find its own earlier asking there, miss a question
  asked ahead of it, or follow a question no model answered is refused in words that name the
  questions to ask with it. `llm.Result.refused` names the models the safety classifier declined
  before one answered, by the ids they were asked by, and a judgement keeps them, so each judge's
  refusals (`judges.<model>.refused`) stand apart from its route's pass-overs for a status such as
  529, which `declined` counts beside them. A stop names what the judge route spent on the call it
  stopped at (`spentAtStopUsd`); the restarts are counted by kind (`restartCount`); and each row
  gives each judge's verdict cut to 200 characters.

## Implementation 15 (alpha 2.2 F.2c: the judge's room set by measurement)

The prompt's §4 lets a ceiling move with a measurement and a line here; the spend caps stay where
they stand. The haiku table's fourteen answers were judged on the table's judge route,
`claude-opus-5-5` then `claude-sonnet-5-5` at effort max, with `JUDGE_TOKENS` at 16,000, where F.2a
held it for the comparison to measure first. Three of the fourteen judgements ran out of room
(eq-eth-01, eq-eth-02 and eq-eth-03, each kept with no score, its `declined` reading "The judge's
answer did not arrive whole (it ran out of room)", 0.345 to 0.385 USD each), and five of the eleven
that arrived whole wrote about 14,000 to 16,000 tokens by their cost (eq-eth-06, 07, 10, 12 and 14).
At effort max the model's thinking counts against the ceiling with its answer.

`JUDGE_TOKENS` is now 32,000, the plan's turn ceiling at effort high (`postdoc/plan.py`, `MAX_TOKENS`), and the
haiku table was judged again at it on the same route (`pnpm eval judge --suite ethanol --tag haiku`,
11:45 to 12:20 UTC on 5 November 2026), so the four tables are judged at one setting; the summary
reads each run's newest judgement. At 32,000 all fourteen arrived whole, each given by
`claude-opus-5-5` with no fallback and no refusal. The largest wrote about 23,900 tokens
(eq-eth-01), three quarters of the room, and five of the fourteen wrote past 16,000 (eq-eth-01, 02,
03, 05 and 07). A judgement cost 0.3346 USD on the mean and 0.5183 at the most, against 0.2928 and
0.3853 at 16,000 (4.6846 USD for the fourteen, against 4.0988). The hold a judge call places on the
daily cap until it settles carries its whole room, now 0.64 USD of output at Opus 5.5's price.

A judgement keeps its cost, and a spend row its USD; neither keeps tokens. Each count above comes
from a judgement's cost at Opus 5.5's prices (4 USD a million tokens in and 20 out; a judge call
caches nothing). A judgement cut short at 16,000 wrote 16,000 tokens, which gives its question's
input exactly, and the input of each other question is estimated from the length of its request by
a line through those three, within a few hundred tokens; the same request went out at both ceilings.

## Implementation 16 (alpha 2.2 F.2g: the plan's room set by the route's effort)

The opus-max table (`claude-opus-5-5` then `claude-sonnet-5-5` at effort max on the plan route) was
asked on 8 November 2026 from 03:53 UTC. Each of its first four questions (eq-eth-01 to eq-eth-04)
spent its 24 tool calls, and the answer after the stop ran out of room at the plan's ceiling of
32,000 tokens: each run keeps "Postdoc's answer did not arrive whole (it ran out of room)", 24 tool
calls, 360 to 438 seconds and 1.25 to 1.46 USD. The other three tables answered whole after their
one stop each at the bound (haiku eq-eth-02, sonnet eq-eth-05, opus-high eq-eth-02). At effort max
the model's thinking counts against the ceiling with its answer, as the judge's did (Implementation
15). The judge's room holds: none of the 32 judgements made at 32,000 on 8 November ran out.

A plan turn's ceiling now follows the plan route's effort (`postdoc/plan.py`, `ceiling`):
`MAX_TOKENS`, 32,000, at high and below; 64,000 at xhigh; 128,000 at max, the output ceiling of
every model the routes name (Opus 5.5, Sonnet 5.5 and Haiku 5.5 on a streamed call, which every
call here is). The question's budget still bounds each turn (`postdoc_agent._turn_tokens`), and the
loop still holds back a `MIN_TOKENS` answer before it asks another round. A turn pays for what it
writes; the hold a call places on the daily cap until it settles carries the turn's whole room.

The table's other ten questions and a measure of the larger room on eq-eth-01 to eq-eth-04 wait on
the Anthropic account's own usage limit, reached at 04:28 UTC on 8 November ("You will regain
access on 2026-12-01 at 00:00 UTC"; `pnpm ready --probe` says it in words). Revisit: when the account
answers again, ask eq-eth-01 to eq-eth-04 on the opus-max table under a tag of their own and see each
answer arrive whole; a larger room that still runs out returns here with its measure.

## Evidence

- `postdoc_agent.py`, `llm.py`, `spend.py`, `tools/__init__.py` at `alpha-1.0`.
