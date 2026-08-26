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

**fermOS cannot be seeded from literature.** Kinetic parameters are fitted to
real runs in a specific vessel, so they come from Deposition. fermOS is the
component that most needs the Assay loop and the one that cannot be built out of
papers.

## The eleven

### Intake

**Documents in, anchored to source.** `/intake` · chord `g i`

Ingest and extraction. A claim enters the system here or it does not enter at all.

Views: [Ingest](#) `/intake/ingest`

| Component | Implemented in |
|---|---|
| Intake | `src/screens/IntakeIngest.tsx`, `src/screens/Intake.tsx` |

### BioRepo

**Records, artifacts, provenance.** `/biorepo` · chord `g b`

The corpus and everything retrieved from it, plus the two components whose job is to say what a record is worth: Audit ticks it, Witness asks whether the extractor reproduces.

Views: [Witness](#) `/biorepo/witness` · [Compare](#) `/biorepo/compare`

| Component | Implemented in |
|---|---|
| BioRepo | `src/data/`, `src/engine/retrieval.ts`, `src/screens/BioRepo.tsx` |
| Audit | `src/components/Provenance.tsx`, `aggregateExclusion() in src/store.ts` |
| Witness | `src/screens/Witness.tsx`, `src/engine/metrics.ts` |

Not built: Common Seal.

### Postdoc

**Ask, plan, answer from records.** `/postdoc` · chord `g o`

The thing you talk to. Runs on Claude Haiku through `openferment-core`; writes claims that carry no numbers of their own.

| Component | Implemented in |
|---|---|
| Postdoc | `src/sim/chat.ts`, `src/screens/Postdoc.tsx` |

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
| Model | `geneos.model` | stub |
| Strain design | `geneos.design` | stub |

| Component | Implemented in |
|---|---|
| geneOS | `src/screens/GeneOS.tsx`, `src/screens/Organisms.tsx`, `src/screens/StrainPage.tsx`, `src/engine/geneos/enumeration.ts` |

### fermOS

**Reactor, kinetics, scale.** `/fermos` · chord `g f`

The vessel: kinetics, oxygen and heat transport, operating mode and feeding, scale-up, instrumentation and control. Dynamics — what a real reactor achieves over time. **This is the emptiest of the eleven, and honestly so**: there is no kinetic model, no transport calculation and no scale-up logic anywhere in the codebase.

| Subsystem | Key | State |
|---|---|---|
| Kinetics | `fermos.kinetics` | stub |
| Transport | `fermos.transport` | stub |
| Operating mode | `fermos.mode` | stub |
| Scale | `fermos.scale` | stub |
| Control | `fermos.control` | stub |

| Component | Implemented in |
|---|---|
| fermOS | `src/screens/FermOS.tsx` |

### pureOS

**Harvest, capture, recovery.** `/pureos` · chord `g u`

Everything after the fermenter: harvest, disruption, capture, polishing, recovery, formulation and storage. Holds the unit-operation vocabulary and `ProcessTrain`. Proforma prices a train; pureOS decides it.

| Subsystem | Key | State |
|---|---|---|
| Harvest | `pureos.harvest` | stub |
| Capture | `pureos.capture` | stub |
| Polish | `pureos.polish` | stub |
| Recovery | `pureos.recovery` | stub |

### Proforma

**Cost, scale, uncertainty.** `/proforma` · chord `g c`

Techno-economics over authored response surfaces. Prices a process; does not choose one.

| Component | Implemented in |
|---|---|
| Proforma | `src/screens/Proforma.tsx`, `src/screens/ProformaScenario.tsx`, `src/engine/grids.ts`, `src/engine/interp.ts` |

### Runbooks

**Claims to be tested.** `/runbooks` · chord `g r`

The outbound falsifiable claim, the protocols that execute it, and the Depositions that report back. This is where the arrow reverses.

Views: [Protocols](#) `/runbooks/protocols` · [Depositions](#) `/runbooks/depositions`

| Component | Implemented in |
|---|---|
| Runbook | `src/screens/Runbooks.tsx`, `src/data/runbooks.ts` |
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

The platform taught through itself. Every embedded widget in a lesson is the real component operating on real session state.

| Component | Implemented in |
|---|---|
| Primer | `src/screens/Primer.tsx`, `src/screens/PrimerLesson.tsx` |

### Guild

**Who may verify.** `/guild` · chord `g g`

The Guild of Applied Life: review, roles, and who decided what.

| Component | Implemented in |
|---|---|
| Guild of Applied Life | `src/screens/Guild.tsx` |


## The full component map

Eighteen named components across seven layers, each owned by one of the eleven.
Internal machinery — Audit, Witness, Clearance, Deposition and the unbuilt
patent pieces — is not a destination and names the destination it lives inside,
so "where does this live" has an answer for every component rather than only
for the ones with a rail entry.

| Component | Layer | Lives in | Surfaced as |
|---|---|---|---|
| Postdoc | The agent | `src/sim/chat.ts`, `src/screens/Postdoc.tsx` | the rail, /postdoc |
| Intake | Evidence in | `src/screens/IntakeIngest.tsx`, `src/screens/Intake.tsx` | the rail, /intake |
| BioRepo | Evidence in | `src/data/`, `src/engine/retrieval.ts`, `src/screens/BioRepo.tsx` | the rail, /biorepo |
| geneOS | Computing | `src/screens/GeneOS.tsx`, `src/screens/Organisms.tsx`, `src/screens/StrainPage.tsx`, `src/engine/geneos/enumeration.ts` | the rail, /geneos |
| fermOS | Computing | `src/screens/FermOS.tsx` | the rail, /fermos |
| Proforma | Computing | `src/screens/Proforma.tsx`, `src/screens/ProformaScenario.tsx`, `src/engine/grids.ts`, `src/engine/interp.ts` | the rail, /proforma |
| Primer | Keeping it honest | `src/screens/Primer.tsx`, `src/screens/PrimerLesson.tsx` | the rail, /primer |
| Audit | Keeping it honest | `src/components/Provenance.tsx`, `aggregateExclusion() in src/store.ts` | provenance ticks and their labels |
| Witness | Keeping it honest | `src/screens/Witness.tsx`, `src/engine/metrics.ts` | a BioRepo tab, /biorepo/witness |
| Common Seal | Keeping it honest | not built | — |
| Claim Workbench | Patents | not built | — |
| Priority Engine | Patents | not built | — |
| Clearance | Patents | `src/engine/clearance.ts`, `src/data/clearanceFindings.ts`, `src/components/Clearance.tsx` | a Dominion tab, /dominion/clearance |
| Enablement | Patents | not built | — |
| Notary | Patents | not built | — |
| Guild of Applied Life | People and permissions | `src/screens/Guild.tsx` | /guild |
| Runbook | Assay | `src/screens/Runbooks.tsx`, `src/data/runbooks.ts` | the rail, /runbooks |
| Deposition | Assay | `src/screens/Deposition.tsx`, `src/screens/Depositions.tsx`, `src/components/DepositionPanel.tsx` | a Runbooks tab, /runbooks/depositions |

## Named nothing yet

Code that sits in a layer without a name of its own.

| What | Layer | Lives in | Does |
|---|---|---|---|
| _the unit engine_ | Keeping it honest | `src/engine/units.ts`, `src/engine/scale.ts` | Units, conversion, scaling, and refusals that carry their reason |

## Reading the map

**"not built" is a real entry.** Five of the components have no code behind
them. They are in the table because the table is the architecture, not an
inventory of what happens to exist — and because a name with nothing under it
is a smaller problem than a system with no name for the thing it is missing.

**A destination can be empty and still be in the rail.** fermOS has a screen,
five named subsystems and no code. That is deliberate: putting it in the
navigation from day one means that when kinetics arrives the question is what
fermOS does with it, not where in the navigation it should go. The screen says
it is empty rather than implying otherwise, and Home says so too.

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
Proforma prices whatever pureOS specifies* (OF-BLD-011 §6). Nothing in the code
forces the question yet, and it is recorded here rather than settled quietly,
because whoever builds it first will settle it by accident otherwise.

**Attribution survives the reorganisation.** `ComponentTag` names the component
that did a piece of work, which is a different job from naming the surface you
are standing on. A tag reading `Clearance · not searched` is still correct now
that Clearance is a Dominion tab.

**One name is a phrase.** "Guild of Applied Life" is the component; `Guild` is
the short form used in the rail, in attribution, and in code identifiers.
