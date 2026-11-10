# H14-02: a kept strain's aliases never resolve a record's organism

**Statement.** Anchoring resolves a paper's organism wording through `validate.vocabulary()`, whose strain map is always empty in the service, so a record whose organism is a kept strain's alias keeps the raw wording and no strain id, and every strain page, the Hosts coverage counts and fermOS's strain filter find no record for the strain.

## Contract

- `src/screens/Organisms.tsx:46-47`: "A record counts for a strain when its organism tag names it: anchoring resolves the wording a paper uses to a strain's id by the name and the other names its entry keeps (validate.strain_id on the service)."
- `core/openferment_core/validate.py:1165-1167`: "the organism, resolved to a strain id where the wording names one (an exact alias, or an alias standing in it as a whole word). The id is what every screen matches on".
- `docs/api/intake.md:94`: a strain's "`aliases`, the other names papers give it"; `docs/api/intake.md:106`: "The readers that had read an empty list read these: geneOS's hosts and the strain aliases".

## Command

```
bash bughunt/repro/H14-02/run.sh
```

It makes the fresh database `bh_r_h14_02_alias`, starts the keyless service on 127.0.0.1:10210, makes a project, pastes a one-sentence document naming "Saccharomyces cerevisiae Ethanol Red", keeps the strain `ethanol-red` with the aliases "Ethanol Red" and "Saccharomyces cerevisiae Ethanol Red", and anchors a candidate through `POST /api/tools/biorepo_write` (action `candidate`, anchoring in code, no model call) whose organism is that wording. It then reads the candidate from `GET /api/biorepo/overlay`, and in the service's Python reads `catalogues.as_strain_aliases()`, `validate.vocabulary()["strains"]` and `validate.strain_id(...)` in the project, with `validate.match_whole_word` over the catalogue's aliases as the control. It stops the service and drops the database on exit.

## Expected

The candidate is anchored with `strainId` = `ethanol-red` and `organism` = `ethanol-red` (the wording kept as `organismText`), so the strain page and the Hosts card count it.

## Observed (both runs)

- Overlay row: `{"organism": "Saccharomyces cerevisiae Ethanol Red", "organismText": null, "strainId": null}`.
- `catalogues.as_strain_aliases()` = `{'ethanol red': 'ethanol-red', 'saccharomyces cerevisiae ethanol red': 'ethanol-red'}`.
- `validate.vocabulary()['strains']` = `{}`; `validate.strain_id('Saccharomyces cerevisiae Ethanol Red')` = `None`.
- Control: `validate.match_whole_word(wording, catalogue aliases)` = `ethanol-red`, so the matching rule resolves the wording when it is handed the catalogue.
- `RESULT: DEFECT` in `run1.log` and `run2.log`.

## Likely cause

- `core/openferment_core/validate.py:874-891`: `vocabulary()` with no path sets `strains = {}` (line 889), and `strain_id` (line 932-934) reads only that map; nothing feeds it `catalogues.as_strain_aliases()` (`core/openferment_core/catalogues.py:600`), whose one reader is `module_stores._strain_aliases` (`core/openferment_core/module_stores.py:304-309`, the search row's names).
- The readers match on the anchoring-time id: `src/screens/StrainPage.tsx:568` (`rec.organism !== strainId`), `src/screens/Organisms.tsx:50` (`r.organism === strainId`), `core/openferment_core/evidence_pool.py:110` (`strainId` only when resolved), `core/openferment_core/fermos.py:1507-1514` (`of_strain` through `validate.strain_id`).
- The tests that claim the resolution hand in a strain table the service never builds: `core/tests/test_validate.py:160-169` and `core/tests/test_fermos_bind.py:142` monkeypatch `validate.vocabulary`.

Severity S2 (Contract break): the strain page, the Hosts counts and fermOS's strain binding are main-path features, and each finds no record for a strain whose papers name it by a kept alias.
