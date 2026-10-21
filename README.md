# openFerment — the prototype

A working prototype of **openFerment**: an agentic RAG platform for precision fermentation and
bioprocessing, built around a literature corpus, values extracted only when a sentence of the
paper states them, executable protocols, flux-balance yield ceilings, kinetic fits of deposited
runs, and techno-economic modeling. A React front end (`src/`) over a Python service (`core/`)
that fetches and indexes papers, calls the model and computes; with the service down the app is
its seed, and each screen says what it lacks.

This repository implements **OF-DES-001 v0.1** (front-end design and working-simulation plan)
against the corpus of **OF-COR-001 v1.0** (`docs/OF-COR-001.md`). `docs/DEMO.md` is the run sheet
for showing it.

## The programs it is built around

The corpus serves three research programs, declared as data in `src/data/programs.ts`. One is
active and two are archived. An archived program's papers, values, strains, products,
scenarios, protocols, runbooks and lessons stay in the repository and leave every default
view, count, suggested question and Postdoc evidence pool; one switch, Settings → Programs →
*Show archived programs and examples*, brings them all back exactly as they were. Nothing is
deleted (OF-BLD-016).

| Program | Threads | Status | Papers in the seed |
|---|---|---|---|
| Yeast ethanol | Q | active | 22 |
| Casein | A–O | archived | 132 |
| PHA | P | archived | 35 |

**Yeast ethanol, the active program**: ethanol from glucose by wild-type *Saccharomyces
cerevisiae* in batch, thread Q, proposed by a fixed rule (`pnpm thread:propose:q`) and applied
on Sean Creighton's approval on 2026-10-20: **22 sources**, two NREL reports from OSTI (the corn
stover design report by Humbird et al. and its successor by Tao et al.), the Saccharomyces Genome
Database entries for S288C and CEN.PK113-7D, and 18 open-access kinetics and physiology papers,
all 22 fetched with full text. Extraction on Haiku anchored **163** values to sentences, all
`unverified` until a person decides them in Guild. geneOS carries two reconstructions of
*S. cerevisiae* S288C, Yeast9 and iMM904, each giving an ethanol ceiling on glucose; Proforma's
stored BioSTEAM benchmark prices the Humbird design, its shelf carries the `biorefineries`
package's dry-grind corn ethanol plant as the program's reference biorefinery, and the seed's
`sc-yeast-1` runs a glucose-to-ethanol flowsheet of our own whose process inputs bind to thread Q
records. Its hosts are the two SGD strains. There is no ethanol product in Dominion's catalogue
yet. `docs/DEMO.md` is the run sheet for showing it.
Home's **Programs** strip counts this program live and names the archived two in one line.

**Casein, archived**: threads A to O, curated by hand before Intake existed, around one
question:

> **Can phosphorylated bovine β-casein be expressed in the cell-wall-deficient
> *Chlamydomonas reinhardtii* strain cw15?**

Caseins have been expressed in bacteria, in yeast, and in plants. They have never been
published in a microalga — Mora Vásquez et al. (2025) tabulate 17 bacterial, 5 yeast and 2
plant studies with no algal row. The case for cw15 assembles from four established facts: a
real ER/Golgi secretory pathway (12–15 mg/L secretion established from UVM4), FDA GRAS status,
cell-wall deficiency as a downstream asset (~3× protein release under pulsed electric field),
and the observation that Ser-x-Glu phosphorylation by FAM20C — what makes casein assemble,
bind calcium and coagulate — is done natively by no yeast, plant or bacterial host. The corpus
keeps the counter-example that complicates this: H4 reports *Pichia*-expressed bovine β-casein
carrying the same degree of phosphorylation as the animal-derived protein, with no kinase
co-expressed.

The honest counterweight is seeded too: nuclear transgene expression in *Chlamydomonas* is
historically weak (~0.2% TSP **for intracellular reporters** — a reporter ceiling, never
measured on a casein or on a secreted product), secreted yields sit two to three orders below
*Trichoderma*
β-lactoglobulin, and whether *C. reinhardtii* even has a Fam20-family kinase is an **open
question the app labels as open** rather than answering.

**PHA, archived**: polyhydroxyalkanoates from waste cellulosic sugars, thread P (OF-BLD-014
Phase 2). Its 35 papers (P1–P35) were proposed by the fixed Europe PMC rule
(`pnpm thread:propose`) and approved by Sean Creighton on 2026-10-14 (`pnpm thread:apply`); all 35 are
fetched with full text, and extraction has anchored **303** values on them, each `unverified`.
It holds no hand-curated record. Two hosts (*Cupriavidus necator* H16, *Pseudomonas putida*
KT2440), two products (PHB, mcl-PHA), five polymer ontology fields and the BioSTEAM scenario
`sc-pha-1` belong to it.

The seed's runbooks, the seven casein protocols, the three authored cost scenarios and the casein
lessons describe runs nobody made. They are flagged `example: true`, hidden with the archived
programs, and shown by the same switch under a banner that says so.

## What is real, and what is modeled

Measured on 2026-10-20 in the build checkout, over the data on `openferment-data`. Nothing a user
sees by default is invented: there is no scripted agent, no sample team, no sample run and no
sample figure on any screen, and the seed's runbooks, casein protocols, authored cost scenarios and
casein lessons, which describe runs nobody made, are flagged as examples and hidden with the
archived programs (above).

| Layer | Status |
|---|---|
| Papers, venues, identifiers | **Real, unevenly keyed** — 189 catalogued entries: 132 in threads A–O, 35 in thread P and 22 in thread Q, the last two approved by rule and by name. 114 carry a DOI, PMCID or PMID, two (the SGD strain entries) a source URL alone, and 73, all in threads A–O, carry none. `pnpm ids:propose` asks Crossref for a DOI for each of the 73 and a person approves each one before `pnpm ids:apply` writes it into the seed |
| Full text | **Real, when fetched** — **88** papers return full text from Europe PMC, OSTI or SGD (`pnpm intake:fetch --all`): 31 of threads A–O, all 35 of thread P and all 22 of thread Q; 26 of threads A–O have no open-access text there (B1 and D1 sit outside Europe PMC's open-access subset, where its full-text endpoint answers 500). Fetched text stays on the machine that fetched it; the rest show the curator's note and say so |
| Extracted values | **Real** — 132 curated records traceable to a source, plus 2 `industry-estimate` figures with no source document (all casein, archived); and **500** values the extractor anchored to a sentence of a fetched paper: **163** on thread Q, 303 on thread P, 34 on threads A–O. Every one is `unverified` until a person decides it in Guild |
| Extractor run | **Real** — `claude-1`, one structured response per fetched paper, every candidate anchored to a verbatim quote or dropped and counted; in this build on `claude-haiku-5-5` at effort `medium` by the owner's rule (`llm.py`'s defaults are Claude Opus 5.5, then Claude Sonnet 5.5). Thread Q's run anchored 163 values and dropped 15 for $0.25 |
| Verified records | **0** — `core/data/biorepo.json` holds no decision. A verified record is one a named reviewer (Settings → Reviewer name; the service refuses `you`) promoted against a quote in the paper's own text, through `biorepo.write` |
| Strains, protocols, ontology | **Real** — drawn from the literature and standard bench practice. Two protocols show by default (`PR-OD-01`, `PR-CIP-01`, generic methods); the seven casein protocols are examples |
| Guild's competence ledger | **Real, when kept** — people, sign-offs, runs and lessons passed, in `core/data/guild.json` on the Mini, which is personnel data and never enters git; levels are computed from it and never stored. With no ledger, Guild and Home's Workforce card say so and offer the form to add the first person, as the lead |
| Witnessed checks | **Real, when run** — proposed each night by fixed rules over the ledger, with every reason written out; scheduled, dismissed or run at the bench by a named assessor, whose calls and words become witnessed entries on the ledger. The brief beside each check is model-written words with no number, told what the ledger shows and never who. Kept in `core/data/checks.json` on the Mini, out of git |
| Practice scenarios and tutor sessions | **Model-written words over copied values** — the model drafts each scenario and asks each tutor question, writing no number of its own; every value in a scenario's evidence pane is copied by the service from the protocol step, material or bench run it cites. A session goes on a person's ledger only when that person is on it. Kept in `core/data/practice.json` on the Mini, out of git |
| Yield ceilings | **Computed by flux balance analysis** on published reaction networks (geneOS → Model): for ethanol, Yeast9 (yeast-GEM v9.1.1) and iMM904, two reconstructions of *S. cerevisiae* S288C, each giving **0.5114** g g⁻¹ on glucose (OF-BLD-016 B.1); for PHB (archived), `e_coli_core` and `iJO1366` as bundled with cobra with the phaCAB route added, and `RehMBEL1391` for *C. necator* H16, fetched at its pinned commit and hash. A ceiling has no time axis and no vessel; geneOS → Model draws thread Q's reported ethanol yields beside it and rings one above it for a reviewer, and Proforma's ceiling check reads a scenario's fermenter yield against it, flagged and never clamped (OF-BLD-019 Phase 5) |
| Computed values | **Computed, with a basis** — a value no paper states (a converted unit, a yield ceiling, a fitted rate, a price) carries the calculation behind it: the tool, its version and every input with its source. Its provenance follows from those sources (`basis_provenance`), and BioRepo → Artifacts keeps each one and replays it. **29** kept on `openferment-data` (25 before OF-BLD-019 §7.1 added two reference runs, a scenario run and a property answer) |
| Retrieval | **Real, measured** — 88 fetched papers cut into **7,179** passages of their own words, with meaning vectors from `BAAI/bge-small-en-v1.5`. Witness → Retrieval's scorecard is measured on thread Q (2026-10-20T07:46:46Z): K 85 questions, S 83, F empty; the rule's score (mean nDCG@10 on K and S) bm25 0.4226, bm25+expand 0.4294, hybrid 0.4587, bm25+rerank **0.5942**, hybrid+rerank not scored. The rule chose bm25+rerank; search is held on **hybrid** (`core/data/index/config.json`), because each reranked search is a model call of about twenty seconds, and Witness names both the lane in use (`laneInUse`) and the rule's choice |
| Fits and forecasts of runs | **Computed from depositions** (fermOS): a run's timed readings are fitted with a growth rate and a kinetic model (logistic growth, Luedeking–Piret production, the substrate balance), each fit kept as an artifact with the deposition as its source, and a forecast is a band for readings drawn from one fit. On synthetic runs the fit returns its generating parameters within 0.1 % and the band holds a fresh reading in 33 to 35 of 40 runs. A fit or forecast can feed a Proforma scenario's titre, yield and productivity when a person chooses it (OF-BLD-019 Phase 5). No run is deposited, so nothing real has been fitted and no fit is on file to feed a scenario: fermOS says *No run deposited yet* and names the readings to deposit and where |
| Predictions and their score | **Locked, and scored by runs** — a prediction is a point, an interval or a bound, locked with what it rests on; Runbooks → Ledger draws each against what reconciled runs measured and counts locked, tested, held, missed and inconclusive runs. The seed's ten runbooks (eight of them locked) are examples, so by default the ledger counts zero and says why; no run has tested a prediction. Postdoc can draft a runbook whose numbers the service writes from artifacts and records |
| Simulation economics, authored | **Modeled, and examples** — the three scenarios S1–S3 are illustrative casein cost surfaces written by hand, not validated, labelled *Cost model v0*, and hidden with the archive |
| Simulation economics, BioSTEAM | **Simulated, from a shelf of four flowsheets** (OF-BLD-019 Phase 2). Two are published reference biorefineries run whole on their package's own defaults: the stored benchmark, `biorefineries.cornstover`, reproduces the NREL 2011 corn stover design at **1.9677** USD per gallon against 1.968 (2026-10-15), and `selling_price` cites it, as it cites the newest kept run of a seed BioSTEAM scenario the program switch shows; the dry-grind corn ethanol plant, `biorefineries.corn`, the yeast program's reference, matched all eleven values its package's own test asserts on this installation, the largest relative difference 1.8×10⁻⁵ against the test's 5 % (measured in the build, STATE.md §2.2). Two are ours: `sc-yeast-1` runs glucose to ethanol, three of its process inputs bound to thread Q records and its productivity, plant scale and glucose price waiting; `sc-pha-1` (archived with PHA) runs fermentation, harvest and drying of PHA. Each scenario run draws 500 seeded samples by default and is `demo` while any input rests on a named person's assumption. Kept on `openferment-data` since OF-BLD-019 §7.1: the corn plant's reference run (`1b2f2c463c872086`), the corn stover plant's through the reference endpoint (`42f80a77d306f673`, 1.967671122 USD per gallon, nine of its package test's eleven values within tolerance, the two misses the package's own on this lock), and one run of `sc-pha-1` (`23c3304c1c35e26d`, `demo`), made in §1.2 on stand-in assumptions under the reviewer name *OF-BLD-019 session* (a test entry), whose base case could not run; no run of `sc-yeast-1` is kept: three of its inputs wait for Sean |
| Vessel designs | **Designed by BioSTEAM, from a kept simulation and a person's scale** (OF-BLD-020 Phase 4) — fermOS → Vessel sizes the vessels a kept batch simulation needs (or, anaerobic, a kept fit) with BioSTEAM's own fermenter classes, in the Proforma worker: how many, how large, the batch cycle, agitator and compressor power, cooling, the oxygen the vessel transfers against the uptake the simulation takes, and BioSTEAM's own cost. Every design parameter is in the parameter panel with its source. The scale is always a named person's assumption, so every design is `demo`. None is kept on `openferment-data` (2026-10-21 05:51 UTC): no simulation is kept yet, because its parameters wait for Sean (STATE.md §3.5), so no vessel has been designed outside the tests and the service double, which design on stand-in simulations (§4.3, run owed) |
| Downstream trains | **Read from a simulated run, never typed** — pureOS reads the train of the newest Proforma run of each scenario from the one artifact that run kept (OF-BLD-019 Phase 4): unit by unit in run order, the mass in and out, the product in and out, the product each unit passes on toward the product stream and what it loses and to which outlet, its recovery and the share still on the path, and the overall recovery. Nothing is simulated again on read. A train exists once somebody runs a scenario. The one scenario run on `openferment-data`, `sc-pha-1`'s (archived), has a base case that could not run, so its train names no product and reads no recovery, and says why; no yeast train is on file, and pureOS says so and how to make one |
| Physical properties | **Computed by thermosteam**, BioSTEAM's property engine, in the Proforma worker: density, heat capacity, viscosity, and bubble and dew points of a run's stream, or of a preset the service fills (the ethanol–water azeotrope, or water and ethanol at a titre record's value). Each answer is an artifact whose basis names the library and its version; a chemical the library lacks is refused in words. One is kept on `openferment-data`: §7.1's beer at a thread Q titre record (`cfdfdee7ec2bae37`, `unverified`, the record's mark) |
| Agent answer prose | **Real model calls in a bounded loop** — Postdoc on the configured model (`claude-haiku-5-5` in this build), restarted once on the fallback on a refusal or an outage, through `openferment-core`. Code sweeps the eleven modules first; the loop reads them, searches the records and passages (at most 6 rounds, 12 tool calls, the per-question cost cap and 180 seconds), and answers with claims that carry no numbers of their own, each citing records, module rows, quoted sentences checked word for word against their passages, or computed values. There is no scripted mode: with the service down Postdoc says so, keeps the history, and offers nothing in its place. The eleven run-sheet questions, each asked twice on 2026-10-20, cost $0.1072 for the 22 and took 8–53 s each (`docs/DEMO.md`). The 13 authored flows are an evaluation set, graded against and never offered |

The corpus is real literature, and since OF-BLD-016 nothing on screen is invented. `demo` is a
provenance, not a mode: it marks a value modeled rather than measured (an authored cost surface, a
computed value resting on a named assumption), and it is one of the two dashed ticks. Everything
else carries its actual provenance.

"Real" is not the same as "complete", and the app is built to say so. Of the 132 casein entries,
36 carry a DOI, 59 carry some persistent identifier, 50 record no authors, and 18 sit at
`year: 0` because OF-COR-001 states no year. `curated` — the provenance on 132 of the 134
seed records — means *transcribed from the curation document and not yet checked against the
source PDF*. It does not mean verified. A record becomes `verified` only through a review decision
in Guild, which `biorepo.write` stores in `core/data/biorepo.json` and `pnpm export:corpus` merges.

### Seed inventory

The seed is what the app is with the service down. With it up, an overlay adds what has been
fetched, extracted and decided (OF-BLD-012 §2.1); the seed itself does not change. Counts from
`pnpm -s check:seed` and the seed files, 2026-10-20; "shows" is the default view, with archived
programs and examples hidden.

```
  3 programs        Yeast ethanol (thread Q, active) · Casein (A–O, archived) · PHA (P, archived)
189 papers          ingest 'catalogued' in the seed: 132 hand-curated in threads A–O (metadata +
                    curator note), 35 in thread P and 22 in thread Q proposed by rule and approved by
                    Sean Creighton; 104 open access. Each fetches as full text through the service,
                    and the reader says which it shows. 22 show
134 records         132 curated · 2 industry-estimate · 7 non-primary; all on casein papers, so none
                    shows (thread Q's 163 values are extracted candidates, arriving with the service)
 40 ontology fields  7 families: expression, PTM, functional, cultivation, downstream & economics,
                    polymer, growth and product kinetics
  8 ontology gaps   real values the v1 ontology cannot express, recorded rather than dropped
 19 strains         4 casein (cw15, UVM4, C. reinhardtii wild type, the bovine reference), 2 PHA
                    (C. necator H16, P. putida KT2440), 2 yeast (S288C, CEN.PK113-7D, from SGD) and 11
                    general comparator hosts; 13 show
119 molecules       12 categories, 11 process families, all modeled; 116 show (β-lactoglobulin is
                    casein's, PHB and mcl-PHA are PHA's)
  9 protocols       10 versions, 126 steps; PR-OD-01 and PR-CIP-01 show, the seven casein ones are
                    examples
 10 runbooks        29 predictions, 8 runbooks locked with their digests; all ten are examples
  5 scenarios       S1–S3 over 3 authored cost models, casein examples; sc-pha-1 (PHA's) and sc-yeast-1
                    (yeast ethanol's) run flowsheets on Proforma's shelf; sc-yeast-1 shows
  7 learn modules   12 lessons, 42 checkpoint questions; m6 (3 lessons) shows, m0–m5 are examples
 11 Postdoc prompts the yeast five and six across the modules
 13 eval flows      graded against, never offered
 14 skills          6 families, tagged on 36 protocol steps across 3 protocols; 3 bench lessons count
                    toward 6 of them
```

## Postdoc runs on a model, and reaches every module

Postdoc's answers come from a real model call, routed through `core/` — a
Python service (`openferment-core`) that is the first surface of the tool layer
everything else will eventually orchestrate. The key lives in `core/.env`,
which is gitignored; it never reaches the browser, and `pnpm check:secrets`
fails the build if anything under `src/` so much as names it.

```
browser ──POST /api/ask/stream──▶ FastAPI
                                    ├─ the coverage pass, code: all eleven modules swept for what the
                                    │    question names; the map goes in round one and is the first trace line
                                    ├─ the loop: the model calls its tools — search_records, search_passages,
                                    │    convert_units, yield_ceiling, growth_forecast, selling_price,
                                    │    draft_runbook, thermo_props, run_flowsheet, stream_table, and a read
                                    │    and a write tool for every module — each step streamed to the browser
                                    │    as it completes
                                    ├─ budget spent (6 rounds, 12 calls, cost, 180 s): one last turn, no tools
                                    ├─ a refusal or outage: asked again once, on the fallback model
                                    ├─ validate_plan: no number, nothing cited that no tool returned,
                                    │    every quote in its passage word for word
                                    └─ AnswerPlan, with its trace, its coverage map and why it stopped
browser ◀───────────────────────────┘   renders values from the cited records, rows and artifacts
```

Every model call in this build runs **`claude-haiku-5-5` at effort `medium`** by the owner's
rule (`OPENFERMENT_MODEL`, `OPENFERMENT_FALLBACK_MODEL`, `OPENFERMENT_INDEX_MODEL`,
`OPENFERMENT_EFFORT` in `core/.env`); `llm.py`'s defaults, with those unset, are Claude Opus 5.5
falling back to Claude Sonnet 5.5.

`POST /api/ask` answers with the same plan in one response, and `mode: 'single'` keeps the
earlier path: one BM25 retrieval over `corpus.json`, one structured response. Text inside a tool
result is evidence to weigh; a passage that tells the model to state a number changes nothing the
validator lets through.

**Claim text may not contain a number.** The model writes prose and cites a
record; the interface renders the value from that record. This is the strongest
available form of Rule 1 — the model is not being asked to be careful with
quantities, it has no slot to put one in. A claim carrying a number, citing an
id that does not resolve, or citing nothing without admitting it is **dropped
and counted, never repaired**: a validator that patches model output is a
validator that hides model failure.

Provenance on a claim is computed server-side as the weakest of its cited
records and computed values; a claim resting on quoted sentences alone is
`unverified`. A claim resting on one gold record and one industry estimate is an
industry estimate.

To run it:

```bash
cp core/.env.example core/.env      # add your key; the file is gitignored
pnpm export:corpus                  # project the TS seed to core/.../corpus.json
cd core && uv run uvicorn openferment_core.api:app --reload
pnpm dev                            # /api proxies to localhost:8000
```

A key that is not scoped to a workspace is refused with a 400 that asks for the
workspace's id. Put the id in `core/.env` as `OPENFERMENT_WORKSPACE_ID`; every
client sends it as the `anthropic-workspace-id` header, and `pnpm ready` names
the setting when the 400 comes back.

Postdoc has one path, the service. If the service is not running the page says
*Postdoc needs the service*, tells you what to type (`pnpm prototype:up`), keeps
your conversations, and puts a question it could not ask back in the box. There is
no scripted mode to fall back to: a convincing fake standing in for a broken service
is worse than a blank screen, because everything looks like it is working.

Its empty state offers the yeast program's five questions and six that cross the
modules (`src/data/livePrompts.ts`), filtered by program. The thirteen authored
conversations of the casein and PHA flows are an evaluation set, graded against and
never offered: `pnpm test:live` asks the real pipeline each one and checks the plan
cites the records a human said were the answer. `pnpm verify` stays offline and
needs no key.

Every model call goes through `core/openferment_core/llm.py`. With nothing set it asks **Claude Opus
5.5** first and **Claude Sonnet 5.5** when Opus declines or is unavailable (this build sets Haiku for both, above), and it
records which model answered in the plan's `usage.models`, shown beside the cost.
Both models reject forced tool use, so the plan comes back through structured
outputs: JSON that matches the schema, checked by the API, with no free-text way to
answer. `OPENFERMENT_MODEL`, `OPENFERMENT_FALLBACK_MODEL` and `OPENFERMENT_EFFORT` in
`core/.env` change the models and how hard they think (`medium` by default); the
fallback may name several models, comma-separated, tried in order.

Both models run safety classifiers, a biology one among them, and a question about
fermentation can trip it. A declined request comes back as a refusal; the same
request goes to Sonnet; a question both decline comes back as a declined plan that
says so. A refusal in the biology category is billed even though it produced
nothing.

Expect a few cents a question at 30 records on Opus (thinking included), less when
Sonnet answers; the plan shows the exact cost. Set a spend limit in the Anthropic
console first, not because the volume is risky, but because a cap turns a runaway
loop from a bill into a bug report.

### Postdoc reaches every module

Found in use on 2026-10-16: asked what is open in Dominion, Postdoc said the corpus held
nothing, while the Dominion screen showed the molecules. It could read records and passages and
nothing else. Now (OF-BLD-015 Phase 7, `docs/TOOLS.md`):

- **Before its first turn, code sweeps all eleven modules** for what the question names and
  hands the model the map. The trace's first line opens to one line a module; the footer says
  *Searched eleven, found in two: Dominion (1), Runbooks (1) · read in part: Runbooks, fermOS,
  BioRepo* (what still lives only in a browser is named). A follow-up ("which of those are
  fenced?") is swept together with the earlier questions it reads, never with the earlier
  answers, so the map follows the conversation.
- **Every module has a read tool** (`dominion_read` … `home_read`) returning rows in one shape
  with one computed state: `open`, `fenced`, `approved`, `locked`, `proposed`, `retired`. A
  claim cites rows the way it cites records, and the screen shows each under the claim with
  its state. A row no tool returned in that run cannot be cited.
- **Every module has a write tool** (`dominion_write` … `home_write`), and it never touches a
  store: each action calls the module's own write function or refuses in words naming the
  person who makes the change. What a model writes lands in the open lane marked as the
  model's, in the audit log (`GET /api/audit`), until a person promotes it. A candidate a
  model writes by hand is anchored to a sentence like the extractor's, kept in its own file
  (`candidates/hand/`), and never counted as an extraction: the extractor still runs on the
  paper, and Witness never scores it.
- **Seven gates** (publish, spend, lock, sign, personnel, bench, notebook) stop an action and
  turn it into a proposal. Home shows each as a card with one button; the button carries it
  out in the reviewer's name, and nothing is signed by a model. A proposal's words hold no
  number, one ask leaves one open proposal of a kind, and a proposed check shows only to the
  lead and assessors, never to the person it names. A model may propose a check and never
  record one: an assessor runs it at the bench.
- **A plan's gaps and its decline are held to the number rule** like its claims: one holding
  a number is dropped and named, and the decline the code writes stands in.
- **Postdoc runs a flowsheet and reads its streams** (OF-BLD-019 Phase 6). `run_flowsheet`
  takes a seed BioSTEAM scenario's id and nothing else and runs it as the service binds it: a
  free write through `proforma.run` (compute, no model money), at no gate, audited as the
  model's. The service holds no person's assumption, so an input no record binds waits and the
  tool says which; a scenario made with New scenario lives in the browser that made it and is
  refused in words. `stream_table` reads a kept run's stream table (a scenario's or a reference
  biorefinery's), its summary cut to what a model may read with the count left out said, the
  whole table in `ToolResult.data`, which the endpoint and the MCP server return and no model
  reads. `selling_price` reads the newest kept run of any seed BioSTEAM scenario the program
  switch shows (`sc-yeast-1`; `sc-pha-1` too with it on), and with none kept names what waits
  and how a run is made; it runs nothing. Each cites the run by its artifact id, and Postdoc's
  prompt asks that a price, a cost or a recovery read from a run cite that run. With the switch
  off, a run of an archived program is hidden from every registry tool that reads runs, from
  pureOS's trains and from BioRepo → Artifacts by one rule, `module_stores.artifact_program`
  (a run is its scenario's, its flowsheet's and its basis's program, an archived one winning);
  the MCP server's `get_artifact` still reads any kept artifact by its id.

`pnpm check:tools` holds its rules in `verify`: a read and a write tool for every module;
`tools/writes.py`, read as parsed Python so a write function reached through an aliased import
is still caught, calling only the module write functions it names; no other tool file reaching
what keeps a Proforma run or writes an audit line, found by following every function of the
service that does, through its imports (rule 2b); a person's name on every gated action; one
gate table in two places; and every name in the closed registry written down. `pnpm eval:o`
runs ten cross-module questions and scores whether the right modules were read (on Haiku,
2026-10-20: searched 80 %, five cents). The footer is not scored: its key and the footer come
from the same coverage call, so it could not miss.

### The same tools, from an assistant outside the app

`core/openferment_core/mcp_server.py` is an MCP server over stdio. It lists the
thirty-two tools Postdoc uses, with the registry's own schemas, and two more:
`ask_postdoc`, which runs the loop and returns the plan, and `get_artifact`. The
registry's rules hold there as everywhere: a number typed into an input is
refused, a write goes through the module's own write function, and anything at
a gate becomes a proposal a person carries out on Home. No tool signs for a
person.

A Claude Code session in this repository picks it up from `.mcp.json`. For
Claude Desktop, add this to `claude_desktop_config.json`, with the path to your
checkout:

```json
{
  "mcpServers": {
    "openferment": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/openfermentui/core", "--all-extras",
               "python", "-m", "openferment_core.mcp_server"]
    }
  }
}
```

`ask_postdoc` spends like a question asked in the app, under the same caps.

## Running it

```bash
pnpm install
pnpm dev            # http://localhost:5173 — /api proxies to the service on :8000
pnpm build          # typecheck + production bundle
pnpm bundle:single  # one self-contained .html (inlined CSS/JS/fonts), openable from file://
```

The service, for Postdoc's live mode and for Intake's real fetch and extraction
(OF-BLD-012). Everything below needs `uv`; only `intake:extract` spends money.

```bash
cp core/.env.example core/.env        # ANTHROPIC_API_KEY — gitignored, guarded by check:secrets;
                                      # set a spend cap in the console first
pnpm export:corpus                    # project the TS seed (+ biorepo.json) to core/.../corpus.json
pnpm ready                            # before spending anything: is the key accepted, is the model there,
                                      # does Europe PMC answer. Free; --no-network for the local checks only
cd core && uv run uvicorn openferment_core.api:app --reload

pnpm intake:fetch --all               # Europe PMC (and OSTI, SGD for thread Q's source URLs) →
                                      # core/data/fulltext/ for the 116 papers with an identifier or a source:
                                      # 88 return full text, 26 casein papers are not open access (no key;
                                      # ≤ 2 requests/s, a User-Agent)
pnpm intake:extract --all             # the configured model, one structured response per fetched paper
                                      # → core/data/candidates/; prints anchored, rejected by rule, cost
                                      # (thread Q on Haiku: 163 anchored, 15 dropped, $0.25)

pnpm ids:propose                      # Crossref, one request a second, for the 73 papers with no identifier
                                      # → core/data/identifiers-proposed.tsv (gitignored). Writes NOTHING to the seed
pnpm ids:apply <file.tsv>             # writes the rows a person changed to APPROVED into src/data/corpus/ and
                                      # prints the diff to commit. PROPOSE is the script's opinion, not an approval
```

Both batch commands are idempotent — a paper already fetched or extracted is skipped unless
`--force`; an outage (a timeout, a 5xx) is not cached, so the next run asks again. Review
decisions made in Guild while the service is up go to `core/data/biorepo.json` through one write
function, signed with the reviewer name from Settings; that file is committed, `fulltext/` and
`candidates/` are not. A typed value — a correction, a gold value — has to sit in a sentence of
the fetched paper like any other number, or the write is refused and Guild says which rule.

### The prototype build's commands (OF-BLD-014)

```bash
pnpm thread:propose      # LIVE, no key: the thread P rule asks Europe PMC and writes core/data/thread-p-proposed.tsv
pnpm thread:apply <tsv> --approved-by "<name>"   # writes the APPROVED and INCLUDE rows into threadP.ts
pnpm prototype:up        # a fresh clone to the running prototype: session:start, a build, the service on
                         # 127.0.0.1:8000 over core/data/, the app on 127.0.0.1:4173. Ctrl-C stops both
pnpm session:start       # what every session runs first: core/.env from OPENFERMENT_API_KEY when the file
                         # is missing, every extra installed, the corpus, data:pull, data:prepare, pnpm ready
pnpm ready               # its last line is the lane: full (a key Anthropic accepts, Europe PMC
                         # answers), model-only (that key alone) or none
pnpm data:push           # the outputs of live runs to the orphan branch openferment-data; data:pull brings
                         # them back. Fetched full text never travels: each machine fetches its own
pnpm decisions:push      # commits core/data/biorepo.json alone as "Guild decisions <date>" and pushes
pnpm witness:numbers     # the precision and recall Witness shows, read from a running service
pnpm shots --prefix p /biorepo/witness    # photographs routes of a running app into docs/shots/
pnpm index:build         # the fetched papers cut into passages, under core/data/index/ (only changed papers);
                         # --dense adds meaning vectors, once Hugging Face answers; --all cuts everything again
pnpm rag:questions --n 100 --thread Q   # needs the key: written evaluation questions from sampled
                         # passages of one thread's papers (kept as questions-Q.jsonl)
pnpm rag:eval -- --thread Q   # every available search lane scored on K, S and F for thread Q's questions,
                         # every search over the whole index; the table goes to Witness → Retrieval and
                         # the rule's choice to core/data/index/config.json (kept on hybrid for now: above)
pnpm geneos:fetch        # the C. necator H16 reconstruction at its pinned commit into core/data/models/,
                         # checked against its sha256; a mismatch is set aside and fails
pnpm ask:batch docs/questions-yeast.txt   # needs the key: each question through Postdoc's loop, the
                         # plans under core/data/live/, one row each: kept, dropped, tools, rounds, seconds, cost
cd core && uv run python -m openferment_core.demo --prototype   # the prototype's fixtures, made by the
                         # real code paths into core/tests/fixtures/prototype/; the smoke double serves them
```

The service also answers `GET /api/tools` (each tool's name, description and input schema) and
`POST /api/tools/{name}`, the same registry Postdoc's loop calls: the seven OF-BLD-014 tools,
a read and a write tool for every module, thermosteam's `thermo_props`, and Proforma's
`run_flowsheet` and `stream_table` (`docs/TOOLS.md`). A tool input carries ids and words; a number typed into one refuses the call.
`pnpm check:tools` is the stage of `verify` that holds the write tools to their module's write
functions and the gates to a named person; `pnpm eval:o` runs eval set O live.
Every model call is charged to the UTC day's spend in `core/data/spend.json`, and `llm.py` refuses
a call that could pass `OPENFERMENT_DAILY_BUDGET_USD` (25 by default, `core/.env.example`).

### Hosting it on the Mac Mini

After a `pnpm build`, the service serves the app itself at `/` beside `/api`, so
`http://127.0.0.1:8000` is the whole of openFerment from one process (OF-BLD-012 §B.4).
`scripts/host/` turns a Mac into the always-on host (Appendix B):

```bash
# once: Homebrew, then the tools; keep the checkout OUTSIDE Documents, Desktop and Downloads,
# which macOS will not let a background job read
brew install git node pnpm uv tailscale
sudo brew services start tailscale && sudo tailscale up   # Tailscale's background service, which runs
                                                         # from power-on (its apps wait for a login)
git clone https://github.com/bytesizedyogurt/openFermentUI.git ~/openferment && cd ~/openferment
cp core/.env.example core/.env          # add the key; spend cap in the console first
scripts/host/install.sh                 # builds, sets power settings, installs both jobs, checks health
pnpm ready                              # is the live loop wired: key, model, corpus, Europe PMC, GitHub, service

scripts/host/deploy.sh                  # after every merged session: pull, install, build, restart
scripts/host/deploy.sh --keep-decisions # when Guild decisions made on the Mini need committing first
scripts/host/sync_decisions.sh          # back up the Mini's decisions alone, no deploy
scripts/host/nightly.sh                 # what the 03:00 job runs, by hand
scripts/host/install.sh --uninstall     # stop and remove both jobs
```

- **Two LaunchDaemons** (macOS's service manager, at the system level): the server, which starts at
  power-on before anyone logs in, restarts if it stops, and runs as you rather than root; and a
  03:00 job that fetches from Europe PMC, extracts from whatever arrived, proposes the night's
  witnessed checks, and drafts a brief for each check that has none. A miss older than a
  week is asked again, since papers become open access later. Logs: `~/Library/Logs/openferment/`.
- **The server listens on loopback only.** The service has no login of its own, so the bind address
  is the access control. `install.sh` runs `tailscale serve`, which publishes the port over HTTPS to
  the devices your tailnet's access rules allow (by default, only yours), with nothing opened on the
  router. Use Tailscale's background service (`tailscaled`, above): the App Store and standalone apps
  run only while someone is logged in, so after a power cut the Mini would be up and unreachable until
  a login, and `install.sh` warns when it finds one of them. A link for someone outside
  your tailnet is a Cloudflare Tunnel with a login page in front, set up by hand when it is needed.
  A request that changes something must also come from a page on openFerment's own address and
  port, so a web page you happen to open elsewhere, or another app running on the Mini, cannot post
  through your browser, and nothing arriving through Tailscale Funnel changes anything
  (`core/openferment_core/guard.py`).
  A name of your own in front of it goes in `OPENFERMENT_ALLOWED_HOSTS`.
- **Review decisions live in this checkout.** Guild writes `core/data/biorepo.json` on the Mini;
  pushing it is the backup, and `deploy.sh` refuses to pull over decisions that are not committed.
  `--keep-decisions` merges them with decisions pushed from elsewhere record by record
  (`scripts/host/merge_biorepo.py`, attached by `.gitattributes`): different records are all kept,
  and one record decided differently on two machines keeps the later decision. A record withdrawn
  on one machine and changed on the other stops the deploy with the file left valid; once the two
  machines agree, the next run goes through, because every unpushed decision is sent as one commit.
  Every clone learns the merge on `pnpm install` (the `prepare` script), so the laptop merges the
  same way.
- **FileVault** holds a rebooted Mini at the unlock screen until someone types the password; the
  server job and Tailscale's background service start after that. With FileVault off, both start at
  power-on and the login window can stay locked.
- **Host and port** default to `127.0.0.1:8000`. `OPENFERMENT_HOST` and `OPENFERMENT_PORT` at install
  time are baked into the job; `deploy.sh` and `pnpm ready` read them back from it. A reinstall without
  `OPENFERMENT_HOST` returns to loopback, so a wider address never lingers unasked.

### The offline demo

```bash
pnpm demo:offline   # no key, no network: all nine demo beats replayed from saved fixtures, on :4317
pnpm demo:offline:intake  # the intake loop with the real service in fixture mode, on :4173
```

Replays the loop from saved responses: open Intake, fetch B5, Extract, open Witness, open Guild,
decide a record, watch Witness move. The web server listens on `127.0.0.1:4173` and serves
nothing outside `dist/`; to show the demo to another machine, set `OPENFERMENT_DEMO_HOST=0.0.0.0`
on purpose. The fixtures live in `core/tests/fixtures/demo/` and say
what they are: B5's text is a structural stand-in document, and the "model response" is
hand-written in the tool's shape. The anchoring, matching, scoring and the write function are
the real code paths, and the demo writes into a scratch copy of the data directory, never into
the committed `biorepo.json`. The first run needs PyPI once, to build `core/.venv`.

To make the demo real, regenerate all three fixtures together — they only make sense as a set,
and `test_demo` checks that they still fit the code:

```bash
pnpm demo:fixtures --real     # needs network (Europe PMC for the JATS) and a key (one extraction of B5);
                              # writes jats/PMC8471596.xml, extract/B5.json and biorepo.json
pnpm demo:fixtures            # no key, no network: rebuilds biorepo.json, the export set and the
                              # smoke overlay fixture from whatever JATS and response are saved
```

The decisions follow the saved response (OF-BLD-014 §1.5). Over the hand-written stand-in they
demonstrate the review: the titre row promoted to gold and corrected, the same row rejected as a
colony time, and the curated `r-B5-3` accepted. Over a real response they are the accept of
`r-B5-3` alone, and the real candidates wait for a person in Guild. `pnpm test:export` exports a
set of its own, `core/tests/fixtures/export/`: the stand-in decided all four ways a decision can
land, which the same command rebuilds whatever the demo set holds. Commit the demo files and the
export set together.

### The gate

The counts below were measured at `1555f0d` (OF-BLD-019 §3.R), in the integration gate run of
2026-10-20 that ended green at 19:55 UTC.

```bash
pnpm verify              # offline — no key, no service, no network — twenty-four stages, in order:
  pnpm check:secrets     #   no key under src/, none committed, core/.env still ignored
  pnpm typecheck         #   tsc --noEmit
  pnpm check:plan        #   every Pydantic model matches its TypeScript mirror, field for field, and the
                         #   provenance ranking is one list on both sides
  pnpm check:reference   #   reference content is domain knowledge, never a result
  pnpm test:core         #   the Python service, 1,742 tests (1 skipped) at 1555f0d: retrieval, units,
                         #   anchoring, match_run, biorepo.write, the computed-value basis, the artifact store
                         #   and replay, llm.py's roles, cached tokens, tool turns and daily cap, the registry's
                         #   thirty-two tools, its gates and the proposals they make, the coverage sweep, the
                         #   program switch on the pool, the passages, the module rows and the coverage map,
                         #   the worker runner, the geneOS worker on a toy network worked by hand and Appendix
                         #   2's bundled-model ceilings, fermOS's fits and forecast band on synthetic runs,
                         #   Postdoc's loop and its budget against a stand-in model, the plan validator, the
                         #   ask stream, the passage cutter, the five search lanes, the scorecard's metrics,
                         #   rule and --thread, guild.py's rules, the competence mirror replayed from
                         #   competence.ts, practice.py's drafts and tutor turns against a stand-in model,
                         #   and checks.py: the ranking replayed from checks.ts, the queue's rules, a run, briefs;
                         #   Proforma's shelf, its one run artifact and its tables, a reference package's test
                         #   values parsed from the installed file, glucose to ethanol's binding over thread Q
                         #   and every refusal of the run contract against a stand-in evaluator; run_flowsheet
                         #   and stream_table, selling_price reading the yeast scenario's run, one archive rule
                         #   for every reader of a run, and check:tools' rule 2b planted in a copy of the package;
                         #   pureOS's trains read from a run's stream table, recovery by pass, and thermosteam's
                         #   questions, refusals and status codes against a stand-in worker; a scenario's newest
                         #   run on the service; a fermOS fit feeding a scenario, its run-out found between grid
                         #   points and every refusal; the ceiling check, flagged and never clamped
  pnpm test:sim          #   the real BioSTEAM worker answers: the corn plant run whole and read back, glucose to
                         #   ethanol converging on stand-in inputs, one result whatever the warm worker built
                         #   before, thermosteam's answers and the ethanol train read by pass among them
                         #   (pytest marker sim; 20 tests)
  pnpm check:licences    #   every dependency's licence against core/licences.toml; THIRD_PARTY.md current
  pnpm check:tools       #   11 modules with a read and a write tool; writes.py calls only the 10 module write
                         #   functions it names, followed through every import and alias; no other tool file
                         #   reaches any of the 24 functions it finds keeping a Proforma run or writing an
                         #   audit line (rule 2b); 12 gated actions need a person's name; the 7 gates in
                         #   gates.py and docs/TOOLS.md alike; each of the 32 names in WHITELIST registered
                         #   and written down in docs/TOOLS.md
  pnpm check:seed        #   every seed invariant, incl. unit dimensional analysis; COMPONENTS.md matches;
                         #   every thread letter has one program and the [A-Q] class follows programs.ts; a
                         #   locked runbook with no deposition behind it is an example; nothing under src/ is
                         #   imported from src/sim, and no string a user sees says demo, sample run,
                         #   stand-in, placeholder or scripted (three named exceptions); a BioSTEAM class names
                         #   one unit-operation step; no scenario takes a reserved id (scenario, reference), and
                         #   a BioSTEAM seed scenario's description names no binding outcome; since OF-BLD-020
                         #   Phase 2, every declared parameter has a written bounds reason (D4), and Proforma's
                         #   and pureOS's screens render no number box or slider outside the panel (E.1‴)
  pnpm check:biorepo     #   biorepo.json is sound and a fresh export reflects every decision in it
  pnpm test:export       #   the decision merge, exercised on core/tests/fixtures/export/; a bent one fails
  pnpm check:anchors     #   the anchoring floor — 93 of the 104 numeric curated records anchor on their own quote
  pnpm check:store       #   the store's contracts (141 checks): the overlay is authoritative, a record remembers
                         #   its original, the program switch survives a reload, archived and example
                         #   entities hide by default and the switch brings them back; scenarios made here,
                         #   pins, a person's parameter overrides (the older assumptions read into them once)
                         #   and fermOS fits survive a reload and Clear drops them, New
                         #   scenario is never disabled, and Proforma's pages read prices from the run
  pnpm check:guild       #   Guild's ladder on a ledger built in memory (no team in the store), the gate in both
                         #   modes, what runs, lessons, practice and checks write to the ledger, and who may see
                         #   a check, or a proposal to check someone (127 checks)
  pnpm check:lock        #   locked runbooks are byte-for-byte what they were locked as, the eight seed digests
                         #   included, every locked seed runbook an example, the flag outside the digest
  pnpm check:capture     #   the free-text → measurement-schema matcher, regression-tested
  pnpm check:figures     #   the figure grammar: one mark per provenance, the non-evidence classes dashed, a table
                         #   row per mark, recharts only where it was; recovery by unit draws no bar where no
                         #   product enters, and says so; the cost waterfall closes on the run's own price,
                         #   never a sum, and it and the tornado stand on the grammar
  pnpm build
  pnpm test:durable      #   the Durable tier survives a reload, finished lessons and series times included
  pnpm test:deposition   #   a deposition on a tablet, glove-tolerant
  pnpm test:reconcile    #   a refuted prediction changes evidence, never a parameter
  pnpm test:smoke        #   72 routes headless with archived programs hidden, 30 redirects, the 6 reference
                         #   shelves and 3 seeded subsystems, 4 requests outside dist/ refused, and twelve flows:
                         #   programs (Settings lists them, every list says what it hides, a deep link opens
                         #   under its banner, the switch brings them back); Proforma's index, a scenario's page
                         #   (a seed and a made scenario run, every section read from the run), the reference
                         #   pages (each held to its package's own test) and Compare over BioSTEAM scenarios; a
                         #   fermOS fit feeding a scenario and the ceiling check, flagged and never clamped; the
                         #   overlay (B5's fetched text, Witness scored, a Guild decision, Postdoc drawing its
                         #   steps and quoting a row, Postdoc down, the figure gallery, geneOS's ceiling, fermOS's
                         #   empty state); the Guild ledger from empty to its first person; the empty states of
                         #   Witness, fermOS and Guild with the service down; pureOS's train (a run's units in
                         #   order, a click cuts the streams, Properties on its broth and product stream, a
                         #   chemical the library lacks refused in words); and fermOS's Properties card (a late
                         #   answer dropped for the record it left, a 503 asked again)
  pnpm test:golden       #   34 checks, the switch turned on first: Postdoc down and back, its eleven questions
                         #   and no scripted mode, a live answer's steps, a replay labelled, the reader, the
                         #   review queue, Witness, scaling, Deposition, an authored cost surface's sweep
                         #   and cost lines, geneOS's ceiling, fermOS naming what to
                         #   deposit, the yeast scenario with the switch off (what bound and what waits, then its
                         #   run's price, cost lines, streams and equipment against the double), the PHA
                         #   scenario, a drafted runbook, the ledger, the palette, search
  pnpm test:deep         #   8 checks: the switch, ingest failure, protocol version diff, scenario compare
pnpm test:live           # the thirteen flows through Postdoc's loop, a real practice draft and tutor
                         # session, a real check brief (these need a key), and the C. necator, Yeast9 and
                         # iMM904 ceilings (need pnpm geneos:fetch) — never in verify
```

The test suite is not decoration. `test:golden` is what caught a markdown-renderer infinite
loop that crashed the tab: a table's `|` header row arriving before its `|---|` separator
consumed no input and allocated empty blocks forever. Every route rendered fine; the app was
still broken. Rendering is not working.

## What "working" means here

The prototype holds itself to nine conditions (design §11, and OF-BLD-016's eighth):

1. **No dead controls.** Every visible button, link, chip, toggle, and slider does its
   designed thing, or is explicitly labeled inactive.
2. **No lorem ipsum.** Every string is real copy; every datum comes from the seeded corpus.
3. **Traversable journeys.** Every cross-entity path — chip → reader → record → strain →
   protocol → scenario — is walkable in both directions.
4. **Time as it is.** No screen waits on an invented delay; each draws when its data is
   there. The browser's job queue (`startJob` / `tickJobs` in `store.ts`) carries Intake's
   fetch, extract and ingest jobs, which report the service's progress; with the service down an
   ingest stops at Fetch and says why. The extraction and research jobs that advanced through
   authored stages, and the speed control that paced them, are gone (OF-BLD-016 §3.R).
5. **Deterministic where it matters.** Simulation results and every computed value are
   reproducible run to run (a computed value is replayed from its inputs); only the model's
   words vary, and a validator holds them to the evidence.
6. **Functional protocols.** Scaling math, timers, run logging, materials aggregation,
   version diffs, and exports actually compute.
7. **Honest boundaries.** Browser-only persistence, catalogued-not-fetched papers, archived
   programs, examples and modeled economics are labeled at every point of possible confusion.
8. **Nothing invented on screen.** No sample team, sample run, sample figure, scripted answer,
   placeholder DOI or demo banner reaches a default view; `check:seed` fails on the words.
9. **The golden path holds.** The demo script runs start to finish with no dead ends,
   offline, with no external calls.

## Module map

| Module | Name | What it proves | Where it lives |
|---|---|---|---|
| 0 | PhycoExtract | Extraction quality is measurable | `/intake`, `/biorepo`, `/guild`, `/biorepo/witness` |
| 1 | Corpus & Postdoc | Agentic RAG with visible retrieval | `/postdoc`, `/biorepo` |
| 2 | Hosts & Protocols | Verified parameters become executable | `/geneos/hosts`, `/runbooks/protocols` |
| 3 | Proforma | Parameters feed a flowsheet BioSTEAM runs and prices | `/proforma`, `/proforma/scenario`, `/proforma/reference`, `/biorepo/compare` |
| — | pureOS | Recovery is read from the train BioSTEAM ran, never typed, and thermosteam answers for its streams | `/pureos`, `/pureos/train` |
| — | Dominion | What could be made, and who owns it | `/dominion` |
| 4 | Primer | The platform doubles as curriculum | `/primer` |
| 5 | Assay | A claim is tested, and the result comes back | `/runbooks`, `/runbooks/depositions` |
| 6 | Workforce | Who may perform a step is recorded, computed and checked at the bench | `/guild/matrix`, `/guild/people`, `/guild/skills`, `/guild/checks`, `/primer/path`, `/primer/practice`, run mode |

## The eleven

**openFerment is Home plus eleven destinations, and the list is closed.**

```
Home
Intake · BioRepo · Postdoc · geneOS · fermOS · pureOS · Proforma
Runbooks · Dominion · Primer · Guild
```

Twelve rail entries. It does not grow. Everything that exists now, and
everything built later, lives inside one of the eleven — when something new
appears the question is which of the eleven owns it, never whether to add a
twelfth. `src/data/nav.ts` is the single source of truth for the rail, the
command palette, the Architecture screen and the smoke tests, and `check:seed`
fails the build if `RAIL` is not exactly twelve.

Five things used to be rail entries and are now views inside their owner. **No
screen was deleted** — each is the same file, mounted somewhere else:

| Was | Is now |
|---|---|
| Organisms | geneOS's default view, as **Hosts** — `/geneos/hosts` |
| Molecules | Dominion's default view — `/dominion/molecules` |
| Protocols | a Runbooks tab — `/runbooks/protocols` |
| Deposition | a Runbooks tab — `/runbooks/depositions` |
| Witness | a BioRepo tab — `/biorepo/witness` |

Every retired path redirects with its tail intact, so `/organisms/cw15` lands
on `/geneos/hosts/cw15` rather than a 404, and the palette still answers to
the old words. `COMPONENTS.md` is the full map; `/settings/architecture` is the
same map in the app.

### The three OS components are three stages, not three toolkits

OF-BLD-011 corrected a boundary error. geneOS and fermOS had been split along
software categories — sequence tools in one, metabolic modelling in the other —
which is how a toolkit is organised, not how bioprocess work is.

| | Owns | Question | Discipline |
|---|---|---|---|
| **geneOS** | The organism as an engineered system | What *can* this cell do? | Stoichiometry |
| **fermOS** | The reactor | What *does* a real vessel achieve over time? | Dynamics |
| **pureOS** | Downstream | How does product become vial? | Separation |

Two seams carry a decision made in one component and paid for in another, and
both are stated on the screens. **geneOS → fermOS** is stoichiometry to
dynamics: a genome-scale model gives a yield ceiling with no time axis, and
titre is fermOS's output rather than geneOS's. **fermOS → pureOS** is the
harvest step, which pays for a choice made back in geneOS — secreted or
intracellular — so the handoff carries product location, not just a titre.
Two more reach Proforma (OF-BLD-019 Phase 5, below): **fermOS → Proforma** is a fit a person
chooses as the source of a scenario's titre, yield and productivity, and **geneOS → Proforma** is
the ceiling a scenario's fermenter yield is read against, flagged and never clamped.

**fermOS fits what a run measured**: kinetics is built from depositions alone,
and the other four subsystems are named and not built. It is the one that
cannot be seeded from literature, because kinetic parameters are fitted to real
runs and come from Deposition. **pureOS** has the
unit-operation vocabulary and reads the train a BioSTEAM flowsheet ran (below); it
has no process model of its own, chooses no train, and its four subsystems are
named and not built. Both say so on the screen
rather than implying otherwise, and Home shows the current state of each of the
eleven beside its name. Putting them in the rail from day one means that when
the work arrives the question is what they do with it, not where it goes.

Hosts, Molecules and Protocols keep their plain names as views. They are
catalogue views of domain objects, not components.

### Proforma on BioSTEAM (OF-BLD-019)

Proforma is a techno-economic tool built on BioSTEAM, an open-source process simulator that
builds a plant unit by unit, balances every stream, sizes and costs the equipment and solves
the selling price. It runs in the Proforma worker; the service talks to it through the worker's
JSON contract. In one account, with the detail phase by phase below:

- **The shelf holds four flowsheets.** Two are reference biorefineries from the BioSTEAM
  project's `biorefineries` package, run whole on the package's own defaults and held to the
  package's own test: `cornstover_benchmark`, the NREL 2011 corn stover design (1.9677 USD per
  gallon against 1.968), and `corn_drygrind`, the dry-grind corn ethanol plant and the yeast
  program's reference (ethanol at the package's own 0.4855 USD kg⁻¹, at which its TEA solves an
  IRR of 0.0538; all eleven of its package test's values within the test's 5 %, measured live in
  §7.1). Two are this repository's, and their files hold no number: `ethanol_glucose_v0`,
  glucose to ethanol, which the active program's `sc-yeast-1` runs, and `pha_sugar_v0`, the PHA
  draft, archived with PHA (`sc-pha-1`).
- **`model` is a source, `computed` a provenance.** `model` is a kind of basis input: a value a
  package, BioSTEAM or thermosteam sets as its own default, named with the package and its
  version. `computed` is the provenance every run carries: a reference run, whose inputs are all
  `model` or stated conventions, is `computed`; a scenario's run is the weakest of `computed`,
  its records' and any fit's, and `demo` while any input rests on a named person's assumption.
- **One artifact per run, and every reader reads it.** A run keeps one artifact holding the
  price, the sensitivity, the TEA's cost breakdown, the streams, the units, the utilities and the
  diagram where it is drawn. Proforma's pages, Compare, pureOS → Train, Postdoc's tools and the
  MCP server read that artifact and compute nothing again.
- **The screens.** `/proforma` (the reference runs, the flowsheets, the scenarios, and **New
  scenario**), `/proforma/scenario/:id` (inputs and their sources in the parameter panel, Run,
  every table of the newest run), `/proforma/reference/:id` (a reference run beside its
  package's test), `/biorepo/compare`, and pureOS's `/pureos/train/:scenarioId`.
- **The bridges.** A fermOS fit a person chooses feeds a scenario's titre, yield and
  productivity; geneOS's ceiling flags a fermenter yield above it and clamps nothing; pureOS
  reads the train, unit by unit, from the run; thermosteam answers density, heat capacity and
  boiling behaviour for a run's streams.
- **The tools.** Postdoc and outside assistants run a seed scenario (`run_flowsheet`), read a
  run's streams (`stream_table`) and its price (`selling_price`), ask thermosteam
  (`thermo_props`) and read Proforma's and pureOS's rows; the MCP server offers the same with no
  change (*Postdoc reaches every module*, above).
- **What waits for Sean.** On this checkout's data `sc-yeast-1` binds its feed glucose (4
  records), titre (9) and yield (18) to thread Q; its productivity (all 14 of its records name no
  carbon source), plant scale and glucose price wait for a named person's assumption, typed into
  the scenario page's parameter panel under a reviewer name, so no yeast run is kept yet
  (STATE.md §7.1). On the Mini, `brew install graphviz` lets the diagram draw.

#### Proforma's shelf, run in the worker (OF-BLD-019 Phase 2)

Proforma prices a flowsheet BioSTEAM ran, and the flowsheets it can run are a **shelf**, declared
as data in `core/openferment_core/flowsheets/shelf.py` (which imports no BioSTEAM, so the service
serves it with no simulator) at `GET /api/proforma/shelf`. Each entry names its title, its source,
its program, every input with the ontology fields that bind it, and the outputs it reports. A
scenario names a flowsheet by its id and nothing else about it.

| Flowsheet | What it is | Program | Runs as |
|---|---|---|---|
| `cornstover_benchmark` | the NREL 2011 corn stover ethanol design, from `biorefineries` | none | a reference, whole, on its package's defaults |
| `corn_drygrind` | the conventional dry-grind corn ethanol plant, from `biorefineries` | yeast ethanol | a reference, whole, on its package's defaults |
| `ethanol_glucose_v0` | glucose to ethanol, this repository | yeast ethanol | a scenario's flowsheet: `sc-yeast-1` |
| `pha_sugar_v0` | PHA from fermentable sugar, this repository | PHA, archived | a scenario's flowsheet: `sc-pha-1` |

An archived program's flowsheet is left off unless `?includeArchived=true` asks, and the toy
flowsheet the tests use is never on the shelf.

- **One artifact per run, and every reader reads it** (OF-BLD-019 D1). A scenario's run is one
  `proforma.run` artifact: the price's quantiles, histogram and Spearman sensitivity over the
  samples, the grid, and the base case's tables, read from BioSTEAM's own objects right after it
  ran: the TEA breakdown (main feedstock, other materials, utilities, other variable costs where
  there are any, fixed operating, capital recovery and co-product credits, which sum to the
  price), every stream, every unit in run order with its costs and duties, the plant's heating,
  cooling and electricity, and the diagram where it is drawn. Capital recovery is the TEA's sales
  less its annual operating cost at the solved price, because BioSTEAM's TEA keeps no annualised
  figure of its own. A reference biorefinery's run is one
  `proforma.reference` artifact holding the same tables. Every reader (Proforma's pages, pureOS's
  train, Postdoc's tools, the MCP server) reads them from that one artifact, the service through
  `proforma.tables_of`, and nothing is computed again on read.
- **A reference run is held to its package's own test.** The corn plant and the corn stover plant
  run whole, built afresh, on every default their package sets: `POST /api/proforma/reference/{id}`
  runs one, `GET` reads the newest and starts nothing, and the benchmark's own endpoints and
  stored artifact are unchanged. Beside each run sit the values its package's test asserts
  (`biorefineries/tests/test_biorefineries.py`, `test_corn` and `test_cornstover`), parsed from the
  installed file without importing it and never retyped, each held as the test holds it
  (`numpy.allclose` at the test's tolerance). `pnpm test:slow` holds the corn plant to all eleven.
  The corn stover plant's own test does not hold on these versions for two of its eleven values
  (installed equipment cost −7.9 %, electricity consumption −5.2 %) while the benchmark's
  1.968 USD per gallon does, and its run's checks say so. A reference run keeps ten significant
  digits, because BioSTEAM sums a set of units in an order that moves the last ones from one
  build to the next.
- **A reference run is `computed`.** The build document asks for it to be `model`; in the tree
  `model` is a kind of basis source, not a provenance. Every input of a reference run names the
  package, BioSTEAM, thermosteam or a stated convention, so `basis_provenance` gives it
  `computed`, as it gives the stored benchmark. A scenario's run is the weakest of `computed` and
  its records' (thread Q's are `unverified` until a person decides them), and `demo` while any
  input rests on a named person's assumption.
- **One line changes the corn package, and every run says so.** biorefineries 2.35.1's
  simultaneous saccharification and fermentation unit hands `bst.BatchBioreactor` two inlets, and
  biosteam 2.54.0 declares that class one fixed inlet, so `corn.load()` stops with *at most 1
  streams expected; 2 given*. The flowsheet lets the unit take its inlets, as BioSTEAM's own
  `NRELEthanolFermentation` declares; no number of the package's changes, and the line and why
  sit in every corn run's basis as a `compatibility` convention.
- **The warm worker keeps no plant's settings.** BioSTEAM holds process-wide state a plant can
  change: utility prices, the plant cost index, the tickets that name unnamed streams, and the
  chemicals each package caches, which packages share by name (the corn plant locks ammonia to
  liquid in the very object the corn stover plant uses). Every plant therefore builds inside
  `package_defaults()`: BioSTEAM's defaults first, as the package's own test builds it, every
  package's chemicals made anew and the tickets cleared; afterwards the worker puts back what it
  held. A scenario flowsheet also sets BioSTEAM's own default utility prices and cost index at the
  start of every case (not the corn plant's settings), reads them back, and its run's basis names
  them (`utility prices and cost index`). A `sim` test runs the plants in three orders in three
  workers and holds every result to a fresh worker's within 10⁻⁹.
- **The diagram is part of the run's basis** (D8). A run says whether its flowsheet diagram is
  drawn: by Graphviz where `dot` is on the path of the host that made it, otherwise the units are
  listed in run order with a line saying so. A host with Graphviz therefore keeps a run of its
  own rather than inheriting one made without it. `pnpm ready` has a `graphviz` row that warns at
  most; Graphviz is absent in the cloud build checkout, and `brew install graphviz` puts it on the
  Mini.

**Glucose to ethanol holds no number of its own** (`flowsheets/ethanol_glucose_v0.py`; an offline
test reads the file and finds no number but 0 and 1). Glucose and its water enter as two streams,
so the glucose alone is priced; a batch fermenter (`bst.BatchBioreactor`) turns glucose into two
ethanol and two carbon dioxide at the bound yield as a share of the theoretical yield, which the
worker computes from that reaction and thermosteam's molecular weights and reads back, for a batch
time of the titre over the productivity; then `biorefineries.ethanol`'s purification train (beer
column, rectifier, molecular sieves) gives fuel-grade ethanol. Chemicals and finance are the
dry-grind corn plant's. A process input binds only to records that name glucose as their carbon
source, on thread Q's papers, through the aggregate gate and `units.py`:

| Input | Its source | `sc-yeast-1` on this checkout's data, 2026-10-20 |
|---|---|---|
| glucose in the feed | `medium_component_conc` records naming glucose | 4 records, 20–100 g L⁻¹ |
| titre | `ethanol_titre` records | 9 records, 57–139 g L⁻¹ |
| yield | `ethanol_yield_substrate` records | 18 records, 0.22–0.518 g g⁻¹ |
| productivity | `ethanol_productivity` records | waiting: all 14 name no carbon source |
| plant scale (t yr⁻¹), glucose price (USD kg⁻¹) | a named person's assumption | waiting |
| ethanol purity | fuel grade, a convention every run's basis states | — |

A looser rule, counting records that name no carbon source, would bind the productivity too;
loosening it is Sean's call (STATE.md, §2.3). One yield record (0.518 g g⁻¹) lies above the
theoretical yield the worker computes (0.5114 g g⁻¹), so a sample drawn above that cannot run, and
the run counts such samples by reason.

**What a scenario runs.** `GET /api/proforma/scenarios` binds every seed scenario the program
switch shows (`sc-yeast-1`; `sc-pha-1` too with it on), `GET /api/proforma/bind?flowsheet=` binds
a shelf flowsheet as a scenario made in the browser shows it, and `POST /api/proforma/run` runs a
seed scenario by its id, or a scenario made in the browser by the flowsheet it names. A reference
biorefinery, the toy, an id the shelf lacks, an authored scenario's id, an assumption that is not
a finite number and a negative seed are each refused in words (422), and an input with neither
records nor a named person's assumption refuses the run, naming it. Every run's basis names the
scenario it belongs to, so a scenario's newest run is found by its id.

**A person's value wins** (OF-BLD-020 D3). A run carries the values this browser holds for its
scope, `proforma:<scenario id>`, as `overrides`. Each is a named person's assumption, and it
replaces the records and any fermOS fit for its input, not only on an input no record binds; the
input says it was chosen in place of the records it bound. The run's basis names each one as an
`assumption` by that person, and says it read overrides, so the run is `demo`. `GET
/api/proforma/bind` and the ceiling check take the same values (`?overrides=`). The older field,
`assumptions`, is still read for one release, the same way. Refused in words: an input named in
both fields, a value in words, an override of another scenario's scope, one that does not say
when it was typed, and a value for a convention or for an input the flowsheet does not take.

#### Proforma's screens (OF-BLD-019 Phase 3)

Every screen reads the service and the runs it kept; none prices anything in the browser.

- **The index** (`/proforma`) has three rows. **Reference runs**: the two reference biorefineries
  on the shelf, each with the price of its newest stored run as the shelf names it, when it ran
  (in UTC), its provenance, how many of its package test's values the run holds, a Run or Rerun
  with the simulator's status line, and a link to its page. Every card reads
  `GET /api/proforma/reference/{id}`; a benchmark kept before reference runs existed still
  shows, price and settings only, with a line saying so. **Flowsheets**: every other flowsheet
  the switch shows (glucose to ethanol with it off), each input and where it gets its value, and
  **New scenario from this**. **Scenarios**: the scenarios of the programs the switch shows, as
  cards with the price of the newest run (median, 5th–95th) or *Not run yet*, how the inputs
  stand (bound to records, assumed, with a fermOS fit chosen, waiting), and a pin. An empty row
  says why and what fills it, and no button on the index is disabled because a list is empty.
- **New scenario** (the header, the empty state, a flowsheet's card, the palette's *New Proforma
  scenario*) opens one chooser: a flowsheet from the shelf (not a reference: those run whole on
  their package's defaults), a name, and the flowsheet's own program (an archived one only with
  the switch on). It makes a BioSTEAM scenario, the only kind it makes, and opens its page.
- **The scenario page** (`/proforma/scenario/:id`) is one page for a seed scenario and one made
  here. The header names the flowsheet and its source, the program and the newest run's
  provenance, with Pin, Compare and, once a run exists, pureOS → Train. **Inputs** is the
  parameter panel over the scenario's scope, `proforma:<id>` (OF-BLD-020 Phase 2; *One parameter
  panel*, under Architecture), in three groups: Process, Economics and Conventions. Each row
  gives the input's value, unit and interval, and its source as a chip: *record ×N low–high*,
  which opens the records, *fitted* with the fermOS fit linked, *assumption by <name>*,
  *convention*, or *waiting*. A person types a value into the row, or moves its slider, under the
  reviewer name, with a low, a high and what it rests on below it, and **Reset to source** takes
  the value away again. **Use a fermOS fit** stays beside the panel. When the service refuses the
  values as they stand, Run waits and shows the service's words. **Run** shows the worker's
  status (cold, starting, ready, failed) and waits while the simulator starts. Then every
  section of the newest run, read from its one artifact: the price (median, 5th–95th, its basis and provenance, the
  base case or why it could not run), the cost breakdown as a waterfall of the TEA's lines that
  closes on the run's own price, the sensitivity tornado, the price distribution, the streams,
  the equipment with installed and purchase cost per unit, the utilities, the diagram or the
  units in run order with the run's line, the values read back after the run grouped by who set
  them (the package, BioSTEAM or a convention; this case's records and assumptions; anything
  else, credited to nobody), and the flowsheet's own questions for a process modeller. Each table
  and figure exports a CSV of the run's own numbers. The newest run is the service's
  (`GET /api/proforma/runs?scenarioId=`, the run pureOS and `selling_price` read too), else the
  one this browser kept.
- **A reference page** (`/proforma/reference/:id`, the corn plant and the corn stover benchmark)
  shows the package and its version, the simulator's, the provenance the run computes, Run or
  Rerun, the price the shelf names with the IRR (for the benchmark, 1.968 USD per gallon beside
  it), and **Held to its package's own test**: each value the test asserts, this run's value, the
  relative difference, the tolerance and within or outside, read from the run's checks. Then the
  scenario page's sections over the one case, **What the TEA holds** (its installed equipment
  cost need not equal the units' sum, and the card says why) and the package's citations. An id
  that is not a reference says so in the service's words. `/proforma/benchmark` and
  `/proforma/biosteam` land on the benchmark's page.
- **Compare** (`/biorepo/compare`) sets pinned BioSTEAM scenarios side by side, each from its
  newest run: the price with its basis, percentiles and provenance, every TEA line per unit of
  the price's basis with its USD per year, and every input as the run's basis names it (records
  with their count and lowest and highest value, an assumption and who made it, an artifact, a
  model, a convention). Nothing is subtracted or summed; two flowsheets draw *Their bases differ*,
  and each cell names its own input. A pinned scenario with no run says so.
- **What this browser keeps, and what the service keeps.** The Durable tier keeps the scenarios
  made here (whole, by a time-based id), the newest run id of a seed scenario, the pins, the
  values a person typed into the parameter panel (`parameterOverrides`, by scope and input) and
  the fermOS fits chosen, by scenario and input; *Clear this browser's data* drops them all. The
  service keeps the runs, each one artifact, and holds no scenario made here and no person's
  value: such a scenario runs by the flowsheet it names, the browser sends the values with each
  run, and the run's basis carries the scenario's id.

#### fermOS and geneOS reach Proforma (OF-BLD-019 Phase 5)

**A fermOS fit is a source, never a copy** (D10). `GET /api/fermos/fits?flowsheet=` lists every
kept kinetic fit and forecast with what each can give the flowsheet's titre, yield and
productivity, or why not, in words; a GET keeps nothing. A kinetic fit is forecast under its run's
own starting values and length, and kept nowhere. Titre is the forecast's final product, yield
its product made over sugar used (the kinetic fit holds no Yp/s of its own), and productivity the
titre over the batch time, the hour the forecast's median sugar runs out. That hour is found
between grid points, by drawing the grid again until one step is at most 2 % of the hour, and the
forecast is drawn again to it with the same fit, starting values and seed, so what a fit feeds does
not depend on how long its forecast was asked to run. Each value is the median with its 5th and
95th percentile. A fit is refused in words naming the parameter: μ or Xmax not identified (and
what run would identify it), no Yp/s, no sugar series, sugar that does not run out, another
product than the scenario's, or a damaged file (the other fits still list). Productivity comes
from a fit only beside titre from the same fit; otherwise the binding and the run are refused,
naming what titre is. A person chooses the fit, input by input, under **Use a fermOS fit** on the
scenario page or with **Send to Proforma** on fermOS → Forecast; a model never picks one. The
choice is kept in this browser by scenario and input, goes with the binding and the run as
`fits`, and the run's basis names the artifact for each input it feeds, and the batch time, so
the run's provenance follows the fit's. No fit is on file in this checkout.

**The ceiling check is a flag, never a bound** (D11). `GET /api/proforma/ceiling-check` sets the
scenario's fermenter yield, bound as its page binds it (records, a named person's assumption, or
a fit), beside the newest stored geneOS ceiling of each shelf model of its organism, on its
flowsheet's sugar (glucose), in g g⁻¹ through `units.py` and in mol mol⁻¹ at the ceiling's own
ratio. A yield whose value or high end is above a ceiling is flagged, with the records above it,
and asks a reviewer to check their basis; nothing is clamped, and the binding, the run and its
artifact are the same with a ceiling on file as without. It is computed when read, kept nowhere,
and starts no worker. The organism is the scenario's host filter when one is chosen, else each
bound record's strain, else the species its paper's words name, else the program's one species,
and the card counts each kind; a model matches by strain, or by species and says so, and a model
with no host matches no scenario. With no ceiling on file it says where one is computed, and does
not send a model fed another sugar to compute one on glucose. geneOS → Model lists the scenarios
above the chosen model's ceiling. On this checkout's data `sc-yeast-1`'s yield binds 18 records,
0.22–0.518 g g⁻¹: 3 name CEN.PK113-7D and 15 no catalogued strain, so iMM904 and Yeast9 (both
S288C) match by species, and the high end is above both their ceilings (0.5114 g g⁻¹) and
flagged, naming one record. The PHA draft's check reads its records unclipped, while its run
still clips a yield above the glucose ceiling (OF-BLD-014 §8.3).

#### pureOS reads the train, and thermosteam answers (OF-BLD-019 Phase 4)

**pureOS → Train** (`/pureos/train/:scenarioId`, or a run's artifact id in
place of the scenario's) reads the newest Proforma run of a scenario from the
one `proforma.run` artifact that run kept (OF-BLD-019 D1), through
`core/openferment_core/pureos.py`. It lists the units in the order the
flowsheet ran them, each with its inlets and outlets, mass in and out, the
product in and out, the product it passes on toward the product stream, what
it loses and to which outlet, its recovery, and the share still on the path
after it; then the overall recovery, the product in the product stream over
that and everything lost on the way together. Clicking a unit cuts the stream table to its
streams, and a unit whose BioSTEAM class is a step of the unit-operation
vocabulary links to it. Every number is arithmetic the service did over the
run's stream table: the page computes none, nothing is typed, and nothing is
simulated again. pureOS's front page lists the trains on file, one a scenario,
with their overall recovery, and says what the program switch hides. A train
is a scenario's run: a reference biorefinery's run (`proforma.reference`) is
not read as one.

- **The product** is the component the run's price is per: in the stream the
  run's TEA prices, the one component whose flow is the TEA's basis flow, else
  that stream's largest. A run with no TEA names no product and reads no
  recovery, and says why; so does a run whose base case could not run.
- **Recovery is not outlets over inlets**, which is one for every unit that
  reacts nothing. It is the product leaving by the outlets that lead on to the
  product stream (directly, through later units or round a recycle) over the
  product entering.
- **It is credited by pass.** A unit whose passes BioSTEAM keeps apart
  (`SEPARATE_PASSES`: today the process heat exchanger, `HXprocess`, whose two
  sides never mix) is credited only on the pass that carries the product on:
  on BioSTEAM's own ethanol purification train the beer column loses its
  bottoms, and the exchanger that heats the beer with them passes the beer on
  whole (a `sim` test holds it). Every other unit is one pass.
- **Product a unit on the path takes in and lets out by no outlet is lost
  there**, so the cumulative share and the overall recovery agree with the
  units' own.
- **The mark is the run's, worked out now**: `basis_provenance` over the run's
  inputs as they stand when the train is read, so a run resting on an
  assumption is `demo`, and the page, the API and `pureos_read` give one train
  one mark.

**thermosteam answers property questions.** thermosteam is BioSTEAM's
property engine, and it runs in the Proforma worker, which has it loaded; the
service talks to it through the worker's JSON contract and never imports it.
A question names a mixture on file and never a number: a stream of a run (its
artifact id and the stream's id), or a preset the service fills,
`ethanol-water-azeotrope` (the composition at which the library's own
vapour-liquid equilibrium gives a vapour of the liquid's composition) or
`beer-at-titre-of` an ethanol titre record (water and ethanol at the record's
value; the beer's cells, residual sugar and dissolved CO2 are not in it, and
the answer says so). A temperature or pressure the question does not carry is
the library's own default, said so. The answer is density, heat capacity,
viscosity, and bubble and dew points in the library's units, kept as one
`thermo_props` artifact whose basis names thermosteam and its version: computed
for a preset, the run's or the record's mark when that is weaker. A chemical
the library lacks, or a stream in more than one phase, is refused in words.
`POST /api/thermo/props` asks; `GET /api/thermo/props` reads the stored
answer and starts no simulator.

A **Properties** card shows the answers: on pureOS → Train for the broth, the
product stream and any stream picked, and on fermOS for an ethanol titre
record of the active program (with no titre record on file, it says what
fills it). Postdoc asks the same through `thermo_props`, each property its own
evidence id. With the service down the trains, the train page and each card
say so, and nothing stands in for an answer.

### fermOS sizes the vessel on BioSTEAM (OF-BLD-020 Phase 4)

fermOS → Vessel (`/fermos/vessel`, `src/screens/FermOSVessel.tsx`, the tab between Simulate and
Forecast) answers two questions about a batch fermOS kept. What vessels would run it? And would
they give the culture the oxygen it takes up? BioSTEAM answers both. Given the broth a fermenter
takes and the reaction inside it, BioSTEAM's fermenter classes size the vessels and their batch
schedule, size the air compressor and the agitator, work out the heat to take away, and cost each
piece from their own correlations. BioSTEAM runs in the Proforma worker, where it is already
loaded. `core/openferment_core/vessel.py` talks to it through the worker's JSON contract and never
imports it; `core/openferment_core/flowsheets/vessel.py` is the worker's side.

- **What a design starts from.** A kept simulation of the `batch_v1` family, ethanol on glucose
  (a fed-batch's feed and a chemostat's flow are refused in words, for now). Or, for an anaerobic
  vessel only, a kept kinetic fit or forecast, read for its titre, yield and batch time the way
  Proforma reads one (`proforma.fit_info` on `ethanol_glucose_v0`). Simulate's **Design the
  vessel** opens the page on its simulation (`?simulation=`); a fit opens with `?fit=`; with
  neither, the newest kept simulation is chosen. The broth is read at the simulation's harvest
  hour, and its oxygen uptake up to that hour, even when the run went on after its sugar ran out.
- **Which vessel.** A simulation that takes up oxygen (its Yx/o is set) gets BioSTEAM's
  `AeratedBioreactor`. It is a stirred tank, whose agitator BioSTEAM sizes and costs and whose kLa
  (how fast oxygen moves from the bubbles into the broth) comes from Riet's correlation; or a
  bubble column, with no agitator and kLa from Dewes'. An anaerobic simulation, and every fit,
  gets the NREL batch fermenter (`NRELAnaerobicBatchBioreactor`, the class the ethanol flowsheet's
  fermenter is built on): no gas inlet, no compressor, and so no oxygen balance.
- **Every parameter in hand.** The parameter panel shows the scope `fermos:vessel:<artifact id>`
  in six groups: Scale, Vessel, Schedule, Aeration, Agitation, Heat. The aerated vessel has 27
  parameters and the NREL one 9. Each value names its source. Most are BioSTEAM's own defaults for
  the class, read from its code when the worker loads it (its signatures, its class attributes,
  and a vessel built with nothing set), and never typed here. The reacting time `tau` is the
  simulation's harvest hour (a fit's batch time). The peak and batch-average oxygen uptake are the
  simulation's. Stated conventions are named in the basis: the air is sized for the peak uptake,
  a bubble column's agitation power is zero (else BioSTEAM costs an agitator), and a vessel type
  or kLa correlation a request names (as Postdoc's tool does) is that request's. A person may type
  any parameter under a reviewer name, as a named assumption. The vessel type is the panel's
  choice `design` (Stirred tank or Bubble column), BioSTEAM's own word for it;
  `vessel_type` is BioSTEAM's word for the vessel's orientation.
- **A design needs a person's scale.** Either a plant scale, in tonnes of product a year, which
  the corn plant's TEA operating hours and the titre at harvest turn into broth an hour; or, for
  the aerated vessel only, one vessel's batch volume in m³, with a loading time. Neither, or both,
  is refused in words, and the line above **Design** says which the panel offers. Other requests
  BioSTEAM cannot design are refused before the worker is asked: a number of vessels that is not
  whole, or under the class's own minimum (the NREL vessel refuses one, read from its code); a
  largest vessel the class refuses; N and V_max both; V_max or N beside a batch volume; one
  aerated vessel at a plant scale with no loading time.
- **The oxygen comes from the reaction.** BioSTEAM's aerated class takes no oxygen demand. It
  sizes the air so that the oxygen it transfers, averaged over the cycle, meets what its reaction
  consumes. So the worker builds the reaction from what the simulation made: glucose and oxygen to
  cells, ethanol, carbon dioxide and water, closed on thermosteam's formulas. It designs once,
  reads the uptake BioSTEAM sized for, scales the reaction's oxygen to the simulation's peak (or
  its batch average, when a person chooses that), and designs again on a fresh unit. A flag says
  by how much. If even the scaled reaction sits under the floor BioSTEAM aerates from (read from
  its code), the design has no air, and says that every hour of uptake is short.
- **The oxygen balance.** After the design, the service sets what the vessel transfers (OTR)
  against what the simulated culture takes up (OUR), hour by hour, in mmol L⁻¹ h⁻¹. OTR is the
  class's own kLa times the driving force BioSTEAM sizes with: the gap between oxygen's
  solubility (at the vessel's temperature and the oxygen's partial pressure in the gas, averaged
  between the sparged air and the vent) and the broth held at the dissolved oxygen setpoint θ, a
  share of it. The `OxygenBalance` figure draws OUR as a computed curve and OTR as a computed
  rule, and shades the hours the service found short. Dissolved oxygen is not a state of the
  simulation: the balance is checked after it, not fed back into it.
- **The heat line.** BioSTEAM's duty comes from the reaction's heats of formation, out less in.
  If a person types a heat per oxygen (`Q_O2_consumption`, unset by default), BioSTEAM's duty is
  that heat times the oxygen the vessel consumed, and the line says so. Beside it, labelled a
  convention, stands an estimate from the oxygen the culture took up: the heat per oxygen that
  `biorefineries.cane`'s aerated fermentation gives BioSTEAM (read from its code; it cites Benz,
  after Cooney's rule that heat follows oxygen uptake), times the oxygen the simulation took up
  over the batch. When the reaction's balanced oxygen and the simulation's differ by more than a
  tenth (`OXYGEN_AGREE_RTOL`, a convention named in the basis), a flag names both.
- **The cost line.** Purchase and installed cost, by item as BioSTEAM lists them (for the aerated
  vessel the pressure vessels, their platforms and ladders, the compressor, the air cooler, the
  heat exchanger, the recirculation pump and motor, and a stirred tank's agitator; the NREL
  vessel's own lines, cleaning in place among them), from BioSTEAM's own correlations at the
  plant cost index it holds, named with its year. BioSTEAM's warnings, such as a vessel taller
  than a cost correlation covers, are kept as flags.
- **One artifact a design.** `POST /api/fermos/vessel` takes a `VesselRequest` (`simulation` or
  `fit`, `vesselType`, `klaMethod`, the scope's `overrides`, `includeArchived`), keeps one
  `fermos.vessel` artifact and answers a `VesselDesign`: the design table (each row naming where
  BioSTEAM put it), the oxygen balance, heat, cost, every parameter with its source and BioSTEAM's
  default beside it, the flags, and one `Evidence` whose id is the artifact's. The basis names the
  simulation or fit, the vessel class, the chemicals, the utility prices and cost index, the
  vessel type, the unit id, the operating hours a plant scale reads, the cross-check's heat per
  oxygen and tolerance for an aerated vessel, and every parameter with its source, each person's
  value by name. Its provenance follows those, so a design is always `demo`. Asked again on the
  same basis, the kept design is returned. A refusal is a 422 in words, a damaged file a 409, and
  a worker that cannot answer a 503.
  `GET /api/fermos/vessel/specs?simulation=|fit=&vesselType=` and
  `GET /api/params/fermos:vessel:<id>` serve the scope (404 for an artifact not on file), and
  `GET /api/fermos/vessels` lists the kept designs without starting a simulator.
- **The screen computes nothing.** Every number on it is the service's or a person's, and it
  renders no number box of its own (`check:seed` reads every fermOS screen for one, E.1‴). It
  offers the design table as CSV, shows the basis, and for the NREL vessel says *Anaerobic: no
  compressor, no oxygen balance*. **Price this in Proforma** says what night two's
  `custom_train_v1` adds, and makes no scenario.
- **Postdoc asks with ids and words.** `fermos_vessel` takes a simulation's or a fit's artifact
  id, a vessel type and a kLa correlation by name, all strings. It and `fermos_write`'s
  `design_vessel` are one function, free at no gate, audited with the model as the agent. The
  service holds no person's scale, so on a real service the tool refuses until a person designs
  on the screen, and Postdoc says the design waits. `fermos_read`'s kind `vessel` lists the kept
  designs. `docs/TOOLS.md` has the rest.
- **Where BioSTEAM overruled the build document.** BioSTEAM takes its oxygen demand from the
  reaction, not from `Q_O2_consumption`, which is a forced heat per oxygen. Only Riet's and
  Dewes' correlations run in the class: BioSTEAM 2.54.0 registers Labik and Galaction for a
  stirred tank, and Deshpande, DeJesus, Akita & Yoshida, Posarac & Tekic, Seno, Suh and Shah for a
  bubble column, and its `AeratedBioreactor` implements none of them, so the panel names them
  and does not offer them. There is no `V` to set: BioSTEAM finds a vessel's size from `V_max` or
  `N`. The NREL vessel stores `Nmin` and `Nmax` and never uses them, and the aerated class has
  neither, so a design holds N to a whole number at or above the class's own minimum instead.
  The air flow, its vvm and the gas velocity are BioSTEAM's to solve, so they are read, not set.
  `batch` stays on: BioSTEAM's continuous mode divides the transfer by one hour where the batch
  time belongs. An aerated design replayed in another process agrees to about one part in a
  million, not bit for bit, because BioSTEAM's air-flow solve starts from sums whose order
  Python's string hashing sets.
- **What waits for Sean.** No simulation is kept on `openferment-data`, because §3.5's parameters
  wait for him, so no vessel has been designed for the yeast program (§4.3, run owed). Once he
  simulates a batch, he types a plant scale on fermOS → Vessel and presses **Design**.

## Architecture

```
src/data/       seed content as typed TS modules — becomes API fixtures in production
src/data/corpus/  the 15 literature threads, A–O, one file per thread group; threadP.ts and threadQ.ts,
                  written by thread:apply; src/data/programs.ts says which program owns which letters
src/engine/     pure logic, unit-testable without UI, ships to production unchanged
src/engine/geneos/  engine code a component owns outright (genus enumeration)
src/components/ shared primitives (citation chip, data table, quantity field, …)
src/screens/    one file per screen, named after the component it is
src/data/nav.ts the navigation vocabulary — labels, descriptors, aliases, redirects
```

The split is deliberate. `engine/` (units, scaling, diff, metrics, interpolation) is production
code already. `data/` seed modules keep the shapes the API will return, so they become fixtures
and contract tests. `src/sim/`, the scripted chat player and its invented delays, is gone
(OF-BLD-016 §3.1); its flows survive in `src/data/flows.ts` as the evaluation set. What is left of
the simulation is `src/engine/retrieval.ts`, the browser's old retrieval, which nothing imports
any more; the job queue in `store.ts` (`startJob`/`tickJobs`) now carries only Intake's jobs, which
report the service's progress (OF-BLD-016 §3.R).

### The evidence tick

The design system's signature: a 3px notched left border on any datum-bearing element,
colored by provenance.

| Tick | Provenance | Means |
|---|---|---|
| solid gold | `gold` | curated gold-set entry |
| solid green | `verified` | checked against the source document |
| green, 45% | `curated` | transcribed from the curation document, **not** yet checked |
| dotted blue | `computed` | a calculation whose every input names a source — basis attached, never aggregated |
| solid grey | `unverified` | extractor output, not reviewed |
| solid blue | `user` | user-entered |
| dashed grey | `industry-estimate` | vendor or market figure — no source document, never aggregated |
| dashed amber | `demo` | modeled, not measured |

Provenance stops being a badge you read and becomes a texture you perceive: a screen of
curated green feels different from one streaked with dashed grey. The two classes that must
never be mistaken for evidence — `industry-estimate` and `demo` — are the two that are dashed,
so they are distinguishable from their neighbours without relying on hue.

`isAggregatable()` is the single gate on what may enter a statistic: it excludes rejected
records, industry estimates, computed values (derived from values already counted), and any record marked `isPrimary: false` (a paper reciting someone
else's measurement, which would double-count). Excluded records stay visible in per-record lists
and plots and say why they were held out — the rule is about medians, not about hiding data.

Two honest limits. Ticks rendered inside `DataTable` are `aria-hidden`, so in those tables
provenance is conveyed by colour alone; the `Tick` component used everywhere else carries a
`title` and screen-reader label. And no tick renders an icon — icons appear on the explicit
`ProvenanceBadge` used in detail views and popovers, not in the ambient ticks.

### Units that refuse

The unit engine — which has no name of its own; Primer used to name it and now names the
Learn screens — does dimensional analysis over 25 unit families and converts freely inside a
family. Across families it does not guess — it fails. For the three crossings that actually
come up in this corpus it fails **with a reason**: %TSP ↔ g/L explains that the conversion
needs the cell density and the total-protein fraction of the biomass; %TSP ↔ % explains why a
share of soluble protein is not a share of anything else; EUR ↔ USD asks for an exchange rate
with a date attached and refuses to invent one. Every other cross-family pair gets a bare
dimension error, which is honest but less useful — the `REFUSALS` table is the mechanism for
upgrading one as soon as a corpus value needs it.

`explainRefusal(from, to)` takes two unit strings, not a record, so a refusal explains what the
*conversion* needs rather than what a particular record lacks.

### Authored cost surfaces, and BioSTEAM

Two kinds of economics, labelled apart. The **authored** cost models behind S1–S3 are *response
surfaces, not a process simulator*: each is written once (CAPEX scaling exponents,
annualization, media/utility/labor line items, downstream yield effects) and evaluated over its
sweep grid at load, and the client interpolates between grid points, so sliders are continuous and
the cost waterfall always sums to the headline. They are casein examples, hidden by default, and
subtitled *Cost model v0*. They step aside and are not deleted (OF-BLD-019 D5): S1–S3 and
`src/engine/grids.ts` stay for the archived examples, the scenario page's authored
branch and the authored compare open them under their banner with the switch on, New scenario
makes BioSTEAM scenarios alone, and Home's pinned card says *Cost model v0* for an authored
surface alone.

**BioSTEAM** runs for real in the Proforma worker (`workers/proforma_worker.py`,
`flowsheets/`), over the shelf above: two published reference biorefineries run whole on their
package's defaults and held to their package's own test, and two flowsheets of our own,
glucose to ethanol for the active program (`sc-yeast-1`) and PHA from sugar for the archived one
(`sc-pha-1`), each pricing from inputs that name a source.

### One parameter panel (OF-BLD-020 Phase 2)

Every number a person may set for a model is a declared parameter, and one panel shows them all.
A screen never builds a form of its own for one.

- **A parameter is declared once, in Python.** `core/openferment_core/params.py` holds the shapes
  (`ParameterSpec`, `ParameterValue`, `Override`, `ParamScope`; mirrored in `src/data/types.ts`
  and listed in `PAIRS`). A spec has a key, a label, a symbol, a sentence on what it means, a
  dimension and a unit, bounds with a written reason, a group, and an ordered rule for where its
  value comes from: a fit a person chose, the records of named fields, a kept artifact or
  simulation, a named person, a stated convention, or the library's own default. The first
  source in the rule that has a value gives it, and the value names that source.
- **The service serves a scope.** `GET /api/params/{scope}` answers with every spec of the scope
  and its value as the service binds it now. `POST /api/params/{scope}/resolve` lays a person's
  values on and says what a run would add to its basis; it runs nothing and keeps nothing.
  Three kinds of scope are served. `proforma:<scenario id>` is a scenario's inputs, bound as a
  run binds them, and starts no worker. `fermos:vessel:<simulation or fit id>` is a vessel
  design's parameters, with BioSTEAM's own defaults read in the Proforma worker, so a read can
  start it. `fermos:family:<family id>` is a kinetics family's parameters. `pureos:unit:…` answers
  404 until pureOS has a provider. A malformed scope or a refused value is a 422 in words.
- **One panel draws every scope.** `src/components/ParameterPanel.tsx` renders one row per
  parameter (`ParameterRow.tsx`), in its group. A row shows the value, the unit and the interval,
  and its source as a chip: *fitted* or *artifact* or *simulation* with a link to the artifact,
  *record ×N low–high*, which opens the records, *assumption by <name>*, *convention*,
  *library default*, or *waiting*. Where the parameter's rule takes a person's value, below them
  are a number box, a slider when the parameter has both bounds, or a list when it is a choice of
  words, then the low, the high and what the value rests on. **Reset to source** shows while a
  person's value stands, and every row has **Why**: what the symbol means, the source rule in
  order with the one that answered, the bounds and their reason, and the library's default. The panel computes nothing: every value and warning on it came from the service or
  from the person. It is live on Proforma's scenario page and on fermOS → Vessel. Its controls
  are 44 px touch targets and nothing on it needs a hover, because it may be used at the bench.
- **A person's change is a named assumption** (D3). Typing needs a reviewer name, set in
  Settings; without one every edit control is off and the row says where to set it. Each change
  is an `Override`: the scope, the key, the value, its low and high, who typed it, when, and
  what it rests on. It is kept in this browser's Durable tier (`parameterOverrides`, by scope).
  A browser that kept Proforma's older `proformaAssumptions` has them read once into
  `proforma:<id>`, and *Clear this browser's data* drops both. The service keeps no override: the
  browser sends a scope's overrides with each run, and the service checks each one. It needs a
  real name, the time it was typed, a number (or one of the offered words), a parameter the scope
  has whose rule takes a person's value, and a value inside its own low and high. With one end
  typed, the empty end is the value itself. The run's basis names each one as an `assumption` by
  that person, so the run is `demo`. A person's value wins over the records and any fit for its
  parameter.
- **Bounds are conventions** (D4). A slider's ends are a choice, and each spec says why in
  `boundsReason`: the ontology's plausibility range for its field, converted into its unit, or a
  physical limit (nothing negative, a share between none and the whole), or a sentence saying why
  it has no bounds (a choice of words). A value typed outside the bounds is kept as typed; the
  row shows the service's warning, and the basis records the value. `check:seed` asks
  `python -m openferment_core.params --check` and fails on a spec with no reason: 156 parameters
  are declared at this commit, across Proforma's flowsheets, fermOS's five model families and the
  vessel, and every one has one.
- **A number box lives only in the panel** (E.1‴). `check:seed` reads Proforma's and pureOS's
  screens (`ProformaScenario.tsx`, `ProformaBiosteam.tsx`, `PureOS*.tsx`) as syntax trees. It
  fails on any `<input>` of type number or range there, and on one whose type it cannot read.
  Three are allowed by name, each with its reason: the authored surfaces' number box and slider
  (S1–S3, the archived casein examples) and the run's grid sliders (*Move three inputs over the
  run's grid*). All three move a view over a computed grid and set no parameter. fermOS's screens
  join the guard once fermOS → Forecast's typed start values and duration move into the panel.
- **A model never sets one.** Postdoc's tools carry ids and words. `proforma_write`'s `bind` is
  refused, and `run_flowsheet` runs a scenario as the service binds it, with no person's value.

### No simulated agent

There was one: a scripted player in `src/sim/` that replayed authored conversations
offline, with invented delays. OF-BLD-016 removed it. Postdoc's only path is the
service's loop of real model calls, and with the service down it says so and plays
nothing in its place. The authored flows survive in `src/data/flows.ts` as the
evaluation set (`pnpm test:live`, and Witness's F set) and are never shown as answers.
The service double the browser tests use (`scripts/lib/service-double.mjs`) replays
loops recorded by the real code over a stand-in model, and a replayed answer says it
is a replay.

## Honesty policy

Real corpus, real model calls, modeled economics — so the labelling is targeted rather than
blanket, and nothing on screen is invented:

1. No demo banner and no demo account: the top bar shows the reviewer name, or *No reviewer
   name set* with the link to set one.
2. Every value carries its provenance tick; the dashed `demo` tick marks a value modeled rather
   than measured. Citation chips show title, authors, year, venue and the quoted span — an
   identifier reaches the clipboard via "Copy citation" when the paper has one.
3. A colophon at `/settings/about` with the fidelity matrix — computed, authored or visual.
4. Authored cost surfaces are permanently subtitled *"Cost model v0 — illustrative economics,
   not validated."*
5. Postdoc's claims carry no number of their own; each value is rendered from the record, row,
   passage or computed value it cites, and the plan shows the model that answered and the cost.
6. Example runbooks, protocols, scenarios and lessons are hidden by default and, when shown,
   open under a banner saying they describe a run nobody made. Archived programs open under a
   banner naming the program and the switch.
7. Exports embed the disclosure. CSVs carry the 11-line provenance header from `src/lib/csv.ts`;
   run logs, review sessions, materials checklists and agent answers carry their own headers
   saying the same thing in the shape their format allows.

## Known open items

Recorded here because the app records them rather than papering over them:

- **The seed is catalogued; full text arrives through the service.** The seed holds metadata
  and a curator note per paper, so with the service down extraction spans anchor to curator
  prose and the reader says so. With it up, the papers Europe PMC holds open-access text for
  fetch as full text (88 here: 31 casein, 35 PHA, 22 yeast), the extractor has run over them
  (500 values anchored), and Witness scores that run (`claude-1`) provisionally against the
  curated values until reviewers flag gold. The curated values are all casein (archived); thread
  Q's values are scored against nothing until a person decides them in Guild. `RUN_OUTPUTS`
  stays empty on purpose: the run arrives through the overlay, not the seed.
- **49 entries are flagged `[verify]`, and they are thinner than that flag suggests.** Only 7 of
  the 49 hold title, a named journal, a real year and a DOI together. 28 carry no `doi`, `pmcid`
  or `pmid` at all, 18 record a placeholder venue rather than a journal, and 12 sit at `year: 0`.
  Where an identifier exists it is the authoritative key, never the author string — but for most
  of these entries no such key is on record yet. The scripted CrossRef/PubMed resolution pass
  (§22.1) is outstanding, and it has more to recover than author names.
- **One gold-set row is blocked.** F1's 5 planned records (gene length, exon count,
  precursor/mature length, variant count) have no expressible field in ontology v1. Marked
  `blocked` rather than silently dropped; extending the ontology is a product decision.
- **D5 is an open question, not an answer.** Whether *C. reinhardtii* encodes a Fam20-family
  kinase wants an HMM search of the v6.1 proteome against Pfam PF03881. The app labels it open.
- **The audit log and the proposals stay on the machine.** `core/data/audit.jsonl` and
  `core/data/proposals.json` are gitignored and are not on the data branch, so a proposal made
  on one machine is answered on that machine. Haiku still types a count or an ordinal into a
  claim now and then, and the validator drops that claim whole; the prompt forbids it, and
  across the ten eval-O questions it happened once.
- **The UI copy migration from the synthetic corpus is done but not proven exhaustive.** OF-COR-001
  replaced the data; the strings describing that data were corrected screen by screen afterwards,
  and several rounds of audit each turned up more. Anything phrased as "synthetic", "fictional",
  "ingested" or "demo" should be read as suspect until checked against `src/lib/csv.ts`, which
  carries the canonical wording.

## Documents

- `docs/DEMO.md` — the run sheet: start, what to point at, the eleven questions in order with what
  each showed on 2026-10-20, and what to steer around.
- `docs/TOOLS.md` — the tool registry, the gates, the program switch and the proposal rules.
- `docs/OF-COR-001.md` — the corpus: 15 threads, the ontology, the gold-set plan, scenarios.
- `BUILD-SPEC.md` — the build contract: ID registry, seed invariants, content and style rules.
- `COMPONENTS.md` — the eighteen components, seven layers, and what has no name yet.
- `core/` — openferment-core, the Python service. Postdoc's model call lives here.
- `scripts/check-seed.ts` — enforces those invariants; run before any bundle.
