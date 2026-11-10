# H13-02: `pnpm lit:report` erases the hand-written sections of the committed retrieval report

**Statement.** `docs/reports/literature-retrieval.md` says its generator writes it and asks to be regenerated alone,
yet holds 37 lines its generator never writes (a hand's comment and the sections "What this run measured" and
"What waits on the account"); the file's own regeneration command, `pnpm lit:report`, run offline and keyless,
rewrites the file and drops all 37, and a project render (`pnpm lit:report --project ethanol ... --render`)
drops them too, since `report.render()` writes neither section.

**Contract.**

- `docs/reports/literature-retrieval.md:1`: "Written by `pnpm lit:report` (core/openferment_core/literature/report.py); regenerate, do not edit."
- `docs/reports/literature-retrieval.md:91`: "the next `pnpm lit:report --project ethanol ... --render` writes this project's part whole from its own run, these two sections with it."
- `CLAUDE.md:106`: "`pnpm lit:report` measures retrieval against the kit's seed questions"

**Command** (from the repository root): `bash bughunt/repro/H13-02/run.sh`

It makes a scratch worktree at 2047f5a and imports that worktree's `openferment_core` (`drive.py check` refuses
to go on otherwise), so every write lands in the worktree; it hashes the main checkout's report pair before and
after. Then:

1. The contract lines, and the sections `report.render()` writes, read from the tree.
2. No database: `report.write()` of the committed JSON's own `ethanol` part over a copy of the committed pair
   (the step `lit:report --project <id> --render` ends with), diffed against the committed file.
3. `pnpm lit:report` whole (`literature_live.main(["report"])`: the kit's demo, offline, no model), its scratch
   database a fresh `bh_r_h13_02_demo` made with `bh_db_fresh` (`drive.py` points `migrate.create` at it in memory;
   every other line runs as committed), with `HF_HUB_OFFLINE=1` over the cached embedder.

It drops the database and removes the worktree on exit.

**Expected.** By line 1, the committed file is its generator's output: regenerating it moves only what the generator
owns (the date, the commit, the ingest time) and every section stays. By line 91, a project render writes the two
sections.

**Observed.** The committed file has 126 lines. A project render of its own committed part gives 89: lines 90 to 126
go (37 lines), nothing is added, and the JSON stays byte for byte. `report.py` names neither section. `pnpm lit:report`
exits 0 in about 15 s and leaves 89 lines. The demo's numbers come back unchanged: the date line moves in the
Markdown, and `generated_at`, `git_commit` and `latest_ingested_at` move in the JSON. The hand's comment and both
sections are deleted, the graph dry run's measured figures among them (814 passages, 92 batches, 1,758,899
characters, 0.2199 and 2.3239 USD), along with the account's waiting lanes and their commands. The main checkout's
pair keeps the same hash.

**Likely cause.** `core/openferment_core/literature/report.py:195-200` (`_save`) writes the whole Markdown from the
demo's text, `PROJECTS_MARK` and `render()` of each part the JSON keeps; `report.py:732-822` (`render`) writes "The
corpus", "The ground truth", "Retrieval", "The judge's relevance", "Answers", "Routes" and "Cost" alone. Text added by
hand after a part therefore has no source to come back from, on the demo path (`report.py:149-170`, `main`) and on the
project path (`report.py:205-212`, `write`) alike. The 37 lines were added by hand at alpha 2.2 F.5 (the comment at
line 91 says so). The dry run's figures are also kept in `docs/PROGRESS.md:609` and `:3372`.
