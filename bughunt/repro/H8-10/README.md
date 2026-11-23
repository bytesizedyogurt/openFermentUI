# H8-10: a catalogue file with one id on two rows answers both kept, and the first row is gone

**Statement.** `POST /api/intake/catalogue` with a CSV whose rows are `S5,First` and `S5,Second` answers
`{"kind": "strain", "kept": ["S5", "S5"], "refused": []}` and writes two `keep_catalogue` audit rows in state
`kept`, while the strain catalogue then holds `S5` "Second" alone: the first row's entry is lost with no
refusal and no word in the answer.

**Contract.** `docs/api/intake.md:104`, the row for `POST /api/intake/catalogue`:
"Every row that is an entry is kept with the file as its source and audited as `keep_catalogue`, its detail
naming the file; every other row is refused with its reason (`{"kind", "kept", "refused"}`)". The service says
the same in `core/openferment_core/api.py:1192-1195` ("every row that is an entry kept with the file as its
source, each audited as `keep_catalogue` naming the file, every other row refused with its reason") and in
`core/openferment_core/catalogues.py:554-556`. The single keep's row above it (`docs/api/intake.md:103`) says
"an entry under the same id replaced", which covers an entry held before the file; within one file the answer
counts the first row among the kept, and the catalogue holds nothing of it.

**Command.** From the repository root: `bash bughunt/repro/H8-10/run.sh`. It makes the database
`bh_r_h8_10_svc` fresh, starts the head's service keyless on 127.0.0.1:9140, makes project `h810`, posts
`dup.csv` (`id,name` / `S5,First` / `S5,Second`) as kind `strain`, reads `GET /api/catalogues/strain` and
`GET /api/audit?action=keep_catalogue&target=strain/S5`, then stops the service and drops the database.

**Expected.** Each row the answer counts as kept is held after the request: the second `S5` row refused with
its reason (or the answer naming the replacement), and `kept` naming `S5` once.

**Observed (both runs).**

```
OBSERVED: HTTP 200, answer {"kind": "strain", "kept": ["S5", "S5"], "refused": []}
OBSERVED: the strain catalogue holds [('S5', 'Second')]
OBSERVED: 2 keep_catalogue audit rows on strain/S5, states ['kept', 'kept']
OBSERVED: rows of the file whose entry the catalogue does not hold: ['First']
RESULT: DEFECT
```

The catalogues screen draws this answer as "Kept 2: S5, S5" (`src/screens/Catalogues.tsx:452-457`), its
list keyed by the id, so two spans share the key `S5`.

**Likely cause.** `core/openferment_core/catalogues.py:566-576`: `intake` validates each row on its own and
appends every valid one to `good` and its id to `out.kept`, with no check for an id already seen in the file.
`_keep` (`catalogues.py:444-469`) then writes each entry in turn through `rows.put` at line 466, keyed by
`_row_id(kind, id)`, so the later row replaces the earlier in the same transaction, and writes an audit row
for each. Confidence high. A small fix: refuse a row whose id an earlier row of the same file holds, with its
row number and the earlier row's, before the keep.

Severity S3 (an edge case; one row an id in the file is the workaround). Kind: contract break.
