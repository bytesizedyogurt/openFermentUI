# H3-12: a candidate's method and organism keep the extractor's numbers; its carbon source is held to the number rule

**Statement (the candidate's).** `validate.anchor_candidate` drops a `carbonSource` that holds a number or stands outside the cited section, and keeps the method "HPLC; a repeat at 30 °C reached 85 g/L in 48 h" and the organism "a strain that made 85 g/L in fed-batch" as the extractor wrote them, numbers and all.

**Verdict: the behaviour reproduces, and it is the contract as the tree writes and tests it.** Both runs end `RESULT: NO-DEFECT`.

## The contract the candidate cites, and what it says

- `CLAUDE.md:54`: "A record's value stands inside the verbatim quote it anchors to, in a unit its field is denominated in". This governs the record's value. On the candidate's inputs the value 45 g/L stands inside its quote, so the rule holds.
- `core/openferment_core/models.py:967-969` (the `carbonSource` comment): "Kept only when the words stand in the cited section and carry no number; dropped otherwise, with the candidate kept and the drop counted". This governs `carbonSource`, and the code keeps it: 'glucose at 120 g/L' is dropped and counted.

The tree's own words on the other two fields:

- `core/openferment_core/models.py:962-964`: "`organism` is the strain id when anchoring resolved the extractor's wording to one (`validate.strain_id`), the wording otherwise".
- `core/openferment_core/validate.py:1165-1168`: "No match leaves the wording as the paper wrote it."
- `core/openferment_core/validate.py:859`: `FIELD_DROP_REASONS = ("carbonSource",)`, the fields anchoring may drop from a kept candidate. `core/openferment_core/models.py:1139` says the same: "Today the one reason is `carbonSource`."
- `core/openferment_core/validate.py:1055-1057`, the `anchor_candidate` docstring: "A candidate that anchors may still lose a field: a carbon source whose words are not in the cited section, or carry a number, is dropped and the candidate kept."
- `core/openferment_core/validate.py:1152-1157`: a method is held to presence where the field requires one; `core/openferment_core/extract.py:107-109` asks the extractor to "Name it as the paper does".
- `core/tests/test_validate.py:200-202` pins an organism wording that stands outside the cited section ("AB12 crossed with CD34", the section naming AB12 alone) kept as written.
- The design the feature came from, `docs/history/build-2026-10-21/OF-BLD-014.md:667` and `:674` (history, no authority), holds the carbon source to the section and the number rule and says "No match leaves `organism` as the paper wrote it."

## Command

```
bash bughunt/repro/H3-12/run.sh
```

Run it from the repository root. It makes the fresh test database `bh_r_h3_12_anchor` (migrated to head, named to the service and the tests) and prints the contract lines as written. It then runs `repro.py` with the repository's Python on the candidate's own inputs. This is a pure function: no service, no key, no model call, no network. `repro.py` reads `FIELD_DROP_REASONS`, the docstring and the `Candidate` comments, and passes wordings a paper writes through `find_number`. The script then runs three of the tree's own tests (six cases, pure, no database touched), checks that nothing under `core/`, `src/`, `scripts/` or `examples/` was written, and drops its database.

## Expected

- From the candidate: method and organism dropped and counted, as `carbonSource` is, when they hold a number or stand outside the cited section.
- From the tree's contract: the value 45 g/L inside its quote, and `carbonSource` dropped and counted. The organism is kept as the extractor's wording when no strain resolves, and the method is kept as given.

## Observed (both runs)

- The candidate anchors. Its value 45 g L⁻¹ stands in its quote, and the method and organism are kept as written.
- `carbonSource` is dropped, with the reason "carbonSource 'glucose at 120 g/L' contains a number ('1')".
- `FIELD_DROP_REASONS == ('carbonSource',)`, and the docstring and the `Candidate` comments read as quoted above. No comment holds the method to anything.
- The three pinned tests pass, 6 cases.
- `find_number`, the rule `carbonSource` passes, finds a number in wordings a paper writes: the strain "Saccharomyces cerevisiae 424A(LNH-ST)" ('4'), "Zymomonas mobilis 8b" ('8'), and the methods "HPLC (Aminex HPX-87H, 65 °C)" ('6') and "absorbance at 600 nm" ('6'). The candidate's expected rule would drop these, and the first is the cellulosic ethanol literature's best-known strain.

`run1.log` and `run2.log` beside this file hold the two runs. Both end `RESULT: NO-DEFECT` and agree line for line, apart from the tree's commit and the test timing.

## Where the behaviour comes from

- `core/openferment_core/validate.py:1154-1155`: the method is read as given.
- `core/openferment_core/validate.py:1169`: the organism wording is read as given and resolved to a strain id where it names one.
- `core/openferment_core/validate.py:1172-1189`: the carbon source is held to the section and to `find_number`.

Each matches its comment, its docstring and its tests. Holding a candidate's method and organism to the paper's words would be a new rule, owed a decision record. The section check would also drop most methods, since a paper names its method in its Methods section and the cited sentence usually stands in its Results.
