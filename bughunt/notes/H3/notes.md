# H3: quantities, units and provenance (2047f5a)

Everything ran keyless. Pure functions ran in the repository's venv. Hypothesis ran in a worktree of my own at
2047f5a, which I removed afterwards. The service ran on 127.0.0.1:8830 over the test database bh_h3_a with
projects p1 and p2, and I dropped the database afterwards. No BioSTEAM worker started: the doors that take values
were reached through the Proforma scope's resolve and the kinetics engine. No file under core/, src/, scripts/ or
examples/ changed (`git diff 2047f5a -- core src scripts examples` is empty).

Rerun: `bash bughunt/notes/H3/scripts/run_service_repros.sh` runs every service probe from a fresh database
(log: `logs/run_service_repros.log`). The pure scripts run with `cd core && .venv/bin/python
../bughunt/notes/H3/scripts/<name>.py`. To run `units_props.py` you need hypothesis in a worktree's venv.

## Units (units.py, schema/units.json)

- I checked every factor and offset by hand and found them right (°F, K, d⁻¹, t d⁻¹, kDa, MJ kg⁻¹, % w/v, mg dL⁻¹).
- Hypothesis, 300 examples per property: A to B to A holds within 1e-12 relative and composition within 1e-9.
  Every cross-family pair and every unknown unit raises UnitError. convert(x, A, A) misses exactness by the last
  digit (201 mg dL⁻¹ comes back as 201.00000000000003). A finite value past a float's range comes back as inf with no
  refusal, and NaN comes back as NaN. Every caller I found guards both.
- normalize gets some spellings wrong:
  - It folds case onto another prefix: Mg reads as mg, ML as mL, Mm as millimolar, S as s and G as g (H3-07).
  - The labelled-gram rule reads g/gal, gal/g and g/gmol as g g⁻¹ (H3-08).
  - The percent family converts % DW, % v/v and % of native sites into each other 1:1, which the table's own
    refusal calls a category error (H3-09).
  - It refuses a Greek mu (H3-16).

## Provenance: the hand table and the code

I worked out by hand, from ADR-006's C.5 note and runs.md, the class each mix of inputs should earn. Then I compared
the table with basis.basis_provenance (`scripts/provenance_table.py`). All 21 rows agree.

| inputs (beside the package's defaults) | class |
|---|---|
| none, or conventions | computed |
| a person's value, or a model's estimate (with anything else) | assumed |
| a reading | measured |
| a reading and a gold, unverified or industry-estimate record | measured (C.5 says so) |
| a reading and an artifact computed with no assumption | measured |
| a reading and an assumed artifact, or a record or artifact nobody can find | assumed |
| a gold or verified record | computed |
| an unverified record | unverified |
| a deposition series (a fit's readings) | computed |
| a measured artifact | computed |

- weakest_provenance gives a claim the weakest class it cites.
- PROVENANCE_RANK in src/store.ts equals PROVENANCE_ORDER member for member.
- The kinetics engine agreed:
  - every value a reading: measured
  - one estimate or one person's value beside readings: assumed
  - every value a person's or a model's: assumed
- Readers that drift from this table:
  - A kept run stays measured after its reading is corrected (H3-06).
  - Measured evidence takes its mark from the page's own fields (H3-04).
  - The deposition screen draws an unconfirmed released value under the measured badge, and the module read calls
    the same row unverified (H3-14).

## Every origin kind at every door I could reach

- **Proforma resolve.** It took person-assumption, model-estimate and measurement, each with the right basis source
  (assumption, model-estimate, deposition). It refused record, artifact, library-default and convention with a 422
  in words.
- **Measurements at that door.** It refused each of these:
  - another project's reading
  - an unconfirmed reading
  - a corrected reading
  - a value, unit, high or depositor other than the reading's own
  - a reading in K for a parameter in g L⁻¹

  It set 0.0125 min⁻¹ as 0.75 h⁻¹ and stated the conversion in the basis note.
- **A corrected reading.** It stands again once its correction's sample time moves, or once its own sample time is
  taken away, while the deposition is open (H3-05).
- **Duplicate entry ids.** A deposition write may append an entry under an id an earlier entry already holds
  (H3-15).
- **Scenario make and run, the Proforma run, the train engine.** I did not run these, because each starts the
  BioSTEAM worker. Each calls basis.resolved, the function the two doors above exercise.

## A model's estimate at every record store

- **Bench records.** A deposition entry with an estimate origin, measured evidence saying assumed, and measured
  evidence with an estimate source are each refused with a 422 ('never a record').
- **test_estimates.py.** It names the four record stores ADR-006 names: BioRepo, candidates, depositions and
  measuredEvidence. The candidates store refuses estimates for hand-written candidates too, through the same _put.
  I found no other record store that needs the refusal.
- **Catalogue.** A person's keep with an estimate field no kind takes is answered 200, and the service drops the
  field without a word (H3-17).
- **Protocols.** They hold no quantity.
- **Measured evidence.**
  - Any later write can overwrite it whole (40 g/L became 400 g/L from another person) with no audit row, and it is
    still served as measured (H3-03, S1).
  - It is kept for a deposition the project does not hold (H3-04).

## Numbers in words

- find_number lets 34 of 41 quantity sentences through (H3-02). Among them:
  - 'two dollars per gallon', 'ten per cent', 'ten tonnes'
  - 'two thirds', 'hundreds of litres'
  - 'the high-90s', 'the mid-40s', 'pH5', 'x10'
  - 'doubled', 'the twentieth', '③', '五'
- validate_plan keeps such a claim with its cited record's class (verified).
- practice.py's own comment names pH7, x10 and the multiplying words as what find_number misses. Postdoc's claims
  have no second check.
- Other free-text fields where numbers in words get through:
  - an estimate's unit (H3-10)
  - a tool quantity's note, which the claim door holds to Rule 1 as a basis (H3-11)
  - a candidate's method and organism; its carbonSource is held to Rule 1 (H3-12)
  - catalogue_write's name, summary and note (H3-13)

## Records and anchoring

- anchor_candidate compares a quote's number bare when the quote's unit does not convert into the candidate's unit.
  It labels the result converted, or exact when the unit token is unknown. Cases that anchor:
  - 2.15 USD/kg on '$2.15/gal'
  - 45 g/L on '45% (v/v)'
  - 0.45 g/g on '0.45 h-1'

  biorepo.write re-anchors a verified or gold decision through the same function (H3-01). test_anchor.py holds the
  same-family case alone.

## What a live model would show

See needsLiveModel in candidates.json: how often a live answering model or the extractor writes the forms that pass
H3-01, H3-02, H3-10, H3-11 and H3-12.
