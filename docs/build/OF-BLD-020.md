# openFerment — fermOS and pureOS on BioSTEAM

**Document:** OF-BLD-020 · **Version:** 1.0 · **Date:** 20 October 2026, 21:30 New York
**Repo:** `bytesizedyogurt/openFermentUI` · **start from** `main` @ `1a92325` (PR #12, OF-BLD-019, merged 2026-10-20 16:45 New York)
**Work branch:** `claude/of-bld-020-vessel-train`
**Builds on:** OF-BLD-019 (the shelf, one artifact per run, `pureos.train_of`, `thermo_props`, the fermOS-fit-to-scenario bridge, the ceiling check, `run_flowsheet` and `stream_table`), OF-BLD-014 Phase 7 (fits and forecasts), OF-BLD-015 Phase 7 (tools and gates), OF-BLD-016 (programs). Replaces OF-BLD-018 Phase 2; OF-BLD-018's other phases (the protocol and runbook, Intake, Dominion, memote, the passphrase) follow it.
**Executor:** Claude Opus 5.5 in Claude Code at extra-high effort, two unattended nights.
**Goal in one line:** fermOS simulates, fits and sizes the vessel, and pureOS builds, runs and reads the train, both on BioSTEAM and thermosteam with scipy underneath, both with a screen where a person can see and change every parameter and see where each number came from, both reachable by Postdoc and outside assistants through tools, and the two joined at the harvest stream so a vessel and a train together become a flowsheet Proforma prices.

---

## For Sean: what this builds, in plain words

Today fermOS fits a logistic curve to a deposited run and pureOS reads the stream table of a run Proforma priced. Both are honest and both are thin. BioSTEAM is already installed and already runs in a warm worker; what it has that neither module uses is a stirred-tank bioreactor designer with oxygen transfer, agitation power, cooling and batch scheduling, and forty-odd separation units with mass balances, utilities and costs. scipy has the integrator the kinetics need. The missing piece is the shape: model families with declared parameters, a unit catalogue with declared parameters, one panel that shows every parameter with its source and lets a person change it under their name, and tools so Postdoc can drive the same code with record ids and words.

After the two nights:

1. **One parameter panel for the whole platform.** Every model family, every unit type and every flowsheet declares its parameters in Python: key, a plain-words gloss of what the symbol means, dimension, unit, bounds with a reason, and the rule for where its value comes from. The browser renders them all with one component: value, interval, a slider inside the bounds, the source chip (fitted, record, artifact, assumption by a name, convention, library default), **Reset to source**, and **Why** (the gloss and the chain back to the source). A change you make becomes a named assumption kept in this browser and sent with the run; the run's basis names it; its provenance shows as such. Postdoc cannot type into it.
2. **fermOS simulates.** Model families: batch with Monod growth, product and substrate inhibition, Luedeking-Piret production and maintenance; fed-batch with a feed profile; chemostat; two-phase storage product (the PHA shape, archived with its program); light-limited as a named socket. A simulation takes its parameters from thread Q records through the same aggregate gate Proforma uses, from a fit, from a kept artifact, or from your assumptions, and is a kept artifact whose provenance follows its inputs. Fits stay as they are: measurements only. The time course draws under the figure grammar beside the geneOS ceiling.
3. **fermOS sizes the vessel on BioSTEAM.** From a simulation or a fit: batch time, titre, yield, the oxygen demand over the batch. BioSTEAM's `AeratedBioreactor` (aerobic) or NREL batch bioreactor (anaerobic) gives the number of vessels, their volume, working volume, agitator power, the kLa the vessel reaches by a named correlation against the kLa the culture needs, compressor and cooling duties, cycle time and installed cost. Every design parameter is in the panel: vessel limit, working fraction, cleaning time, aspect ratio, power per volume, kLa method, gas flow, dissolved oxygen setpoint, temperature, pressure, material.
4. **pureOS builds the train.** A catalogue of unit types, each a BioSTEAM class with its own parameters (solids centrifuge, pressure and rotary vacuum filters, clarifier, flash, binary and shortcut distillation, molecular sieve, multi-effect evaporator, mixer-settler extraction, adsorption column, spray and drum dryers, batch crystalliser, heat exchanger, storage and mix tanks, pump) plus three in-house units BioSTEAM lacks (ultrafiltration and diafiltration, cell disruption, a chromatography step with declared recovery and purity until CADET arrives). The Builder takes an inlet (a simulation's harvest broth, a run's stream, or typed under your name), lets you add units in order and set each unit's parameters in the panel, runs the train in the worker, and shows the stream table, recovery per unit, purity per stream, utilities, unit costs and the diagram.
5. **The seam.** A simulation's end state is the harvest stream; a vessel design plus a train is a flowsheet on the shelf; Proforma prices it with the same TEA the shelf flowsheets use. One run, three readers.
6. **Postdoc and outside assistants** get `fermos_simulate`, `fermos_vessel`, `pureos_build` and `pureos_propose`; the existing `run_flowsheet`, `stream_table`, `thermo_props`, `growth_forecast`, `pureos_train` and the reads keep working; the MCP server offers them all.

Appendix 1 is what you do in the morning. Appendix 2 is the full parameter list, so you can check nothing you wanted in hand is missing.

---

# PART A — HOW TO EXECUTE

OF-BLD-014 Part A applies in full, with: id prefix `OF-BLD-020`; the document at `docs/build/OF-BLD-020.md`; unattended, Part D defaults, the deletion stop; the 10:30 UTC clock; 2.00 USD per night; verify green and pushed before every commit.

**A worker run is a test.** Every model family has an offline test (scipy only) that integrates a synthetic case mass-balanced within 0.1 %. Every vessel design and every catalogue unit has a `sim` test that builds it in the real worker on stand-in inputs marked `assumption` and checks it converges; `test:sim` runs in verify. A unit that does not converge on its own defaults does not enter the catalogue.

**Night two** starts from `main` after Sean's merge on `claude/of-bld-020-vessel-train-2`, reads the night-one STATE section, and resumes at the first step id missing from the log.

---

# PART B — MEASURED STATE

Measured 20 October 2026, 21:00 New York, on `main` @ `1a92325` and the installed BioSTEAM 2.54.0 source. A.2 step 5 applies: confirm each row before building on it; a false row stops the session and the tree wins.

## B.1 fermOS today

- `core/openferment_core/fermos.py` (688 lines): `growth_fit` (OLS over the best window of four or more readings), `logistic` (closed form), `kinetic_fit` (`least_squares` over logistic growth, Luedeking–Piret, substrate balance, two weighted passes, intervals from the covariance and Student's t, μ and Xmax `identified` when the interval excludes zero), `fit` (artifacts `growth_fit`, `kinetic_fit`, source `deposition`), `forecast` (200 seeded draws, ends when the median sugar runs out), `forecast_run`, `unidentified`, `check_forecastable`, `fit_of`, `forecast_for`, `to_run_out`. No ODE integration; no Monod term; no inhibition term; no feed; no oxygen.
- `tools/fermos.py`: `growth_forecast` (strict). `fermos_read` and `fermos_write` from OF-BLD-015 (`forecast_run` is the one write action).
- `src/screens/FermOS.tsx` (357 lines; tabs Fits, Forecast; the Properties panel from OF-BLD-019 §4.2 keyed by a titre record), `FermOSForecast.tsx` (195). **The header states: "No parameter from a paper enters fermOS"** (OF-BLD-011 D6, OF-BLD-014 §3). This document amends it (D1).
- `src/data/subsystems.ts`: `fermos.kinetics` live; `fermos.transport`, `fermos.mode`, `fermos.scale`, `fermos.control` are stubs, `UNBUILT`.
- Durable (OF-BLD-019 D6): `createdScenarios`, `scenarioRuns`, `pinnedScenarios`, `proformaAssumptions` (`Record<scenarioId, InputAssumption[]>`; `InputAssumption` = key, value, low, high, by, at, note), `proformaFits`. The browser's own fits are sent with each fit request; the service keeps the fit artifacts.

## B.2 pureOS today

- `core/openferment_core/pureos.py` (387 lines): `train_of(artifact)` reads one `proforma.run` artifact through `proforma.tables_of`: units in run order, inlets and outlets, product mass in and out, recovery per unit and cumulative, overall; `GET /api/pureos/trains`, `GET /api/pureos/train/{key}`; `pureos_train` read tool; `TrainUnit`, `Train`, `TrainSummary` in `PAIRS`.
- `src/screens/PureOS.tsx` (337), `PureOSTrain.tsx` (390; recovery by pass, the Properties panel keyed by a stream), `src/components/figures/RecoveryByUnit.tsx`.
- `src/data/vocabulary.ts`: `UNIT_OPERATIONS` (27 entries: centrifugation, microfiltration, depth-filtration, homogenisation, bead-mill, uf-df, nanofiltration, electrodialysis, iex, hic, imac, affinity-custom, sec, mixed-mode, heat-step, refolding, protease-cleavage, crystallisation, precipitation, lle, distillation, spray-dry, lyophilisation, granulation, sterile-filtration, endotoxin-removal, nuclease-clearance; OF-BLD-019 §4.1 added `molecular-sieve` and `biosteamClasses` on the entries that map). `pureos.harvest`, `pureos.capture`, `pureos.polish`, `pureos.recovery` are stubs.
- Nothing in pureOS builds or runs a unit; it reads what Proforma ran.

## B.3 Proforma and the worker (OF-BLD-019)

- `flowsheets/shelf.py` (358): `FlowsheetInfo` (id, title, description, source, program, reference, inputs: `FlowsheetInput` (key, name, dimension, unit, fields, kind process|economic|convention, note), outputs, priceOutput, priceBasis, leavesOut, gridInputs, regression), `SHELF` = cornstover_benchmark, corn_drygrind, ethanol_glucose_v0, pha_sugar_v0; `toy` test-only.
- `flowsheets/ethanol_glucose_v0.py` (289): `Fermenter(bst.BatchBioreactor)` running Glucose → 2 Ethanol + 2 CO₂ at the bound yield over the theoretical (0.51143 g g⁻¹ computed from thermosteam's molecular weights), `tau` = titre / productivity, `V_wf` 0.9 (BioSTEAM's), `V_max` 3,785 m³ (`bst.AnaerobicBioreactor.V_max_default`), then `biorefineries.ethanol.create_ethanol_purification_system`; TEA from `biorefineries.corn.create_tea`. No number in the file but 0 and 1 (an AST test holds it).
- `proforma.py` (1,795): `bind_inputs` (shelf-driven; aggregate gate; carbon source; `units.py`), `run` (one `proforma.run` artifact: price, TEA breakdown, Spearman, stream table, unit table, utilities, diagram), `tables_of`, `fit_info` / `apply_fits` (a `kinetic_fit` or `growth_forecast` feeds titre, yield, productivity as source `artifact`), `ceiling_check`, `GET /api/proforma/shelf`, `/scenarios`, `/bind`, `/run`, `/runs`, `/reference/{id}`, `GET /api/fermos/fits`.
- `workers/proforma_worker.py` (775): ops `run`, `evaluate`, `grid`, `montecarlo`, `benchmark`, `reference`, `thermo_props`; `stream_table`, `unit_table`, `utility_duties`, `tea_breakdown`, `diagram` (Graphviz's `dot` absent in the cloud: the ordered list fallback), `package_defaults()`; thermosteam chemicals cached per set.
- `ProformaScenario.tsx` (1,666): the inputs table (binding records | assumption | artifact | waiting; value, low, high, sampling, source, records with count and range), **Keep assumption** (value, low, high, what it rests on, under the reviewer name), **Use a fermOS fit**, Run, the run's sections from one artifact, the ceiling check. This is the pattern Phase 2 generalises.
- Tools: thirty-two names in `WHITELIST` (the seven, the twenty-two module reads and writes, `thermo_props`, `run_flowsheet`, `stream_table`); `test_tools.NAMES` is the one literal list; `test_mcp` counts thirty-four (the registry's plus `ask_postdoc` and `get_artifact`); `check:tools` green and holds rule 2b (no tool file but `writes.py` reaches what keeps a Proforma run or writes an audit line).
- Live on 2026-10-20: corn reference 0.4855 USD kg⁻¹, 11 of 11 package values within 5 %; `sc-yeast-1` bound over thread Q: feed glucose 4 records, titre 9, yield 18; productivity waits (its 14 records name no carbon source); plant scale and glucose price wait for a named person.

## B.4 What BioSTEAM 2.54.0 ships for this document (read from its source)

- `AeratedBioreactor(AbstractStirredTankReactor)`: parameters `theta_O2` (dissolved oxygen as a fraction of saturation), `Q_O2_consumption` (the oxygen demand the reaction sets), `optimize_power`, `design`, `method` (kLa correlation: `'Riet'` for stirred tanks, `'Dewes'` for bubble columns; `kLa_methods` in `design_tools/aeration.py` also registers Labik, Deshpande, DeJesus, Akita–Yoshida), `kLa_kwargs`, `cooler_pressure_drop`, `compressor_isentropic_efficiency`, `tau`, `T`, `P`, `V_wf`, `length_to_diameter`, `V_max`, `vessel_material`, `vessel_type`, `batch`, `tau_0` (3 h default), `N`, `heat_exchanger_configuration`, `dT_hx_loop`, `jacket_annular_diameter`, `loading_time`; from the base class `kW_per_m3`, `N_vessels`. Design items include reactor volume, agitator power, compressor power, cooling duty.
- `NRELAnaerobicBatchBioreactor` (aliases `BatchBioreactor`, `Fermentation`): `tau`, `N`, `V`, `T` (305.15 K), `P` (101325 Pa), `Nmin` 2, `Nmax` 36, `loading_time`; attributes `tau_0` 3 h, `V_wf` 0.9; design items reactor volume, cycle time, batch time, loading time, total dead time, reactor duty, recirculation flow; NREL batch tank cost with the 6/10 exponent.
- `design_tools/aeration.py`: `kLa_stirred_Riet(P, V, U, coefficients)`, `kla_bubcol_Deshpande`, `kla_bubcol_DeJesus`, `kla_bubcol_Akita_Yoshida`, `C_O2_L(T, P_O2)` (oxygen solubility by Henry), `Henrys_law_constant`, diffusion coefficients (Hayduk–Laudie, Wilke–Chang).
- Separation units: `SolidsCentrifuge`, `RotaryVacuumFilter`, `PressureFilter`, `ScrewPress`, `Clarifier`, `Flash`, `SplitFlash`, `BinaryDistillation`, `ShortcutColumn`, `MESHDistillation`, `MolecularSieve`, `MultiEffectEvaporator`, `Evaporator`, `LiquidsSplitCentrifuge`, `LLECentrifuge`, `MixerSettler`, `MultiStageMixerSettlers`, `SingleComponentAdsorptionColumn`, `SprayDryer`, `DrumDryer`, `BatchCrystallizer`, `HXutility`, `StorageTank`, `MixTank`, `Mixer`, `Splitter`, `Pump`, `EnzymeTreatment`, `HammerMill`. Each has documented parameters in its class docstring; §5.1 reads them.
- thermosteam 0.54.2: `Stream` with `rho`, `Cp`, `mu`, `bubble_point_at_P`, `dew_point_at_P`, `Hf` (heat of formation, for heat of fermentation), chemicals by name; `Reaction` with stoichiometry and conversion.

## B.5 Guards that matter

`check:plan` (`PAIRS`), `check:seed` (programs, E.3′ strings, `example`, reserved segments), `check:reference`, `check:figures` (every new chart through the grammar with `toTable`), `check:tools` (`ALLOWED_WRITES`, a read and a write per module), `check:store` (141 checks; Durable round-trips), `test:sim` (in verify), `test:slow`, the smoke (72 routes, twelve flows), golden path (34 steps), `test_workers` (`biosteam` imported in the worker and `flowsheets/` alone).

---

# PART C — WHAT IS TRUE WHEN THE DOCUMENT IS DONE

1. `core/openferment_core/params.py` declares `ParameterSpec` and `ParameterValue`; every model family, vessel design, catalogue unit and shelf flowsheet exposes its parameters as a list of them; `GET /api/params/{scope}` serves any scope's specs with its current values and sources; `src/components/ParameterPanel.tsx` renders every scope the same way; a person's change is an `Override` in the Durable tier under their reviewer name, sent with the run, named in the artifact's basis as an `assumption`, and shown with that provenance everywhere the result shows. A model never sets one.
2. `core/openferment_core/kinetics.py` holds the model family registry: `batch_v1`, `fedbatch_v1`, `chemostat_v1`, `storage_v1`, and the named socket `light_v1`; each integrates on `solve_ivp`, fits on `least_squares`, declares its parameters, states and the records that can bind each parameter; `fermos.simulate` makes a `fermos.simulation` artifact from records, a fit, an artifact or assumptions, provenance by `basis_provenance`; `fermos.fit` takes a deposition's series and a family and keeps a `kinetic_fit` as today, with `model` naming the family; the logistic fit stays as `logistic_v0` for what is kept.
3. fermOS → Simulate (`/fermos/simulate`) and fermOS → Vessel (`/fermos/vessel`) exist with the panel; the time course draws under the grammar with the ceiling as a rule; a simulation can be sent to Proforma as a scenario input (the §5.1 bridge, now over simulations too), fitted to a deposition, or used to design a vessel.
4. `fermos.vessel` designs a vessel in the BioSTEAM worker from a simulation or a fit: `AeratedBioreactor` or `NRELAnaerobicBatchBioreactor` by the family's oxygen demand; outputs N vessels, volume, working volume, batch and cycle times, agitator power, compressor power, cooling duty, kLa achieved by the named method against kLa needed over the batch, installed cost, and the oxygen balance over time (OTR against OUR); every design parameter in the panel; a `fermos.vessel` artifact.
5. `core/openferment_core/pureos/catalogue.py` declares the unit catalogue (Appendix 2 §B), each entry a BioSTEAM class or an in-house `bst.Unit` subclass with its parameters as `ParameterSpec`s and their source rules; `pureos/train.py` holds the train model (inlet, ordered units, connections, side streams) and `build_system` in the worker; `pureos.run_train` makes a `pureos.train_run` artifact with the stream table, unit table, recovery per unit (through `train_of`), purity per stream, utilities, costs and diagram.
6. pureOS → Builder (`/pureos/build/:trainId`) exists: inlet chooser, the palette by stage, ordered steps each with the panel, side-stream routing, Run, every table, diagram or the ordered list, CSV, Save, **Price this in Proforma**.
7. The shelf gains `custom_train_v1`: a fermenter from a `fermos.vessel` artifact and a train from a `pureos.train_run`, priced by the TEA the shelf flowsheets use with its financial assumptions in the panel; a scenario on it runs through `proforma.run` and is read by Proforma, pureOS and fermOS alike.
8. `pureos.propose(product, host, inlet)` proposes a train by rules that each name their basis (secreted or intracellular, product class, volatility from thermosteam, molecular weight and isoelectric point from Biopython ProtParam for a protein); the proposal opens in the Builder; nothing in it carries a number the rules did not read from a property.
9. The registry holds `fermos_simulate`, `fermos_vessel` (writes through `fermos_write`, free, audited), `pureos_build` (write, free: new, add_unit, remove_unit, set_from_record, run, propose), `pureos_propose` (read); `test_tools.NAMES` gains them; `check:tools` green with rule 2b extended to the new artifact kinds; `test_mcp`'s count follows `WHITELIST`; Postdoc's prompt says a simulation, a vessel and a train are cited by artifact id and their numbers read from the artifact.
10. `docs/DEMO.md` has fermOS and pureOS sections with what a person does and what each live run showed; README, COMPONENTS, CLAUDE (a *fermOS simulates and sizes the vessel* section, a *pureOS builds the train* section, the amended rule), TOOLS, STATE true for the tree; one PR per night.

---

# PART D — DECISIONS

- **D1 — The fermOS rule, amended.** A *fit* takes only a deposition's measured series (as today, provenance `measured` under it). A *simulation* may take its parameters from records through the aggregate gate (provenance `unverified` or better as the records carry), from a fit or forecast artifact (`computed`), from a kept simulation, from a named person's assumption (`demo`) or a stated convention; its provenance is `basis_provenance` over all of them, so a simulation from unverified records shows as unverified and one with any assumption as demo. The `FermOS.tsx` header and `CLAUDE.md`'s "fermOS computes from depositions: no parameter from a paper enters it" are rewritten to say this. A simulation never pretends to be a measurement: its figure line is a computed curve, its card says what it was built from.
- **D2 — One parameter panel, declared in Python.** `ParameterSpec`: `key`, `label`, `symbol` (as written in the equations, plain Unicode), `gloss` (what the symbol means, in words, for the panel's Why), `dimension` (a `units.ts` family or a word), `unit`, `min`, `max`, `step`, `scale` (`linear` | `log`), `group`, `sourceRule` (an ordered list of where a value comes from: `fit`, record field ids, `artifact`, `assumption`, `convention`, `library-default`), `note`, `boundsReason`. `ParameterValue`: `key`, `value`, `low`, `high`, `source` (`BasisSource`), `identified` (null when not a fit), `overriddenBy` (a name, or null), `libraryDefault` (the BioSTEAM default read from its code, or null). Mirrored in `types.ts`, in `PAIRS`. A screen never hand-writes a form for a parameter.
- **D3 — An override is a named assumption, kept in the browser, sent with the run.** `Override` = `scope`, `key`, `value`, `low`, `high`, `by`, `at`, `note`; `parameterOverrides: Record<scope, Override[]>` in the Durable tier (`proformaAssumptions` migrates into it under scope `proforma:<scenarioId>` with a one-time read of the old field; `check:store` round-trips both). A run request carries the overrides for its scope; the service merges them as `assumption` inputs with the person's name; the basis names each; `basis_provenance` makes the artifact `demo`. **Reset to source** removes the override. The service keeps no override: a run made from a browser carries that browser's.
- **D4 — Bounds are conventions.** Every `ParameterSpec.min`/`max` is a selection convention with `boundsReason` written (a physical limit, an ontology plausibility range, or the library's own validity range) and a `check:seed` test that every spec has one. A person may type outside the slider's bounds; the panel warns and the basis records it.
- **D5 — Model families are code, written once, with their equations in the module docstring** in plain Unicode. `batch_v1`: dX/dt = μ·X − kd·X; μ = μmax · S/(Ks + S) · 1/(1 + S/Ki) · (1 − P/Pmax)ⁿ; dP/dt = (α·μ + β)·X; dS/dt = −(1/Yxs)·μ·X − (1/Yps)·dP/dt − m·X; states X, S, P; optional kd, Ki, m (zero when absent, said so). `fedbatch_v1`: adds V with dV/dt = F(t), feed concentration Sf, profile `constant` | `exponential` (set μ_set, F = μ_set·X·V/(Yxs·(Sf − S))) | `steps` (a table), dilution terms on every state. `chemostat_v1`: dilution D on every state, feed Sf, steady state solved and the dynamic path integrated; washout reported when D ≥ μmax·Sf/(Ks + Sf). `storage_v1`: a second substrate N with its own Monod term limiting growth, a storage product Q accumulating when N is exhausted at rate qQ,max·S/(Ks+S)·(1 − Q/Qmax); the PHA and lipid shape, program-archived with PHA but general. `light_v1`: declared with its parameters (incident irradiance, path length, attenuation coefficient, photoinhibition constant) and no `rhs`: a socket that refuses to run in words. Oxygen for every family: a specific oxygen uptake qO2 = μ/Yxo + mo (parameters Yxo, mo; zero and said so for anaerobic families), so OUR(t) = qO2·X exists for the vessel design; DO is not a state in night one (the vessel design checks OTR against OUR after the fact; a DO-limited integration is D-later).
- **D6 — Parameter sources for a simulation, in order.** A fit artifact chosen by the person; records through the aggregate gate by field (Appendix 2 §A names the field for each parameter); a kept simulation; an assumption; a convention. A parameter with none refuses the run naming it (as Proforma's 422 does). Initial conditions X0, S0, P0 (and V0, N0) come from a deposition's first readings when fitting, from `medium_component_conc` records on glucose (there is no `glucose_initial_conc` field) or assumptions when simulating.
- **D7 — The vessel is BioSTEAM's.** Aerobic families (any with Yxo set) design an `AeratedBioreactor`; anaerobic ones an `NRELAnaerobicBatchBioreactor`. The oxygen demand passed is the peak OUR over the simulated batch (and the time course kept for the balance plot); `theta_O2` is the DO setpoint; the kLa method defaults to `'Riet'` for a stirred tank and `'Dewes'` for a bubble column (`vessel_type` in the panel chooses); the vessel's installed cost comes from BioSTEAM's own correlations with the CEPCI it uses, named. Heat duty: BioSTEAM's reactor duty from the reaction's enthalpy on thermosteam's `Hf`; the panel shows it beside a Cooney-style estimate from OUR as a cross-check labelled a convention.
- **D8 — The catalogue copies BioSTEAM.** Each catalogue entry names its BioSTEAM class, lists that class's documented parameters with BioSTEAM's defaults read from the code at import (`inspect.signature` and class attributes; never retyped), and adds the source rule for each (a record field where the ontology has one, else `assumption` or `library-default`). The three in-house units are `bst.Unit` subclasses with `_run` as a split and `_design`/`_cost` left to BioSTEAM's `Unit` defaults (no cost) until a correlation with a source is added; the panel says *no cost model* on them.
- **D9 — A train is data.** `TrainSpec`: `id`, `name`, `program`, `product` (a catalogue product id), `inlet` (`{kind: 'simulation' | 'run-stream' | 'typed', ref, streamId}`), `units: [{id, type, params: Override-shaped values by key, outlets: {name: 'onward' | 'waste' | 'recycle:<unitId>'}}]`. The worker builds `bst.System` from it: a linear chain by default, side outlets to waste streams named by the unit, recycles allowed only backward to a named unit (the worker refuses a forward recycle). Trains made in the browser live in the Durable tier (`trainsMade`) and are sent whole with a run, like scenarios; the service keeps the runs.
- **D10 — The harvest stream.** A simulation's end state at harvest (the hour the median sugar runs out, or a time the person sets) gives biomass X, product P, residual substrate S and water as a `tmo.Stream` on the flowsheet's chemicals (Yeast, Ethanol, Glucose, Water for the yeast program; a product chemical the catalogue names otherwise); by-products the family does not model are absent and the basis says so. A typed inlet is a named assumption per component.
- **D11 — `custom_train_v1` on the shelf** is a flowsheet whose fermenter is built from a `fermos.vessel` artifact (its unit parameters) fed by the scenario's bound titre, yield and batch time, followed by a `pureos.train_run`'s units, priced with `biorefineries.corn.create_tea`'s `ConventionalEthanolTEA` for the yeast program and BioSTEAM's `TEA` with named financial assumptions for any other product; its inputs are the union of the vessel's, the train's and the economic ones; one `proforma.run` artifact; `pureos.train_of` reads it as any run.
- **D12 — The proposer's rules are written, each with its basis**, in `pureos/propose.py`: product class (small molecule volatile → flash or distillation then dehydration if an azeotrope exists by thermosteam; small molecule non-volatile → extraction or crystallisation; protein secreted → clarify, concentrate by UF, capture by the chromatography placeholder keyed on pI and MW, polish, formulate; protein intracellular → harvest by centrifuge, disrupt, clarify, then as secreted; polymer intracellular → harvest, digest or extract, wash, dry), and the properties it reads (volatility and azeotrope from `thermo_props`, MW and pI from ProtParam on a sequence the product entry carries, else the proposer says which property is missing). A proposal is a `TrainSpec` with every parameter at its library default or assumption-pending, never a number of its own.
- **D13 — Tools carry ids and words.** `fermos_simulate(family, strain, product, recordsByParam: {key: [record ids]}, fitArtifact, startFrom: 'records' | 'fit' | 'simulation:<id>', durationPreset: 'until-sugar-runs-out' | 'fit-length')`; `fermos_vessel(simulationArtifact | fitArtifact, vesselType: 'stirred-tank' | 'bubble-column', klaMethod)`; `pureos_build(action, trainId, unitType, afterUnitId, product, inletRef, recordsByParam)`; `pureos_propose(product, host, inletRef)`. A number anywhere refuses the call as the registry already does. Every write is audited `agent: model`; none is gated (compute is free), recorded in `docs/TOOLS.md`.
- **D14 — Figures.** `TimeCourse.tsx` (states over time as computed curves; measured readings as filled points when a deposition is drawn against a simulation or fit; a forecast band; the ceiling as a rule on the yield panel; secondary axis for OUR), `OxygenBalance.tsx` (OTR and OUR over the batch, the limited interval shaded), `PurityByStream.tsx` (product mass fraction per stream along the path); `RecoveryByUnit` reused. All through the grammar with `toTable`; `check:figures` holds them.
- **D15 — Subsystems go live.** `fermos.mode` (families), `fermos.transport` (the oxygen balance), `fermos.scale` (the vessel design) become `live` with `implementedIn`; `fermos.control` stays a stub and says what would build it; `pureos.harvest`, `pureos.capture`, `pureos.polish`, `pureos.recovery` become `live` with the catalogue and the train.
- **D16 — Branching.** Night one on `claude/of-bld-020-vessel-train`, PR to `main`; night two on `claude/of-bld-020-vessel-train-2` from `main`, PR to `main`. The Mini runs `main`.

---

# PART E — CONTRACTS

OF-BLD-014 Part E, OF-BLD-015 Part A.3, OF-BLD-016 Part E and OF-BLD-019 Part E hold. Added:

- **E.1‴ A parameter is declared or it does not exist.** No screen renders a numeric control that is not a `ParameterSpec` served by the service; `check:seed` greps `src/screens/FermOS*.tsx`, `PureOS*.tsx`, `ProformaScenario.tsx` for `<input type="number"` and `<input type="range"` outside `ParameterPanel.tsx` and fails on any.
- **E.2‴ Every result is an artifact with a basis** naming the family or unit types, the library versions, every parameter with its source, every override by name, and (for a vessel or a train) the BioSTEAM unit ids.
- **E.3‴ BioSTEAM stays in the worker.** `biosteam` and `thermosteam` are imported in `workers/proforma_worker.py` and `flowsheets/` and `pureos/catalogue.py` (for class references, imported lazily inside functions the worker calls) alone; `test_workers` greps are extended to the new files. scipy is imported in `kinetics.py` and `fermos.py` alone among the service's modules (the worker may use it too).
- **E.4‴ A model's parameter is a source, never a value.** `check:tools` is extended: no tool input schema under `fermos_*` or `pureos_*` has a numeric field.

---

# NIGHT ONE

# PHASE 1 — Baseline

## §1.1 Branch, document, baseline

As OF-BLD-019 §1.1: branch from `main`, `session-start.sh`, `pnpm ready`, `pnpm data:pull` (record artifact counts: `proforma.run`, `proforma.reference`, `thermo_props`, `kinetic_fit`, `growth_forecast`), `pnpm verify`, Part B confirmed line by line (open each file; `python -c "import biosteam.units as u; print(u.AeratedBioreactor.__init__.__doc__ or u.AeratedBioreactor.__doc__)"` in the worker's venv; `which dot`), STATE heading `## OF-BLD-020 night one (branch claude/of-bld-020-vessel-train, from <hash>)`.
**Commit:** `OF-BLD-020 §1.1: the branch, the document, and the baseline measured`

---

# PHASE 2 — One parameter panel

## §2.1 `ParameterSpec`, `ParameterValue`, `Override`, and the endpoint

**Files:** `core/openferment_core/params.py` (new: the models of D2 and D3; `resolve(specs, sources, overrides, by)` → values with sources; `scope` naming `fermos:family:<id>`, `fermos:vessel:<simulation id>`, `pureos:unit:<train id>:<unit id>`, `proforma:<scenario id>`; `bounds_check`), `models.py` (`ParameterSpec`, `ParameterValue`, `Override`, `ParamScope`), `types.ts`, `check-plan.mjs`, `api.py` (`GET /api/params/{scope}` returns specs with current values and sources for a scope the service knows; `POST /api/params/{scope}/resolve` takes overrides and returns the resolved values and the basis inputs they would add, running nothing), `basis.py` (an `assumption` input from an `Override` carries `by` and `note`), `src/lib/durable.ts` and `src/store.ts` (`parameterOverrides` Durable; `proformaAssumptions` read once into scope `proforma:<id>` and kept until the next save writes the new field; `setOverride`, `clearOverride`, `overridesFor(scope)`), `check-store.ts` (round-trip; the migration), `core/tests/test_params.py` (new: resolution order per `sourceRule`; an override wins and is named; a value outside bounds is kept and flagged; a spec without `boundsReason` fails `check:seed` (negative-tested)).

**Commit:** `OF-BLD-020 §2.1: a parameter is declared once, resolved with its source, and a person's change is a named assumption`

## §2.2 `ParameterPanel.tsx`, and Proforma's inputs rendered through it

**Files:** `src/components/ParameterPanel.tsx` (new: one row per spec, grouped by `group`: label and symbol, the value (numeric input) and the slider inside `min..max` on `scale`, unit, interval when the source has one, the source chip (`fitted` · `record ×N low–high` with a link to the records · `artifact` with a link · `assumption by <name>` · `convention` · `library default`), **Reset to source**, **Why** (a popover: the gloss, the source chain, the bounds reason, the library default when one exists); typing creates or updates an `Override` under the reviewer name, disabled with *Set a reviewer name in Settings* when none; a value outside bounds shows the warning the service returns; keyboard and touch targets per `Deposition.tsx`'s constraints since the Builder may be used at the bench), `src/components/ParameterRow.tsx`, `src/screens/ProformaScenario.tsx` (the inputs table and **Keep assumption** become the panel over scope `proforma:<id>`; `ProformaRunRequest.assumptions` becomes `overrides` with a shim that accepts the old field for one release; the records chooser stays as the panel's record link), `src/lib/proforma.ts`, `smoke.mjs` (the scenario page's assumption flow rewritten against the panel: type, see the chip, run, see `assumption by` in the basis, reset), `service-double.mjs` (`/api/params/*` answered from fixtures `demo.py --prototype` writes).

**Commit:** `OF-BLD-020 §2.2: one panel renders every parameter with its source, and Proforma's inputs go through it`

## §2.R and §2.T

**Commits:** `OF-BLD-020 §2.R: …` · `OF-BLD-020 §2.T: README, COMPONENTS and STATE for the parameter panel`

---

# PHASE 3 — fermOS simulates

## §3.1 The model families

**Files:** `core/openferment_core/kinetics.py` (new: `FAMILIES` registry of D5; each family a class with `id`, `title`, `equations` (the docstring, plain Unicode), `states`, `specs: list[ParameterSpec]` (Appendix 2 §A), `rhs(t, y, p)`, `simulate(p, y0, t_end, dt)` on `solve_ivp` (`LSODA`, rtol 1e-6, mass balance checked after: carbon in substrate consumed against biomass, product and CO₂ by the yields, within 1 % or the result carries a flag), `fit(series, p0, fixed)` on `least_squares` from the logistic fit's estimate, intervals as `fermos.kinetic_fit` computes them, `identified` per parameter; `oxygen(p, traj)` → OUR(t); `harvest(traj, when)`), `fermos.py` (`simulate(request)` → `fermos.simulation` artifact: family, parameters with sources, start values with sources, the trajectory as series by state, OUR(t), the end state, the hour the median sugar runs out, a comparison of Yps against the stored ceiling for the strain's host model and sugar when one exists (read, never clamped); `fit` gains `family`, default `logistic_v0`; `batch_v1` fits need biomass or run with μ unidentified per OF-BLD-018 D4), `artifacts.py` (registration, version `kinetics <family> 1 · scipy <v>`), `models.py` (`SimulationRequest`, `SimulationResult`, `FamilyInfo`), `types.ts`, `check-plan.mjs`, `api.py` (`GET /api/fermos/families`, `GET /api/fermos/families/{id}` with specs, `POST /api/fermos/simulate`, `GET /api/fermos/simulations`), `core/tests/test_kinetics.py` (new: per family a synthetic case integrates mass-balanced within 0.1 %; glucose never negative; a product above Pmax never forms; `chemostat_v1` washes out at the predicted D; `storage_v1` accumulates only after N is exhausted; `light_v1` refuses in words; a fit of a synthetic `batch_v1` run recovers its parameters within 1 %; a product-and-substrate-only fit reports μ unidentified), `test_fermos.py`.

**Commit:** `OF-BLD-020 §3.1: fermOS's model families integrate on scipy, declare every parameter, and keep what they simulate`

## §3.2 Parameters from records, fits and assumptions

**Files:** `fermos.py` (`bind_parameters(family, strain, product, sugar, pool, overrides, fit, by)`: for each spec, the `sourceRule` in order: the chosen fit's parameter; records of the field ids in Appendix 2 §A on the strain (its aliases) and carbon source through `proforma`'s aggregate gate and `units.py` (reused, moved to a shared `binding.py` if the move is clean); a kept simulation; the override; the convention; `library-default`; a parameter with none → 422 naming it and the field that would bind it; start values the same way), `binding.py` (new, when the move happens; `proforma.py` imports it), `api.py` (`GET /api/fermos/bind?family=&strain=&product=&sugar=&fit=` → `ParameterValue`s and what waits, starting no integration), `core/tests/test_fermos_bind.py` (a stand-in pool binds μmax and Ks from records, Yps from a fit, Pmax waits; an override replaces a record and the basis names the person).

**Commit:** `OF-BLD-020 §3.2: a simulation's parameters come from a fit, the records, a kept artifact or a named person, in that order, each named`

## §3.3 fermOS → Simulate

**Files:** `src/screens/FermOSSimulate.tsx` (new, `/fermos/simulate`: family chooser with each family's equations shown in plain Unicode and a one-line what-it-is; strain, product, sugar choosers (active program); **Start from**: records | a fit (list from `/api/fermos/fits`) | a kept simulation; the panel over scope `fermos:family:<id>` in groups *Growth*, *Product*, *Substrate*, *Inhibition*, *Oxygen*, *Feed* (fed-batch), *Dilution* (chemostat), *Storage* (storage), *Start values*, *Run length*; **Simulate**; the result: `TimeCourse` (X, S, P, V where it varies, OUR on the secondary axis), the end state card (final titre, yield achieved, productivity, hour the sugar runs out), the ceiling card (Yps against the model ceiling, flagged when above), the parameter table with sources and intervals, the basis; **Fit this family to a deposition** (opens Fits with the family chosen), **Design the vessel** (→ `/fermos/vessel?simulation=`), **Send to Proforma** (the §5.1 bridge: `fit_info` extended to read a simulation), CSV), `src/components/figures/TimeCourse.tsx` (D14), `FermOS.tsx` (header rewritten per D1; the Fits tab gains a family chooser for the fit), `FermOSForecast.tsx` (a forecast from a `batch_v1` fit as from a logistic one), `nav.ts` (`simulate` and `vessel` reserved under fermOS; `SUB_VIEWS`), `tabs.ts` (Fits, Simulate, Vessel, Forecast), `App.tsx`, `components.ts`, `COMPONENTS.md`, `subsystems.ts` (D15: `fermos.mode` live), `src/lib/fermos.ts`, `check-figures.ts`, `smoke.mjs` (simulate against the double; the panel's override flow; the ceiling card), `service-double.mjs`, `demo.py --prototype` (fixtures: families, bind, a simulation run by the real `kinetics.py`, which needs no BioSTEAM).

**Commit:** `OF-BLD-020 §3.3: fermOS simulates a run from its sources, draws it against the ceiling, and hands it on`

## §3.4 `fermos_simulate`, and the reads

**Files:** `tools/fermos.py` (`fermos_simulate` per D13, loose; `fermos_read` rows gain `simulation` kind with family, strain, final titre and yield as words-free detail and the artifact ref), `tools/writes.py` (`fermos_write` action `simulate` → `fermos.simulate` under `ALLOWED_WRITES`; `check:tools` rule 2b extended so that only `writes.py` reaches what keeps a `fermos.simulation`, `fermos.vessel` or `pureos.train_run` artifact), `tools/__init__.py`, `validate.py` (`SeenSet` learns `fermos.simulation` ids; a claim about a simulated titre cites the artifact), `postdoc_agent.py` (prompt: a simulation's numbers are read from its artifact; a model never states them), `docs/TOOLS.md`, `test_tools.py`, `test_module_tools.py`, `test_mcp.py` (count), `test_postdoc_agent.py` (a stand-in run asks for a simulation and cites it).

**Commit:** `OF-BLD-020 §3.4: Postdoc simulates a run from record ids and a family name, and cites the artifact`

## §3.5 LIVE — a batch from thread Q

1. `pnpm prototype:up`. `GET /api/fermos/bind?family=batch_v1&strain=s-cerevisiae-cenpk113-7d&product=ethanol&sugar=glucose`: record which parameters bound (count, range, mode), which wait. Simulate what binds with the rest at convention or library default where the spec allows, else record the waiting list and owe the run to Sean with the parameters named; type nothing.
2. If it runs: record final titre, yield, productivity, the ceiling comparison, seconds. `pnpm data:push`.
3. Ask Postdoc twice: *Simulate a glucose batch for CEN.PK113-7D from the extracted kinetics and compare the predicted yield with the Yeast9 ceiling.* Record claims kept and dropped, cost.

**Commit:** `OF-BLD-020 §3.5: a batch simulated from thread Q's own numbers` (` (run owed)` when a parameter waits)

## §3.R and §3.T

**Commits:** `OF-BLD-020 §3.R: …` · `OF-BLD-020 §3.T: README, COMPONENTS and STATE for fermOS simulating`

---

# PHASE 4 — fermOS sizes the vessel on BioSTEAM

## §4.1 The vessel design in the worker

**Files:** `workers/proforma_worker.py` (op `vessel_design(spec)`: builds `AeratedBioreactor` or `NRELAnaerobicBatchBioreactor` on the flowsheet's chemicals with the parameters of Appendix 2 §C, a feed stream from the simulation's start state scaled to `plant_scale` or `batch_volume` (one of the two is a required source), the reaction from the family's yields at the simulated conversion, `tau` from the simulation's harvest hour, `Q_O2_consumption` from peak OUR, runs `simulate()`, reads design and cost: N, V per vessel, working volume, cycle time, loading and dead time, agitator power, compressor power, cooling duty, kLa achieved (BioSTEAM's `kLa` by the named method) and the superficial gas velocity it assumed, purchase and installed cost, the CEPCI year; then the oxygen balance over the batch: OTR = kLa·(C* − C_L) with C* from `C_O2_L` at T and the gas's oxygen partial pressure, C_L = θ·C*, against OUR(t); the interval where OUR exceeds OTR, if any), `core/openferment_core/vessel.py` (new: `VesselRequest`, `VesselDesign`, `design(request)` → `fermos.vessel` artifact with every parameter and its source, the design table, the oxygen balance series, the basis naming biosteam and thermosteam versions and the correlation; `specs()` for scope `fermos:vessel:<simulation id>` reading BioSTEAM's defaults from the classes at import inside the worker and served through the worker to keep E.3‴), `artifacts.py`, `models.py`, `types.ts`, `check-plan.mjs`, `api.py` (`GET /api/fermos/vessel/specs?simulation=`, `POST /api/fermos/vessel`, `GET /api/fermos/vessels`), `core/tests/test_vessel.py` (`sim`: an aerobic stand-in simulation designs an aerated vessel that converges, N within `Nmin..Nmax`, kLa achieved a positive number by `'Riet'`, the oxygen balance names a limited interval when OUR is set above OTR; an anaerobic one designs the NREL vessel with no compressor; a `plant_scale` and `batch_volume` both missing refuses in words).

**Commit:** `OF-BLD-020 §4.1: BioSTEAM sizes the vessel a simulation needs, and the oxygen balance says where it is short`

## §4.2 fermOS → Vessel, and `fermos_vessel`

**Files:** `src/screens/FermOSVessel.tsx` (new, `/fermos/vessel`: simulation or fit chooser; vessel type (stirred tank | bubble column); the panel over the vessel scope in groups *Scale* (plant scale or batch volume), *Vessel* (V_max, N or V, V_wf, length_to_diameter, material, type), *Schedule* (tau_0, loading time, batch | continuous), *Aeration* (kLa method, gas flow or vvm, DO setpoint θ, compressor efficiency), *Agitation* (kW_per_m3, optimize_power), *Heat* (T, P, dT_hx_loop, exchanger configuration); **Design**; results: the design table, `OxygenBalance` figure, the cost line with its CEPCI year, the basis; **Price this in Proforma** (→ a `custom_train_v1` scenario in Phase 6; until then, the button says what Phase 6 adds), CSV), `src/components/figures/OxygenBalance.tsx`, `tabs.ts`, `components.ts`, `subsystems.ts` (`fermos.transport`, `fermos.scale` live), `src/lib/fermos.ts`, `tools/fermos.py` (`fermos_vessel` per D13), `tools/writes.py` (`fermos_write` action `design_vessel`), `tools/__init__.py`, `docs/TOOLS.md`, `test_tools.py`, `test_mcp.py`, `smoke.mjs`, `service-double.mjs` (fixtures from a real worker run in `demo.py --prototype` when the sim extra is present, else the stand-in, the fixture saying which).

**Commit:** `OF-BLD-020 §4.2: fermOS shows the vessel with every design parameter in hand, and Postdoc can ask for one`

## §4.3 LIVE — the yeast vessel

Design the vessel for §3.5's simulation (or the owed stand-in) at a plant scale typed as `OF-BLD-020 session`'s assumption only if §3.5 ran; otherwise owe it. Record N, V, batch and cycle time, power, duty, cost, and that the anaerobic design has no compressor. Ask Postdoc once: *Design a fermenter for that simulated batch and tell me how many vessels and what working volume it needs.* `pnpm data:push`.
**Commit:** `OF-BLD-020 §4.3: the yeast vessel designed` (` (run owed)` as needed)

## §4.R and §4.T

**Commits:** `OF-BLD-020 §4.R: …` · `OF-BLD-020 §4.T: README, COMPONENTS and STATE for the vessel`

---

# PHASE 8 (night one) — Live, the run sheet, the truth

## §8.1 LIVE, §8.2 run sheet, §8.R, §8.T

As OF-BLD-019 Phase 7, over this night's work: the eleven run-sheet questions once, the new ones twice, `pnpm ask:batch`, `pnpm data:push`; `docs/DEMO.md` gains *fermOS* (simulate, vessel, what the live runs showed, steer-around); §8.R over the branch diff; §8.T: README (the module table: fermOS simulates on scipy and sizes on BioSTEAM), COMPONENTS, CLAUDE (*fermOS simulates and sizes the vessel*, D1's amended rule, D2–D7, E.1‴–E.4‴), TOOLS, STATE; `pnpm shots --prefix of-bld-020-n1` for `/fermos/simulate`, `/fermos/vessel`, `/proforma/scenario/sc-yeast-1`; verify; push; PR.
**Commits:** `OF-BLD-020 §8.1: night one's questions asked live` · `OF-BLD-020 §8.2: the run sheet after night one` · `OF-BLD-020 §8.R: …` · `OF-BLD-020 §8.T: say true things about fermOS on BioSTEAM`

---

# NIGHT TWO

# PHASE 5 — pureOS builds the train

## §5.1 The unit catalogue

**Files:** `core/openferment_core/pureos/__init__.py`, `pureos/catalogue.py` (new: `UNIT_TYPES`, Appendix 2 §B: for each, `id` (the vocabulary id, with new ids `flash`, `evaporation`, `adsorption`, `drying-drum`, `crystallisation` reused, `heat-exchange`, `tank`, `pump`, `mixer`, `splitter`, `cell-disruption` (maps homogenisation and bead-mill), `chromatography` (maps iex, hic, imac, affinity-custom, sec, mixed-mode as a `mode` parameter)), `stage` (harvest | disruption | clarification | concentration | capture | polish | formulation | drying | utility), `biosteamClass` or `inhouseClass`, `specs` read from the class (D8) plus the source rules, `insOuts` (how many inlets and outlets and what each is), `notes`), `pureos/inhouse.py` (new: `Ultrafiltration(bst.Unit)` (sieving coefficient per component, concentration factor, diafiltration volumes; `_run` as a split; no cost), `CellDisruption(bst.Unit)` (release fraction per pass, passes; the product moves from the cell to the liquid), `Chromatography(bst.Unit)` (mode, recovery, purity as splits on product and on host impurities, bind capacity → column volume as a design item; no cost)), `vocabulary.ts` (the new ids with `biosteamClasses`; `check:seed` holds the catalogue's ids to the vocabulary's), `api.py` (`GET /api/pureos/catalogue`, `GET /api/pureos/catalogue/{id}/specs`), `models.py` (`UnitType`, `UnitSpecs`), `types.ts`, `check-plan.mjs`, `core/tests/test_catalogue.py` (every entry's class imports; every spec has a bounds reason; the specs' defaults equal the class's signature defaults, read both ways; `sim`: each unit type builds alone on a stand-in stream and converges — one parametrised test over the catalogue), `test_workers.py` (greps extended).

**Commit:** `OF-BLD-020 §5.1: a catalogue of unit operations, each a BioSTEAM class with its own parameters and their sources`

## §5.2 The train model and the run

**Files:** `pureos/train.py` (new: `TrainSpec` per D9; `validate(spec)` (types in the catalogue, connections resolve, recycles backward only, every parameter in the unit's specs); `build_system(spec, inlet_stream)` in the worker: units in order on the flowsheet's chemicals, side outlets to named waste streams, recycles through BioSTEAM's recycle loop; `run_train(spec, inlet, overrides, by)` → `pureos.train_run` artifact: the stream table, the unit table, recovery per unit through `train_of` (now over any artifact carrying the tables), purity per stream (product mass fraction and the largest impurities), utilities, costs for units that have a cost model, the diagram or the ordered list), `pureos.py` (`inlet_stream(ref)` per D10 from a `fermos.simulation`, a run's stream, or a typed composition), `workers/proforma_worker.py` (op `train_run`), `artifacts.py`, `models.py` (`TrainSpec`, `TrainUnitSpec`, `TrainRun`), `types.ts`, `check-plan.mjs`, `api.py` (`POST /api/pureos/train/validate`, `POST /api/pureos/train/run`, `GET /api/pureos/train-runs`), `core/tests/test_train.py` (`sim`: a three-unit train (solids centrifuge, flash, drum dryer) on a stand-in yeast broth converges, recovery per unit is between 0 and 1, the overall equals the product of onward fractions along the path; a forward recycle is refused; the ethanol train (beer column as `BinaryDistillation`, rectifier, `MolecularSieve`) built from the catalogue on `ethanol_glucose_v0`'s harvest stream gives an ethanol purity within 1 % of that flowsheet's own purification system on the same inlet).

**Commit:** `OF-BLD-020 §5.2: a train is data; the worker builds it, runs it, and every reader reads the one artifact`

## §5.3 pureOS → Builder

**Files:** `src/screens/PureOSBuilder.tsx` (new, `/pureos/build/:trainId`, `new` for a fresh one: **Inlet** (a simulation's harvest from `/api/fermos/simulations`, a run's stream from `/api/proforma/runs`, or typed per component under the reviewer name); **Steps**: the palette grouped by stage from the catalogue, each type with its one-line what-it-does; the ordered list of units, each a card with the panel over `pureos:unit:<train>:<unit>` and its outlet routing (onward | waste | recycle to an earlier unit); move up, move down, remove; **Run**; results: `PurityByStream` and `RecoveryByUnit`, the stream table, the unit table with costs where a model exists and *no cost model* where none, utilities, the diagram or the list, the basis, CSV; **Save** (Durable `trainsMade`); **Price this in Proforma** (Phase 6); **Start from a run's train** (reads a `proforma.run`'s units into a spec where every unit maps to a catalogue type, and says which do not)), `src/screens/PureOS.tsx` (the index: trains built here, train runs on the service, **New train**, **Propose a train** (Phase 7)), `src/components/figures/PurityByStream.tsx`, `nav.ts` (`build` reserved), `tabs.ts` (Trains, Builder, Train), `App.tsx`, `components.ts`, `subsystems.ts` (D15: the four pureOS subsystems live), `src/lib/pureos.ts` (new), `durable.ts`, `check-store.ts`, `check-figures.ts`, `smoke.mjs` (build a three-unit train against the double, set a parameter, run, read recovery), `service-double.mjs`, `demo.py --prototype`.

**Commit:** `OF-BLD-020 §5.3: pureOS builds a train, unit by unit, with every parameter in hand, and runs it`

## §5.4 `pureos_build`, and the reads

**Files:** `tools/pureos.py` (`pureos_build` per D13, loose; `pureos_read` rows gain trains and train runs), `tools/writes.py` (`pureos_write` actions `new_train`, `add_unit`, `remove_unit`, `set_from_record` (a unit parameter bound to record ids), `run_train`), `tools/__init__.py`, `validate.py`, `postdoc_agent.py`, `docs/TOOLS.md`, tests as §3.4.

**Commit:** `OF-BLD-020 §5.4: Postdoc builds and runs a train from unit type names and record ids`

## §5.5 LIVE — the yeast train, built and compared

Build the ethanol train from the catalogue on the harvest stream of §3.5's simulation (or `sc-yeast-1`'s newest run stream), run it, record purity and recovery against `ethanol_glucose_v0`'s own purification system on the same inlet; ask Postdoc: *Build a train that recovers fuel-grade ethanol from the simulated beer and tell me the recovery at each step.* `pnpm data:push`.
**Commit:** `OF-BLD-020 §5.5: the yeast train built from the catalogue, and checked against the package's own`

## §5.R and §5.T

**Commits:** `OF-BLD-020 §5.R: …` · `OF-BLD-020 §5.T: README, COMPONENTS and STATE for the train`

---

# PHASE 6 — The seam

## §6.1 `custom_train_v1` on the shelf

**Files:** `flowsheets/custom_train.py` (new: per D11; the fermenter rebuilt from a `fermos.vessel` artifact's parameters as the same BioSTEAM class, fed by the scenario's bound titre, yield and batch time (or the simulation's), the train from a `pureos.train_run`'s spec; TEA per D11 with its financial parameters as specs in scope `proforma:<scenario>` group *Finance* (IRR, tax, depreciation schedule, operating days, Lang factor, construction years, as the package's defaults name them)), `flowsheets/shelf.py` (`custom_train_v1`, program taken from the train's; inputs: the vessel's scale, the train's inlet, the economic ones), `proforma.py` (`bind_inputs` for the composite; `run` through the worker as any flowsheet), `workers/proforma_worker.py`, `NewScenarioDialog.tsx` (New scenario from a vessel and a train: choosers for both artifacts), `FermOSVessel.tsx` and `PureOSBuilder.tsx` (**Price this in Proforma** creates the scenario and opens it), `ProformaScenario.tsx` (the Finance group in the panel; the fermenter and the train named with links), `core/tests/test_custom_train.py` (`sim`: a vessel artifact plus the three-unit train prices on stand-in assumptions and converges; the stream table's units are the vessel's class plus the train's).

**Commit:** `OF-BLD-020 §6.1: a vessel and a train become a flowsheet Proforma prices, and every reader reads the one run`

## §6.2 The harvest stream, both ways

**Files:** `pureos.py` (`inlet_stream` from a simulation at a chosen hour; from a scenario's run; the basis names which), `fermos.py` (`harvest(simulation, hour)` as an artifact-free read), `FermOSSimulate.tsx` (**Use as a train's inlet** → the Builder with the inlet set), `PureOSBuilder.tsx` (the inlet chooser lists simulations with their harvest composition), `core/tests/test_seam.py` (the composition at harvest equals the simulation's end state by component within rounding; a simulation with no product series refuses to be an inlet in words).

**Commit:** `OF-BLD-020 §6.2: the broth that leaves fermOS is the stream that enters pureOS`

## §6.R and §6.T

**Commits:** `OF-BLD-020 §6.R: …` · `OF-BLD-020 §6.T: README, COMPONENTS and STATE for the seam`

---

# PHASE 7 — The train proposer

## §7.1 Properties a proposal reads

**Files:** `core/pyproject.toml` (`biopython` in the base dependencies; its licence line), `uv.lock`, `licences.toml`, `THIRD_PARTY.md`, `core/openferment_core/protparam.py` (new: MW, pI, extinction coefficient, GRAVY from a sequence through `Bio.SeqUtils.ProtParam`; a `computed` artifact with the library version; refuses a sequence with non-standard letters in words), `src/data/products.ts` (a `sequence` field where a product entry carries one; none invented: left absent), `thermo.py` (`volatility(product)`: boiling point and whether an azeotrope with water exists by `thermo_props`), `core/tests/test_protparam.py` (a published sequence gives the library's own pI within rounding).

**Commit:** `OF-BLD-020 §7.1: a product's properties, computed from its sequence or its thermodynamics, with the library named`

## §7.2 The rules, and `pureos_propose`

**Files:** `pureos/propose.py` (D12: `propose(product, host, inlet)` → a `TrainSpec` with every unit at library defaults and a `reasons` list, one per unit, each naming the property and its artifact), `api.py` (`POST /api/pureos/propose`), `PureOS.tsx` (**Propose a train** → the Builder with the proposal and its reasons shown beside each unit), `tools/pureos.py` (`pureos_propose`, loose read), `tools/__init__.py`, `docs/TOOLS.md`, `core/tests/test_propose.py` (ethanol proposes distillation then dehydration because thermosteam finds the azeotrope; a secreted protein with a sequence proposes clarify, UF, chromatography keyed on pI; a product with no sequence and no thermodynamics proposes nothing and names the missing property), `test_tools.py`, `test_mcp.py`.

**Commit:** `OF-BLD-020 §7.2: a train proposed by rules that each name the property they read`

## §7.R and §7.T

**Commits:** `OF-BLD-020 §7.R: …` · `OF-BLD-020 §7.T: README, COMPONENTS and STATE for the proposer`

---

# PHASE 8 (night two) — Live, the run sheet, the truth

As night one's Phase 8 over night two's work; `docs/DEMO.md` gains *pureOS*; CLAUDE gains *pureOS builds the train* (D8–D12, E.1‴–E.4‴ as they apply); shots `of-bld-020-n2` for `/pureos/build/<id>`, `/pureos/train/<id>`, `/proforma/scenario/<custom>`; verify; push; PR.
**Commits:** `OF-BLD-020 §8.1: night two's questions asked live` · `OF-BLD-020 §8.2: the run sheet after night two` · `OF-BLD-020 §8.R: …` · `OF-BLD-020 §8.T: say true things about fermOS and pureOS on BioSTEAM`

---

# PART F — ORDER OF WORK

| Night | Phase | Steps | Estimate |
|---|---|---|---|
| 1 | 1 baseline | §1.1 | 30 min |
| 1 | 2 the panel | §2.1 §2.2 §2.R §2.T | 1 h 45 |
| 1 | 3 fermOS simulates | §3.1 §3.2 §3.3 §3.4 §3.5 §3.R §3.T | 3 h |
| 1 | 4 the vessel | §4.1 §4.2 §4.3 §4.R §4.T | 2 h |
| 1 | 8 live, sheet, truth | §8.1 §8.2 §8.R §8.T | 1 h |
| 2 | 5 the train | §5.1 §5.2 §5.3 §5.4 §5.5 §5.R §5.T | 3 h 30 |
| 2 | 6 the seam | §6.1 §6.2 §6.R §6.T | 1 h 30 |
| 2 | 7 the proposer | §7.1 §7.2 §7.R §7.T | 1 h 15 |
| 2 | 8 live, sheet, truth | as above | 1 h |

Each night is about eight hours against roughly seven on the clock; the wall-clock rule decides, Phase 8 runs whatever state the others are in, and Phase 7 drops first.

---

# APPENDIX 1 — Sean's part, each morning

```
git fetch --all --prune && git switch <the night's branch> && git pull --ff-only
tail -80 STATE.md        # MORNING, FERMOS, PUREOS, EVERY PARAMETER, POSTDOC, STEER AROUND
```
Merge the PR (squash). On the Mini, in Terminal, in the openferment folder:
```
bash scripts/host/deploy.sh --keep-decisions
pnpm data:pull
sudo launchctl kickstart -k system/com.umutuzo.openferment
pnpm ready
```
Then open fermOS → Simulate, choose `batch_v1`, CEN.PK113-7D, ethanol, glucose, **Start from records**; type under your name whatever the panel says is waiting (the report names it); **Simulate**; **Design the vessel**; type a plant scale; **Design**. After night two: pureOS → New train → inlet from that simulation → add the beer column, the rectifier and the molecular sieve from the palette → **Run** → **Price this in Proforma**.

---

# APPENDIX 2 — Every parameter, so nothing you want in hand is missing

Each line: key · symbol · what it means · unit · where its value comes from (first source wins) · bounds reason. Bounds are conventions the session writes with their reason (D4); none is a result.

## §A fermOS model families (scope `fermos:family:<id>`)

**Growth** (all families)
- `mu_max` · μmax · the fastest the cells can grow with nothing limiting · h⁻¹ · fit → `growth_rate_mu` records → assumption · ontology range
- `ks` · Ks · the substrate concentration at which growth runs at half speed · g L⁻¹ · fit → `monod_ks` → assumption · ontology range
- `kd` · kd · the death or decay rate of cells · h⁻¹ · fit → assumption → zero (said so) · physical (≥ 0)
- `yxs` · Yx/s · grams of cells made per gram of substrate used · g g⁻¹ · fit → `biomass_yield_substrate` → assumption · physical (0–1)

**Product** (all)
- `alpha` · α · product made per unit of growth (growth-associated) · g g⁻¹ · fit → `ethanol_lp_alpha` → assumption · physical (≥ 0)
- `beta` · β · product made per gram of cells per hour whatever the growth (non-growth-associated) · g g⁻¹ h⁻¹ · fit → `ethanol_lp_beta` → assumption → zero (said so) · physical (≥ 0)
- `yps` · Yp/s · grams of product per gram of substrate · g g⁻¹ · fit → `ethanol_yield_substrate` (or the product's own field) → assumption · the ceiling from geneOS when one exists, else the theoretical from the reaction
- `maintenance` · m · substrate the cells burn just to stay alive per gram per hour · g g⁻¹ h⁻¹ · fit → `maintenance_coefficient` (new field) → assumption → zero · physical

**Inhibition** (all)
- `p_max` · Pmax · the product concentration at which growth stops · g L⁻¹ · fit → `ethanol_max_conc` → assumption · ontology range
- `n_inhibition` · n · how sharply growth falls as product builds toward Pmax · – · fit → assumption → 1 (convention) · convention (0.5–3)
- `ki_substrate` · Ki · the substrate concentration above which it inhibits (Haldane) · g L⁻¹ · fit → `substrate_inhibition_ki` → assumption → off (said so) · ontology range

**Oxygen** (families that set it; anaerobic families show zero and say so)
- `yxo` · Yx/o · grams of cells per gram of oxygen · g g⁻¹ · fit → `biomass_yield_oxygen` (new) → assumption · physical
- `mo` · mO · oxygen for maintenance per gram of cells per hour · g g⁻¹ h⁻¹ · assumption → zero · physical

**Feed** (`fedbatch_v1`)
- `feed_profile` · F(t) · constant, exponential or a step table · – · assumption · –
- `feed_rate` · F · litres fed per hour (constant) · L h⁻¹ · assumption · physical
- `mu_set` · μset · the growth rate an exponential feed holds · h⁻¹ · assumption · ≤ μmax
- `feed_conc` · Sf · substrate concentration in the feed · g L⁻¹ · `medium_component_conc` → assumption · solubility (convention)
- `feed_start_h`, `feed_end_h` · – · when the feed runs · h · assumption · run length

**Dilution** (`chemostat_v1`)
- `dilution_rate` · D · feed flow over working volume · h⁻¹ · assumption · < washout, computed and shown
- `feed_conc` · Sf · as above

**Storage** (`storage_v1`)
- `n_initial` · N0 · the second nutrient at the start · g L⁻¹ · `medium_component_conc` → assumption
- `k_n` · KN · half-speed concentration of the second nutrient · g L⁻¹ · fit → assumption
- `yxn` · Yx/N · cells per gram of the second nutrient · g g⁻¹ · fit → assumption
- `q_storage_max` · qQ,max · the fastest storage-product formation per gram of cells · g g⁻¹ h⁻¹ · fit → `pha_productivity`-derived (said so) → assumption
- `q_max` · Qmax · the most storage product the cells can hold · g g⁻¹ · fit → `pha_content_cdw` → assumption

**Light** (`light_v1`, a socket: declared, refuses to run)
- `irradiance`, `path_length`, `attenuation`, `k_photoinhibition` · – · declared with glosses · the socket says what would build it

**Start values** (all)
- `x0`, `s0`, `p0` · X0, S0, P0 · cells, substrate and product at time zero · g L⁻¹ · a deposition's first readings (fit) → `medium_component_conc` on glucose (S0) → assumption; X0 and P0 assumption or the fit's
- `v0` · V0 · working volume at the start · L · assumption → the vessel's (when designed)
- `t_end` · – · how long to integrate · h · until the median sugar runs out (convention) → assumption

## §B pureOS unit catalogue (scope `pureos:unit:<train>:<unit>`)

Each entry: the BioSTEAM class and the parameters its docstring documents, read at import (D8); below, the parameters a person most needs in hand, with their gloss. The full list per unit is whatever the class declares.

- **Solids centrifuge** · `SolidsCentrifuge` · `split` per component (what fraction goes with the solids), `moisture_content` of the cake, `solids` (which chemicals are solids) · sources: `step_recovery` (new field) for the product's split → assumption → library default
- **Pressure filter** · `PressureFilter` · split, cake moisture, pressure drop · as above
- **Rotary vacuum filter** · `RotaryVacuumFilter` · split, moisture · as above
- **Clarifier** · `Clarifier` · split · as above
- **Cell disruption** (in-house) · passes, release fraction per pass (first-order), product location before and after · `disruption_protein_yield` (existing field) → assumption
- **Ultrafiltration / diafiltration** (in-house) · sieving coefficient per component, concentration factor, diafiltration volumes, flux (for area, no cost) · `sieving_coefficient` (new) → assumption
- **Flash** · `Flash` · T, P or V (vapour fraction) · assumption → library default
- **Binary distillation** · `BinaryDistillation` · light key, heavy key, `x_bot` (light key left in the bottoms), `y_top` (light key in the distillate), `k` (reflux ratio over the minimum), P, partial or total condenser · assumption → library default; the azeotrope limit from thermosteam shown as a warning
- **Shortcut column** · `ShortcutColumn` · as binary distillation, by the Fenske–Underwood–Gilliland shortcut
- **Molecular sieve** · `MolecularSieve` · split per component (water removed) · assumption → library default
- **Multi-effect evaporator** · `MultiEffectEvaporator` · V (fraction evaporated), P per effect · assumption → library default
- **Mixer-settler extraction** · `MixerSettler` / `MultiStageMixerSettlers` · solvent, solvent-to-feed ratio, partition coefficients (`partition_coefficient`, new field) or thermosteam's LLE, stages · records → assumption → library
- **Adsorption column** · `SingleComponentAdsorptionColumn` · adsorbate, superficial velocity, cycle time, adsorbent capacity · assumption → library default
- **Chromatography** (in-house placeholder) · mode (iex | hic | imac | affinity | sec | mixed-mode), recovery (`step_recovery`), purity (`product_purity`, new field), binding capacity, column volumes of buffer · records → assumption; *no cost model*, and *CADET replaces this* in its note
- **Batch crystalliser** · `BatchCrystallizer` · T, residence time, crystal yield or solubility · assumption → library default
- **Spray dryer** / **Drum dryer** · `SprayDryer` / `DrumDryer` · outlet moisture content, T · assumption → library default
- **Heat exchanger** · `HXutility` · outlet T · assumption
- **Storage tank**, **Mix tank**, **Pump**, **Mixer**, **Splitter** · their class parameters; a splitter's split per component is the one parameter a person sets

New ontology fields (family *downstream*, with ranges as conventions and justifications; extractable like any field): `step_recovery` (fraction), `product_purity` (fraction), `partition_coefficient` (–), `sieving_coefficient` (fraction), `cake_moisture` (fraction). New kinetics fields: `maintenance_coefficient` (g g⁻¹ h⁻¹), `biomass_yield_oxygen` (g g⁻¹), `specific_oxygen_uptake` (mmol g⁻¹ h⁻¹), `kla_measured` (h⁻¹).

## §C fermOS vessel design (scope `fermos:vessel:<simulation id>`)

- *Scale*: `plant_scale` (t product yr⁻¹) or `batch_volume` (m³) · one required · assumption → the scenario's
- *Vessel*: `V_max` (the largest single vessel) · `N` or `V` · `V_wf` (working fraction) · `length_to_diameter` · `vessel_material` · `vessel_type` (stirred tank | bubble column) · library defaults read from the class; assumption
- *Schedule*: `tau` (from the simulation's harvest hour; shown, overridable) · `tau_0` (cleaning and unloading) · `loading_time` · `batch` (true | false) · library defaults
- *Aeration* (aerobic only): `method` (Riet | Dewes | Labik | Deshpande | DeJesus | Akita–Yoshida, as `kLa_methods` registers them) · gas flow as vvm · `theta_O2` (DO setpoint as a fraction of saturation) · `compressor_isentropic_efficiency` · `Q_O2_consumption` (from peak OUR; shown, overridable)
- *Agitation*: `kW_per_m3` · `optimize_power`
- *Heat*: `T` · `P` · `heat_exchanger_configuration` · `dT_hx_loop` · `jacket_annular_diameter` · `cooler_pressure_drop`
- Outputs (read, never set): N vessels, V each, working volume, cycle time, dead time, agitator power, compressor power, cooling duty, kLa achieved, superficial gas velocity, OTR and OUR over time, purchase and installed cost, CEPCI year, the reactor duty

## §D Proforma finance (scope `proforma:<scenario>`, group *Finance*, Phase 6)

IRR, income tax, operating days per year, construction and startup schedule, depreciation, Lang factor, working capital fraction, labour and maintenance fractions — the package's `default_tea_parameters` names, read from `biorefineries.corn.create_tea` and shown with *library default* until a person sets one.

---

# APPENDIX 3 — Spend

Night one: the live questions and fixture regeneration, under 0.30 USD. Night two: the same, under 0.30 USD. BioSTEAM and scipy runs cost nothing but time.

---

# APPENDIX 4 — What this document leaves to OF-BLD-018

The anchored yeast protocol and the runbook path (018 Phase 3), Intake on Docling, Dominion on PatentsView, memote on the shelf, the lab passphrase. And after both: dynamic FBA as a model family (COBRApy inside the ODE), lmfit and emcee for fit posteriors, CADET behind the chromatography placeholder, Pioreactor as fermOS's first instrument, DO as a state with a control loop, Graphviz on the Mini for the diagrams (`brew install graphviz`).
