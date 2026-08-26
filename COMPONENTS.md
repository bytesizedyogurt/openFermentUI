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
| geneOS | `/geneos` | `e` | sequence, structure, function |
| fermOS | `/fermos` | `f` | hosts, metabolism, strain design |
| pureOS | `/pureos` | `u` | downstream, recovery, storage |
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
| Organisms | fermOS's default view — `/fermos/organisms` |
| Molecules | Dominion's default view — `/dominion/molecules` |
| Protocols | a Runbooks tab — `/runbooks/protocols` |
| Deposition | a Runbooks tab — `/runbooks/depositions` |
| Witness | a BioRepo tab — `/biorepo/witness` |

Every retired path redirects, tail intact: `/organisms/cw15` lands on
`/fermos/organisms/cw15`. Old words still resolve in the palette — typing
"molecules" reaches Dominion.

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

**Sequence, structure, function.** `/geneos` · chord `g e`

A destination with a screen and no tooling. Homology search, structure prediction, enzyme annotation and genus enumeration are named and unbuilt.

| Component | Implemented in |
|---|---|
| geneOS | `src/screens/GeneOS.tsx` |

### fermOS

**Hosts, metabolism, strain design.** `/fermos` · chord `g f`

The organism side. Organisms — the strain catalogue — is the built part; metabolic models, pathway design and strain design are not.

Views: [Organisms](#) `/fermos/organisms`

| Component | Implemented in |
|---|---|
| fermOS | `src/screens/FermOS.tsx`, `src/screens/Organisms.tsx`, `src/screens/StrainPage.tsx` |

### pureOS

**Downstream, recovery, storage.** `/pureos` · chord `g u`

Everything after the fermenter. Holds the unit-operation vocabulary and `ProcessTrain`. Proforma prices a train; pureOS decides it.

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
| geneOS | Computing | `src/screens/GeneOS.tsx` | the rail, /geneos |
| fermOS | Computing | `src/screens/FermOS.tsx`, `src/screens/Organisms.tsx`, `src/screens/StrainPage.tsx` | the rail, /fermos |
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

**A destination can be empty and still be in the rail.** geneOS has a screen
and no tooling. That is deliberate: putting it in the navigation from day one
means that when sequence work arrives the question is what geneOS does with it,
not where in the navigation it should go. The screen says it is empty rather
than implying otherwise, and Home says so too.

**The Assay layer is where the arrow reverses.** Everything above Runbook is
software reasoning about the world. Deposition is the world reporting back.
Runbook is an outbound falsifiable claim; Deposition is the inbound account of
what actually happened, and it is the only ground truth the platform gets about
its own predictions.

**Proforma prices a train; pureOS decides it.** Asking what a centrifugation
step costs at ten cubic metres is an economics question. Asking whether
centrifugation or filtration suits a cell-wall-deficient alga is a process
question. They were living in the same place, and now they are not.

**Attribution survives the reorganisation.** `ComponentTag` names the component
that did a piece of work, which is a different job from naming the surface you
are standing on. A tag reading `Clearance · not searched` is still correct now
that Clearance is a Dominion tab.

**One name is a phrase.** "Guild of Applied Life" is the component; `Guild` is
the short form used in the rail, in attribution, and in code identifiers.
