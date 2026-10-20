# Components

**openFerment is Home plus eleven destinations, and the list is closed.**

This file is the canonical map every future specification points at
(OF-BLD-008 §8). `src/data/nav.ts` is the single source of truth the rail, the
command palette, the Architecture screen and the smoke tests all read from;
this document is the same content written for a person, and `check:seed` fails
the build if the two disagree.

## The rule

| | Path | Chord | Descriptor |
|---|---|---|---|
| Home | `/` | `h` | where things stand |
| Intake | `/intake` | `i` | documents in, anchored to source |
| BioRepo | `/biorepo` | `b` | records, artifacts, provenance |
| Postdoc | `/postdoc` | `o` | ask, plan, answer from records |
| geneOS | `/geneos` | `e` | host, construct, pathway, design |
| fermOS | `/fermos` | `f` | reactor, kinetics, scale |
| pureOS | `/pureos` | `u` | harvest, capture, recovery |
| Proforma | `/proforma` | `c` | cost, scale, uncertainty |
| Runbooks | `/runbooks` | `r` | claims to be tested |
| Dominion | `/dominion` | `d` | what is fenced, what is open |
| Primer | `/primer` | `n` | how the system works |
| Guild | `/guild` | `g` | who may verify |

Twelve rail entries. **It does not grow.** Everything that exists now, and
everything built later, lives inside one of the eleven. When something new
appears and does not obviously belong, the question is which of the eleven owns
it — never whether to add a twelfth. If a thirteenth ever seems necessary the
honest options are to find its owner, or to argue that the eleven are wrong.
Adding one is not an option, and `check:seed` enforces that rather than
trusting anybody to remember it.

Five things used to be destinations and are now views inside their owner.
**None of their screens were deleted** — each is the same file, mounted
somewhere else:

| Was | Is now |
|---|---|
| Organisms | geneOS's default view, as **Hosts** — `/geneos/hosts` |
| Molecules | Dominion's default view — `/dominion/molecules` |
| Protocols | a Runbooks tab — `/runbooks/protocols` |
| Deposition | a Runbooks tab — `/runbooks/depositions` |
| Witness | a BioRepo tab — `/biorepo/witness` |

Every retired path redirects, tail intact: `/organisms/cw15` lands on
`/geneos/hosts/cw15`. Old words still resolve in the palette — typing
"molecules" reaches Dominion, and "organisms" reaches geneOS.

## The three OS components

They are the three **stages of making something**, in order. OF-BLD-011 §1
corrected an earlier split along software categories — sequence tools in one
component, metabolic-modelling libraries in the other — which is how a toolkit
is organised, not how bioprocess work is.

| | Owns | Question | Discipline |
|---|---|---|---|
| **geneOS** | The organism as an engineered system | What *can* this cell do? | Stoichiometry |
| **fermOS** | The reactor | What *does* a real vessel achieve over time? | Dynamics |
| **pureOS** | Downstream | How does product become vial? | Separation |

Two consequences of the old split were actively wrong, and both are fixed.
**Strain design sat in fermOS** — deciding which genes to knock out is genetic
design and belongs with the rest of it. And **fermOS had no kinetics at all**,
which meant the component named after fermentation contained nothing about
running a fermenter.

### The seams

Two boundaries carry a decision made in one component and paid for in another.
Both are stated on the screens, not only here.

**geneOS → fermOS is stoichiometry to dynamics.** A genome-scale model says the
pathway can reach a yield; it has no time axis and no vessel. Kinetics says what
happens in a 2,000 litre reactor over ninety hours. **Titre is fermOS's output,
not geneOS's**, and the gap between the ceiling and the titre achieved is
exactly what reconciliation measures against a Deposition.

**fermOS → pureOS is the harvest step**, and it is where **secreted or
intracellular** gets paid for — a decision made back in geneOS when the chassis
and signal peptide were chosen. A secreted product starts at centrifuge and
filter; an intracellular one starts at lysis and inherits every problem after
it. The handoff must carry product location, not just a titre.

**Properties flow downstream; operations do not flow back.** Thermostability is
predicted in geneOS and consumed in pureOS, where it decides whether thermal
clarification can replace most of the capture chromatography. Store it once in
geneOS. Do not duplicate it.

Two more seams carry data rather than a decision, and both are built
(OF-BLD-019 Phase 4).

**Proforma → pureOS is the run artifact.** A Proforma run keeps one
`proforma.run` artifact holding BioSTEAM's stream and unit tables for its base
case (OF-BLD-019 D1). pureOS reads the train from that artifact, unit by unit,
and simulates nothing again: the flowsheet, its units and its mass balance are
BioSTEAM's, run in Proforma's worker, and pureOS reads the recovery out of
them.

**pureOS → thermosteam goes through the Proforma worker.** A stream's physical
properties (density, heat capacity, viscosity, bubble and dew points) are
thermosteam's, BioSTEAM's property engine, asked in the Proforma worker where it
is already loaded. The service names a run's stream or a preset, never a
number, and keeps the answer as a `thermo_props` artifact; fermOS asks the same
worker about water and ethanol at a measured titre.

One more carries records into a flowsheet, and it is built too (OF-BLD-019
Phase 2).

**BioRepo → Proforma is the binding.** A scenario's flowsheet holds no input
value of its own: for each input records can set, Proforma's shelf names the
ontology fields that bind it, and the service binds it to the records of those
fields on its program's papers that pass the aggregate gate and name a feed the flowsheet
takes as their carbon source, converted by `units.py`. Glucose to ethanol binds
its feed concentration, titre and yield to thread Q's records today; its
productivity waits, because no thread Q productivity record names a carbon
source. What no record binds waits for a named person's assumption (or, for
titre, yield and productivity, a fermOS fit a person chooses, below), and the
run's basis names every record, assumption and fit it used.

Two more carry the reactor and the organism into the price, and both are built
(OF-BLD-019 Phase 5).

**fermOS → Proforma is a fit a person chooses.** A kept kinetic fit or
forecast can be the source of a scenario's titre, yield and productivity
(`proforma.fit_info` and `apply_fits`, `GET /api/fermos/fits`): titre the
forecast's final product, yield its product made over sugar used, productivity
the titre over the hour its median sugar runs out, found between grid points
and drawn again to that hour (`fermos.to_run_out`). Nothing is copied: the run's
basis names the fit for each input it feeds, so the run's provenance follows
the fit's. A person chooses it, on the scenario page or with Send to Proforma on
fermOS → Forecast, and a fit's productivity feeds only beside its own titre; a
fit that cannot give an input is refused naming the parameter.

**geneOS → Proforma is a flag, never a bound.** The ceiling check
(`proforma.ceiling_check`, `GET /api/proforma/ceiling-check`) sets a scenario's
fermenter yield, as bound, beside the newest stored geneOS ceiling of each shelf
model of its organism on its flowsheet's sugar, flags a yield above it with the
records above, and changes nothing: the binding, the run and its artifact are
the same with a ceiling on file as without. The organism is read from the bound
records' strains and species, a model matches by strain or by species, and the
check is computed when read and kept nowhere. geneOS → Model lists the
scenarios above a model's ceiling.

**fermOS cannot be seeded from literature.** Kinetic parameters are fitted to
real runs in a specific vessel, so they come from Deposition. fermOS is the
component that most needs the Assay loop and the one that cannot be built out of
papers.

## The eleven

### Intake

**Documents in, anchored to source.** `/intake` · chord `g i`

Ingest and extraction. A claim enters the system here or it does not enter at all. With openferment-core running, Fetch asks Europe PMC for a paper's open-access full text and Extract runs Claude Opus 5.5 once over it (Sonnet 5.5 where Opus declines), every candidate anchored to a verbatim quote (OF-BLD-012 §5–6); the seed's curator notes stand in for the papers nobody has fetched, and the reader says which is which.

Views: [Ingest](#) `/intake/ingest`

| Component | Implemented in |
|---|---|
| Intake | `src/screens/IntakeIngest.tsx`, `src/screens/Intake.tsx`, `core/openferment_core/intake.py`, `core/openferment_core/extract.py` |

### BioRepo

**Records, artifacts, provenance.** `/biorepo` · chord `g b`

The corpus and everything retrieved from it, plus the two components whose job is to say what a record is worth: Audit ticks it, Witness measures whether the extractor reproduced the curated values on the papers it read — one run so far, `claude-1`, scored provisionally until reviewers flag gold. Review decisions are the one thing that changes a record's status, and every one of them goes through `biorepo.write` into the committed `core/data/biorepo.json` (OF-BLD-012 §2.3, §7). Artifacts keeps every value the service computed, with the inputs it was computed from and the source of each, and replays it on request (OF-BLD-014 §3.2); its subsystem is the first marked `live`.

Views: [Search](#) `/biorepo/search` · [Witness](#) `/biorepo/witness` · [Artifacts](#) `/biorepo/artifacts` · [Compare](#) `/biorepo/compare`

| Component | Implemented in |
|---|---|
| BioRepo | `src/data/`, `src/engine/retrieval.ts`, `src/screens/BioRepo.tsx`, `core/openferment_core/biorepo.py`, `src/screens/BioRepoArtifacts.tsx`, `core/openferment_core/artifacts.py`, `src/screens/BioRepoSearch.tsx`, `core/openferment_core/passages.py`, `core/openferment_core/retrieve.py`, `src/components/figures/` |
| Audit | `src/components/Provenance.tsx`, `aggregateExclusion() in src/store.ts`, `core/openferment_core/basis.py` |
| Witness | `src/screens/Witness.tsx`, `src/engine/metrics.ts`, `core/openferment_core/witness.py`, `core/openferment_core/rageval.py`, `src/components/RetrievalScorecard.tsx` |

Not built: Common Seal.

### Postdoc

**Ask, plan, answer from records.** `/postdoc` · chord `g o`

The thing you talk to. Before its first turn, code sweeps all eleven modules for what the question names and hands the model the map; then a bounded loop of tools runs on one model (`claude-haiku-5-5` in this build, restarted once on the fallback model on a refusal or an outage) through `openferment-core`: it reads any module through that module's read tool, searches the records and the papers' passages, shows each step as it runs, and writes claims that carry no numbers of their own, each citing a record, a module row with its computed state, a sentence checked word for word against its passage, or a computed value. It writes through each module's write tool, which calls the module's own write function and marks the result as the model's in the audit log; an action at a gate becomes a proposal that waits on Home for a person. A follow-up is swept with the earlier questions it reads, never their answers. A plan's gaps and decline hold no number, like its claims, and so do a proposal's words; a proposal to check a person shows to the lead and assessors alone, never to the person it names. A candidate the model writes by hand is anchored like the extractor's and kept apart from the extractor's file, so it never counts as an extraction. With archived programs hidden, the default, its evidence pool, its passages and every module's rows leave casein and PHA out; a question that names something archived is told which program holds it and where the switch is, and the switch reaches the service with the question, never from the model.

| Component | Implemented in |
|---|---|
| Postdoc | `src/lib/postdoc.ts`, `src/screens/Postdoc.tsx`, `core/openferment_core/postdoc_agent.py`, `core/openferment_core/validate.py`, `core/openferment_core/module_stores.py`, `core/openferment_core/tools/`, `core/openferment_core/audit.py`, `core/openferment_core/proposals.py`, `core/openferment_core/evidence_pool.py`, `src/components/ProposalsCard.tsx` |

### geneOS

**Host, construct, pathway, design.** `/geneos` · chord `g e`

The organism as an engineered system: host choice, genetic parts, pathway assembly, the genome-scale model, strain design. Stoichiometry — what a cell *can* do, before any vessel is involved. Hosts (the strain catalogue) and Pathway (the biosynthetic vocabulary) are seeded; the other six subsystems are named and unbuilt.

Views: [Hosts](#) `/geneos/hosts` · [Pathway](#) `/geneos/pathway`

| Subsystem | Key | State |
|---|---|---|
| Hosts | `geneos.hosts` | seeded |
| Parts | `geneos.parts` | stub |
| Pathway | `geneos.pathway` | seeded |
| Sequence search | `geneos.search` | stub |
| Structure | `geneos.structure` | stub |
| Function | `geneos.function` | stub |
| Model | `geneos.model` | live |
| Strain design | `geneos.design` | stub |

| Component | Implemented in |
|---|---|
| geneOS | `src/screens/GeneOS.tsx`, `src/screens/Organisms.tsx`, `src/screens/StrainPage.tsx`, `src/engine/geneos/enumeration.ts`, `src/screens/GeneOSModel.tsx`, `core/openferment_core/geneos.py`, `core/openferment_core/workers/geneos_worker.py` |

### fermOS

**Reactor, kinetics, scale.** `/fermos` · chord `g f`

The vessel: kinetics, oxygen and heat transport, operating mode and feeding, scale-up, instrumentation and control. Dynamics — what a real reactor achieves over time. **Kinetics is built, from depositions alone**: a run's readings become time series, the service fits a growth rate and a kinetic model (logistic growth, Luedeking–Piret production, the substrate balance) and keeps each fit as an artifact, and a forecast is a band drawn from one fit. No parameter from a paper enters it. A fit or forecast can feed a Proforma scenario's titre, yield and productivity when a person chooses it (fermOS → Proforma, above). Transport, operating mode, scale-up and control are not built.

| Subsystem | Key | State |
|---|---|---|
| Kinetics | `fermos.kinetics` | live |
| Transport | `fermos.transport` | stub |
| Operating mode | `fermos.mode` | stub |
| Scale | `fermos.scale` | stub |
| Control | `fermos.control` | stub |

| Component | Implemented in |
|---|---|
| fermOS | `src/screens/FermOS.tsx`, `src/screens/FermOSForecast.tsx`, `src/engine/series.ts`, `core/openferment_core/fermos.py` |

### pureOS

**Harvest, capture, recovery.** `/pureos` · chord `g u`

Everything after the fermenter: harvest, disruption, capture, polishing, recovery, formulation and storage. Holds the unit-operation vocabulary and `ProcessTrain`. Proforma prices a train; pureOS decides it. **pureOS reads the train a flowsheet ran** (OF-BLD-019 Phase 4): `/pureos/train/:scenarioId` (`src/screens/PureOSTrain.tsx`) shows the units of the newest Proforma run of a scenario in run order, each with its inlets and outlets, mass in and out, the product in and out, the product it passes on toward the product stream and what it loses and to which outlet, its recovery and the share still on the path, and the overall recovery, read by the service (`core/openferment_core/pureos.py`, `GET /api/pureos/trains`, `GET /api/pureos/train/{key}`) from the run artifact's stream table and never typed; the front page lists the trains on file. Recovery is credited by pass: a unit whose passes BioSTEAM keeps apart (`SEPARATE_PASSES`, the process heat exchanger) is counted only on the pass that carries the product on, and product a unit on the path takes in and lets out by no outlet is lost there. A train's mark is its run's, worked out from the run's inputs as they stand when it is read. A vocabulary entry names the BioSTEAM classes that perform it, so a unit links to its step. A **Properties** card asks thermosteam, through the Proforma worker, about the broth, the product stream or any stream of the run (`core/openferment_core/thermo.py`, `src/components/PropertiesPanel.tsx`); fermOS carries the same card for a measured titre. `pureos_read` reads trains (kind `train`) and their units (kind `train-unit`), and `thermo_props` asks thermosteam. With the service down each says so. Choosing a train is not built, and the four subsystems below remain stubs.

Views: [Train](#) `/pureos/train`

| Subsystem | Key | State |
|---|---|---|
| Harvest | `pureos.harvest` | stub |
| Capture | `pureos.capture` | stub |
| Polish | `pureos.polish` | stub |
| Recovery | `pureos.recovery` | stub |

### Proforma

**Cost, scale, uncertainty.** `/proforma` · chord `g c`

Techno-economics on BioSTEAM: published reference biorefineries run whole, and scenarios made from a flowsheet on the shelf, every input bound to records or to a named person's assumption. Prices a process; does not choose one. The authored response surfaces S1–S3 step aside for the archived casein examples and are not deleted.

Views: [Corn ethanol reference](#) `/proforma/reference/corn_drygrind` · [Corn stover benchmark](#) `/proforma/reference/cornstover_benchmark`

**Proforma runs flowsheets from a shelf** (OF-BLD-019 Phase 2). The shelf is data (`core/openferment_core/flowsheets/shelf.py`, `GET /api/proforma/shelf`): two published reference biorefineries from the `biorefineries` package, the NREL corn stover design (`cornstover_benchmark`) and the dry-grind corn ethanol plant (`corn_drygrind`, the yeast program's reference), each run whole on its package's own defaults and held to its package's own test values, read from the installed test file; and two flowsheets of this repository that a scenario runs, glucose to ethanol (`ethanol_glucose_v0`, run by `sc-yeast-1`, yeast ethanol) and PHA from sugar (`pha_sugar_v0`, run by `sc-pha-1`, archived). BioSTEAM runs in the Proforma worker, where every plant builds as it would in a worker that had built nothing before. Each run is one artifact holding the price, the sensitivity and the base case's TEA breakdown, stream table, unit table, utility duties and diagram (`proforma.run` for a scenario, `proforma.reference` for a reference biorefinery), and every reader reads that artifact; nothing is computed again on read. A scenario flowsheet's file holds no input value: an input the shelf ties to ontology fields binds to records of its program's papers, any other waits for a named person's assumption, and a run is `demo` while an assumption remains.

**A reference biorefinery has a page** (OF-BLD-019 §3.3): `/proforma/reference/:id` (`src/screens/ProformaReference.tsx`) shows a published biorefinery from the `biorefineries` package run whole on its own defaults, its price as the shelf names it, and each value of the package's own regression test beside what the run measured, read from the run's `proforma.reference` artifact, then the same tables a scenario page shows. BioRepo → Compare (`/biorepo/compare`) sets two or more pinned BioSTEAM scenarios side by side from each one's newest run.

**Proforma's screens read the run and price nothing** (OF-BLD-019 Phase 3). The index (`src/screens/Proforma.tsx`) has three rows: the reference runs, each with its newest stored price, when it ran, its provenance and how many of its package test's values it holds; the other flowsheets on the shelf, each with **New scenario from this**; and the scenarios of the programs the switch shows, with the newest run's price or *Not run yet*. **New scenario** (`src/components/NewScenarioDialog.tsx`) makes a `biosteam` scenario on a non-reference flowsheet, in that flowsheet's own program, and nothing is disabled because a list is empty. The scenario page (`/proforma/scenario/:id`, `src/screens/ProformaScenario.tsx`) is one page for a seed scenario and one made here: its inputs with their sources, Run with the worker's status, and every section of the newest run (`src/screens/ProformaBiosteam.tsx`): price, the TEA's cost breakdown as a waterfall closing on the run's own price, the tornado, the distribution, streams, equipment, utilities, diagram, the values read back and who set each, and the flowsheet's own questions; the newest run is the service's (`GET /api/proforma/runs`), else this browser's. Scenarios made here, the pins, the assumptions and the fermOS fits chosen are kept in this browser's Durable tier; the runs are kept by the service. The authored branch and the authored compare open the archived casein examples alone, and recharts stays there.

| Component | Implemented in |
|---|---|
| Proforma | `src/screens/Proforma.tsx`, `src/screens/ProformaScenario.tsx`, `src/screens/ProformaBiosteam.tsx`, `src/screens/ProformaReference.tsx`, `src/engine/grids.ts`, `src/engine/interp.ts`, `core/openferment_core/proforma.py`, `core/openferment_core/flowsheets/` |

### Runbooks

**Claims to be tested.** `/runbooks` · chord `g r`

The outbound falsifiable claim, the protocols that execute it, and the Depositions that report back. This is where the arrow reverses.

Views: [Protocols](#) `/runbooks/protocols` · [Depositions](#) `/runbooks/depositions`

| Component | Implemented in |
|---|---|
| Runbook | `src/screens/Runbooks.tsx`, `src/data/runbooks.ts`, `src/screens/RunbookLedger.tsx`, `src/engine/ledger.ts` |
| Deposition | `src/screens/Deposition.tsx`, `src/screens/Depositions.tsx`, `src/components/DepositionPanel.tsx` |

### Dominion

**What is fenced, what is open.** `/dominion` · chord `g d`

The molecule catalogue and the patent layer. Clearance is built; Claim Workbench, Priority Engine, Enablement and Notary are not.

Views: [Molecules](#) `/dominion/molecules` · [Clearance](#) `/dominion/clearance`

| Component | Implemented in |
|---|---|
| Clearance | `src/engine/clearance.ts`, `src/data/clearanceFindings.ts`, `src/components/Clearance.tsx` |

Not built: Claim Workbench, Priority Engine, Enablement, Notary.

### Primer

**How the system works.** `/primer` · chord `g n`

The platform taught through itself. Every embedded widget in a lesson is the real component operating on real session state. A lesson may count toward Guild's skills (OF-BLD-013): passing its checkpoint records a lesson passed on the learner's ledger, which puts them at Learning, and My path shows one person the next step on each skill, from lesson to bench. Practice drafts a scenario from the protocol steps and the bench runs that need a skill, and a tutor questions the trainee's reasoning; the model writes words and cites sources, every value is copied from its source, and a closed session goes on the learner's ledger as practice. The drafts and the tutor are model calls the service makes in `core/openferment_core/practice.py`.

Views: [My path](#) `/primer/path` · [Practice](#) `/primer/practice`

| Component | Implemented in |
|---|---|
| Primer | `src/screens/Primer.tsx`, `src/screens/PrimerLesson.tsx`, `src/screens/PrimerPath.tsx`, `src/screens/PrimerPractice.tsx`, `core/openferment_core/practice.py` |

### Guild

**Who may verify.** `/guild` · chord `g g`

The Guild of Applied Life: who may verify a record, and who may perform, cosign and witness a protocol step. The review queue keeps `/guild`. Beside it, the competence ledger (OF-BLD-013): people, the skills protocol steps need, and every entry an assessor signs, from which each person's level on each skill is computed and never stored. The rules live in `core/openferment_core/guild.py`; the ledger is `core/data/guild.json`, which is gitignored. Checks are proposed each night by fixed rules over the ledger (`src/engine/checks.ts`, mirrored in `core/openferment_core/checks.py`), each with its reasons written out and a brief the model drafts with no number in it; an assessor schedules one, dismisses it with a reason, or runs it at the bench one criterion at a time and signs it, which writes a witnessed entry per skill. The person checked never sees a check that names them until it has been run.

Views: [Matrix](#) `/guild/matrix` · [People](#) `/guild/people` · [Skills](#) `/guild/skills` · [Checks](#) `/guild/checks`

| Component | Implemented in |
|---|---|
| Guild of Applied Life | `src/screens/Guild.tsx`, `src/screens/GuildMatrix.tsx`, `src/screens/GuildPeople.tsx`, `src/screens/GuildSkills.tsx`, `src/screens/GuildChecks.tsx`, `src/screens/BenchCheck.tsx`, `src/engine/competence.ts`, `src/engine/checks.ts`, `core/openferment_core/guild.py`, `core/openferment_core/checks.py` |


## The full component map

Eighteen named components across seven layers, each owned by one of the eleven.
Internal machinery — Audit, Witness, Clearance, Deposition and the unbuilt
patent pieces — is not a destination and names the destination it lives inside,
so "where does this live" has an answer for every component rather than only
for the ones with a rail entry.

| Component | Layer | Lives in | Surfaced as |
|---|---|---|---|
| Postdoc | The agent | `src/lib/postdoc.ts`, `src/screens/Postdoc.tsx`, `core/openferment_core/postdoc_agent.py`, `core/openferment_core/validate.py`, `core/openferment_core/module_stores.py`, `core/openferment_core/tools/`, `core/openferment_core/audit.py`, `core/openferment_core/proposals.py`, `core/openferment_core/evidence_pool.py` | the rail, /postdoc |
| Intake | Evidence in | `src/screens/IntakeIngest.tsx`, `src/screens/Intake.tsx`, `core/openferment_core/intake.py`, `core/openferment_core/extract.py` | the rail, /intake |
| BioRepo | Evidence in | `src/data/`, `src/engine/retrieval.ts`, `src/screens/BioRepo.tsx`, `core/openferment_core/biorepo.py`, `src/screens/BioRepoArtifacts.tsx`, `core/openferment_core/artifacts.py`, `src/screens/BioRepoSearch.tsx`, `core/openferment_core/passages.py`, `core/openferment_core/retrieve.py`, `src/components/figures/` | the rail, /biorepo |
| geneOS | Computing | `src/screens/GeneOS.tsx`, `src/screens/Organisms.tsx`, `src/screens/StrainPage.tsx`, `src/engine/geneos/enumeration.ts`, `src/screens/GeneOSModel.tsx`, `core/openferment_core/geneos.py`, `core/openferment_core/workers/geneos_worker.py` | the rail, /geneos |
| fermOS | Computing | `src/screens/FermOS.tsx`, `src/screens/FermOSForecast.tsx`, `src/engine/series.ts`, `core/openferment_core/fermos.py` | the rail, /fermos |
| Proforma | Computing | `src/screens/Proforma.tsx`, `src/screens/ProformaScenario.tsx`, `src/screens/ProformaBiosteam.tsx`, `src/screens/ProformaReference.tsx`, `src/engine/grids.ts`, `src/engine/interp.ts`, `core/openferment_core/proforma.py`, `core/openferment_core/flowsheets/` | the rail, /proforma |
| Primer | Keeping it honest | `src/screens/Primer.tsx`, `src/screens/PrimerLesson.tsx`, `src/screens/PrimerPath.tsx`, `src/screens/PrimerPractice.tsx`, `core/openferment_core/practice.py` | the rail, /primer |
| Audit | Keeping it honest | `src/components/Provenance.tsx`, `aggregateExclusion() in src/store.ts`, `core/openferment_core/basis.py` | provenance ticks and their labels |
| Witness | Keeping it honest | `src/screens/Witness.tsx`, `src/engine/metrics.ts`, `core/openferment_core/witness.py`, `core/openferment_core/rageval.py`, `src/components/RetrievalScorecard.tsx` | a BioRepo tab, /biorepo/witness |
| Common Seal | Keeping it honest | not built | — |
| Claim Workbench | Patents | not built | — |
| Priority Engine | Patents | not built | — |
| Clearance | Patents | `src/engine/clearance.ts`, `src/data/clearanceFindings.ts`, `src/components/Clearance.tsx` | a Dominion tab, /dominion/clearance |
| Enablement | Patents | not built | — |
| Notary | Patents | not built | — |
| Guild of Applied Life | People and permissions | `src/screens/Guild.tsx`, `src/screens/GuildMatrix.tsx`, `src/screens/GuildPeople.tsx`, `src/screens/GuildSkills.tsx`, `src/screens/GuildChecks.tsx`, `src/screens/BenchCheck.tsx`, `src/engine/competence.ts`, `src/engine/checks.ts`, `core/openferment_core/guild.py`, `core/openferment_core/checks.py` | /guild |
| Runbook | Assay | `src/screens/Runbooks.tsx`, `src/data/runbooks.ts`, `src/screens/RunbookLedger.tsx`, `src/engine/ledger.ts` | the rail, /runbooks |
| Deposition | Assay | `src/screens/Deposition.tsx`, `src/screens/Depositions.tsx`, `src/components/DepositionPanel.tsx` | a Runbooks tab, /runbooks/depositions |

## Named nothing yet

Code that sits in a layer without a name of its own.

| What | Layer | Lives in | Does |
|---|---|---|---|
| _the unit engine_ | Keeping it honest | `src/engine/units.ts`, `src/engine/scale.ts` | Units, conversion, scaling, and refusals that carry their reason |
| _the worker runner_ | Computing | `core/openferment_core/workers/` | Runs a simulator in a process of its own, kept warm, restarted on a timeout or a crash |

## Reading the map

**"not built" is a real entry.** Five of the components have no code behind
them. They are in the table because the table is the architecture, not an
inventory of what happens to exist — and because a name with nothing under it
is a smaller problem than a system with no name for the thing it is missing.

**A destination can be thin and still be in the rail.** pureOS has a screen,
the unit-operation vocabulary and no process model of its own: it reads the
train a Proforma run simulated, and decides nothing yet. fermOS had a screen and five
named subsystems with no code until kinetics arrived, fitted from depositions
alone; transport, operating mode, scale and control are still named and not
built. Putting them in the navigation from day one means that when the work
arrives the question is what the destination does with it, not where in the
navigation it should go. Each screen says what it lacks rather than implying
otherwise.

**A program is not a destination.** The corpus serves three research programs
(`src/data/programs.ts`): yeast ethanol, active, and casein and PHA, archived
(OF-BLD-016). A program cuts across the eleven: its papers sit in BioRepo, its
hosts in geneOS, its scenarios in Proforma, its runbooks and protocols in
Runbooks. So it is a filter every destination applies through one selector in
the store, not a twelfth entry, and the one switch that shows archived programs
lives in Settings → Programs.

**The Assay layer is where the arrow reverses.** Everything above Runbook is
software reasoning about the world. Deposition is the world reporting back.
Runbook is an outbound falsifiable claim; Deposition is the inbound account of
what actually happened, and it is the only ground truth the platform gets about
its own predictions.

**Proforma prices a train; pureOS decides it.** Asking what a centrifugation
step costs at ten cubic metres is an economics question. Asking whether
centrifugation or filtration suits a cell-wall-deficient alga is a process
question. They were living in the same place, and now they are not.

**One boundary is still open: mass balance.** It is listed under Proforma today,
and a mass balance is a statement about a process train rather than about money.
The cleaner split would be *pureOS specifies the train and its recovery;
Proforma prices whatever pureOS specifies* (OF-BLD-011 §6). The code now
answers it the other way, for the moment: the train is a flowsheet
on Proforma's shelf, BioSTEAM closes its mass balance in the Proforma worker,
and pureOS reads each unit's recovery out of the run artifact (OF-BLD-019
Phase 4). pureOS specifies nothing yet. It is recorded here rather than settled
quietly, because whoever builds train selection will otherwise settle it by
accident.

**Attribution survives the reorganisation.** `ComponentTag` names the component
that did a piece of work, which is a different job from naming the surface you
are standing on. A tag reading `Clearance · not searched` is still correct now
that Clearance is a Dominion tab.

**One name is a phrase.** "Guild of Applied Life" is the component; `Guild` is
the short form used in the rail, in attribution, and in code identifiers.
