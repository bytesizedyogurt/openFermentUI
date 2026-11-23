# R1-05: the handoff report gives `docs/TOOLS.md` at CORE one line too many

**Statement.** The handoff report counts the `docs/TOOLS.md` the agent builder read at `CORE=6f85338` as
838 lines; that file holds 837 lines (84,382 bytes, its last byte a newline), and it held 837 at 37e6bd0,
the commit that wrote the count.

R2-04 (`bughunt/notes/R2/candidates.json`) reports the same line and the same count; this reproduction
shows it once.

Kind: Wrong number (in a report). Severity: S4 (a count in a measured report, one line off; no screen,
record or provenance label reads it).

## Contract

- `docs/reports/handoff-2026-11.md:82` (at 2047f5a): "**What it read.** `.mcp.json`, `docs/TOOLS.md` whole
  (838 lines) and `docs/api/openapi.json`".
- `docs/reports/handoff-2026-11.md:11`: "`CORE=6f85338` (the D.0 commit, green on CI run 41865693107)", and
  lines 85 and 86: "all in the worktree at `CORE`".
- The report's other measure of the same file holds: line 127, "an 84 KB `docs/TOOLS.md`", matches its
  84,382 bytes.
- The repository's own way of counting a document's lines is `splitlines()`
  (`core/tests/test_guidance.py:25`, the count behind CLAUDE.md's "under 250 lines").

## Command

```
bash bughunt/repro/R1-05/run.sh
```

A static defect: every read is a git object (`git show`), so the script needs no database, service,
worktree or model call, and it writes nothing in the checkout. It prints the report's lines 11, 82 and
127 at 2047f5a, finds the commit that wrote line 82 (`git log -L`), counts `docs/TOOLS.md` at 6f85338 and
at that commit four ways (`wc -l`, `awk` NR, Python `splitlines()`, bytes and the last byte), then counts
Python `split('\n')` pieces and finds the first commit after CORE whose `TOOLS.md` held 838 lines.

## Expected

`docs/TOOLS.md` at `CORE=6f85338` holds the 838 lines the report gives it.

## Observed

Both runs (`run1.log`, `run2.log`), identical:

- at 6f85338: `wc -l` 837, `awk` NR 837, `splitlines()` 837; 84,382 bytes; the last byte `\n`;
- at 37e6bd0, the commit that wrote line 82: the same file, 837 lines;
- Python `split('\n')` over the file at 6f85338 gives 838 pieces, the last one empty;
- the first `TOOLS.md` of 838 lines comes at 50a4f96 (E.8), after 37e6bd0, so no copy the report could
  have read at its writing held 838 lines.

`RESULT: DEFECT` both times.

## Likely cause

`docs/reports/handoff-2026-11.md:82`, written at 37e6bd0 (D.2 to D.4). The count matches the number of
pieces `split('\n')` gives a file that ends in a newline (or a viewer that numbers the empty position after
the last newline), one more than the file's lines. The fix is the one number: 837.
