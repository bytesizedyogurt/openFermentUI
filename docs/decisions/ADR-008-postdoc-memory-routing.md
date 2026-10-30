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

## Revisit condition

That evaluation (development plan §8, "Let the simple system compete").

## Evidence

- `postdoc_agent.py`, `llm.py`, `spend.py`, `tools/__init__.py` at `alpha-1.0`.
