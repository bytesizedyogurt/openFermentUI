# H12-13: is_measurement's note clause, and no test that it decides

**Statement.** Dropping the `measured on` note clause from `basis.is_measurement` (mutation M05) leaves `test_basis.py`, `test_estimates.py`, `test_measurements.py`, `test_finite_inputs.py`, `test_params.py`, `test_fermos.py`, `test_exports.py`, `test_comparisons.py` and the two `test_engines.py` tests that build a reading green, because no test under `core/tests/` builds a deposition source whose id is reading-shaped and whose note says something other than `measured on <at>`.

**Contract.** `core/openferment_core/basis.py:195-200`, the docstring of `is_measurement`:

> Whether a basis source is a deposition's reading a run set (`measurement_source`): a deposition naming one reading, `<deposition id>/<entry id>`, its note saying when the reading was taken. A deposition naming a whole series (the readings a kinetic fit is made on, fermos.py) is the bench's record the fit rests on.

`docs/decisions/ADR-006-quantities-and-estimates.md:188-192`:

> A reading's basis source is a `deposition` naming it (`basis.measurement_source`): its id the ref, its `by` the depositor and its note `measured on <at>` with any conversion. `basis.origin_of` reads it back as a `measurement`. A deposition source naming a whole series (the readings a kinetic fit is made on) reads back as the bench's record, as it did, and the fit's provenance stays what it was.

**Command.** From the repository root:

    bash bughunt/repro/H12-13/run.sh

The run is keyless, makes no model call and starts no service. It makes a scratch worktree of 2047f5a, with the conform scratch prefix renamed to `bh_r_h12_13_conform`. It also makes a fresh database `bh_r_h12_13_probe` and the test databases `bh_r_h12_13_t_*`. When it ends it drops all of them and removes the worktree.

1. It prints the contract.
2. It reads the syntax tree of every `core/tests/test_*.py` and lists each deposition basis source a test builds (`BasisSource(kind="deposition")`, `measurement_source`, `fermos.fit`, and a fit request body), with the id and note it carries. It counts the ones whose id is reading-shaped (`models.READING_REF`) and whose note begins with something other than `measured on`. Those are the only sources the note clause decides.
3. On the fresh database it asks about a deposition source `dep-b1/de-1` carrying fermOS's series note (`fermos.py:367-368`), on the tree and then with M05. It asks `is_measurement`, `origin_of`, `is_set` and `basis_provenance`, and it reads the provenance of the kinetic fit that `fermos.fit("dep-b1/de-1", …)` keeps in a project of its own. That id is one `POST /api/fermos/fit` takes as the request names it: `models.py:1730`, `depositionId: str`.
4. It applies M05 with a counter appended to `basis.py`. The counter returns M05's answer and writes one line for each call whose answer the note clause decides. With both in place it runs the hunt's eight test files for M05 and the two `test_engines.py` tests that build a reading (`test_a_kept_trains_defaults_each_name_one_of_the_five_default_origins_by_every_path_that_keeps_one` and `test_the_copy_holds_every_row_a_trains_resolution_reads_and_resolves_each_train_as_the_project_does`).

**Expected.** Some test builds a deposition source whose id is reading-shaped and whose note is fermOS's series note, or any note other than `measured on <at>`. That test holds the source to the bench's record, so a fit resting on it stays `computed`. With M05 applied, that test fails.

**Observed (run1.log, run2.log, the same in both).**

- On the tree, the source reads as `is_measurement=False`, origin `record` and `is_set=False`, with `basis_provenance` `computed`. The fit for `dep-b1/de-1` is kept as `computed`. The code keeps its contract.
- With M05, the same source reads as `is_measurement=True` and `is_set=True`, with `basis_provenance` `measured`. `origin_of` raises a ValidationError (`Origin` holds a measurement to an `at`, and the series note has none). The fit for `dep-b1/de-1` is kept as `measured`, a provenance label one class above gold. The fit for `dep-b1` stays `computed` both ways. In the probe, the counter records 6 calls that the note clause decides.
- The scan finds 36 deposition sources and fits built in the tests, and 0 of them carry a reading-shaped id with a note other than `measured on`. Each reading-shaped id is built by `measurement_source`, which stamps `measured on` (`basis.py:102-103`), or written with a `measured on` note (`test_engines.py:1978`). The one series source a test builds is `d-1` (`test_basis.py:211`), which has no slash.
- With M05 and the counter in place, the selection gives 225 passed, exit 0. The counter records 0 calls that the note clause decides.
- Both runs print `RESULT: DEFECT`.

The tree labels the fit correctly. A change that drops or weakens the note clause would let a fermOS fit, kept through a request whose `depositionId` holds a slash, be labelled `measured`, and every test would still pass. Severity S4, kind Hollow test.

**Likely cause.** `core/tests/test_basis.py:203-212` (`test_a_measurement_is_a_deposition_naming_its_reading_and_when_it_was_taken`) holds the series case with `BasisSource(kind="deposition", id="d-1", …)` alone. The id clause already rejects that id, so the note clause at `core/openferment_core/basis.py:202` (`and bool(_MEASURED.match(source.note or ""))`) is never the clause that decides a test's answer. The fix is small: in that test, add a series source with a reading-shaped id (`dep-b1/de-1`) and fermOS's note, and assert `is_measurement` False, `origin_of(...).kind == "record"` and `basis_provenance` `computed`. A `test_fermos.py` fit with `depositionId="dep-b1/de-1"` that asserts the kept fit is `computed` holds the same rule at the door.
