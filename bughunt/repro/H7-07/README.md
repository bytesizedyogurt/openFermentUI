# H7-07: Deposition at 810 px, Next step 43 px wide and the staged run's runbook link 18 px tall

**Statement.** At 810x1080 with touch, the protocol run's Next step button measures 43 x 56 px on every step, and the
staged run's link to its runbook measures 18 px tall (174.1 x 18 px here) and shows its underline only on hover.

**Contract.**

- `CLAUDE.md:59`: "`src/screens/Deposition.tsx` is a glove-tolerant full-screen takeover (810 px portrait, 44 px
  targets, 7:1 step-text contrast, no hover affordance); extend it and keep its header comment."
- `src/screens/Deposition.tsx:9`: "touch targets ≥ 44px, because the hand operating this is gloved;"
- `src/screens/Deposition.tsx:11-12`: "no hover-dependent affordance anywhere — a tablet has no hover state to give, so
  anything that only appears on hover does not exist here;"

**Command.** `bash bughunt/repro/H7-07/run.sh` from the repository root. It makes a fresh database
`bh_r_h7_07_bench` (bh_db_fresh through bh_svc_start) and starts a keyless service on 127.0.0.1:10327 over the built app
in `dist/`. It puts one placeholder locked runbook and one placeholder three-step protocol through the API and opens
the protocol's run against the runbook from the runbook's page in Chromium at 810x1080 with touch (`measure.mjs`).
On the staged view it measures the runbook link and reads its underline at rest and under a hover. After Begin
recording it measures Next step on steps 1, 2 (timed) and 3. It stops the service and drops the database on the way out.

**Expected.** Every target in the takeover at least 44 x 44 px, the Next step button and the runbook link among them,
and no affordance that appears on hover alone.

**Observed** (both runs).

- Next step measures 43 x 56 px on steps 1, 2 and 3, `min-width: auto`. Beside it in the footer, Back is 96 x 56,
  Mark step complete 527.9 x 56 and Skip 75.1 x 56.
- The staged view's runbook link ("H7-07 placeholder runbook", class `text-accent hover:underline`, display inline)
  measures 174.1 x 18 px. Its `text-decoration-line` is `none` at rest and `underline` under a hover, from the one
  matching rule `.hover\:underline:hover { text-decoration-line: underline; }`. Begin recording beside it measures
  171.1 x 56 px.

**Likely cause.**

- `src/screens/Deposition.tsx:954-960`: the Next step `Button` sets `style={{ minHeight: 56 }}` and no width around a
  17 px icon (`<ArrowRight size={17} />`). `src/styles.css:366-376` gives `.btn` `padding: 6px 12px` and a 1px
  border, so the width is 17 + 24 + 2 = 43 px.
- `src/screens/Deposition.tsx:351`: `<a className="text-accent hover:underline" href={href(`/runbooks/${runbook.id}`)}>`.
  It is an inline anchor in body text with no `min-h-[44px]` or padding, so its box is one line of text tall, and its
  underline comes from a hover utility.

**Scope checked.** The hunt's note on texts under 7:1 beside the step (primary button labels, the capture preview, the
read-back note, the close modal's warning) falls outside this contract. The contract asks 7:1 of step text, and the hunt
measured step text at 14.9:1. The `.btn:hover` background tint on every button changes a control that is visible at
rest, so it adds nothing that exists on hover alone. The link's underline does exist on hover alone.
