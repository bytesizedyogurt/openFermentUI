"""H9: what a call costs on the day's spend when the API names the model it served by an
id the price table does not hold (a dated snapshot of an alias the route asked for).
A stand-in client answers one call; no model is called.

    OPENFERMENT_DATABASE_URL=<bh_h9_spend> bh_py ../bughunt/notes/H9/scripts/served_id_price.py
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from openferment_core import llm, spend


def client_serving(served: str):
    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_final_message(self):
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="an answer")], stop_reason="end_turn",
                                   usage=SimpleNamespace(input_tokens=100_000, output_tokens=20_000,
                                                         cache_read_input_tokens=0, cache_creation_input_tokens=0),
                                   model=served)

    class Client:
        def __init__(self):
            self.messages = self

        def stream(self, **request):
            return Stream()

    return Client


for served in ("claude-opus-5-5", "claude-opus-5-5-20261101"):
    before = spend.total_today()
    r = llm.call(system="", user="q", schema=None, max_tokens=20_000, client_factory=client_serving(served),
                 family="explain")
    print(json.dumps({"askedOn": llm.chain("explain")[0], "servedAs": served, "resultCostUsd": r.usage.costUsd,
                      "chargedToTheDayUsd": round(spend.total_today() - before, 6),
                      "sameTokensAtOpusPrice": llm.cost_usd("claude-opus-5-5", 100_000, 20_000)}))
