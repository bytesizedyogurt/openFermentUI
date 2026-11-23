# H11-09: an exported CDPATH stops install.sh, deploy.sh and nightly.sh at their first cd

**Statement.** `scripts/host/lib.sh:6` computes `REPO` with `cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd`
inside a command substitution. Run as the runbook writes it (`scripts/host/install.sh` from the checkout) with
CDPATH exported as `.:$HOME`, bash's cd resolves the relative path through the CDPATH entry `.`, prints the
new directory, `pwd` prints it again, `REPO` holds the checkout twice on two lines, and each of install.sh,
deploy.sh and nightly.sh stops at its own first `cd "$REPO..."`.

**Contract.**
- `docs/runbooks/live-host-install.md:113` `cd ~/openferment`, then `:133` "scripts/host/install.sh" (step 3,
  run from the checkout).
- `docs/runbooks/live-host-install.md:253` "Bring the Mini to `main` and restart | `scripts/host/deploy.sh`".
- `docs/runbooks/live-host-install.md:257` "`scripts/host/nightly.sh` runs its work by hand".
- `scripts/host/install.sh:3` "Run as yourself, from the checkout, after `git clone`" and
  `scripts/host/deploy.sh:3` "Run as yourself, from anywhere".

The runbook and the scripts' own headers name no shell setting the scripts need, so each command written there
should run the same under any CDPATH a person's shell exports.

**Command** (from the repository root): `bash bughunt/repro/H11-09/run.sh`

It needs no database and no service. It adds a detached worktree of 2047f5a under
`$BH_WORK/H11-09/wt`, puts the H11 hunt's stand-ins for macOS and Homebrew on PATH
(`bughunt/notes/H11/scripts/standins.sh`, plus a `git` stand-in that answers `pull`), and runs two passes,
each with a fresh HOME and fresh stand-ins: CDPATH unset, then CDPATH exported as `.:$HOME`. Each pass prints
lib.sh's `REPO` (sourced as the scripts source it) and runs `scripts/host/install.sh`, `scripts/host/deploy.sh`
and `scripts/host/nightly.sh` from the checkout. The worktree is removed at the end.

**Expected.** Both passes alike: `REPO` is the checkout's one absolute path, and all three scripts get past
their first cd (on the stand-ins, each exits 0).

**Observed** (run1.log and run2.log, the same in both):

```
== CDPATH unset
   lib.sh's REPO: <checkout>
   scripts/host/install.sh: exit 0; no cd failure
   scripts/host/deploy.sh: exit 0; no cd failure
   scripts/host/nightly.sh: exit 0; no cd failure
== CDPATH='.:$HOME' exported
   lib.sh's REPO: $'<checkout>\n<checkout>'
   scripts/host/install.sh: exit 1; scripts/host/install.sh: line 23: cd: $'<checkout>\n<checkout>': No such file or directory
   scripts/host/deploy.sh: exit 1; scripts/host/deploy.sh: line 17: cd: $'<checkout>\n<checkout>': No such file or directory
   scripts/host/nightly.sh: exit 1; scripts/host/nightly.sh: line 18: cd: $'<checkout>\n<checkout>/core': No such file or directory
RESULT: DEFECT
```

A probe of the same line under other values: CDPATH empty, `/nonexistent` or `:/nonexistent` (an empty
entry) leave `REPO` whole; any explicit `.` entry (`.:/x`, `/x:.`) doubles it; and the form
`./scripts/host/install.sh` escapes it, since bash skips CDPATH for a path that starts with `./`. The launchd
jobs run nightly.sh by its absolute path, so the 03:00 job is untouched; the break is in the commands a person
types.

**Likely cause.** `scripts/host/lib.sh:6`: a `cd` on a relative path, its stdout captured by `$(...)`. Bash's
cd writes the new directory to stdout whenever a non-empty CDPATH entry found it (POSIX asks for this). The
usual guard is `CDPATH= cd -- "..." >/dev/null && pwd`. Confidence high.

**Workaround.** `unset CDPATH` before the command, or type it as `./scripts/host/install.sh`.

**Severity.** S3: an edge case (a shell that exports CDPATH with a `.` entry) with a workaround. The hunt
filed it as S4; the scale keeps S4 for wording, cosmetic marks and drift, and here the install, the deploy and
the hand-run nightly stop.
