# openferment-core

The canonical openFerment entity schema and unit engine, in Python.

Everything that has to be callable by BioSTEAM, COBRApy, PaperQA2, Inspect AI or
the extraction pipeline lives here, because all four of those are Python-only. A
TypeScript implementation that a Python one has to agree with is not a head
start; it is two things to keep in step, and keeping them in step by hand is the
failure this package exists to prevent.

`src/data/types.ts` in the UI is generated from these models. Do not edit it.
Edit the models, run `pnpm gen:types`, and the TypeScript follows.

See `CLAUDE.md` at the repository root for the routing table.
