# H12-14: the rank of `user` against `industry-estimate` is held by nothing but the two copies agreeing

**Statement.** Swapping `user` and `industry-estimate` in `PROVENANCE_ORDER` and in `PROVENANCE_RANK` together
passes `check:plan` and every test over the provenance readers, and it moves the class of a claim resting on a
person's artifact and a vendor figure from `industry-estimate` to `user`; either copy swapped alone is caught.

**Contract.**

- `core/openferment_core/models.py:23-27`: "The provenance classes, strongest first and weakest last ... The order
  IS the ranking: `weakest_provenance` walks PROVENANCE_ORDER below, which `check:plan` holds to these classes, so
  adding a class in the wrong place silently changes what a claim claims."
- `core/openferment_core/models.py:41-42`: "The same order as PROVENANCE_RANK in src/store.ts, member for member;
  `check:plan` parses both and fails on any difference".
- `core/openferment_core/models.py:371-373` (`weakest_provenance`): "A claim is worth exactly as much as its worst
  evidence."
- `scripts/check-plan.mjs:10-14` and `docs/decisions/ADR-011-guards.md:62-67` (E.15): the check holds the union and
  the order to the same classes, the order to start at `measured`, `measured` above `gold`, an unverified
  extraction at least as high as an industry estimate, and `PROVENANCE_RANK` in the order's order.

The tree ranks `user` (6) above `industry-estimate` (7) in all three declarations (the Literal, the order, the
rank), and ADR-006:198 names the weaker classes in that order. Of the order's nine places, the tests pin the first
six (`core/tests/test_basis.py:88-92`) and `check:plan` pins `industry-estimate` below `unverified`; the place of
`user` against `industry-estimate` is held only by the order and the rank agreeing with each other.

**Command.** `bash bughunt/repro/H12-14/run.sh` from the repository root. Keyless, no service. It makes a
worktree of 2047f5a and a fresh database `bh_r_h12_14_probe`, runs `check:plan` on the tree, with G1 (the rank
swapped alone) and with G2 (the order swapped alone), applies G4
(`bughunt/notes/H12/mutations/G4-user-industry-swap-order-and-rank.patch`: both swapped, the Literal untouched),
asks `weakest_provenance` and `basis_provenance` about a basis on a `user` artifact and an `industry-estimate`
record, runs `check:plan` and `test_basis.py test_validate.py test_evidence_pool.py test_postdoc_agent.py
test_openapi.py`, and runs `test_openapi.py` with G3 (the Literal swapped too) as the control that the run reads
the mutated worktree. No bytecode is kept, so a two-line swap of equal size cannot hide behind a cached `.pyc`.
Every database made is `bh_r_h12_14_*`; all are dropped and the worktree removed at the end.

**Expected.** A check or a test that holds `user` above `industry-estimate`, so the swap of both copies fails
something (or a record that the two are unordered).

**Observed.** `check:plan` exits 0 on the tree, 1 on G1, 1 on G2 and 0 on G4 ("✓ PROVENANCE_RANK holds
PROVENANCE_ORDER, member for member."). With G4, `weakest_provenance(["user", "industry-estimate"])` and the
basis's provenance are `user` (on the tree, `industry-estimate`), the Literal's tail
(`unverified > user > industry-estimate > assumed`) differs from the order's
(`unverified > industry-estimate > user > assumed`), and the five files pass (185 tests). The control G3 fails
`test_openapi.py::test_the_committed_document_is_the_services`. No test file holds a `user` class beside an
`industry-estimate` one.

**Likely cause.** `scripts/check-plan.mjs:47-59` holds the union to the order by membership alone (a `Set`, lines
34-38) and pins three relations, none on `user`; `core/tests/test_basis.py:88-92` pins the order up to
`unverified` and compares the Literal to the order as sets (line 92). A fix is small: compare the Literal to the
order member for member in `check:plan` (the Literal's comment already calls it strongest first), or pin the full
order in `test_basis.py`.

**Severity.** S4, a hollow guard: the tree's ranking is right today, and a reordering that changes what a claim
claims passes every gate.
