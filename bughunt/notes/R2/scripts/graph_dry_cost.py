"""R2: the concept graph's dry run prices 92 requests as one prompt, so Haiku 5.5's long-prompt tier
applies to all of them.

`pnpm lit:graph --project ethanol --dry-run` (literature_live.graph_command) recorded "814 passages
in 92 batches and 1,758,899 prompt characters (439,725 kit tokens): their input comes to 0.2199 USD
on claude-haiku-5-5, and the most the build could cost, each batch's whole answer counted, to
2.3239 USD" (docs/reports/literature-retrieval.md 115-117, docs/PROGRESS.md 609 and 3372,
commit 0dd8415). The build sends one request a batch (graph.build, ten passages a batch), and
llm.LONG_PROMPT_PRICES says "past the threshold (in prompt tokens ...) the whole request pays the
second pair": a batch of about 4,800 kit tokens pays the first pair.

This script drives graph_command's own dry-run branch with stand-ins for the database read (92
prompts whose characters sum to the recorded 1,758,899), prints what it prints, then prices the
same 92 prompts one request at a time with the same llm functions: cost_usd for the input, and
worst_case_usd's arithmetic (what the day's cap holds before each call) for the most.
No database, no network, no key. Run: cd core && .venv/bin/python ../bughunt/notes/R2/scripts/graph_dry_cost.py
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json

from openferment_core import llm, literature_live
from openferment_core.literature import graph

TOTAL, BATCHES = 1_758_899, 92
sizes = [TOTAL // BATCHES + (1 if i < TOTAL % BATCHES else 0) for i in range(BATCHES)]
prompts = ["x" * n for n in sizes]
assert sum(map(len, prompts)) == TOTAL

literature_live.db.run = lambda coro: (coro.close() if hasattr(coro, "close") else None) or [("c", "d", "t")] * 814
literature_live.graph.prompts = lambda rows: prompts
literature_live.projects.using = lambda project: contextlib.nullcontext()

out = io.StringIO()
with contextlib.redirect_stdout(out):
    literature_live.graph_command(argparse.Namespace(project="ethanol", dry_run=True, rebuild=False, limit=None, by="R2"))
printed = json.loads(out.getvalue())
print("graph_command's dry run prints:", json.dumps(printed))

model = llm.chain("index")[0]
answer = max(graph.ANSWER_TOKENS, llm.KIT_ROOM[llm.routes()["index"].effort])
per_input = sum(llm.cost_usd(model, round(len(p) / 4), 0) for p in prompts)
per_most = sum(llm.cost_usd(model, len(p) // llm.CHARS_PER_TOKEN_ESTIMATE + 1, answer) for p in prompts)
print(f"one request a batch: largest prompt {max(sizes)} characters, about {max(sizes) // 4} kit tokens "
      f"(the long-prompt threshold is {llm.LONG_PROMPT_PRICES[model][0]} tokens)")
print(f"  input of the 92 requests at their own tier: {per_input:.4f} USD  (dry run says {printed['inputUsd']:.4f})")
print(f"  the most, each request's hold summed:       {per_most:.4f} USD  (dry run says {printed['mostUsd']:.4f})")
print(f"  prices: short tier {llm.PRICES[model]}, long tier {llm.LONG_PROMPT_PRICES[model][1]} USD per million")
