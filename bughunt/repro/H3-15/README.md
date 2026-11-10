# H3-15: a deposition keeps a second entry under an id an earlier entry holds

**Statement.** `PUT /api/state/depositions/{id}` keeps a write that appends an entry whose id repeats a
kept entry's id, so deposition depD holds two readings under d1, and the ref `depD/d1`, the readings list
and the lookup reach the first of them alone.

**Contract.**

- `docs/decisions/ADR-006-quantities-and-estimates.md:230`: "A reading's ref keeps naming one entry. A
  deposition's, an entry's, an observation's and a measured evidence's id is unique across page loads
  (`timeId`)."; and line 237: "Every other write is refused in words".
- `docs/api/studies.md:100`: "A reading's ref keeps naming one entry: each deposition, entry, observation
  and measured evidence id is unique across page loads (`timeId`), and the service keeps a deposition the
  bench's way (`project_state.deposition_refusal`)"; line 105: "every other write is refused in words, a
  422 at `PUT /api/state/depositions/{id}`".

**Command** (from the repository root): `bash bughunt/repro/H3-15/run.sh`

It makes a fresh database `bh_r_h3_15_svc`, starts a keyless service on the first free port of
10390..10399, makes project p1, runs `repro.py`, then stops the service, drops the database and removes
the service's data copy. Nothing is mutated or built, so it needs no worktree.

**Expected.** The second write of depD (an appended entry under d1, 99 g/L on measure `other`) refused in
words with a 422: d1 is an id the deposition already holds, and a ref `depD/d1` would name two readings.
depD keeps one entry under d1.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`):

```
depD second write appends another entry under d1 (99 g/L on other): 200
depD entries kept: [('d1', 10.0, 'mz'), ('d1', 99.0, 'other')]
depD readings offered in g/L: [('depD/d1', 10.0, 'mz')]
also, depE: d1 at 10 g/L, then d1 again at 12 g/L on mz: 200; kept [('d1', 10.0, 'mz'), ('d1', 12.0, 'mz')]; readings offered []
also, depF made in one write with two entries under d1: 200; kept [('d1', 10.0, 'mz'), ('d1', 20.0, 'other')]
```

The 99 g/L reading is kept and confirmed, and no ref reaches it. On one measure (depE) the two entries
under d1 each find the other as their correction (`measurements.corrected_by` matches by id), so the
measure offers no reading at all, and a run naming `depE/d1` is refused with words that name the ref as
its own correction ("reading depE/d1 was corrected by depE/d1"). A first write (depF) holding two entries
under one id is kept too.

**Likely cause.**

- `core/openferment_core/project_state.py:271-289` (`_appended`): it checks that every kept id is still
  sent, in its order, with its fields, and checks no appended id against the kept ones or against each
  other.
- `core/openferment_core/project_state.py:586-590` (`_put`): `deposition_refusal` runs only when the row
  exists, and `_checked` with the `Deposition` model (`models.py:4932`) holds no uniqueness of entry ids,
  so a first write with repeated ids is kept as sent.
- The readers resolve an id to its first match: `core/openferment_core/measurements.py:139` (`reading`)
  and `measurements.py:98` (`corrected_by`).

Severity S3: an edge case reached by a client other than the bench page (the page's `timeId`,
`src/store.ts:208`, gives fresh ids), with a workaround (a fresh id); the second reading stays in the
record and no run can take it.
