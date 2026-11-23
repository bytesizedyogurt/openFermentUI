"""Repro H12-03's probe: two reservations at once against a cap with room for one.

spend.reserve says (core/openferment_core/spend.py:175-177): "Check and hold are one step under the day's lock, so
two calls at once cannot each see room that only one of them has (§3.R)." Each round, two threads behind a barrier
each ask spend.reserve for $0.60 against a $1.00 cap, on real connections of their own (no test binding), and the
round counts as an overrun when both are held. Run from a tree's core/ with that tree first on PYTHONPATH and
OPENFERMENT_DATABASE_URL naming a migrated bh_r_h12_03_* database.

    python probe.py [rounds]
"""
import inspect
import os
import sys
import threading

from openferment_core import projects, spend

os.environ[spend.DAILY_SETTING] = "1.00"
rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
locked = 'db.lock(s, "spend"' in inspect.getsource(spend._reserve)
print(f"spend from {spend.__file__}; _reserve takes the day's lock: {locked}")
over = 0
most_reserved = 0.0
for n in range(rounds):
    gate = threading.Barrier(2)
    held: list[str] = []

    def ask() -> None:
        with projects.using(None):
            gate.wait()
            try:
                held.append(spend.reserve("plan", 0.60))
            except spend.CapReached:
                pass

    ts = [threading.Thread(target=ask) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    most_reserved = max(most_reserved, spend.state()["reservedUsd"])
    if len(held) > 1:
        over += 1
    for rid in held:
        spend.settle(rid, "plan", 0.0)
print(f"PROBE: {rounds} rounds of two $0.60 reservations against a $1.00 cap: both held (the cap overrun) in {over}; "
      f"the most held at once ${most_reserved:.2f}")
