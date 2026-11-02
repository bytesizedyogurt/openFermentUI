# OF-BLD-016 — the overnight session, in one message

Paste everything below this line into a Claude Code cloud session on `bytesizedyogurt/openFermentUI`. Claude Opus 5.5, extra-high effort. Nothing else to attach.

---

You are executing **OF-BLD-016 version 2.0** on the openFerment repository, unattended, overnight. I am Sean Creighton, the owner. I am asleep until about 07:00 New York (11:00 UTC) and I show this app to my professor that morning from the Mac Mini at `https://seans-mac-mini-1.tail918752.ts.net/`, which serves `main`.

The build document, OF-BLD-016 v2.0, is the second half of this message, after the line `=== THE DOCUMENT ===`. Read it from there; it is not a separate file unless you choose to save it to `docs/build/OF-BLD-016.md` in §1.1, which the document asks you to do.

## Part A — Read first, in this order

1. `CLAUDE.md`, `STATE.md` (all of it; the two newest sections, "Yeast-ethanol demo prep" and "OF-BLD-015 Phase 7", matter most), `COMPONENTS.md`, `README.md`, `docs/DEMO-YEAST.md`.
2. `docs/build/OF-BLD-014.md` Parts A to E (the protocol you follow) and, on the branch `claude/of-bld-015-postdoc`, `docs/build/OF-BLD-015-phase7.md` Part A and `docs/build/DEMO-PHASE7.md`.
3. `OF-BLD-016.md`, twice. It is what you execute. Where it and the tree disagree, the tree wins and your report says so.

## Part B — Rules that do not move

- Start from `main` at `7e3ebb0`. Work on `claude/of-bld-016-demo`. Push after every commit.
- One commit per step, message exactly as the document gives it. `pnpm verify` green before every commit; red after two attempts at the cause is a stop.
- Every model call the platform makes runs `claude-haiku-5-5` at effort `medium`, from the environment variables already set. The key is `OPENFERMENT_API_KEY` in the environment; never printed, logged, pasted or returned.
- Rule 1 covers you: you type no process number into seed data or product code.
- Delete nothing under `src/data/corpus/`, no record, no candidate, no decision, no artifact, no person. Archive and flag, as Part D says. Deleting `src/sim/` and `src/data/guildSample.ts` is allowed by name in Part D.
- Merge `claude/of-bld-015-postdoc` as a merge commit (D2). Resolve `postdoc_agent.py` by hand so the coverage pass, the module tools and the prior-turn opening all survive, and regenerate the fixture with `pnpm demo:fixtures --prototype`. Never edit a fixture by hand.
- **Ask me nothing.** I am asleep. Every open choice is settled by Part D of the document; where Part D is silent, take the smaller, reversible option that keeps verify green and record it in `STATE.md` under the step. The only reasons to stop are the stop conditions in Part A of the document (a deletion of data, verify red after two attempts, a stated fact that measures false, the key reaching a log or a response, the wall clock).
- Wall clock: `date -u` at the start of every step. From **10:30 UTC** start no new step; finish the one in hand, go green, push, write the report, stop. Spend cap for the night: stop at 1.50 USD.
- When context passes two thirds, finish the step, commit, push, stop, and say which step is next.

## Part C — Order and priority

Phase 1 (merge Phase 7), Phase 2 (programs, casein and PHA archived), Phase 3 (nothing invented on screen), Phase 4 (scorecard on thread Q, the questions live, one run sheet, truth pass, pull request). Phase 5 only if the clock allows. **Phase 4 runs whatever state Phases 2 and 3 are in**, so `docs/DEMO.md` matches the tree I deploy; its "Steer around" list names anything a skipped step would have removed.

## Part D — Report

End with the A.7 report from OF-BLD-014, with these lines at the top:

```
MORNING: <green and ready to merge | stopped at §x.y, run "next phase" | do not deploy, because …>
STEER AROUND: <every screen, control or question I must not touch in the meeting>
MERGE: <Phase 7 merged: yes/no; the two live check questions: claims kept, cost>
PROGRAMS: <switch built: yes/no; what still shows with it off>
```

Write for me in plain English, short sentences. Explain any open-source tool by what it does.

Begin with §1.1.

