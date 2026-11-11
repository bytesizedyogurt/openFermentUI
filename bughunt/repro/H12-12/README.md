# H12-12: a reading corrected twice, and no test that asks about one

**Statement.** A `corrected_by` that names the first of two corrections passes `test_measurements.py`, `test_basis.py` and `test_finite_inputs.py`, because no test in `core/tests/` asks which entry corrects a reading that was corrected twice.

**Contract.** `core/openferment_core/measurements.py:90-95`, the docstring of `corrected_by`:

> The id of the entry that corrects `entry` in its deposition, or None when `entry` is the reading that stands for its measure: the latest entry on the same measure that shares its sample time, or that has none when `entry` has none (the module's docstring).

The module's `standing` rule (`measurements.py:19-25`) adds that a later entry still waiting to be read back corrects a reading too, and that the refusal says the newer number waits. The bench appends a new entry for every correction (`src/store.ts:2170` `amendEntry`), so a person who corrects one reading twice leaves two later entries on its measure.

**Command.** From the repository root:

    bash bughunt/repro/H12-12/run.sh

Keyless, no model call, no service. It makes a scratch worktree of 2047f5a (with the conform scratch prefix renamed to `bh_r_h12_12_conform`), a fresh database `bh_r_h12_12_probe`, and the test databases `bh_r_h12_12_t_*`. It drops all of them and removes the worktree when it ends.

1. It lists every test that asks which entry corrects a reading. Each one asks about a reading whose deposition holds a single correction after it: de-1 to de-3, de-5 to de-7, and de-3 to de-10.
2. In a project of its own on the fresh database it deposits one flow read three times: de-1 (confirmed), its correction de-3 (read back), and a second correction de-10 (still waiting to be read back). It then asks `corrected_by` and `looked_up` about de-1, first on the tree as it stands and then with mutation M37 (`later[-1]` becomes `later[0]`).
3. With M37 applied, it runs the three test files the hunt recorded for this function.

**Expected.** `corrected_by(de-1)` names de-10. The refusal reads "was corrected by …/de-10, which waits for a person to confirm its number at the bench". When the first correction (de-3) is named, some test of a reading corrected twice fails.

**Observed (run1.log, run2.log).**

- On the tree: `corrected_by(de-1) = de-10`, and the refusal names de-10 and says it waits. The code keeps its contract.
- With M37: `corrected_by(de-1) = de-3`, and the refusal reads "reading …/de-1 was corrected by …/de-3, the reading that stands for its measure now". That names the wrong reading, and the state it gives is false: de-3 is itself corrected by de-10, which waits.
- With M37 applied, `test_measurements.py`, `test_basis.py` and `test_finite_inputs.py` give 139 passed and exit 0.
- No test under `core/tests/` asks about a reading corrected twice. The count is 0.
- `RESULT: DEFECT` in both runs.

The refusal stands under the mutation, so no run takes the stale reading and no number or provenance is wrong. The mutation changes the refusal's words, and no test sees them change. Severity S4, kind Hollow test.

**Likely cause.** `core/tests/test_measurements.py:57-68` (ENTRIES and SAMPLE_TIMES) and `core/tests/test_measurements.py:201-206` (`test_the_reading_that_stands_for_its_measure_is_the_latest_at_its_time`) give every corrected reading a single correction. The choice between the first and the latest correction at `core/openferment_core/measurements.py:104` (`return str(later[-1].get("id")) if later else None`) therefore goes untested. The fix is small: add an assertion that `corrected_by` names de-10 for de-1 when the deposition holds de-3 and de-10 after it, together with the refusal's words for that case.
