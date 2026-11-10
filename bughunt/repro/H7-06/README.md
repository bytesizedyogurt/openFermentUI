# H7-06: with the service stopped, five detail pages say the project holds no such row

**Statement.** When the service does not answer a page's first reads, the runbook, deposition, paper and Guild skill
pages say the project keeps no row of that id and say nothing of the service, and the Postdoc page lists no
conversation for the one its address names; the strain, lesson and protocol pages, reading the same failed loads, say
the service is not running and name the command that starts it.

**Contract.** `src/lib/http.ts:3-4`:

> `ServiceDown`: nothing answered, or it answered with an error a person cannot act on here; the remedy names the
> command that starts the service.

and `src/lib/http.ts:12-13`: "What a ServiceDown says when nothing answered: the service is not running, and a write
waits in this browser's outbox." (`NOT_RUNNING = 'The service is not running.'`). The store keeps that failure for the pages: `stateProblem` (`src/store.ts:696-697`,
set at `src/store.ts:1050` when the project's rows cannot be loaded), `cataloguesProblem` (`src/store.ts:705-706`, set at
`src/store.ts:1098-1102` with the remedy), and `serviceUp: false` when the overlay finds nothing answering
(`src/store.ts:2698-2700`). The strain page shows the shape a page gives that state
(`src/screens/StrainPage.tsx:915-917`): "The project's strain catalogue could not be read: The service is not running.
Start it with pnpm prototype:up from the repository root."

**Command.** From the repository root:

```
bash bughunt/repro/H7-06/run.sh
```

It makes a fresh database (`bh_r_h7_06_words`), serves the built app and the service on 127.0.0.1:10020, makes one
project and keeps placeholder rows through the service's own routes (`seed.py`: a runbook and a deposition through
`PUT /api/state`, a Postdoc conversation the same way, a skill, a strain and a lesson through `/api/catalogues`, a
protocol through `/api/protocols`, a paper through `POST /api/intake/paste`). `words.mjs` opens each row's page in
Chromium with the service up; then the service is stopped (nothing listens on 10020) and `words.mjs` opens the same
addresses in a fresh browser, the page's own files served from `dist/` inside the browser (as Vite serves them under
`pnpm dev`, or as a page holds them when the service goes away under it) and every `/api` request failing at the
closed port. Keyless, no model call, about 40 s. The service is stopped and the database and its data copy dropped on
the way out.

**Expected.** With the service stopped, each detail page of a row the project keeps says the service is not running
and names the command that starts it, as the strain, lesson and protocol pages do; no page says the project holds no
such row.

**Observed** (run1.log and run2.log, the same in both). With the service up, all eight pages show their row. With the
service stopped (65 of 66 `/api` requests failed at the connection, none answered):

| page | address | words with the service stopped | names the service |
|---|---|---|---|
| runbook | `/runbooks/rb-h706` | "Runbook not found. This project holds no runbook with this id. … The project keeps no runbook of that id; the link may be from another project." | no |
| deposition | `/runbooks/depositions/dep-h706` | "Deposition not found. This project holds no deposition with this id." | no |
| paper | `/biorepo/paper/<id>` | "No such paper. <id> is not a document this project holds." | no |
| Guild skill | `/guild/skills/h706-skill` | "No such skill. The project's skill catalogue holds no skill h706-skill." | no |
| Postdoc | `/postdoc/lc-h706` | list: "No conversation yet: a person asks the first question."; panel: "Ask the corpus a question" | yes, in the composer: "Postdoc needs the service. Start it with pnpm prototype:up …" |
| strain (control) | `/geneos/hosts/h706-strain` | "The project's strain catalogue could not be read: The service is not running. Start it with pnpm prototype:up from the repository root." | yes |
| lesson (control) | `/primer/h706-lesson` | "The lessons could not be read. The service is not running. Start it with pnpm prototype:up …" | yes |
| protocol (control) | `/runbooks/protocols/h706-protocol` | "The protocols could not be read. The service is not running. Start it with pnpm prototype:up …" | yes |

No banner elsewhere on the page names the service for the four pages that say nothing of it. RESULT: DEFECT, both runs.

**Likely cause.** Each page under test draws its empty state from the store's list alone and reads none of the failure
the store kept:

- `src/screens/RunbookDetail.tsx:584-596`: `if (!runbook)` renders "This project holds no runbook with this id" and
  "The project keeps no runbook of that id; the link may be from another project" without reading `stateProblem`.
- `src/screens/DepositionDetail.tsx:220,249-255`: `stateProblem` ends the loading state (line 220), and then
  `if (!deposition)` renders "This project holds no deposition with this id" without saying why.
- `src/screens/PaperReader.tsx:254-260`: `if (!paper)` renders "… is not a document this project holds" without reading
  `serviceUp` or `overlayProblem`.
- `src/screens/GuildSkills.tsx:83-88`: `if (!skill)` renders "The project's skill catalogue holds no skill …" without
  reading `cataloguesProblem`, which the strain page reads from the same catalogue load.
- `src/screens/Postdoc.tsx:395-397`: the list renders "No conversation yet" from `liveConversations` alone; the page
  knows the service is down (`down`, line 248) and says so only in the composer.

A small fix: each of these branches reads its load's problem (as `StrainPage.tsx:900-917` and `ProtocolDetail.tsx:861`
do) and says the service is not running with its remedy.
