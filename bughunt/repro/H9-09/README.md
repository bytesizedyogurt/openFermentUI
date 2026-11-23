# H9-09: a call held before midnight UTC settles into the next day, which never counted its hold

**Statement.** A model call reserved at 23:59:30 UTC is checked and held against that day alone, and its
settlement at 00:00:40 lands on the new day, so a second call reserved at 00:00:10 sees an empty new day,
is held, and the new day's spend reaches 1.80 USD against a 1.00 USD cap.

**Contract.**
- `core/openferment_core/llm.py:37-39`: "ONE DAILY CAP. Every response is charged to `spend.py` under its
  role, and a call whose worst case could take the UTC day past `OPENFERMENT_DAILY_BUDGET_USD` is refused
  before it is sent (`BudgetExhausted`)."
- `core/openferment_core/spend.py:3-5`: "`llm.py` charges every response here, and asks before every call
  whether the call could pass `OPENFERMENT_DAILY_BUDGET_USD`. The day is the UTC day; a new day starts from
  zero."
- `CLAUDE.md:48` (R): "Every model call goes through `core/openferment_core/llm.py` ... under the day's cap
  `OPENFERMENT_DAILY_BUDGET_USD`"; `CLAUDE.md:140` lists "Spend above the daily cap" as a stop condition.

**Command** (from the repository root):

    bash bughunt/repro/H9-09/run.sh

It makes the test database `bh_r_h9_09_spend` fresh, sets the cap to 1.00 USD, and drives `spend.reserve`
and `spend.settle` (the two calls `llm.py:588` and `llm.py:946`/`1068` make around every model call) with
the spend module's own clock (`spend.datetime`) set to each step's instant. No service, no model, no key.
A control runs the same two 0.90 USD calls within one day first. The database is dropped at the end.

**Expected.** With a 1.00 USD cap, two calls whose worst case is 0.90 USD each never both spend on one UTC
day: the call held at 23:59:30 either counts against the new day while it is in flight (so the 0.90 USD
call asked at 00:00:10 is refused, as the control's second call is within one day), or its cost is charged
to the day that held it.

**Observed** (both runs):
- control, one day: the second 0.90 reservation is refused ("today $0.00 spent and $0.90 reserved of the
  $1.00 cap");
- at 00:00:10 the new day's state reads `reservedUsd` 0 while A's 0.90 is in flight;
- B's 0.90 reservation on 2026-11-11 is held;
- 2026-11-10 spent 0.00 USD; 2026-11-11 spent 1.80 USD in 2 calls against the 1.00 USD cap;
- spend rows: `2026-11-11|settled|0.900000` twice (A's charge moved off the day that held it).

**Likely cause** (confidence high).
- `core/openferment_core/spend.py:116-126` `_day_state` counts the reservations whose `day` is the day
  queried, so `_reserve` (`spend.py:153-163`) at 00:00:10 checks the new day without the hold A keeps on
  the old day.
- `core/openferment_core/spend.py:181-192` `_settle` takes `day = today()` at settle time, deletes the
  reservation by its id whatever its day, and inserts the cost under the settling day, a day whose check
  never counted that hold. The old day ends with nothing charged for A.

A fix keeps the cost on the reservation's own day (settle reads the reserved row's `day`), or counts
every unexpired reservation in a day's check; either is small.

**Severity** S3: an edge case at the UTC day boundary. The overshoot is bounded by the worst cases held
in flight at midnight (a reservation lives up to `RESERVATION_TTL_S`, 1800 s, `spend.py:79`), and the cap
holds again for every later call of the new day.
