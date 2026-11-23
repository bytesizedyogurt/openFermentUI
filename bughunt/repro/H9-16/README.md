# H9-16: callers outside any ask share one "ask" at the twin rule

**Statement.** At the tool door every caller outside an ask carries `askId` None, so after Alice Person proposes `runbooks lock` on `rb-same`, Bob Other's and the assistant `other/1`'s proposals of the same action on the same target are each refused as "already proposed in this ask", though none of the three calls belongs to an ask.

**Contract.**
- `core/openferment_core/proposals.py:132-133`: "One open proposal of a kind per ask (§1.R finding 2): a restart, or a second call worded otherwise, asks for what is already waiting".
- `core/openferment_core/proposals.py:20-21`: "One ask makes one open proposal of a kind (module, action, target); the second is refused."
- `core/openferment_core/models.py:248-249` (the audit row's `askId`): "The ask of Postdoc's the write was part of; left out for a write from outside an ask."
- `core/tests/test_proposals_review.py:133`: "Another target, or another ask, is another proposal."

A call at the tool door belongs to no ask, so the rule keyed to an ask has no ask to hold it to, and a refusal that says "in this ask" names an ask that does not exist.

**Command.** `bash bughunt/repro/H9-16/run.sh` from the repository root. It makes the database `bh_r_h9_16_twin` fresh, serves it on 127.0.0.1:9826 keyless, makes project `h916`, posts the same `runbooks_write` body (`lock` on `rb-same`) three times at `POST /api/tools/runbooks_write` (as `?by=Alice%20Person`, as `?by=Bob%20Other`, and with `X-OpenFerment-Assistant: other/1`), reads the open proposals and the audit rows, then stops the service and drops the database.

**Expected.** Each call, outside any ask, is judged on its own: Bob's and the assistant's are kept as proposals of their own; or, where one open card per action and target is wanted at this door, the refusal names the open proposal without calling it "this ask".

**Observed** (run1.log and run2.log, the same both times).
- Alice: `pr-de9099562586` (run 1), `pr-6fa5ee9802be` (run 2).
- Bob and the assistant: `runbooks_write refused lock: runbooks lock on rb-same is already proposed in this ask (pr-…) and waits for a person. Nothing was proposed. Say so in gaps.`
- One open proposal, by Alice Person, its `askId` null; one audit row for the lock, Alice's, its `askId` absent.

**Likely cause.** `core/openferment_core/proposals.py:134` matches a twin by `p.askId == made.askId`, and every tool-door and MCP call reaches `proposals.propose` with `ask_id` None (`core/openferment_core/tools/writes.py:271`, `getattr(ctx, "ask_id", None)` on a `ToolContext` whose `ask_id` is `""`, made `None` at `proposals.py:122`), so None equals None and every outside caller falls in one shared "ask". The refusal's words at `proposals.py:138` then say "in this ask". High confidence. A small fix: hold the twin rule to calls with an ask (skip it when `made.askId` is None), or word the refusal for an outside call by the open proposal and who made it.

**Severity.** S4, an inconsistency: the refused callers lose their own proposal with a reason that names an ask they are not in, and Alice's open card remains for a person to carry out.
