# H5-07: Guild's and Practice's unknown-skill refusal names alpha 2.0

**Statement.** A skill the project's skill catalogue lacks is refused by Guild and Practice as
"'X' is not a skill Guild holds (none ship with alpha 2.0)", while on this tree Guild's skills are the
project's skill catalogue, kept on `/catalogues`, and the protocol keep refuses the same fact in words
naming that catalogue and `/catalogues`.

**Contract.**
- `CLAUDE.md:15`: "A project's catalogues (strains with their aliases, products, Guild's skills, Primer's
  lessons) have a screen at `/catalogues`, Primer's lessons come from the lesson catalogue, and Guild's
  protocol steps name skills from the skill catalogue (alpha 2.2 prompt §1 item 4, §6.5)."
- `CLAUDE.md:87`: "a refusal is a 422 in words."
- The tree's own words for the same refusal, `core/openferment_core/protocols.py:97-100`: "step {id} of
  version {v} needs {skill}, which the project's skill catalogue does not hold; a step names the skills it
  needs from that catalogue, so keep the skill there first (/catalogues)".

**Command.** `bash bughunt/repro/H5-07/run.sh` from the repository root. It makes a fresh test database
`bh_r_h5_07_skillwords`, starts a keyless service on the first free port of 127.0.0.1:9800-9809, makes
project `bh-a` keeping one skill `SK-A`, and asks (`probe.py`):
- control: `POST /api/guild/check` naming `SK-A` passes the skill rule (Guild's skills are the catalogue's);
- sibling: `POST /api/protocols` with a step naming `SK-NONE` (the alpha 2.2 words);
- probes: `POST /api/guild/evidence`, `POST /api/guild/check`, `POST /api/practice/draft` naming `SK-NONE`.

Then it greps the tree for the phrase, stops the service and drops the database. No model is called:
`practice.draft` refuses at `_skill` before any call, and the service is keyless.

**Expected.** Words saying the project's skill catalogue holds no such skill, and where a skill is kept
(`/catalogues`), as the protocol keep says it.

**Observed (both runs).**
- `POST /api/guild/evidence`: 422 `{"detail": "skill: 'SK-NONE' is not a skill Guild holds (none ship with alpha 2.0)"}`
- `POST /api/guild/check`: 200 `{"ok": false, "rule": "skill", "why": "'SK-NONE' is not a skill Guild holds (none ship with alpha 2.0)"}`
- `POST /api/practice/draft`: 422 `{"detail": "skill: 'SK-NONE' is not a skill Guild holds (none ship with alpha 2.0)"}`
- control: `SK-A`, kept in the catalogue, passes the skill rule (the check stops later, at `source`);
  sibling: the protocol refusal names "the project's skill catalogue" and "(/catalogues)".
- The phrase stands on five lines: two refusals, one model docstring, and the two files generated from it
  (`docs/api/openapi.json:2053`, `src/api/types.gen.ts:3528`).

`RESULT: DEFECT` in run1.log and run2.log.

**Likely cause.** The alpha 2.0 words were left when alpha 2.2 moved Guild's skills to the project's skill
catalogue (`guild.projection`, `core/openferment_core/guild.py:142-160`):
- `core/openferment_core/guild.py:395` (`_precheck`, the refusal for evidence and the check);
- `core/openferment_core/practice.py:487` (`_skill`, the refusal for a Practice draft);
- `core/openferment_core/models.py:1426` (the `CheckCriterion` docstring), carried by `pnpm gen:api` into
  `docs/api/openapi.json:2053` and `src/api/types.gen.ts:3528`.

A small fix: the two refusals take the protocol keep's words (the project's skill catalogue holds no such
skill; keep it at `/catalogues`), the docstring drops the version, and `pnpm gen:api` regenerates.

**Severity.** S4 (Drift): the refusal itself is right and lands where it should; its words name a past
version and leave out where a skill is kept.
