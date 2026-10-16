# The demo, in ten minutes

One question travels the whole chain: **what would it take to make PHA from
waste cellulosic sugar?** Nine beats, one screen each. The clicks below are the
ones the golden path walks (`pnpm test:golden`, sections 10b to 10f), so they
are checked every time `pnpm verify` runs.

## Before you start

| | Live | Offline |
|---|---|---|
| Start | `pnpm prototype:up` (the service on :8000, the build on :4173) | `pnpm demo:offline` (the build and the service double on :4317) |
| Needs | a key the Models API accepts, the passage index (`pnpm data:prepare`), thread P extracted | nothing: no key, no network, no Python |
| Postdoc | asks the model | replays a recorded run and labels it as a replay: *Replay of a run on <date>* for a real recording, *Replay of a recorded test run, made with a scripted stand-in* for the fixtures made with no key |

Start the offline one in a second terminal before the demo. When the live
service fails on the day, switch the browser tab to it.

Set a reviewer name first (Settings → Corpus → Reviewer name): beat 7's
assumptions and beat 8's decisions carry it.

## The beats

| # | Open | Click | What appears | Say |
|---|---|---|---|---|
| 1 | Intake → Ingest (`/intake/ingest`) | a PHA paper's title (thread P, ids P1 to P35) | the paper's own words, extraction spans highlighted | "Every number in here is pinned to the sentence it came from." |
| 2 | BioRepo → Search (`/biorepo/search`) | type *PHB from xylose hydrolysate*, press Enter, open the first hit | passages with the matching sentence; the reader opens on it and marks its words | "It searches what the authors wrote." |
| 3 | BioRepo → Witness (`/biorepo/witness`) | scroll to **Extraction**, then **Retrieval** | two scorecards from real runs, each with its date | "This is how often it is right. The table picked the default." |
| 4 | Postdoc (`/postdoc`) | **Live (Postdoc service)**; ask *What PHB yields on glucose have been reported, and how far are they from the ceiling?* | the trace fills in step by step; claims with no number in the prose; beside each, values from records, quoted sentences, a computed card | "It writes the words and the citations, and the screen fills in the numbers from the sources." |
| 5 | geneOS → Model (`/geneos/model`) | pick **PHB**, **glucose**; then **fructose** | a dotted ceiling for each model that can use the sugar; every reported yield as a point | "The gap between the points and the lines is the room left." |
| 6 | fermOS (`/fermos`), then **Forecast** | pick a deposition with a time course (or **Load a sample run**); on Forecast, **Forecast** | a fitted curve through measured points with its parameters; a band for the next run | "Filled points are measurements, and the band is the forecast." |
| 7 | Proforma → *PHA from cellulosic sugar — draft flowsheet* (`/proforma/scenario/sc-pha-1`) | read the inputs table; type the assumptions you can defend (value, low, high, what it rests on, **Keep assumption**); **Run the scenario** | a source on every input; a price distribution, a tornado, the sliders | "Dashed amber means a person assumed it. It turns solid as records replace assumptions." |
| 8 | Postdoc, then the runbook | ask *Draft a runbook for …*; **Turn into a runbook**; on its page **Lock predictions**; then Runbooks → **Ledger** | predictions with intervals and a lock time; the dossier behind them; the ledger's counts | "It keeps score on itself." |
| 9 | Claude Desktop | ask the same question as beat 4 | the same tools, called from outside the app (README: *The same tools, from an assistant outside the app*) | "Any assistant can use the same evidence." |

## What each beat shows today (2026-10-16)

The live loop has not run: the key in the cloud environment is refused
(`pnpm ready` reads lane `none`), so thread P is fetched and indexed but not
extracted. Until it is:

- **Beat 1** shows the 66 papers fetched with full text; extraction spans
  appear only on the curated records.
- **Beat 3**'s Extraction scorecard waits for the first extraction; Retrieval
  is real (bm25, from 2026-10-15) and says it is provisional.
- **Beat 4** live answers only with a key. Offline, the replay is a recorded run
  of the real loop with a scripted stand-in in place of the model, over a
  stand-in paper, and the panel says so.
- **Beat 5** draws the ceilings; no reported PHA yield exists yet to draw beside
  them.
- **Beat 6** has no deposited run with a time course; the sample run is
  invented and labelled.
- **Beat 7**: all seven inputs wait for a source until thread P's records
  arrive, so the run needs seven assumptions. Offline, the double binds four
  inputs to stand-in records and runs a closed-form stand-in in place of
  BioSTEAM; the benchmark card shows the real corn stover result (1.9677 USD per
  gallon against 1.968).
- **Beat 8** offline drafts from a recorded run over stand-in artifacts; the
  adopted runbook, its lock and the ledger are the real code.
- **Beat 9** works with nothing more than `uv`: `.mcp.json` starts the server for
  a Claude Code session in this repository, and the README gives Claude
  Desktop's snippet. `ask_postdoc` needs the key; the other tools do not.

`STATE.md` → `## Live owed` lists the runs that turn each of these into the
real thing, with the command for each.
