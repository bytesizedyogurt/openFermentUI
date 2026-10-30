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

## Revisit condition

That evaluation (development plan §8, "Let the simple system compete").

## Evidence

- `postdoc_agent.py`, `llm.py`, `spend.py`, `tools/__init__.py` at `alpha-1.0`.
