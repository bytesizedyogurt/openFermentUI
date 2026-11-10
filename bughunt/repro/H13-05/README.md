# H13-05: the mirror README's check line fails from the directory its test line names

**Statement.** Followed line by line, `examples/engines/openferment-engine-mirror/README.md` puts the
reader in `core/` (line 8) and then in the package's own directory (line 9), and its line 10 begins
`cd core &&`, a step that succeeds from the repository root alone, a directory the page never names.

**Contract.** `examples/engines/openferment-engine-mirror/README.md`:

- line 8: "Install ... from the repository's `core/` in bash or zsh, then restart the service: `uv pip install ...`"
- line 9: "Test from this directory, with no database: `../../../core/.venv/bin/python -m pytest`"
- line 10: "Check it against the contract on a PostgreSQL server: `cd core && uv run python -m openferment_core.engine.conform mirror`"

Each line names the directory it runs from (line 8 `core/`, line 9 "this directory"), so a reader who
follows them stands in the package's directory when line 10 comes.

**Command.** From the repository root: `bash bughunt/repro/H13-05/run.sh`

It makes a clean worktree of `2047f5a` (no `core/.env`), links core's environment into it read-only,
puts a stand-in `uv` on PATH that prints where it was reached from and with what, and stands in line
8's install with the entry-point record an install writes, on PYTHONPATH. So nothing installs into or
syncs `core/.venv`. It reads the commands of lines 9 and 10 out of the page itself and runs them:
line 9 from the package's directory, then line 10 verbatim from line 9's directory, from line 8's
`core/` and from the root. Beside that it runs line 10's check from the root with no database named,
then with `OPENFERMENT_DATABASE_URL` naming a fresh migrated test database (`bh_r_h13_05_cfg`, the
checks' own scratch database renamed `bh_r_h13_05_conform_...` in memory), and greps both example
pages for what they name. It drops every database and removes the worktree when it ends.

**Expected.** Line 10, run from the directory line 9 leaves the reader in, reaches `uv run` and checks
the mirror.

**Observed** (run1.log, run2.log, the same both times):

- line 9 from the package's directory: `30 passed`
- line 10 from line 9's directory: `bash: line 1: cd: core: No such file or directory`, exit 1
- line 10 from line 8's directory `core/`: `bash: line 1: cd: core: No such file or directory`, exit 1
- line 10 from the repository root: `uv` is reached, from `<checkout>/core`
- line 10's check from the root with no database named: `✗ the checks run on a database of their own, made on the PostgreSQL server the setting names: OPENFERMENT_DATABASE_URL is not set. Put it in core/.env: ...`, exit 2
- with `OPENFERMENT_DATABASE_URL` naming a migrated test database: `mirror (engine run 1 · mirror · openferment-engine-mirror 0.1.0): every check holds`, exit 0
- the mirror page names the database setting on 0 lines and a command that starts the service on 0;
  its line 3 names `docs/api/engines.md`, which holds both (`docs/api/engines.md:112-119`, `:128-129`,
  `:802-808`)
- the record-reader page names `--project proof` and a running service on its line 2, and names on no
  line how that project or service comes to be; `pnpm prove --keep` is named in `docs/BASE.md:99` and
  `docs/TOOLS.md:900`

`RESULT: DEFECT` on both runs.

**Likely cause.** `examples/engines/openferment-engine-mirror/README.md:10` carries the form
`docs/api/engines.md:802` gives for the repository root ("Run it as `cd core && uv run python -m
openferment_core.engine.conform <name>`") after line 9 has moved the reader into the package's
directory. A fix names the root on line 10 (for example "From the repository root:") or writes it for
the package's directory (`cd ../../../core && uv run python -m openferment_core.engine.conform mirror`),
and points at `docs/api/engines.md` for the database and the service.

**Severity.** S4: wording; the refusal and the shell's own words lead a reader to the root and the
setting after one failed command.
