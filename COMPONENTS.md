# Components

openFerment has a named architecture of eighteen components. This file is the
canonical mapping between those names and the code, and it is the reference
every future specification points at (OF-BLD-006 §2.3).

## The rule

**The component names ARE the user-facing vocabulary.**

This reverses §2.2, which held that these names were for building the system
and that the rail should say "Ask" rather than "Postdoc". That was the wrong
call for these users. Researchers acquire domain vocabulary constantly — it is
most of what a first year of graduate work consists of — and they will use this
daily. A precise name learned once beats a generic one re-read forever. "Ask"
names the verb and tells you nothing about what you are talking to; "Postdoc"
tells you it plans, retrieves, shows its working, and can be handed a
half-formed question.

So a component name appears in four places:

1. **Module organisation** — code for a component is identifiably that
   component's code, and the file is named after it: Deposition's screen is
   `Deposition.tsx`.
2. **The product** — rail labels, page titles, routes, the command palette,
   the guided tour. One vocabulary, in the code and on the screen.
3. **Attribution in the UI** — when work is done, the component doing it is
   named: `geneOS · homology sweep`, `Clearance · not searched`. Rendered by
   `src/components/ComponentTag.tsx`. This survives the reversal unchanged:
   naming the surface you are standing on and naming the component that did a
   particular piece of work are different jobs.
4. **This file** — the single canonical mapping.

Three things keep an invented word learnable rather than hostile, and all three
live in `src/data/nav.ts` rather than being left to each screen:

- a **descriptor** under every label, so nobody meets a bare coinage;
- an **alias** in the command palette, so typing "library" still finds BioRepo;
- a **redirect**, so `/library/papers/H4` lands on `/biorepo/papers/H4` rather
  than a not-found page.

Organisms, Molecules and Protocols keep their plain names. They are catalogue
views of domain objects a biologist already has words for, not components, and
coining over them would be coining for its own sake.

## The map

| Component | Layer | Lives in | Surfaced as |
|---|---|---|---|
| Postdoc | The agent | `src/sim/chat.ts`, `src/screens/Postdoc.tsx` | the rail, /postdoc |
| Intake | Evidence in | `src/screens/IntakeIngest.tsx`, `src/screens/Intake.tsx` | the rail, /intake |
| BioRepo | Evidence in | `src/data/`, `src/engine/retrieval.ts`, `src/screens/BioRepo.tsx` | the rail, /biorepo |
| geneOS | Computing | not built | — |
| fermOS | Computing | not built | — |
| Proforma | Computing | `src/screens/Proforma.tsx`, `src/engine/grids.ts`, `src/engine/interp.ts` | the rail, /proforma |
| Primer | Keeping it honest | `src/screens/Primer.tsx`, `src/screens/PrimerLesson.tsx` | the rail, /primer |
| Audit | Keeping it honest | `src/components/Provenance.tsx`, `aggregateExclusion() in src/store.ts` | provenance ticks and their labels |
| Witness | Keeping it honest | `src/screens/Witness.tsx`, `src/engine/metrics.ts` | /witness |
| Common Seal | Keeping it honest | not built | — |
| Claim Workbench | Patents | not built | — |
| Priority Engine | Patents | not built | — |
| Clearance | Patents | `src/engine/clearance.ts`, `src/data/clearanceFindings.ts` | ambient on Molecules |
| Enablement | Patents | not built | — |
| Notary | Patents | not built | — |
| Guild of Applied Life | People and permissions | `src/screens/Guild.tsx` | /guild |
| Runbook | Assay | `src/screens/Runbooks.tsx`, `src/data/runbooks.ts` | the rail, /runbooks |
| Deposition | Assay | `src/screens/Deposition.tsx`, `src/components/DepositionPanel.tsx` | launched from a Runbook |

## Named nothing yet

Code that sits in a layer without a name of its own.

| What | Layer | Lives in | Does |
|---|---|---|---|
| _the unit engine_ | Keeping it honest | `src/engine/units.ts`, `src/engine/scale.ts` | Units, conversion, scaling, and refusals that carry their reason |

## Reading the map

**"not built" is a real entry.** Seven of the eighteen have no code behind them.
They are in the table because the table is the architecture, not an inventory
of what happens to exist — and because a name with nothing under it is a
smaller problem than a system with no name for the thing it is missing.

**Primer moved.** It used to name the unit engine; it now names the Learn
section — an introductory text, and a bio pun that earns its place. The unit
engine was not handed a replacement name on the spot. It sits in "Keeping it
honest" unnamed until somebody chooses one deliberately, because an unnamed
thing on the map is honest and a hastily renamed one is a name nobody picked.

**The Assay layer is where the arrow reverses.** Everything above Runbook is
software reasoning about the world. Deposition is the world reporting back.
Runbook is an outbound falsifiable claim; Deposition is the inbound account of
what actually happened. It is the only ground truth the platform gets about its
own predictions, and nothing in the literature can supply it.

**Two components share one screen.** Runbook and Deposition are separate
components, and Deposition launches from a Runbook rather than living inside
it. `Deposition.tsx` — formerly `RunMode.tsx` — is Deposition's screen: bench
execution, glove-tolerant, a tablet held at arm's length. Its accessibility
constraints are load-bearing rather than incidental, and the rename changed
none of them. Extend it; do not rewrite it.

**One name is a phrase.** "Guild of Applied Life" is the component; `Guild` is
the short form used in the rail, in attribution, and in code identifiers. The
full phrase appears on the screen itself, once, where there is room to learn it.
