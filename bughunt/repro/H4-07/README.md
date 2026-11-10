# H4-07: ethanol_glucose_v0 takes a titre at harvest that its beer never reaches

**Verdict: did not reproduce as a defect (RESULT: NO-DEFECT in both runs).** The behaviour the candidate measured is
real and the same in both runs. It is also the behaviour the titre input's own declared note promises, and the
service serves that note on the shelf and shows it as the input's gloss on the parameter panel.

## Statement (the candidate's)

The titre input sets only the batch time (titre over productivity), and the beer's ethanol follows from the feed's
glucose and the yield, so a run with titre 70 g/L, feed 150 g/L and yield 0.45 makes beer at 61.83 g/L and is priced
on a 35 h batch; nothing holds the titre to what the feed can make, so a titre above feed x yield is priced too.

## Contract

- Cited by the candidate: `core/openferment_core/flowsheets/ethanol_glucose_v0.py:54`:
  `"titre": ("ethanol titre at harvest", "g L-1", None)`. That line is the input's label and unit alone.
- The input's declared description, in `core/openferment_core/flowsheets/shelf.py:85-87`:
  `FlowsheetInput(key="titre", name="ethanol titre at harvest", ... note="with the productivity, sets the batch time;
  the beer's own ethanol follows from the feed's glucose and the yield, and the run reads it back")`.
  `GET /api/proforma/shelf` serves this note, and `core/openferment_core/params.py:628` makes it the panel's `gloss`
  for the input (`gloss=fi.note`), which `src/components/ParameterRow.tsx:264` shows under the row's Why.
- The module's docstring, `ethanol_glucose_v0.py:17`: "The batch time is the titre over the productivity." The run's
  basis names the same rule as a convention (`proforma.py:1220`, `batch time` = `titre / productivity`).

## Command

    bash bughunt/repro/H4-07/run.sh

A fresh database `bh_r_h4_07_run`, a keyless service on 127.0.0.1:10010-10019, project `h407`, one run of
`ethanol_glucose_v0` through `POST /api/engines/biosteam/run` (feed 150 g/L, titre 70 g/L, yield 0.45 g/g,
productivity 2 g/L/h, scale 100,000 t/yr, glucose 0.4 USD/kg), then `GET /api/proforma/shelf` and
`GET /api/params/proforma:h407new?flowsheet=ethanol_glucose_v0`. `judge.py` sets the read-back beside the served note.
Everything is stopped, dropped and removed at the end.

## Expected

The candidate expects beer at the titre the run names (70 g/L), or a refusal in words when the feed and the yield
cannot make it. The input's served description expects the titre to set the batch time with the productivity, the
beer's ethanol to follow from the feed's glucose and the yield, and the run to read the beer back.

## Observed (both runs, identical)

- Run `6bcc5c975cc3e312`, status done: `beerEthanolGPerL` 61.8303, `batchTimeH` 35 (= 70 / 2),
  `fermenterConversion` 0.8799, base price 1.0536688973 USD/kg, no refusal. Feed x yield is 67.5 g/L, so the titre
  typed stands 2.5 g/L above it; the beer over the batch time is 1.7666 g/L/h.
- The served shelf note and the served panel gloss for the titre input both read: "with the productivity, sets the
  batch time; the beer's own ethanol follows from the feed's glucose and the yield, and the run reads it back".
- The run reads back both the beer's ethanol and the batch time, so the gap between the titre typed and the beer
  made stands on the run's own page (`src/lib/proforma.ts:1111` lists `batchTimeH` and `beerEthanolGPerL` in the
  case table).

## Likely cause (of the behaviour)

`core/openferment_core/flowsheets/ethanol_glucose_v0.py:219`: `b.R1.tau = v["titre"] / v["productivity"]`, with the
glucose fed set from the plant scale and the yield (`:215`) and the water from the feed concentration (`:218`). The
three inputs over-determine the batch, and the module resolves it as its declared note says.

## Why NO-DEFECT

The contract the candidate cites is the input's label. The input's declared note, served by the shelf and shown on
the panel, states the very behaviour observed, and the run reads back the numbers that show it. A check of titre
against feed x yield, or a word on the run when they part, would be a modelling improvement; the shelf promises
neither. The label "ethanol titre at harvest" sits beside a note that qualifies it, which is wording at most (S4).

`custom_train_v1` (the candidate's evidence) sets its batch time the same way (`custom_train_v1.py:304`) and reads
back `beerProductGPerL` and `batchTimeH`; its titre note (`shelf.py:156-159`) says the titre "with the productivity,
sets the fermenter's batch time" and leaves the beer's own concentration unsaid, a wording gap of S4 at most.
