# H2-08: a comparison asked again with a title of spaces loses the title it was kept with

**Statement.** A title of three spaces passes `ComparisonCreate`'s `min_length=1`, the service strips it to an
empty string and writes it over the kept comparison's title, its `by` and `created_by` staying the first asker's.

**Contract.**
- `core/openferment_core/models.py:4809` (`ComparisonCreate`): "title: str = Field(min_length=1, max_length=200)"
- `docs/api/studies.md:149`: "`POST /api/studies/comparisons` | `{title, runIds, by}`: two to twelve runs compared, kept"
- `core/openferment_core/api.py:1520-1521`: "Two or more engine runs set side by side, computed as one
  `study.comparison` artifact and kept with the title."

**Command** (from the repository root): `bash bughunt/repro/H2-08/run.sh`

It makes the fresh database `bh_r_h2_08_svc`, starts the head's service keyless on 127.0.0.1:10090 in the proof's
offline mode, makes two kinetics forecast runs from two fits of placeholder logistic series, keeps a comparison of
them titled `default beside measured`, asks the same runs again with the title `"   "` by `Someone Else`, reads the
comparison back (one and the list) and its `comparisons` row, and asks the runs reversed with a title of spaces as a
first ask. It stops the service and drops the database at the end. About 6 s.

**Expected.** The title of spaces refused in words (a 422, as the route refuses other bad asks), or the comparison
left with the title it was kept with.

**Observed** (both runs, `run1.log` and `run2.log`):
- the second ask answers 200 with title `''` and by `Hunter H2-08`;
- `GET /api/studies/comparisons/{id}` and `GET /api/studies/comparisons` both give title `''`;
- the row holds `created_by 'Hunter H2-08', body title '', body by 'Hunter H2-08'`;
- a first ask with a title of spaces (the runs reversed, a new comparison) is kept with title `''` as well.

**Likely cause.** `core/openferment_core/studies/comparisons.py:270`:
`comparison = StudyComparison(id=art.id, title=asked.title.strip(), ...)` strips the title after validation with no
blank check, and `_put` (`comparisons.py:235-237`, `rows.put`) writes the new body over the kept one. The model's
`min_length=1` counts the spaces before the strip. The browser's Studies screen trims the title and disables the
Compare button on a blank one (`src/screens/ProformaStudies.tsx:492`, `:582`), so the doors that reach it are the
REST route and the tool registry's `make_comparison` (`core/openferment_core/tools/writes.py:620`).

**Fix size.** Small: refuse a title blank after the strip (a `field_validator` on `ComparisonCreate`, or a
`ComparisonRefused` in `make`).
