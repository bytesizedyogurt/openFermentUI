"""R1-03 / R2-01: the concept graph's dry run prices every batch of a build as one prompt.

Run by run.sh from core/ with OPENFERMENT_DATABASE_URL naming its fresh database, after the real CLI's
two dry runs (`literature_live graph --project r103 --dry-run [--limit 40]`) wrote their JSON lines to the
two files named on the command line. Keyless: no model is asked, nothing reaches the network.

1. The build itself, `graph.build`, runs over the same passages on a client that records each prompt it
   is handed and answers an empty graph: one request a batch, each the size the dry run measured.
2. Each recorded request is priced as llm.py prices it: `llm.usage_of` on a response of that request's
   input (what every answer is charged through, llm.py:533 and :1067) and `llm.cost_usd` on the hold
   arithmetic the dry run itself uses, one request at a time.
3. The recorded F.5 measure (92 batches, 1,758,899 prompt characters) is driven through graph_command's
   own dry-run branch, its two reads stood in for, and priced one request at a time the same way.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys

from openferment_core import db, literature_live, llm, projects
from openferment_core.literature import graph
from sci_rag.llm.client import LLMClient

PROJECT = "r103"
small, full = (json.loads(open(p, encoding="utf-8").read().strip().splitlines()[-1]) for p in sys.argv[1:3])
model = full["model"]
threshold, (long_in, long_out) = llm.LONG_PROMPT_PRICES[model]
short_in, short_out = llm.PRICES[model]
answer = max(graph.ANSWER_TOKENS, llm.KIT_ROOM[llm.routes()["index"].effort])


class Recording(LLMClient):
    """The kit's client for a graph batch, answering an empty graph and keeping each prompt."""

    def __init__(self) -> None:
        self.model, self.prompts, self.ceilings = model, [], []

    async def generate(self, prompt, *, system=None, temperature=0.2, max_tokens=2048, json_mode=False):
        self.prompts.append(prompt)
        self.ceilings.append(max_tokens)
        return '{"entities": [], "relationships": []}'

    async def stream(self, prompt, *, system=None, temperature=0.2, max_tokens=2048):
        yield await self.generate(prompt, system=system, temperature=temperature, max_tokens=max_tokens)


def per_request(prompts: list[str]) -> tuple[float, float]:
    """Input and the most, each prompt priced as the one request it is sent as."""
    charged = sum(llm.usage_of({"model": model, "stop_reason": "end_turn",
                                "usage": {"input_tokens": round(len(p) / 4), "output_tokens": 0}}).costUsd
                  for p in prompts)
    held = sum(llm.cost_usd(model, len(p) // llm.CHARS_PER_TOKEN_ESTIMATE + 1, answer) for p in prompts)
    return charged, held


# 1. The build, on the recording client.
rec = Recording()
with projects.using(PROJECT):
    built = db.run(graph.build(PROJECT, llm=rec, rate_limit_s=0))
sizes = [len(p) for p in rec.prompts]
print(f"build: {built.batches_run} batches run, {len(rec.prompts)} requests sent, {built.chunks_processed} passages read; "
      f"each request {min(sizes)} to {max(sizes)} characters, about {round(max(sizes) / 4)} kit tokens "
      f"({max(sizes) // llm.CHARS_PER_TOKEN_ESTIMATE + 1} at the guard's estimate); each asks {set(rec.ceilings)} output tokens")
print(f"model {model}: {short_in}/{short_out} USD a million up to {threshold} prompt tokens a request, "
      f"{long_in}/{long_out} past it (llm.py:330-345)")
same_prompts = sum(sizes) == full["promptCharacters"] and len(sizes) == full["batches"]
print(f"the dry run measured the same requests: {same_prompts} "
      f"({full['batches']} batches, {full['promptCharacters']} characters)")

# 2. The fresh database's build, both ways.
fresh_in, fresh_most = per_request(rec.prompts)
print(f"dry run, --limit 40 ({small['batches']} batches, {small['kitTokens']} kit tokens): "
      f"inputUsd {small['inputUsd']}, mostUsd {small['mostUsd']}; "
      f"input a batch {small['inputUsd'] / small['batches']:.6f} USD")
print(f"dry run, whole   ({full['batches']} batches, {full['kitTokens']} kit tokens): "
      f"inputUsd {full['inputUsd']}, mostUsd {full['mostUsd']}; "
      f"input a batch {full['inputUsd'] / full['batches']:.6f} USD")
print(f"each request priced as itself: input {fresh_in:.6f} USD, most {fresh_most:.6f} USD; "
      f"the dry run says {full['inputUsd'] / fresh_in:.2f} and {full['mostUsd'] / fresh_most:.2f} times that")

# 3. The recorded F.5 measure through graph_command's own dry-run branch.
TOTAL, BATCHES = 1_758_899, 92
f5 = ["x" * (TOTAL // BATCHES + (1 if i < TOTAL % BATCHES else 0)) for i in range(BATCHES)]
real_run, real_prompts = literature_live.db.run, literature_live.graph.prompts
literature_live.db.run = lambda coro: (coro.close() if hasattr(coro, "close") else None) or [("c", "d", "t")] * 814
literature_live.graph.prompts = lambda rows: f5
out = io.StringIO()
try:
    with contextlib.redirect_stdout(out):
        literature_live.graph_command(argparse.Namespace(project=PROJECT, dry_run=True, rebuild=False, limit=None,
                                                         by=None))
finally:
    literature_live.db.run, literature_live.graph.prompts = real_run, real_prompts
said = json.loads(out.getvalue())
f5_in, f5_most = per_request(f5)
print(f"F.5's measure through graph_command: batches {said['batches']}, promptCharacters {said['promptCharacters']}, "
      f"kitTokens {said['kitTokens']}, inputUsd {said['inputUsd']}, mostUsd {said['mostUsd']}")
print(f"F.5's 92 requests priced each as itself: input {f5_in:.4f} USD, most {f5_most:.4f} USD "
      f"(the largest a batch can be is {max(sizes)} characters, under the threshold at either estimate)")

fresh_wrong = full["inputUsd"] > 1.5 * fresh_in and full["mostUsd"] > 1.5 * fresh_most
f5_wrong = round(said["inputUsd"], 4) == 0.2199 and round(said["mostUsd"], 4) == 2.3239 and f5_most < 0.5
batch_jump = full["inputUsd"] / full["batches"] > 1.5 * small["inputUsd"] / small["batches"]
print(f"EXPECTED: the dry run's inputUsd and mostUsd are the sums of each batch request's own price: "
      f"{fresh_in:.6f} and {fresh_most:.6f} USD for this database's {full['batches']} batches, and "
      f"{f5_in:.4f} and {f5_most:.4f} USD for F.5's 92 (each request far under {threshold} prompt tokens)")
print(f"OBSERVED: the dry run prints {full['inputUsd']} and {full['mostUsd']} USD here "
      f"({full['inputUsd'] / fresh_in:.1f} times), and {said['inputUsd']} and {said['mostUsd']} USD for F.5's measure, "
      f"the records' 0.2199 and 2.3239; the same batch is priced at {short_in} USD a million input tokens in a "
      f"{small['batches']}-batch dry run and {long_in} in a {full['batches']}-batch one")
print("CHECK:", json.dumps({"samePrompts": same_prompts, "freshWrong": fresh_wrong, "f5MatchesRecords": f5_wrong,
                            "batchPriceJumps": batch_jump}))
print("VERDICT:", "DEFECT" if same_prompts and fresh_wrong and f5_wrong and batch_jump else "NO-DEFECT")
