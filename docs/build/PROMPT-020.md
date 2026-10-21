# OF-BLD-020 — fermOS and pureOS on BioSTEAM: the vessel and the train, every parameter in hand (one message, two nights)

Paste everything below this line into a Claude Code cloud session on `bytesizedyogurt/openFermentUI`. Claude Opus 5.5, extra-high effort. Nothing else to attach. Night one starts at §1.1. The next evening, the same paste with the words "next phase" resumes at the first step id missing from the commit log.

---

You are executing **OF-BLD-020** on the openFerment repository, unattended, overnight. I am Sean Creighton, the owner. I am asleep until about 07:00 New York (11:00 UTC). The document is the second half of this message, after `=== THE DOCUMENT ===`; save it to `docs/build/OF-BLD-020.md` in §1.1.

## Part A — Read first, in this order

1. `CLAUDE.md` (all of it; the sections *Proforma on BioSTEAM*, *Proforma's screens*, *fermOS fits what a run measured*, *Figures and geneOS's ceiling*, *Computed values, tools and budgets*, *Postdoc reaches every module*, *Programs*, *Nothing invented on screen*), `STATE.md` (the OF-BLD-019 section whole; it is the measured state of everything this document builds on), `COMPONENTS.md`, `README.md`, `docs/TOOLS.md`, `docs/DEMO.md`.
2. `docs/build/OF-BLD-014.md` Parts A to E and Phase 7 (fermOS as first built), `docs/build/OF-BLD-019.md` whole (Proforma on BioSTEAM; its D1–D12 are this document's foundations).
3. These files whole: `core/openferment_core/fermos.py`, `proforma.py`, `pureos.py`, `thermo.py`, `flowsheets/shelf.py`, `flowsheets/ethanol_glucose_v0.py`, `workers/proforma_worker.py`, `workers/__init__.py`, `artifacts.py`, `basis.py`, `tools/__init__.py`, `tools/fermos.py`, `tools/proforma.py`, `tools/pureos.py`, `tools/writes.py`, `tools/gates.py`, `module_stores.py`; `src/screens/FermOS.tsx` (its header is a design decision this document amends), `FermOSForecast.tsx`, `PureOS.tsx`, `PureOSTrain.tsx`, `ProformaScenario.tsx` (the inputs table and **Keep assumption** are the pattern the parameter panel generalises), `src/components/PropertiesPanel.tsx`, `src/components/figures/*`, `src/lib/fermos.ts`, `src/lib/proforma.ts`, `src/lib/durable.ts`, `src/data/subsystems.ts`, `src/data/vocabulary.ts` (the unit-operation vocabulary), `src/data/ontology.ts`, `src/engine/units.ts`.
4. BioSTEAM's own code for the units this document names, in `core/.venv` (`biosteam/units/aerated_bioreactor.py`, `abstract_stirred_tank_reactor.py`, `nrel_bioreactor.py`, `design_tools/aeration.py`, `solids_separation.py`, `distillation.py`, `molecular_sieve.py`, `_flash.py`, `_multi_effect_evaporator.py`, `liquid_liquid_extraction.py`, `adsorption.py`, `drying.py`, `_batch_crystallizer.py`, `_clarifier.py`, `heat_exchange.py`, `tank.py`, `mixing.py`, `splitting.py`, `_pump.py`): read each unit's documented parameters before writing its catalogue entry. The catalogue copies BioSTEAM's parameter names and defaults; it invents none.
5. The document below, twice. Where it and the tree disagree, the tree wins and your report says so.

## Part B — Rules that do not move

- Start from `main` at its head (`1a92325`, OF-BLD-019, or later). Work on `claude/of-bld-020-vessel-train`. Push after every commit.
- One commit per step, message exactly as the document gives it. `pnpm verify` green before every commit (twenty-four stages; `test:sim` runs the real BioSTEAM worker). Red after two attempts at the cause is a stop.
- Every model call the platform makes runs on the models the environment names; `llm.py` defaults stay untouched.
- Rule 1 covers you: no process number enters seed data, a model family, a unit catalogue entry or product code from you. A parameter's value comes from a fit of a deposition, a record through the aggregate gate, a kept artifact, a named person's assumption typed in the panel, a stated convention, or BioSTEAM's own default read from its code, and the basis says which. Bounds on a slider are conventions with a written justification each.
- A model (Postdoc) never types a number: its tool inputs carry ids and words (record ids, artifact ids, model family and unit type names, named presets). The parameter panel is for people, under a reviewer name.
- Delete nothing under `src/data/corpus/`, no record, candidate, decision, artifact or person.
- **Ask me nothing.** Part D settles every open choice; where it is silent, take the smaller, reversible option that keeps verify green and record it in `STATE.md` under the step. Stop only on the stop conditions in Part A of the document.
- Wall clock: `date -u` at the start of every step. From **10:30 UTC** start no new step; finish the one in hand, go green, push, write the report, stop. Spend cap per night: 2.00 USD.
- When context passes two thirds, finish the step, commit, push, stop, name the next step.

## Part C — Approvals I give in advance

1. **The fermOS rule is amended** as Part D's D1 says: fits take only measurements; simulations may take records, fits, artifacts, assumptions and conventions, labelled. Rewrite the `FermOS.tsx` header and the `CLAUDE.md` line accordingly.
2. **Licences.** No new library is expected: BioSTEAM, thermosteam, biorefineries and scipy are installed. `lmfit` (BSD-3) may be added for fit intervals if §3.2 finds scipy's covariance insufficient; Biopython (its own permissive licence) may be added in §7.1. Any permissive string lands with its line; a copyleft string waits and is owed.
3. **The reviewer name** for any assumption or carry-out the session makes on the live service is `OF-BLD-020 session`, recorded in STATE as a test entry I may withdraw.

## Part D — Order and priority

Night one: Phase 1 (baseline), Phase 2 (the parameter panel, shared by every module), Phase 3 (fermOS kinetics families and the Simulate tab), Phase 4 (fermOS's vessel on BioSTEAM and the Vessel tab), then Phase 8 (live, run sheet, truth, PR) **whatever state 3 and 4 are in**. Night two, after I merge: Phase 5 (pureOS's unit catalogue, the train model and the Builder), Phase 6 (the seam: a train and a vessel become a flowsheet Proforma prices), Phase 7 (the train proposer), then Phase 8 again. Phase 7 is the first to drop.

## Part E — Report

End with the A.7 report from OF-BLD-014, with these lines at the top:

```
MORNING: <green and ready to merge | stopped at §x.y, run "next phase" | do not deploy, because …>
FERMOS: <what a person can do on it now: simulate, fit, design a vessel; which model families run; what the live simulation from thread Q gave>
PUREOS: <what a person can do: build a train, run it, read recovery and purity; which unit types are in the catalogue and which ran in test:sim>
EVERY PARAMETER: <where the panel is live (fermOS Simulate, Vessel, pureOS Builder, Proforma inputs), how many parameters it exposes per screen, and that an override is a named assumption in every basis>
POSTDOC: <the tools added, each checked live once with claims kept/dropped and cost>
STEER AROUND: <every control or screen that still fails>
```

Plain English, short sentences. Explain any open-source tool by what it does.

Begin with §1.1.
