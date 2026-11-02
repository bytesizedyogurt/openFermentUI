# openFerment — Proforma stands on BioSTEAM

**Document:** OF-BLD-019 · **Version:** 1.0 · **Date:** 20 October 2026, 08:40 New York
**Repo:** `bytesizedyogurt/openFermentUI` · **start from** `main` @ `a261f30` or later
**Work branch:** `claude/of-bld-019-proforma`
**Builds on:** OF-BLD-014 Phase 8 (Proforma's worker, the cornstover benchmark, `pha_sugar_v0`, `bind`, Spearman), OF-BLD-015 Phase 7 (tools, gates), OF-BLD-016 (programs, nothing invented). Replaces OF-BLD-018 Phase 1 and takes its §1.2–§1.5 further; OF-BLD-018's remaining phases follow it.
**Executor:** Claude Opus 5.5 in Claude Code at extra-high effort, one session of about nine hours.
**Goal in one line:** Proforma is a techno-economic tool a person can use on its own, built on BioSTEAM end to end: a shelf of flowsheets (two published reference biorefineries and one glucose-to-ethanol flowsheet of our own), a New scenario that works, a scenario page that runs the flowsheet and shows price, cost breakdown, sensitivity, stream table, equipment, utilities and diagram, every input naming its source; and the parts of BioSTEAM that belong to other modules reach them: pureOS reads the train and the stream table, thermosteam answers property questions, fermOS's fits feed the fermenter, geneOS's ceiling bounds its yield, Postdoc and outside assistants call all of it.

---

## For Sean: what this builds, in plain words

BioSTEAM is already installed and already runs on the Mini: the corn stover benchmark card is a real BioSTEAM run and `pnpm test:sim` starts the real worker in every verify. What is missing is everything a person would do with it. The index shows nothing with the archive switch off (every scenario on file is casein or PHA), "New scenario" copies the first scenario in the list and so has nothing to copy, the scenario page is built around hand-written cost surfaces from the casein days, and no other module reads a BioSTEAM result.

After this session:

1. **A shelf of flowsheets** lives in the worker. Two are published reference biorefineries from the BioSTEAM project's own `biorefineries` package: the NREL corn stover design (already the benchmark) and the **dry-grind corn ethanol plant**, which is a yeast ethanol process end to end (liquefaction, saccharification and fermentation in one vessel, beer column, rectifier, molecular sieves, DDGS drying) with the package's own regression values to prove it ran right. The third is ours: **glucose to ethanol**, a batch fermenter feeding the same ethanol purification train the corn plant uses, with no number of its own: titre, yield, productivity and feed concentration bind to thread Q records; sugar price and plant scale are assumptions you type under your name.
2. **New scenario works.** Pick a flowsheet from the shelf, name it, choose the program; the scenario page opens with its inputs listed, each either bound to records (with the count and range), computed from an artifact, or waiting for an assumption.
3. **The scenario page is an instrument.** Run; the minimum selling price with its basis; the cost breakdown as BioSTEAM's TEA gives it (feedstock, other materials, utilities, capital recovery, labour and fixed, by-product credits); a tornado from the Spearman run that already exists; the stream table; the equipment list with installed costs; heating, cooling and electricity duties; the flowsheet diagram when the host can draw it; CSV export; pin and compare. All read from one artifact per run.
4. **BioSTEAM reaches the other modules.** pureOS → Train reads the run's units and streams and shows recovery at each step. A `thermo_props` tool on thermosteam (BioSTEAM's property engine) answers density, heat capacity, boiling point and vapour-liquid behaviour for a named mixture, which fermOS and pureOS both show. fermOS's kinetic fit feeds the fermenter's titre, yield and batch time as a `computed` source. geneOS's ceiling is checked against the fermenter's yield, and a scenario above it is flagged. Postdoc gets `run_flowsheet`, `stream_table` and `thermo_props`; the MCP server picks them up with no change.

Your part afterwards: merge, deploy on the Mini, open Proforma, make a scenario from the shelf, type the two assumptions it asks for under your name, run it. Appendix 1 has the commands.

---

# PART A — HOW TO EXECUTE

OF-BLD-014 Part A applies in full, with: id prefix `OF-BLD-019`; the document at `docs/build/OF-BLD-019.md`; unattended, Part D defaults, the deletion stop; the nine-hour clock; the 2.00 USD cap; verify green and pushed before every commit.

**A worker run is a test.** `test:sim` runs in verify and starts the real worker, so every flowsheet on the shelf has at least one `sim` test that runs it on stand-in inputs marked `assumption` and checks it converges; the reference biorefineries have `slow` tests that hold their package regression values. A flowsheet that does not converge in `test:sim` does not go on the shelf.

**Hosts.** Nothing in this document needs the network beyond PyPI. Graphviz may be absent in the cloud; the code draws the diagram when `dot` is on the path and otherwise shows the unit list in order with an honest line.

---

# PART B — MEASURED STATE

Measured 20 October 2026, 08:30 New York, on `main` @ `a261f30`. A.2 step 5 applies: confirm each row before building on it; a false row stops the session and the tree wins.

## B.1 Proforma today

- `core/openferment_core/proforma.py` (547 lines): one warm `SimWorker`; `GET /api/proforma/status` (cold, starting, ready, failed); `GET`/`POST /api/proforma/benchmark` (the cornstover run, artifact sourced `model`, 1.9677 USD gal⁻¹ against 1.968); `GET /api/proforma/scenarios` (`ProformaScenarioInfo` with bindings over thread P records for `sc-pha-1`); `POST /api/proforma/run` (`ProformaRunRequest` → `ProformaRunResult`: one artifact, `demo` while any assumption remains; Spearman with averaged ranks); `selling_price` is the sixth tool and never runs a scenario; given `proforma_benchmark` it cites the stored benchmark.
- `flowsheets/`: `__init__.py` (`KNOWN = ("toy", "pha_sugar_v0")`), `cornstover_benchmark.py` (49 lines), `pha_sugar_v0.py` (229 lines, no input value in the file, sugar and dilution water as two streams, `tea._sales` reset before every `solve_price`), `toy.py` (a water/ethanol mixer and splitter for tests).
- `workers/proforma_worker.py`: `biosteam` imported here and in `flowsheets/` alone (`test_workers` greps).
- `src/screens/Proforma.tsx` (282 lines): the index; `BenchmarkCard`; a grid of scenario cards (`kind: 'authored' | 'biosteam'`); **"New scenario" calls `duplicateScenario(scenarios[0]?.id ?? '')` and is disabled when the filtered list is empty** — with the archive switch off every scenario on file is archived (`sc-s1…s3` casein examples, `sc-pha-1` PHA), so the index shows "Every scenario here is in an archived program" and the button does nothing. That is the broken button.
- `src/screens/ProformaScenario.tsx` (617 lines): built for authored surfaces (`CostModel` S1–S3 in `src/data/scenarios.ts`, swept by `src/engine/grids.ts` into a `ResultGrid`; waterfall of `CostLine`s summing to MSP; sliders over `dims`); a `biosteam` branch for `sc-pha-1` with the inputs table, assumptions (value, low, high, what it rests on, **Keep assumption** under the reviewer name), **Run the scenario**, a price distribution, a tornado. `recharts` is allowed here and in Compare (`check:figures`).
- `src/screens/ProformaBiosteam.tsx` (395 lines): the benchmark page.
- `src/data/types.ts`: `Scenario` (`modelId`, `kind`, `dims`, `point`, `assumptions`, `pinned`, `program`, `example`), `CostModel`, `ResultGrid`, `ScenarioInput`, `ProformaScenarioInfo`; `models.py` mirrors `ScenarioInput`, `ProformaScenarioInfo`, `ProformaRunRequest`, `ProformaRunResult` (in `PAIRS`).
- The store: `duplicateScenario`, `proformaAssumptions` (Durable, merged by input key), pins.

## B.2 What the `biorefineries` package ships (2.35.1, read from the sdist)

Modules: `biodiesel`, `cane`, `cellulosic`, `corn`, `cornstover`, `ethanol`, `fattyalcohols`, `gas_fermentation`, `lactic`, `lipidcane`, `milk`, `oilcane`, `sugarcane`, `tea`. Of these:

- **`corn`** — the dry-grind corn ethanol plant: `biorefineries.corn.load()` builds `system` and `tea`; `corn.units.SimultaneousSaccharificationFermentation(bst.BatchBioreactor)` with `tau=60.`, `yield_=0.95`, `V_wf=0.83`, `T=305.15`; a `yeast` stream; purification through `biorefineries.ethanol.create_ethanol_purification_system`; DDGS centrifuge and dryer. Its test (`biorefineries/tests/test_biorefineries.py::test_corn`, rtol 5 %) asserts: `tea.IRR` 0.05381572438333119, `feedstock.price` 0.13227735731092652 USD kg⁻¹, `product.price` 0.48547915353569393 USD kg⁻¹, `tea.sales` 74992038.86, `tea.material_cost` 52925382.43, `tea.installed_equipment_cost` 65387501.94, `tea.utility_cost` 10442066.33, heating duty 111.36, cooling duty 105.09, electricity consumption 1.6249, production 0.0 (GWh or the package's own units: read them from the test file). **These are the package's numbers and are cited as such; they are the regression values for §2.2.**
- **`ethanol`** — `create_beer_distillation_system(ins, outs, beer_column_heat_integration, IDs, mockup)`, `create_ethanol_purification_system_after_beer_column`, `create_ethanol_purification_system(ins=[beer, denaturant], outs=[ethanol, stillage, recycle_process_water], beer_column_heat_integration=True, IDs={})`. This is the purification train §2.3 reuses.
- **`cornstover`** — the benchmark, unchanged.
- **`tea`** — the TEA classes the reference designs use.

## B.3 What BioSTEAM ships that the modules can use (2.54.0, read from the sdist)

`biosteam/units/`: `aerated_bioreactor.py` (`AeratedBioreactor`), `nrel_bioreactor.py` (`NRELEthanolFermentation`, `NRELAnaerobicBatchBioreactor`), `abstract_stirred_tank_reactor.py`, `anaerobic_bioreactor.py`, `gas_fed_bioreactor.py`, `distillation.py`, `molecular_sieve.py`, `_flash.py`, `solids_separation.py`, `liquid_liquid_extraction.py`, `adsorption.py`, `drying.py`, `heat_exchange.py`, `tank.py`, `_pump.py`, `mixing.py`, `splitting.py`, `_multi_effect_evaporator.py`, `_clarifier.py`; `_tea.py` (`TEA`: `solve_price`, `IRR`, `sales`, `material_cost`, `utility_cost`, `installed_equipment_cost`, and the cost table methods); `bst.Model` (parameters and metrics for Monte Carlo); `bst.UnitGroup` (`get_heating_duty`, `get_cooling_duty`, `get_electricity_consumption`); `System.diagram()` (Graphviz). `thermosteam` underneath: `Chemical`, `Chemicals`, `Thermo`, `Stream` with `rho`, `Cp`, `mu`, `bubble_point`, `dew_point`, `vle`.

## B.4 Guards that matter

`check:plan` (`PAIRS`), `check:seed` (programs, E.3′ strings, `example`), `check:reference`, `check:figures` (`recharts` only in Compare and ProformaScenario; new figures through the grammar), `check:tools` (a module's read and write tools; `ALLOWED_WRITES`), `test:sim` (in verify), `test:slow` (outside), `check:store` (Durable round-trips), the smoke (68 routes) and golden path (32 steps; walks `/proforma/scenario/sc-pha-1` with the switch on).

---

# PART C — WHAT IS TRUE WHEN THE DOCUMENT IS DONE

1. `flowsheets.SHELF` lists four flowsheets with a title, a one-line description, the source (package and version, or this repository), the inputs each takes (key, name, dimension, unit, the ontology fields that bind it) and the outputs it reports: `cornstover_benchmark`, `corn_drygrind` (new), `ethanol_glucose_v0` (new), `pha_sugar_v0` (archived with PHA). `toy` stays off the shelf.
2. `corn_drygrind` runs in the worker on the package's defaults and `test:slow` holds it to the package's own test values within 5 %; its run is an artifact sourced `model`, like the benchmark, and shows on the index as the yeast program's reference biorefinery.
3. `ethanol_glucose_v0` runs in `test:sim` on stand-in inputs marked `assumption`, and live over thread Q with titre, yield, productivity and feed glucose bound to records; its purification train is `create_ethanol_purification_system`; its fermenter is `bst.BatchBioreactor` with the batch time, yield and titre set from the bound inputs; the file holds no number.
4. Proforma's index shows the shelf, the reference runs with their prices and dates, and the scenarios of the active program; **New scenario** opens a chooser over the shelf and creates a scenario that opens with its inputs; nothing on the index is disabled when the list is empty.
5. The scenario page runs a flowsheet and shows: the price with its basis and provenance; the TEA cost breakdown; the tornado; the stream table; the equipment list with installed cost per unit; utility duties; the diagram or the ordered unit list; CSV of each table; pin and Compare. Every input shows its source (records with count and range, an artifact, a named assumption) and the run is `demo` while an assumption remains.
6. pureOS → Train (`/pureos/train/:scenarioId`) shows the run's units in order with mass in, mass out and recovery per unit and overall, read from the same artifact. `thermo_props` answers for a named mixture and both screens use it.
7. fermOS's kinetic fit can be sent to a scenario as its titre, yield and batch time (`source: artifact`), and a fermenter yield above the geneOS ceiling for that strain and sugar is flagged on the scenario page with both numbers' bases.
8. The registry holds `run_flowsheet` (a write through `proforma.run`, free), `stream_table` and `thermo_props` (reads); `check:tools` is green; `test_mcp` counts them.
9. `docs/DEMO.md` has a Proforma section with what a person does and what each reference run showed; README, COMPONENTS, CLAUDE, TOOLS, STATE true for the tree; a PR to `main`.

---

# PART D — DECISIONS

- **D1 — One artifact per run, every reader reads it.** `proforma.run` writes one `proforma_run` artifact holding price, the TEA breakdown, the sensitivity, the stream table, the unit table, the utilities and the diagram (SVG text when drawn). Proforma, pureOS, fermOS, Postdoc and the MCP server read that artifact; nothing recomputes on read.
- **D2 — The shelf is data in Python, mirrored for the browser.** `flowsheets/shelf.py` declares each flowsheet's `FlowsheetInfo` (id, title, description, source, program, inputs, outputs, `reference: bool`); `GET /api/proforma/shelf` serves it; `types.ts` mirrors it through `PAIRS`. A scenario names a flowsheet by id and nothing else about its structure.
- **D3 — Reference runs are `model`, our flowsheet is `computed`.** A reference biorefinery run on the package's defaults is provenance `model` with the package and version in its basis (as the benchmark is today). `ethanol_glucose_v0` over bound records is `computed`, `demo` while an assumption remains (as `pha_sugar_v0` is today).
- **D4 — No input value in a flowsheet file.** As `pha_sugar_v0`: the binding layer sets every process input. `ethanol_glucose_v0`'s inputs: `feed_glucose_conc` (g L⁻¹; `glucose_initial_conc`, else `medium_component_conc` on glucose), `titre` (`ethanol_titre`), `yield` (`ethanol_yield_substrate`), `productivity` (`ethanol_productivity`; batch time = titre / productivity, stated), `plant_scale` (t ethanol yr⁻¹, assumption), `glucose_price` (USD kg⁻¹, assumption), `ethanol_purity` (fuel grade, a convention named in the basis). The fermenter's `yield_` is the bound yield as a fraction of the theoretical, with the theoretical (0.511 g g⁻¹) a stated convention in the basis.
- **D5 — The authored surfaces step aside, they are not deleted.** S1–S3 and `src/engine/grids.ts` stay for the archived casein scenarios and `check:lock`; the scenario page keeps its authored branch behind the switch and the BioSTEAM branch becomes the page. `New scenario` creates `kind: 'biosteam'` only.
- **D6 — Scenarios persist in the Durable tier**, keyed by id, with their flowsheet id, name, program, assumptions and the id of the newest run artifact; the seed's `scenarios.ts` keeps the archived examples and `sc-yeast-1` as the one shipped yeast scenario (so a fresh install has something to open). `check:store` round-trips a created scenario.
- **D7 — Monte Carlo stays Spearman on the existing sampler**; `bst.Model` is used only where it is cheaper than the current code, and the switch is recorded. Sample count is a request field with a cap, default the current one.
- **D8 — Diagrams are optional.** `System.diagram(format='svg')` when `dot` is found; otherwise the ordered unit list with *Graphviz is not installed here; the diagram draws on a host that has it (`brew install graphviz` on the Mini)*. `ready.py` gains a row.
- **D9 — thermosteam answers, never guesses.** `thermo_props(components: {name: mass fraction}, T, P)` builds a `Stream` on BioSTEAM's chemical library and returns density, Cp, viscosity, bubble and dew points; a chemical the library lacks is an error in words. The result is a `computed` artifact with the library version in its basis.
- **D10 — The fermOS bridge is a source, not a copy.** `proforma.bind` accepts `source: artifact` for titre, yield and batch time from a `kinetic_fit` or `batch_simulation` artifact; the scenario page offers "Use a fermOS fit" listing the fits on file; the basis names the fit.
- **D11 — The geneOS check is a flag, never a bound.** When a scenario's strain and sugar have a stored ceiling, the page shows the fermenter yield beside it and flags a yield above it; nothing is clamped.
- **D12 — Branching.** `claude/of-bld-019-proforma` from `main`; PR to `main`; the Mini runs `main`. OF-BLD-018 night one is reissued afterwards without its Phase 1.

---

# PART E — CONTRACTS

OF-BLD-014 Part E, OF-BLD-015 Part A.3, OF-BLD-016 Part E hold. Added: E.1″–E.4″ of OF-BLD-018 (a tool behind every capability; every external result an artifact with a basis; a worker per heavy library; a source carries its licence line) apply here.

---

# PHASE 1 — Measure and diagnose

## §1.1 Branch, document, baseline

As OF-BLD-016 §1.1: branch, `session-start.sh`, `pnpm ready`, `pnpm data:pull`, `pnpm verify`, Part B confirmed line by line (open each file B.1 names; run `cd core && uv run --all-extras python -c "import biosteam, biorefineries, thermosteam; print(biosteam.__version__, biorefineries.__version__, thermosteam.__version__)"`; `which dot`), STATE heading `## OF-BLD-019 (branch claude/of-bld-019-proforma, from <hash>)`.
**Commit:** `OF-BLD-019 §1.1: the branch, the document, and the baseline measured`

## §1.2 The diagnosis, written down

Drive the built app against the live service with the smoke's browser driver, with the switch off and on: the index, New scenario, `sc-pha-1`'s page (switch on), the benchmark page, Compare. Record in STATE every control that does nothing, errors, or shows an invented thing, with the file and line. Confirm the New scenario root cause in B.1. Run `corn.load()` once in the worker's Python and time it. No code change in this step.
**Commit:** `OF-BLD-019 §1.2: what Proforma does and does not do today, measured`

---

# PHASE 2 — The shelf, in the worker

## §2.1 The shelf and the run artifact

**Files:** `flowsheets/shelf.py` (new: `FlowsheetInfo`, `SHELF`), `flowsheets/__init__.py` (`KNOWN` from the shelf), `workers/proforma_worker.py` (`run(flowsheet, inputs, samples)` returns price, TEA breakdown via the `TEA` object's own methods, Spearman, stream table (every stream: id, source unit, sink unit, phase, T, P, mass flow by component), unit table (id, class, installed cost, purchase cost, utilities), `UnitGroup` duties, and the diagram SVG when `dot` exists), `proforma.py` (`run` writes the one artifact of D1; `shelf()`), `artifacts.py`, `models.py` (`FlowsheetInfo`, `FlowsheetInput`, `StreamRow`, `UnitRow`, `UtilityDuties`, `TeaBreakdown`; `ProformaRunResult` grows), `types.ts`, `check-plan.mjs`, `api.py` (`GET /api/proforma/shelf`), `core/tests/test_proforma.py`, `test_proforma_shelf.py` (new; `sim`: the toy flowsheet's run artifact carries every table; the shelf refuses `toy`).

**Commit:** `OF-BLD-019 §2.1: a shelf of flowsheets, and one artifact per run that every reader reads`

## §2.2 The dry-grind corn plant, as the yeast program's reference

**Files:** `flowsheets/corn_drygrind.py` (new: `biorefineries.corn.load()` under BioSTEAM's default settings, the package's own defaults, no change to them; exposes `system`, `tea`, the ethanol and corn streams), `shelf.py` (`reference: True`, program `yeast`, source `biorefineries 2.35.1, corn`), `proforma.py` (`GET /api/proforma/reference/{id}` reads, `POST` runs; the artifact sourced `model` as the benchmark is), `api.py`, `core/tests/test_proforma_slow.py` (`slow`: IRR, feedstock price, ethanol price, sales, material cost, installed equipment cost, utility cost and the three duties against B.2's values within 5 %, read from the package's test as the authority), `core/tests/test_proforma.py` (`sim`: the shelf entry loads and names its inputs).

**Commit:** `OF-BLD-019 §2.2: the dry-grind corn ethanol plant runs as the yeast program's reference biorefinery`

## §2.3 Glucose to ethanol, ours, with no number of its own

**Files:** `flowsheets/ethanol_glucose_v0.py` (new: a glucose solution feed stream built from `feed_glucose_conc` and `plant_scale`; `bst.BatchBioreactor` subclass with the fermentation reaction glucose → ethanol + CO₂ at the bound yield fraction, `tau` from titre over productivity, `V_wf` BioSTEAM's default; `create_ethanol_purification_system` from `biorefineries.ethanol` with a denaturant stream at zero unless an input says otherwise; stillage out; a `TEA` from `biorefineries.tea` or BioSTEAM's `TEA` with the package's default financial assumptions cited; `solve_price` on ethanol with `tea._sales` reset as `pha_sugar_v0` does), `shelf.py` (inputs per D4), `proforma.py` (`bind` for the yeast fields, the theoretical-yield convention in the basis, the 422 for an input with neither source), `src/data/scenarios.ts` (`sc-yeast-1`, `kind: 'biosteam'`, flowsheet `ethanol_glucose_v0`, program `yeast`, no `example`), `core/tests/test_proforma.py` (`sim`: converges on stand-in assumptions; an infeasible yield above 1 names its reason), `test_proforma_slow.py` (`slow`: the price on fixed stand-in inputs as a regression value, tolerance 1 %).

**Commit:** `OF-BLD-019 §2.3: a glucose-to-ethanol flowsheet of our own, every input bound or named`

## §2.R and §2.T

**Commits:** `OF-BLD-019 §2.R: …` · `OF-BLD-019 §2.T: README, COMPONENTS and STATE for the shelf`

---

# PHASE 3 — Proforma's screens

## §3.1 The index and New scenario

**Files:** `src/screens/Proforma.tsx` (rewritten around the shelf: a **Reference runs** row (benchmark and corn, each with price, date, provenance `model`, a Run/Rerun button and a link to its page), a **Flowsheets** row from `/api/proforma/shelf` (each with inputs listed and a **New scenario from this** button), the active program's scenarios as cards (price of the newest run or *not run yet*, bound/waiting counts, pin); the empty state names the shelf; nothing disabled), `src/components/NewScenarioDialog.tsx` (new: flowsheet, name, program (active by default), create → `/proforma/scenario/:id`), `src/store.ts` (`createScenario(flowsheetId, name, program)`, scenarios in the Durable tier per D6, `duplicateScenario` kept), `src/lib/proforma.ts` (shelf, reference, run, artifact readers), `check-store.ts` (round-trip), `CommandPalette.tsx` ("New Proforma scenario" opens the dialog), `smoke.mjs` (create a scenario, land on its page), `service-double.mjs` (shelf and run fixtures from `demo.py --prototype` with the stand-in evaluator).

**Commit:** `OF-BLD-019 §3.1: the index shows the shelf and the reference runs, and New scenario makes one`

## §3.2 The scenario page

**Files:** `src/screens/ProformaScenario.tsx` (the BioSTEAM branch becomes the page: header with flowsheet, program, provenance; **Inputs** table (name, dimension, unit, source: *N records, low–high* with a link to the chooser, *artifact* with its link, *assumption by <name>* with value, low, high, what it rests on, or *waiting*; **Keep assumption** as today; **Use a fermOS fit** per D10 when a fit exists); **Run** with the worker status line (cold/starting/ready/failed, seconds); **Result**: price with basis and provenance tick; **Cost breakdown** from the TEA (a waterfall under the grammar through `src/components/figures/CostWaterfall.tsx`, `toTable`), **Sensitivity** tornado (existing, moved under the grammar as `Tornado.tsx`), **Streams** table, **Equipment** table, **Utilities**, **Diagram** (SVG or the ordered list with the D8 line), **Ceiling check** per D11 when a ceiling exists; CSV per table; pin; Compare link; the authored branch kept for archived scenarios under the banner), `src/components/figures/CostWaterfall.tsx`, `Tornado.tsx`, `check:figures` (recharts allowed in ProformaScenario stays; the new figures use the grammar), `src/lib/proforma.ts`, `smoke.mjs` (run against the double, every section present), `golden-path.mjs` (its Proforma beat on `sc-yeast-1` with the switch off, replacing the PHA beat's role; the PHA beat stays under the switch).

**Commit:** `OF-BLD-019 §3.2: the scenario page runs the flowsheet and reads every table from the run`

## §3.3 Reference pages and Compare

**Files:** `ProformaBiosteam.tsx` (generalised to `/proforma/reference/:id`: benchmark and corn; the same tables as a scenario page over the `model` artifact; the package test values beside the run's, as the benchmark page shows 1.968), `Compare.tsx` (two or more `biosteam` scenarios side by side on price, breakdown and bound inputs; the authored compare kept for archived), `nav.ts` (`reference` reserved under Proforma; `REDIRECTS` from the old benchmark path), `tabs.ts`, `components.ts`, `COMPONENTS.md`, `smoke.mjs`.

**Commit:** `OF-BLD-019 §3.3: reference pages for the two published biorefineries, and Compare over BioSTEAM scenarios`

## §3.R and §3.T

**Commits:** `OF-BLD-019 §3.R: …` · `OF-BLD-019 §3.T: README, COMPONENTS and STATE for Proforma's screens`

---

# PHASE 4 — pureOS and thermosteam

## §4.1 pureOS → Train

**Files:** `src/screens/PureOS.tsx` (header rewritten: *pureOS reads the train a flowsheet ran*; the index lists runs on file by scenario with overall recovery; `PLANNED` shortened), `src/screens/PureOSTrain.tsx` (new: `/pureos/train/:scenarioId`: the units in order from the run artifact, each with inlet and outlet streams, product mass in and out, recovery per unit and cumulative, the stream table filtered to that unit on click; the unit operation vocabulary entry linked where the BioSTEAM class maps to one (`vocabulary.ts` gains `biosteamClasses: string[]` on the entries that map: distillation, molecular-sieve (new), centrifugation, uf-df, spray-dry, lyophilisation, heat-step, lle, precipitation, crystallisation), `src/components/figures/RecoveryByUnit.tsx` (bars under the grammar), `nav.ts`, `tabs.ts`, `App.tsx`, `components.ts`, `tools/pureos.py` (`pureos_train` read over the artifact; `pureos_read` rows include trains), `tools/__init__.py`, `module_stores.py`, `docs/TOOLS.md`, `smoke.mjs`, `service-double.mjs`, `core/tests/test_pureos.py` (new).

**Commit:** `OF-BLD-019 §4.1: pureOS reads the train, unit by unit, from the run Proforma priced`

## §4.2 thermosteam answers property questions

**Files:** `workers/proforma_worker.py` (`thermo_props` per D9, in the same worker: thermosteam is already loaded there), `core/openferment_core/thermo.py` (new: the request shape, the artifact `thermo_props`), `tools/thermo.py` (`thermo_props` read tool: components by name with mass fractions as words? — no: fractions are numbers, and tool inputs carry no numbers; so the tool takes a **record id or a stream id** whose composition is already on file, or a named preset (`ethanol-water-azeotrope`, `beer-at-titre-of <record id>`), and the service fills the numbers), `tools/__init__.py`, `PureOSTrain.tsx` and `FermOS.tsx` (a **Properties** card for the broth and the product stream: density, Cp, bubble point, with the library version), `docs/TOOLS.md`, `core/tests/test_thermo.py` (`sim`: pure water at 298 K gives density within 1 % of 997 kg m⁻³ as the library's own value; an unknown chemical is an error in words).

**Commit:** `OF-BLD-019 §4.2: thermosteam answers density, heat capacity and boiling behaviour for streams on file`

## §4.R and §4.T

**Commits:** `OF-BLD-019 §4.R: …` · `OF-BLD-019 §4.T: README, COMPONENTS and STATE for pureOS on the train`

---

# PHASE 5 — fermOS and geneOS bridges

## §5.1 A fit feeds the fermenter

**Files:** `proforma.py` (`bind` accepts `source: artifact` with a `kinetic_fit` or `batch_simulation` id: titre from the fitted or simulated final product, yield from Yp/s, batch time from the time the median sugar runs out; refuses a fit whose needed parameter is unidentified), `models.py` (`ScenarioInput.source` gains `artifact`), `types.ts`, `ProformaScenario.tsx` (**Use a fermOS fit**), `FermOSForecast.tsx` (**Send to Proforma** on a fit: opens the scenario chooser), `src/lib/proforma.ts`, `core/tests/test_proforma.py` (a stand-in fit binds; an unidentified μ refuses with the parameter named).

**Commit:** `OF-BLD-019 §5.1: a fermOS fit feeds a scenario's titre, yield and batch time as a computed source`

## §5.2 The ceiling check

**Files:** `proforma.py` (`ceiling_check(scenario)`: the newest stored `geneos.ceiling` for the scenario's strain's host model and sugar, if any; the fermenter yield beside it; a flag when above), `models.py`, `types.ts`, `ProformaScenario.tsx` (**Ceiling check** card with both bases), `GeneOSModel.tsx` (a scenario above the ceiling is listed under the model), `core/tests/test_proforma.py`.

**Commit:** `OF-BLD-019 §5.2: a scenario's yield is read against the geneOS ceiling, and flagged, never clamped`

## §5.R and §5.T

**Commits:** `OF-BLD-019 §5.R: …` · `OF-BLD-019 §5.T: README, COMPONENTS and STATE for the bridges`

---

# PHASE 6 — Postdoc and outside assistants

## §6.1 Three tools

**Files:** `tools/proforma.py` (`run_flowsheet`: scenario id and nothing else, a free write through `proforma.run` (it spends no model money; it is compute), audited with the model as agent; `stream_table`: a run artifact id, the table cut to the summary cap with the whole table in `ToolResult.data`), `tools/thermo.py` (§4.2), `tools/__init__.py` (`WHITELIST`; the two reads loose, the write as the module writes are), `tools/writes.py` (`proforma_write` gains `run`), `gates.py` (unchanged: a run is not gated; recorded), `validate.py` (the new id families in `SeenSet`), `postdoc_agent.py` (prompt rule: price and recovery claims cite the run artifact), `docs/TOOLS.md`, `test_tools.py`, `test_mcp.py` (count), `test_postdoc_agent.py`.

**Commit:** `OF-BLD-019 §6.1: Postdoc runs a flowsheet, reads its stream table and asks thermosteam, and the MCP server offers the same`

## §6.R and §6.T

**Commits:** `OF-BLD-019 §6.R: …` · `OF-BLD-019 §6.T: README, TOOLS and STATE for the tools`

---

# PHASE 7 — Live, the run sheet, the truth

## §7.1 LIVE — the reference runs and the first yeast scenario

1. `pnpm prototype:up`. Run the corn reference through the API; record price, IRR, the package's values beside them, seconds. Rerun the cornstover benchmark; unchanged.
2. Bind `sc-yeast-1` over thread Q: record each input's source (count and range, or waiting). Type nothing; a run that waits for assumptions is owed to Sean with the inputs listed. If every process input binds and only the two economic assumptions wait, record that exactly.
3. Ask Postdoc, twice: *What does the dry-grind corn ethanol reference plant give for its ethanol price, and what does the glucose-to-ethanol scenario still wait for?* and *What is the density and boiling point of the beer at the titre thread Q reports for CEN.PK113-7D?* Record claims kept and dropped, cost. `pnpm data:push`.

**Commit:** `OF-BLD-019 §7.1: the reference plants run, the yeast scenario bound, two questions answered`

## §7.2 Run sheet, §7.R, §7.T

`docs/DEMO.md` gains a Proforma section: the five things a person does (new scenario, inputs, run, read, compare), what the reference runs showed, the two questions, and "Steer around" current. §7.R over the branch diff (four lenses; refuters; every confirmed finding fixed test-first). §7.T: README (Proforma's section rewritten: the shelf, the three flowsheets, what is `model` and what is `computed`; the module table says pureOS reads BioSTEAM), COMPONENTS, CLAUDE (a *Proforma on BioSTEAM* section replacing the Phase 8 bullets: the shelf, one artifact per run, D3, D4, D8, the bridges, the tools), TOOLS, STATE; `pnpm shots --prefix of-bld-019` for `/proforma`, `/proforma/scenario/sc-yeast-1`, `/proforma/reference/corn_drygrind`, `/pureos/train/sc-yeast-1`; verify; push; PR with the STATE entries.
**Commits:** `OF-BLD-019 §7.2: the run sheet's Proforma section` · `OF-BLD-019 §7.R: …` · `OF-BLD-019 §7.T: say true things about Proforma on BioSTEAM, everywhere the repository speaks`

---

# PART F — ORDER OF WORK

| Phase | Steps | Estimate |
|---|---|---|
| 1 | §1.1 §1.2 | 45 min |
| 2 | §2.1 §2.2 §2.3 §2.R §2.T | 2 h 15 |
| 3 | §3.1 §3.2 §3.3 §3.R §3.T | 2 h 30 |
| 4 | §4.1 §4.2 §4.R §4.T | 1 h 30 |
| 5 | §5.1 §5.2 §5.R §5.T | 45 min |
| 6 | §6.1 §6.R §6.T | 45 min |
| 7 | §7.1 §7.2 §7.R §7.T | 1 h |

About nine and a half hours against nine on the clock. Phase 7 runs whatever state the others are in; Phase 6 is the first to drop, then §4.2.

---

# APPENDIX 1 — Sean's part, after the pull request

On the Mini, in Terminal, in the openferment folder, after merging:

```
bash scripts/host/deploy.sh --keep-decisions
pnpm data:pull
sudo launchctl kickstart -k system/com.umutuzo.openferment
pnpm ready
brew install graphviz      # once; the flowsheet diagram draws after it
```

Then in the app: Proforma → the corn reference card → **Run** (a minute or two the first time; the worker stays warm after). Proforma → **New scenario** → Glucose to ethanol → name it → open it; the inputs table shows what bound to thread Q; type the two economic assumptions (glucose price, plant scale) under your reviewer name with what each rests on; **Run**. pureOS → Train shows the same run's recovery per unit.

---

# APPENDIX 2 — Spend

Two Postdoc questions twice and fixture regeneration: under 0.20 USD. BioSTEAM runs cost nothing but time (the corn plant loads in about a minute cold).

---

# APPENDIX 3 — What this document leaves to OF-BLD-018

fermOS's own kinetics (Monod, inhibition, the ODE fit), the anchored protocol and the runbook path, Intake on Docling, Dominion on PatentsView, memote, the passphrase. OF-BLD-018 night one is reissued after this merges, without its Phase 1.
