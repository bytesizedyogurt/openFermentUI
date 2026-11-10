# H5-03: an `/api/state` write under another kind's id replaces a study scenario or a model's kept train

**Statement.** `PUT /api/state/scenarios/{id}` naming a study scenario's id, and `PUT /api/state/trains/{id}`
naming a train a model kept, each answer 200 and overwrite that row in place: the study scenario (its title,
plant, values and `runIds`) and the model's kept train are lost, and the one DELETE route then removes the row.

## Contract

- `core/openferment_core/pureos/kept.py:12`: "ONE WRITE FUNCTION. `keep_train` is the only function that
  writes the store". The store is the `trains` rows of kind `kept` (kept.py:39-42). `keep_train` also refuses
  a new kept train under an id a person's train holds: kept.py:98, "a train is already named {spec.id} in this
  project". The two kinds of train therefore share one id space, and the store keeps that guard in one direction.
- `docs/TOOLS.md:48-49`: "pureOS's kept trains hold a model's work alone, and a person's call to keep one is
  refused in the store's words."
- `core/openferment_core/db/models.py:214-216`: "Two kinds of scenario share the table (migration 0004):
  `proforma`, the rows the Proforma screens keep (project_state.py), and `engine`, a study's scenario on a
  library plant or an openFerment flowsheet (studies/)." `docs/api/studies.md:9-10` says the same: a study
  scenario is "a row of `scenarios` with kind `engine` (the Proforma screens' rows in the same table are kind
  `proforma`)". No route but `/api/state` takes a study scenario or a kept train back (`core/openferment_core/api.py`
  holds one `@app.delete`, line 2854).

## Command

```
bash bughunt/repro/H5-03/run.sh
```

It makes a fresh database `bh_r_h5_03_kinds` and starts a keyless service on the first free port of
127.0.0.1:9330-9339 with the collectors refusing the network. Then it makes one project, a study scenario on
`cornstover` with no values (the BioSTEAM worker reads the plant's parameters, under a minute), a kinetics
run, and a model's kept train (`pureos_build` `new` in the model's lane). After that it runs the two writes
as the person `bob` and reads each store back, with the row's `kind` column from the database. It stops the
service, drops the database and removes the data copy. It exits 0 either way.

## Expected

Each PUT is refused in words (a 422) naming the row another kind keeps under that id. The study scenario
reads back from `GET /api/studies/scenarios/{id}` as made, and the kept train stays in
`GET /api/pureos/trains-kept`.

## Observed (run1.log, run2.log: the same in both)

- `PUT /api/state/scenarios/ssc-21b4b9fdadce` 200. Then `GET /api/studies/scenarios/ssc-21b4b9fdadce` 404
  "the project holds no scenario ssc-21b4b9fdadce", `GET /api/studies/scenarios` `[]`, and the row's
  kind `engine` is now `proforma`. `DELETE /api/state/scenarios/ssc-21b4b9fdadce` 200 removes the row.
- `PUT /api/state/trains/tr-…` 200. `GET /api/pureos/trains-kept` goes from `['tr-…']` to `[]`, and the
  row's kind `kept` is now `made`.
- The row keeps its first maker in `created_by` (`rows.put` keeps who made a row that exists,
  `db/rows.py:59-60`): the scenario row bob wrote reads `proforma, made by alice`, and bob's saved train reads
  `made, made by bh-h5-03-agent/0.1`, a person's train with the model as its maker.
- The audit records each overwrite as an ordinary first keep (`keep_scenarios`, `keep_trains` by `bob`)
  and names no replaced row.

## Likely cause (high confidence)

- `core/openferment_core/project_state.py:522-531` (`_held`, called at line 579) reads only the kind's own rows:
  `KINDS["scenarios"].where` is `kind == "proforma"` and `KINDS["trains"].where` is `kind == "made"`
  (lines 146-149). The other kind's row under the same id reads as absent, `existed` is False, and the
  write goes ahead as a new keep.
- `core/openferment_core/project_state.py:611` calls `rows.put`. That function upserts on
  `(project_id, id)` (`core/openferment_core/db/rows.py:61-66`, `on_conflict_do_update`), and its `columns`
  set `kind` to `proforma` or `made` (project_state.py:146, 148). The other kind's body and kind are
  replaced in one statement.

The guard at `pureos/kept.py:97-98` covers one direction: a model's new train under a person's train id is
refused. `project_state._put` holds no matching check. A small fix: `_put` refuses an id the table holds under
another kind, in words naming that row.

## Reach

The pages never send such an id. Browser train ids are `tr-<base36>-<n>` (`src/store.ts:208`), the Builder
copies a kept train under a new id (`src/screens/PureOSBuilder.tsx:20-23`), study scenario ids are
`ssc-<12 hex>` and model train ids `tr-<12 hex>` (`pureos/build.py:55-73`). The write comes from any HTTP
caller in the project that names an id of the other kind, and the row is then lost.
