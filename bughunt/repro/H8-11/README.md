# H8-11: a catalogue file's row that names a source keeps it, and the file goes unnamed

**Statement.** A row of a catalogue file that carries its own `source` is kept with the row's words as the
entry's source, so the entry S6 taken in from `rows.json` names the file nowhere; the file shows up only in
the audit row's detail.

**Contract.** `docs/api/intake.md:104`, the `POST /api/intake/catalogue` row: "Every row that is an entry is
kept with the file as its source and audited as `keep_catalogue`, its detail naming the file". The same
words stand in the function's own docstring, `core/openferment_core/catalogues.py:554-556` ("every row that
is an entry kept in the name of `by` with the file as its source"), and on the catalogues screen,
`src/screens/Catalogues.tsx:426-427` ("Every row that is an entry is kept in your name with the file as its
source").

**Command.** From the repository root: `bash bughunt/repro/H8-11/run.sh`. It starts the head's service on
127.0.0.1:9811 over a fresh test database `bh_r_h8_11_svc`, keyless, makes the project `h811`, posts the
JSON file `rows.json` with two strain rows (S6 with `"source": "a row's own words"`, S7 with no source),
reads both entries and their `keep_catalogue` audit rows, then stops the service and drops the database.

**Expected.** Both entries are kept with the file as their source: S6's and S7's `source` each name the
file `rows.json` (S6 may carry the row's words beside the file).

**Observed (both runs).**

```
OBSERVED: HTTP 200, answer {"kind": "strain", "kept": ["S6", "S7"], "refused": []}
OBSERVED: GET /api/catalogues/strain/S6 source: "a row's own words"
OBSERVED: GET /api/catalogues/strain/S7 source: "the file rows.json"
OBSERVED: keep_catalogue audit on strain/S6, detail [{'kind': 'strain', 'file': 'rows.json'}]
OBSERVED: keep_catalogue audit on strain/S7, detail [{'kind': 'strain', 'file': 'rows.json'}]
RESULT: DEFECT
```

S7, with no source of its own, holds "the file rows.json"; S6 holds the row's words alone, and the file
it came in by is named only in the audit detail.

**Likely cause.** `core/openferment_core/catalogues.py:571`, in `intake`:
`"source": r.get("source") or f"the file {filename}"`. The same call writes `by`, `agent`, `via` and `at`
over whatever the row sends (`core/tests/test_catalogues.py:88`: "a file is taken in a person's name,
whatever its rows say"), and lets a row's `source` stand over the file. The one test of the file's source,
`core/tests/test_catalogues.py:87`, posts rows that carry no source, so it cannot see this branch. The CSV
path reaches the same line: a CSV with a `source` column keeps each row's words the same way.

**Severity.** S4 (a contract's words and the code's behaviour drift apart; the file is still named in the
audit row, and a file whose rows leave `source` out is kept as the contract says).
