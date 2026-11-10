# H3-13: catalogue_write keeps a paper's measured values written in words

**Statement.** An assistant's `catalogue_write`, in the model's lane, keeps a strain named "Strain making 45 g/L" with the summary "reaches a titre of 45 g/L at 30 °C in 48 h" and the note "read from a paper: 0.45 g/g yield": a paper's numbers kept in the catalogue, outside any record, by a door whose own description says the catalogue takes names and words only.

## Contract

- `docs/TOOLS.md:142` and `core/openferment_core/tools/catalogues.py:109`, the tool's description the model reads: "Names and words only, never a measured value: a number a paper reports is a record."
- `core/openferment_core/tools/catalogues.py:10`: "A catalogue holds names and words, never a measured value".
- `core/openferment_core/catalogues.py:30-31`: "A catalogue holds names and words, never a measured value: a number a paper reports is a record (ADR-006)."
- `core/openferment_core/catalogues.py:41`: "`catalogue_write` takes no number and no lesson's body."
- `docs/api/intake.md:83-84`: "Names and words only: a number a paper reports is a record."

## Command

```
bash bughunt/repro/H3-13/run.sh
```

From the repository root. It makes the fresh test database `bh_r_h3_13_catalogue` (migrated to head), starts the service keyless on the first free port in 9700-9709 (no worker, no model call), makes the project `h3-13`, and sends two calls to `POST /api/tools/catalogue_write` with `X-OpenFerment-Assistant: hunt-agent/0.1`: a control whose `summary` is the JSON number 45, then the candidate's strain with its numbers written in `name`, `summary` and `note`. It reads the entry back at `GET /api/catalogues/strain/hunt-agent.0.1-s1`, prints the row in `openferment.catalogue` and its audit row, then stops the service, drops the database and removes its data copy.

## Expected

The write refused in words naming the field that states a number, as the same door refuses `summary` sent as a JSON number, with nothing kept. The service's own number finder, `validate.find_number`, finds a number in each of the three word fields sent ('4' in the name and the summary, '0' in the note).

## Observed (both runs)

- Control: `catalogue_write refused: a number was typed into summary. Tool inputs carry ids, words and quantities; ...`.
- The words write answers 200 with no error, and the catalogue holds `hunt-agent.0.1-s1` with `agent: model`, `via: http`, `by: hunt-agent/0.1`, the name "Strain making 45 g/L", the summary "reaches a titre of 45 g/L at 30 °C in 48 h" and the note "read from a paper: 0.45 g/g yield".
- `openferment.catalogue`: `strain/hunt-agent.0.1-s1 | hunt-agent/0.1 | model | http | Strain making 45 g/L | reaches a titre of 45 g/L at 30 °C in 48 h | read from a paper: 0.45 g/g yield`.
- The audit: `geneos | catalogue_write | open | strain/hunt-agent.0.1-s1 | hunt-agent/0.1 | model`.

`run1.log` and `run2.log` beside this file hold the two runs; both end `RESULT: DEFECT`.

## Likely cause

- `core/openferment_core/tools/writes.py:569-572`, `keep_catalogue`: the input's word fields go to `catalogues.keep_fields` as they came, and nothing reads them with `validate.find_number` (`core/openferment_core/validate.py:193`).
- `core/openferment_core/tools/__init__.py:400-422` and `:516`: `tools.numbers_in`, the one number check every tool input passes, reads JSON numbers alone, so a number written inside a string reaches the tool untouched.
- `core/openferment_core/catalogues.py:497-508`, `keep_fields`: it validates the entry's shape alone.
- The model's other word doors hold their text to `find_number`: a proposal's words (`core/openferment_core/proposals.py:147-157`), a runbook draft's (`core/openferment_core/runbook_draft.py:39-42`) and a plan's claims (`core/openferment_core/postdoc_agent.py:306-308`).

Fix size: small (in `keep_catalogue`, for the model's lane, refuse in words a `name`, `summary`, `note`, alias or mastery item in which `find_number` finds a number, naming the field and what it found).
