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

## Revisit condition

That evaluation (development plan §8, "Let the simple system compete").

## Evidence

- `postdoc_agent.py`, `llm.py`, `spend.py`, `tools/__init__.py` at `alpha-1.0`.
