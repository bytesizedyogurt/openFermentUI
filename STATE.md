# STATE

One line per session, newest last — what landed, and the measured number that
says it landed. The full §0.5 report for each session is in that session's
transcript; this file is the index a later session reads first.

- **2026-09-15 · OF-BLD-012.1 §6.1 (F1.1–F1.3)** — `export-corpus.ts` emits
  `range` and `negativeResult` as data instead of folding them into the
  `conditions` prose; §2.4 rule 3 reads the quote as quantities (units the
  paper wrote, the range it states, numbers written in words) instead of bare
  numbers, and records how it found the value as `valueBasis`; `biorepo.write`
  passes the record's recorded structure into anchoring. **30 of the 34**
  refused gold records now anchor, not the 32 the spec predicted: `r-A2-1` and
  `r-O8-1` refuse on rule 5, the field's own range, which no rule-3 fix
  reaches. `pnpm verify` green, all sixteen stages.
- **2026-09-15 · OF-BLD-012.1 §6.2 (F1.4–F1.5)** — `emit_candidates` gains
  `range` and `negativeResult` and the prompt says what each is for, so the
  extractor can say what the curators recorded; `match_run` scores a range
  candidate against a range record on its endpoints. `biorepo.write` grows a
  `dry_run`, `POST /api/biorepo/check` asks it, and Guild gates Accept and
  Gold on that answer with `writeRefusal` demoted to the offline fallback —
  the rules are not mirrored. New verify stage `check:anchors` holds the
  anchoring floor at **93 of 104**; seventeen stages now. Both new guards
  negative-tested. `pnpm verify` green.
- **2026-09-16 · OF-BLD-012.1 §6.3 (F2)** — decisions are signed by a person.
  Settings gains a Reviewer name field, kept in the Durable tier under
  `reviewerName`; `reviewerName()` in the store is the one place it is read and
  replaces all **12** hard-coded `'you'` sites (the spec said 10); an audit line
  made before a name is set says `this browser`, which can never be posted.
  `writeRefusal` gains a blocking `reviewer` rule while the service is up, and
  `biorepo.write` refuses a name under two characters or in the closed
  placeholder list (`you`, `me`, `reviewer`, `user`, `test`). The smoke now
  reviews as a named person and checks the posted decision carries that name;
  the durable check reloads the page and finds the name still there. Both new
  assertions negative-tested. `pnpm verify` green.
- **2026-09-16 · OF-BLD-012.1 §6.4 (F3)** — the overlay is authoritative.
  `Overlay.candidates` and `runs` are a list or `null` in both languages; a
  list replaces whatever its length, and only `null` keeps what was there. An
  undecided `haiku-1` record absent from an incoming list is removed from the
  store and the review queue; a decided one stays and carries `absentFromRun`,
  which the review card explains. New verify stage `check:overlay` drives the
  real store through five scenarios; eighteen stages now. Negative-tested.
  Correction to the spec: the eight store scenarios it says live in `scripts/`
  were scratchpad probes — this stage is the first one in the tree.
  `pnpm verify` green.
- **2026-09-16 · OF-BLD-012.1 §6.5 (F6–F7)** — `match_run` pairs by distance:
  every agreeing (record, candidate) pair is scored, sorted, and consumed
  greedily, ties breaking on record then candidate order, so the result no
  longer depends on arrival order and a record cannot take the candidate its
  sibling was closer to. The dropped-span pass is paired the same way and the
  docstring states the algorithm. `ExtractionRecord.original` is stamped once
  as a record enters the store and never touched by a decision;
  `reanchoredSpan` and the withdrawal of a correction read it instead of
  diffing against `RECORDS`, which a corpus update would move underneath a
  decided record. The overlay guard grew the F7 scenarios and is renamed
  `pnpm check:store`. Both fixes negative-tested. `pnpm verify` green.
- **2026-09-17 · OF-BLD-012.1 §6.6 (F8)** — a truncated paper is split, never
  discarded. `MAX_TOKENS` is 16 000 and no longer derived from Postdoc's; a
  response that hits the limit halves the paper by character count and asks
  again, twice deep, and only the remainder that still will not fit is
  reported. `ExtractResponse` gains `calls` and `truncatedSections` (the spec
  said `ExtractRun`; that model is Witness's per-run aggregate, and these are
  per-extraction facts that belong beside `usage`). Every call is paid for in
  `usage`. A paper that truncates all the way down is still refused and still
  cached as nothing. Negative-tested. `pnpm verify` green.
- **2026-09-17 · OF-BLD-012.1 §6.7 (F4–F5)** — the merge is tested and the
  guard brings its own export. `export-corpus.ts` takes
  `OPENFERMENT_CORPUS_OUT`; `check:biorepo` takes `OPENFERMENT_DATA_DIR` and
  exports into a temp directory itself, so it passes on a fresh clone with no
  `corpus.json`. New stage `pnpm test:export` exports the demo's decisions and
  checks the corrected value, the SI twin, the re-anchored quote, the appended
  record, gold provenance and the excluded rejection. The demo fixture now
  carries one of each kind of decision. **Tension resolved:** F4 asks the
  guard to fail on a bent value, but after F5 the guard builds the corpus it
  checks, so bending the decision bends both sides — rule 4 is testable
  through `OPENFERMENT_CORPUS_IN`, which nothing in verify sets. Nineteen
  stages. Both negative-tested. `pnpm verify` green.
