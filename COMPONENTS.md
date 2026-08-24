# Components

openFerment has a named architecture of eighteen components. This file is the
canonical mapping between those names and the code, and it is the reference
every future specification points at (OF-BLD-006 §2.3).

## The rule

**Nav labels stay. Component names are the architecture layer beneath them.**

"Ask" is not renamed to "Postdoc" in the rail. Someone looking for a chat
interface finds "Ask"; "Postdoc" would be worse UX. These names are for
building the system, not for navigating it.

A component name surfaces in exactly three places:

1. **Module organisation** — code for a component is identifiably that
   component's code.
2. **Attribution in the UI** — when work is done, the component doing it is
   named: `geneOS · homology sweep`, `Primer · conversion refused`,
   `Clearance · not searched`. Rendered by `src/components/ComponentTag.tsx`.
3. **This file** — the single canonical mapping.

Nowhere else. A component name in body copy, a heading, or a nav label is a
defect against this rule.

## The map

| Component | Layer | Lives in | Surfaced as |
|---|---|---|---|
| Postdoc | The agent | `src/sim/chat.ts`, `src/screens/Ask.tsx` | Ask |
| Intake | Evidence in | `src/screens/Ingest.tsx`, `src/screens/Extract.tsx` | Extract |
| BioRepo | Evidence in | `src/data/`, `src/engine/retrieval.ts` | Library |
| geneOS | Computing | not built | — |
| fermOS | Computing | not built | — |
| Proforma | Computing | `src/screens/Simulate.tsx`, `src/engine/grids.ts`, `src/engine/interp.ts` | Simulate |
| Primer | Keeping it honest | `src/engine/units.ts`, `src/engine/scale.ts` | inline refusals |
| Audit | Keeping it honest | `src/components/Provenance.tsx`, `aggregateExclusion()` in `src/store.ts` | provenance ticks |
| Witness | Keeping it honest | `src/screens/Validation.tsx`, `src/engine/metrics.ts` | Validation |
| Common Seal | Keeping it honest | not built | — |
| Claim Workbench | Patents | not built | — |
| Priority Engine | Patents | not built | — |
| Clearance | Patents | `src/engine/clearance.ts`, `src/data/clearanceFindings.ts` | ambient on molecules |
| Enablement | Patents | not built | — |
| Notary | Patents | not built | — |
| Guild of Applied Life | People and permissions | `src/screens/Review.tsx` | Review |
| Runbook | Assay | `src/screens/Runbooks.tsx`, `src/data/runbooks.ts` | Runbooks |
| Deposition | Assay | `src/screens/RunMode.tsx` | launched from a Runbook |

## Reading the map

**"not built" is a real entry.** Seven of the eighteen have no code behind them.
They are in the table because the table is the architecture, not an inventory
of what happens to exist — and because a name with nothing under it is a
smaller problem than a system with no name for the thing it is missing.

**The Assay layer is where the arrow reverses.** Everything above Runbook is
software reasoning about the world. Deposition is the world reporting back.
Runbook is an outbound falsifiable claim; Deposition is the inbound account of
what actually happened. It is the only ground truth the platform gets about its
own predictions, and nothing in the literature can supply it.

**Two components share one screen.** Runbook and Deposition are separate
components, and Deposition launches from a Runbook rather than living inside
it. `RunMode.tsx` is Deposition's screen — bench execution, glove-tolerant, a
tablet held at arm's length — and its accessibility constraints are load-
bearing rather than incidental. Extend it; do not rewrite it.

**One name is a phrase.** "Guild of Applied Life" is the component; `Guild` is
the short form used in attribution and in code identifiers.
