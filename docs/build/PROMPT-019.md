# OF-BLD-019 — Proforma stands on BioSTEAM, and BioSTEAM reaches every module it belongs in (one message)

Paste everything below this line into a Claude Code cloud session on `bytesizedyogurt/openFermentUI`. Claude Opus 5.5, extra-high effort. Nothing else to attach. This runs today, before OF-BLD-018 night one; it replaces that document's Phase 1 and goes further.

---

You are executing **OF-BLD-019** on the openFerment repository. I am Sean Creighton, the owner. I may be around, but build as if I am not: ask me nothing, take the defaults in Part D, record each choice in `STATE.md` under the step. The document is the second half of this message, after `=== THE DOCUMENT ===`; save it to `docs/build/OF-BLD-019.md` in §1.1.

## Part A — Read first, in this order

1. `CLAUDE.md`, `STATE.md` (the OF-BLD-016 section and the morning report), `COMPONENTS.md`, `README.md`, `docs/TOOLS.md`, `docs/DEMO.md`.
2. `docs/build/OF-BLD-014.md` Parts A to E, and its Phase 8 (§8.1–§8.6: how Proforma was built on BioSTEAM the first time).
3. The whole of `core/openferment_core/proforma.py`, `flowsheets/`, `workers/proforma_worker.py`, `src/screens/Proforma.tsx`, `ProformaScenario.tsx`, `ProformaBiosteam.tsx`, `src/lib/proforma.ts`, `src/data/scenarios.ts`, `src/engine/grids.ts`, and the Proforma routes in `api.py`.
4. The document below, twice. Where it and the tree disagree, the tree wins and the report says so.

## Part B — Rules that do not move

- Start from `main` at its head. Work on `claude/of-bld-019-proforma`. Push after every commit.
- One commit per step, message exactly as the document gives it. `pnpm verify` green before every commit (twenty-four stages; `test:sim` runs the real BioSTEAM worker, so a broken flowsheet is red there, which is the point). Red after two attempts at the cause is a stop.
- Every model call the platform makes runs on the models the environment names (`OPENFERMENT_MODEL` and kin); `llm.py` defaults stay untouched.
- Rule 1 covers you: no process number enters seed data, a flowsheet file or product code from you. A flowsheet's inputs arrive bound to records, computed artifacts or a named person's assumptions; equipment and thermodynamics are BioSTEAM's own; a reference biorefinery's defaults are the package's, cited as such.
- Delete nothing under `src/data/corpus/`, no record, candidate, decision, artifact or person. The authored cost surfaces S1–S3 and `sc-pha-1` stay (archived examples).
- Wall clock: `date -u` at the start of every step. Nine hours after the start, begin no new step; finish the one in hand, go green, push, write the report, stop. Spend cap: 2.00 USD.
- When context passes two thirds, finish the step, commit, push, stop, name the next step.

## Part C — Approvals I give in advance

1. **Licences.** No new Python library is expected: `biosteam`, `biorefineries`, `thermosteam` (BioSTEAM's dependency) and `scipy` are in the `sim` extra. Graphviz, if used for diagrams, is a system package (EPL-1.0) that the code calls only when present. Any permissive string lands with its line; a copyleft string waits for me and is listed as owed.
2. **The reviewer name** for any assumption or carry-out the session makes on the live service is `OF-BLD-019 session`, recorded in STATE as a test entry I may withdraw.

## Part D — Order and priority

Phases in order: 1 (measure and diagnose), 2 (the flowsheet shelf in the worker), 3 (Proforma's screens), 4 (pureOS and thermosteam), 5 (fermOS and geneOS bridges), 6 (Postdoc and MCP), 7 (live, run sheet, truth, PR). **Phase 7 runs whatever state the others are in.** Phase 3 is the one I will look at first: a working New scenario, a scenario page that is useful on its own, nothing broken on the index.

## Part E — Report

End with the A.7 report from OF-BLD-014, with these lines at the top:

```
MORNING: <green and ready to merge | stopped at §x.y, run "next phase" | do not deploy, because …>
PROFORMA: <what a person can do on it now, in five lines: new scenario, run, read, compare, export>
BIOSTEAM REACHES: <which modules read a BioSTEAM result on this tree and how: pureOS, fermOS, geneOS, Postdoc, MCP>
REFERENCE RUNS: <corn dry-grind: price and IRR against the package's own test values; cornstover: unchanged; ethanol_glucose_v0: bound inputs and price, or what waits>
STEER AROUND: <every control or screen that still fails>
```

Plain English, short sentences. Explain any open-source tool by what it does.

Begin with §1.1.

