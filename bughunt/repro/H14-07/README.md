# H14-07: the bench files "7,4 g/L" as 74 g/L

**Statement.** The bench's capture box strips every comma before it reads a number, so a reading said with a decimal
comma ("titre came in at 7,4 g/L") is previewed and filed as a measurement of 74 g/L, and "0,74 g/L" as 74 g/L too,
where the matcher's own rule keeps a doubtful line as words.

**Contract.** `src/engine/capture.ts:9-13`:

> So matching is deliberately conservative: when in doubt this returns null and the text is kept verbatim as an
> Observation. A false negative costs a person one reclassification later; a false positive silently writes a number
> into a slot it does not belong in and the reconciliation is quietly wrong.

The read-back panel names the same hazard, `src/components/DepositionPanel.tsx:131-132`: "“Four two” is 4.2 or 42,
and getting it wrong is silent."

**Command** (from the repository root):

    bash bughunt/repro/H14-07/run.sh

No database, service or worktree: the matcher is a pure function of the browser bundle. `capture.ts` beside this file
runs `matchToSchema` and `readBackText` from the tree's own `src/engine/capture.ts` under tsx, over a g/L measure
shaped as a runbook made from a run carries it (`core/openferment_core/studies/runbooks.py:136`). grep shows the path
from the matcher to the filed entry and the read-back, and that `dist/` carries the same comma strip.

**Expected.** "titre came in at 7,4 g/L" is kept as an observation (a comma with one digit after it is doubtful), or
filed as 7.4 g/L. No reading of "7,4" gives 74: a decimal comma reads 7.4, and a thousands group holds three digits.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`):

- "titre came in at 7.4 g/L" files as 7.4 g/L (the control).
- "titre came in at 7,4 g/L" files as 74 g/L; read-back text "74 g/L".
- "titre came in at 0,74 g/L" files as 74 g/L.
- "titre came in at 1,250 g/L" files as 1250 g/L.

The panel previews "files as Ethanol titre = 74 g/L" (`DepositionPanel.tsx:47`, `:110-111`), Enter files that preview
(`:65`), the store keeps `value: match.value` with `confirmed: false` (`src/store.ts:2136-2140`), and the read-back
beat shows "74 g/L" above "you said: “titre came in at 7,4 g/L”" (`DepositionPanel.tsx:141`, `:146`). Once a person
presses "That is right", the entry is a confirmed number, which is what a scenario's `measurement` origin may name
(`core/openferment_core/measurements.py:165-171`).

**Likely cause.** `src/engine/capture.ts:25-31`: `normalise` runs `.replace(/[,]/g, '')` (line 28) over the whole line
before the number regex `/(-?\d+(?:\.\d+)?)/g` at line 100, so "7,4" reaches the regex as "74" and "0,74" as "074".
The fix is small: read a comma between digits as a thousands separator only when exactly three digits follow it, and
return null (the line kept as an observation) for any other comma between digits.

**Severity.** S3: an edge case with a workaround. The preview and the read-back beat both show 74 beside the words
said, and "No — fix it" or a decimal point avoids it; a person who confirms without reading files a number ten times
too large as a measurement.
