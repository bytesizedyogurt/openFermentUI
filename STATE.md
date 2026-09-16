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
