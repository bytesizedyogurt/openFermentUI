// SIMULATION — REMOVED WITH THE SCRIPTED AGENT.
//
// Removed in: the migration phase that puts `src/sim/` behind an
// `AgentAdapter`, alongside `chat.ts`. `sim/` is retired last, by design
// (README, Architecture).
// Replaced by: `AgentAdapter.suggestedPrompts()`, answered by whatever is
// actually behind the Ask screen. A real model needs no exact triggers, so
// what a server returns there is a set of good questions rather than a set of
// keys — the list below stops being data and becomes a fixture for the
// entry path.
//
// ── Why these are not corpus data ─────────────────────────────────────
//
// They arrived here from `src/data/flows.ts`, which is where the SCRIPTED
// FLOWS live and will stay: those survive this file as regression fixtures for
// the real agent's answer formatter (README, Architecture). The chips did not
// belong beside them, and the docstring below says why in one line — each
// string is one flow's TRIGGER verbatim, so that clicking a chip is an exact
// match. That property is a property of the scripted matcher in `chat.ts`,
// which `matchFlow` scores by exact match then whole-phrase containment and
// nothing else. Nothing in OF-COR-001 authors these six; they are the demo's
// entry path, and an entry path into a simulation is simulation.
//
// Which is the whole routing argument: the other three modules this phase
// moved went behind a SERVER adapter, because a server will answer them.
// Nothing will answer this one — the day the real agent lands, the exact-match
// guarantee it exists to provide is gone, so it retires with the thing that
// needed it rather than being carried across.
//
// Kept as its own file rather than folded into `chat.ts` so that the two Node
// scripts reading it (`check-seed`, `capture-answer-shapes`) can import six
// strings without pulling the store, the corpus and React in behind them.

/**
 * Prompt chips on the empty Ask screen. Each string is one flow's trigger
 * verbatim, so clicking a chip is an exact match rather than a fuzzy one.
 */
export const SUGGESTED_PROMPTS: string[] = [
  'What titers have been achieved for recombinant β-casein?',
  'Has anyone expressed a casein in an alga?',
  'Compare Chlamydomonas and Pichia as casein hosts',
  'What is the maximum secreted protein yield from Chlamydomonas?',
  'Does phosphorylation actually matter for making cheese?',
  'What is the regulatory status of C. reinhardtii as food?',
];
