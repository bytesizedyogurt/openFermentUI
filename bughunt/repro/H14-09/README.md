# H14-09: Studies says "Ran cornstover" for a run the project already held

**Verdict: did not reproduce as a defect (both runs print `RESULT: NO-DEFECT`).** What the hunt saw holds: pressing
Run it on a basis the project holds answers at once with the held row, and the card reads "Ran cornstover. Run
bfda026530692adc". The contract it names governs the store's answer, and the store keeps it.

## Statement (the candidate's)

Pressing Run it on a plant whose basis the project already ran answers at once with the kept row, and the card says
"Ran cornstover. Run bfda026530692adc" with no word that the run is the earlier one, kept by another person at
another time.

## Contract named

`docs/api/runs.md:186-189` (at 2047f5a):

> The same run kept twice is one row, answered as it was first kept: when the project holds the row already, done
> with its SFF record or its words, or as a receipt, keep_run answers it from the store, writes nothing and says
> nothing on the event stream, so its `by`, `at` and `scenarioId` stay the first asker's.

`docs/api/engines.md:541-542` says the same for any engine: "The same request twice is one row, answered as it was
first kept: its `by` and `created_by` are the first asker's, whoever asks again."

These lines say how the service answers and stores a repeat ask. They do not say what the Studies card shows. No
document at 2047f5a asks the card to name a held run's keeper or time. `run.sh` greps `docs/api`, `docs/decisions`
and `src/screens` for that wording and finds no hit about runs. The screen's own contract (`docs/api/studies.md:261`
and the header of `src/screens/ProformaStudies.tsx:25-26`, "the run lands in the list and its page is a link away")
holds as well.

## Command

```
bash bughunt/repro/H14-09/run.sh
```

It makes the fresh database `bh_r_h14_09_held`, starts the service keyless on a port in 9190-9199 and makes the
project `h14-09`. Person One then runs `cornstover` through `POST /api/library/cornstover/run` (17 s and 33 s of
BioSTEAM in the two runs). Person Two sets their name in Settings and presses Run it on cornstover in the built app's
Studies page in headless Chromium (`screen.mjs`). The script then reads `GET /api/runs` and stops the service, drops
the database and removes its files.

## Expected (by the contract named)

The second ask is answered from the held row as it was first kept and nothing is written, so the row's `by` and `at`
stay Person One's. The card answers that run and links to its page, and the runs list shows it by Person One.

## Observed (run1.log, run2.log)

- The card answered in 0.2 s and 0.1 s with "Ran cornstover. Run bfda026530692adc Computed · basis attached · its
  SFF file run-bfda026530692adc". It names neither person and gives no time, as the hunt saw.
- `GET /api/runs` holds one run before and after. Run `bfda026530692adc` stays by "Person One" at its first `at`, and
  the runs table on the same page shows "Person One | 2026-11-11 00:0x UTC".
- The run's page shows its keeper and time too (`src/screens/ProformaRun.tsx:661`, "Run for {run.by},
  {stamp(run.at)}").

The service does exactly what the contract says. The card states nothing that contradicts it: "Ran" reports the
status of the run it answers (`done`), and the run it links to was run.

## Likely cause of what the hunt saw

`src/screens/ProformaStudies.tsx:90`: `{ran.run.status === 'done' ? 'Ran' : 'Refused'} {ranWhat(ran.run, titles)}`
uses the same words for a fresh run and a held one. The card never shows `run.by` or `run.at`. The `RunReport` the
route answers has no field that marks a held answer, so the card could only tell by comparing `run.by` and `run.at`
with the request. Naming the keeper and time on the card would be a wording improvement (S4 at most). It is not a
break of the contract the candidate names.
