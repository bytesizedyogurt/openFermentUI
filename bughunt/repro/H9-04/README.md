# H9-04: Postdoc keeps claims whose words state a quantity

**Statement.** Postdoc's loop keeps a claim that reads "Ethanol titre roughly doubled under anaerobic conditions", the plan prompt's own example of a claim discarded whole, and it keeps claims saying "halved", "quadrupled", "Table IV", "x10", "pH7" and "pH-4" in the same way, along with a gap saying "doubled at pH7"; each one cites a passage that states none of it, and no typed value comes with it.

## Contract

- `CLAUDE.md:55` (R): "A number in a Postdoc claim or a tool input stands only in a typed quantity with its origin; a claim with a number in its words is dropped and counted (ADR-006)."
- `core/openferment_core/postdoc/plan.py:51-59`: "NEVER WRITE A NUMBER IN CLAIM TEXT. Not in digits, not in words, not as "twofold" or "an order of magnitude". … A claim containing a number is discarded whole — it is not corrected and it is not shown." Its third example: `bad: "Ethanol titre roughly doubled under anaerobic conditions"`.
- `core/openferment_core/postdoc/plan.py:64-65`: "Ordinals, fractions and labels are numbers too: … not "Table 1" or "Figure 2"".
- `core/openferment_core/postdoc_agent.py:144-146` (AGENT_SYSTEM rule 9): "A temperature, a time window, a year, a percentage, a pH, a rate of return, a table or figure number or a concentration in claim text or in a gap discards it".

## Command

```
bash bughunt/repro/H9-04/run.sh        # from the repository root
```

The script makes a fresh database `bh_r_h9_04_loop` and the project `h9-04`, then pastes one sentence into the project through `intake.paste`, embedding it with the tests' offline hash embedder. Next it runs `postdoc_agent.ask` with a scripted stand-in for the model, the `converse` hook `core/tests/test_postdoc_agent.py` uses. The stand-in calls `search_passages` once over the project's document and answers a plan in which every claim quotes the returned sentence word for word. No model is asked, the model API's address is a closed loopback port, and nothing is spent. The script then greps the contract and the validator's lists. At the end it drops the database and removes its work directory.

## Expected

Each of the seven claims whose words state a quantity (doubled, halved, quadrupled, Table IV, x10, pH7, pH-4) is dropped and counted, `rejected` 7, each reason naming the word. The three controls get that treatment today: "twofold", "tenfold" and "pH 7" are dropped with reasons `('twofold')`, `('tenfold')`, `('7')`. The gap "Whether the titre doubled at pH7 is measured nowhere in the project" is dropped, as the gap saying "twofold" is.

## Observed (both runs)

```
{"claim": "d1", "text": "Ethanol titre roughly doubled under anaerobic conditions", "kept": true, "reason": null}
... d2 to d7 kept, k1 to k3 dropped ...
{"gap": "Whether the titre doubled at pH7 is measured nowhere in the project", "kept": true}
SUMMARY {"defectKept": 7, "defectTotal": 7, "byDesignKept": 2, "controlDropped": 3, "controlTotal": 3, "gapDoubledKept": true, "gapTwofoldDropped": true, "passageCited": true}
RESULT: DEFECT
```

The kept "doubled" claim comes back with `support: "direct"`, `provenance: "unverified"`, the document's paper id, the quote "Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions." and `values: []`. The answer the service would keep and show therefore carries a doubling that its cited sentence never states.

The practice drafts' check (`practice.check_text`) refuses six of the same seven words ("Table IV" excepted), so Postdoc's claims and practice drafts treat the same words differently.

For reference, "phase 3" and "phase III" are both kept. That agrees with the validator's step-label rule (`validate.py:139`, `STEP_WORDS` holds "phase"), so this repro leaves the candidate's "phase III" item out of the defect.

## Likely cause

- `core/openferment_core/validate.py:66-77`: `_WORD_NUMBERS` holds counts, ordinals and "once twice thrice". It holds no multiplying verb (doubled, halved, tripled, quadrupled) and no Roman numeral, so "doubled", "halved", "quadrupled" and "Table IV" pass. ("tripled once" in the hunt's script is caught on "once" alone.)
- `core/openferment_core/validate.py:105`: `_IDENTIFIER` blanks any letters-then-digit span before the digit search, so "pH7", "pH-4" and "x10" are read as identifiers (the same carve-out that keeps "cenpk113-7d").
- `core/openferment_core/validate.py:416` (`validate_plan`) and `core/openferment_core/postdoc_agent.py:646-650` (`held_to_rule_one`, for gaps) rely on `find_number` alone. `core/openferment_core/practice.py:73-80` adds `PRACTICE_QUANTITY` (pH with a digit, x or × with a digit, double/triple/quadruple/halve) for practice drafts only. Its comment says this is "what validate.find_number lets through" and that it was kept apart "so Postdoc's claims keep the validator they were tuned against". `core/tests/test_practice.py:164-170` names the same words as ones "the shared validator lets through". No decision record or `docs/PROGRESS.md` row relaxes the R line for Postdoc's claims, and the plan prompt still tells the model that the "doubled" claim is discarded.
