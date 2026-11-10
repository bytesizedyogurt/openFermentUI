# H7-03: a refused bench reading stays listed as recorded in the tab that wrote it

**Statement.** When one running deposition is open at its bench in two tabs, and the service refuses the reading the
tab with the older view records (the recorded debt below), that tab's bench, its close dialog and the deposition's
record page go on listing the refused reading as read back, recorded and standing for its measure, with nothing left
in the queue to send it, until a reload shows the service's row.

**What this reproduction counts.** `docs/PROGRESS.md:641` records as a debt left by decision: "Two devices writing one
deposition: a page that lacks the entries another device appended writes a deposition the service refuses as leaving
them out, and the page's own new entries go with the refused write, said in words". The 422, the lost 8.8 USD/kg and
the toast are that debt, and the run prints them as such. RESULT: DEFECT counts the part past those words alone: what
the refused tab goes on showing after the refusal.

## Contract

- `src/screens/Deposition.tsx:1086-1087`: "The deposition is the record, kept on the service as it changes".
- `src/screens/Deposition.tsx:1226` (the bench's own words to the person): "Every number is read back before it is kept."
- `src/lib/projectState.ts:4`: "The service is the store."
- `src/lib/projectState.ts:159-160`: "A refusal is the service's answer and the row is dropped with its reason"; the
  activity line the store writes says the same (`src/store.ts:1176`, "The service refused ${entry.kind} ${entry.id}
  and it was dropped").

## Command

From the repository root:

    bash bughunt/repro/H7-03/run.sh

It makes `bh_r_h7_03_sameonline` fresh (`bh_db_fresh` through `bh_svc_start`), serves the built app on
127.0.0.1:9340, puts one placeholder runbook and locks it, then drives two Chromium tabs (`sameonline.mjs`): tab A sets
the person's name and begins a deposition with the readings alone; tab B opens that deposition's bench; tab A records
and reads back 7.7 USD/kg; tab B records and reads back 8.8 USD/kg. It waits 20 s, past the store's 15 s retry, then
reads tab B's bench, its toasts, its close dialog and the record page (by its Exit button, no reload), then reloads tab
B. The service is stopped and the database and its data copy dropped on exit. Keyless, no model call. `run1.log` and
`run2.log` are two runs, each on its own fresh database; both print RESULT: DEFECT.

## Expected

Once the service refuses tab B's writes, tab B shows what the service keeps for the deposition (tab A's 7.7 USD/kg)
and takes the refused 8.8 USD/kg back from its bench, its counts and the record page, so every reading the tab lists
as recorded is one the service holds.

## Observed (both runs)

- The recorded debt, as written: both of tab B's `PUT /api/state/depositions/<id>` writes (the reading, then its read
  back) answer 422 "dep-… keeps every reading it was given, and this write leaves out de-…-2; a reading is corrected by
  a new one", shown as two toasts; the service holds 7.7 USD/kg alone.
- Past the debt: 20 s on, the browser's queue is empty, so nothing will ever send 8.8 USD/kg; the toasts are gone; tab
  B's bench header says "1 measured", its measure line reads "8.8 USD/kg" with no "to read back" mark, and its panel's
  "Recorded here" lists "A placeholder output 8.8 USD/kg". The close dialog says "1 measurement and 0 observations
  recorded." The record page, opened from the bench, lists the entry "8.8 USD/kg · stands for its measure"
  (`data-stands="true"`).
- After a reload tab B's bench reads "7.7 USD/kg": the page had shown a reading the service never kept.

## Likely cause

- `src/lib/projectState.ts:180-183`: a refused row leaves the outbox (`refused.push(...); continue;`), and nothing
  takes the page's copy of the row back.
- `src/store.ts:1170-1181` (`flushProjectState`): on a refusal the store writes the activity line and the toast and
  leaves `depositions` and `stateSeen` as the page holds them; it reads no row again from the service.
- `src/store.ts:3649`: the page's own rows became `stateSeen` when the write was queued, so the refused reading is the
  page's baseline from then on, and the bench (`src/screens/Deposition.tsx:1214`, `1228-1249`) and the record page
  (`src/screens/DepositionDetail.tsx:385`) render it from the store.

Confidence: high. A fix of the part counted here is small: after a refusal, read the refused row (or the project's
rows, `hydrateProjectState`) again and lay the outbox over it, as a project's opening does (`src/store.ts:1073`).
