"""Probe for M45: two reservations at once against a cap that has room for one. spend.reserve holds the day's
lock while it checks and holds (spend.py: "Check and hold are one step under the day's lock, so two calls at
once cannot each see room that only one of them has"). With the lock, at most one of each pair is held; without
it, both can be. Run from a tree's core/ with OPENFERMENT_DATABASE_URL naming a migrated bh_h12_* database.

    python spend_race.py [rounds]
"""
import os
import sys
import threading

from openferment_core import projects, spend

os.environ[spend.DAILY_SETTING] = "1.00"
rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 30
over = 0
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
    state = spend.state()
    if len(held) > 1:
        over += 1
    for rid in held:
        spend.settle(rid, "plan", 0.0)
print(f"{rounds} rounds of two $0.60 reservations against a $1.00 cap: both held (the cap overrun) in {over}")
