# H6-04: db:import-alpha1 prints and audits a count of rows its upsert did not keep

**Statement.** For an alpha 1.0 `guild.json` naming one person twice under one id, `pnpm db:import-alpha1`
prints and audits 3 people carried while the new project keeps 2, the second entry replacing the first; an
artifact held by two files (`<id>.json` and a file manager's `<id> copy.json`) is likewise counted 2 and kept
once, and the import answers exit 0 with no `refused:` line.

**Contract.** `docs/runbooks/live-host-install.md:217-218`: "The import prints the new project's id and what
it carried, one count a kind; the decisions count is the number of decisions in the file." The import's own
docstring, `core/openferment_core/import_alpha1.py:13-15`: "Every file is read and checked before anything is
written, and everything is written in one transaction: an import lands whole or not at all."

**Command** (from the repository root): `bash bughunt/repro/H6-04/run.sh`

It makes a worktree of 2047f5a under `$BH_WORK/H6-04/`, links the repository's venv into it (the worktree
holds no `core/.env`), writes two alpha 1.0 data directories with alpha 1.0's own models (`gen.py`), makes
the fresh database `bh_r_h6_04_imp` migrated to head, and runs the import's command
(`python -m openferment_core.import_alpha1 --name … --by … --data …`, package.json's `db:import-alpha1`
without `uv run`) on each directory. For each project it reads the printed counts, the `import_alpha1` audit
row's `detail.counts` and the rows `guild_people` and `artifacts` keep. No service, no port, no model call.
It drops the database and removes the worktree on exit.

- `one` (control): `guild.json` with p-ada and p-ben; `artifacts/00000000000000aa.json`.
- `dup`: `guild.json` with p-ada, p-ben "Ben Ortiz" and p-ben "Ben Ortiz (again)"; `artifacts/00000000000000aa.json`
  and `artifacts/00000000000000aa copy.json`, the same bytes.

**Expected.** For each kind the printed count, the audit row's count and the rows kept are one number
(2 people, 1 artifact for `dup`), or the duplicate id is refused in words with a `refused:` line and nothing
written.

**Observed** (both runs). Control: printed 2 people, audited 2, kept 2; printed 1 artifact, audited 1, kept 1.
Duplicates: exit 0, no `refused:` line; printed 3 people, audited 3, kept 2 (`p-ada Ada Moreno`,
`p-ben Ben Ortiz (again)`: the first p-ben entry is gone with no word); printed 2 artifacts, audited 2, kept 1.

**Likely cause.** `core/openferment_core/import_alpha1.py:79-93` (`Found.counts`) counts the entries each file
holds (`len(self.guild.people)` at line 82, `len(self.artifacts)` at line 89), and `_write` writes each entry
with `rows.put` (`import_alpha1.py:183-185` for people, `:206-208` for artifacts), which
`core/openferment_core/db/rows.py:59-66` makes an upsert on `(project_id, id)`; `read`
(`import_alpha1.py:124-153`) checks each file's shape and never two entries of one id. The same counts are
printed by `main` (`import_alpha1.py:245-247`) and written into the audit row (`import_alpha1.py:216-221`).
Confidence high.

**Scope.** Alpha 1.0's guild store refused or replaced a person of a known id
(`git show alpha-1.0:core/openferment_core/guild.py`, lines 269-305), so a duplicate person comes only from a
hand-edited file; a copied artifact file is the likelier path, and its bytes match, so nothing differs but the
count. Decisions are keyed by record id in `biorepo.json`, so the decisions count the runbook names cannot
disagree this way.
