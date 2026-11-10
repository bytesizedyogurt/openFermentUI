"""P-01: one llm.call on a route that names a local model alone, answered at a stub OpenAI-compatible endpoint.

usage (keyless, the repository's Python): python local_call.py STUB_PORT DEAD_PORT [placeholder]

OPENFERMENT_LOCAL_BASE_URL names the stub; OPENFERMENT_ROUTES gives `explain` one model,
openai-compatible:local-stub. ANTHROPIC_BASE_URL also points at the stub, so an Anthropic request, were one
made, is logged there and reaches nothing else; every proxy points at a dead loopback port. With `placeholder`
the run sets a placeholder ANTHROPIC_API_KEY (the control arm); without it ANTHROPIC_API_KEY stays empty.
Prints one line: ANSWERED <model> cost=<usd> text=<...> or RAISED <type>: <words>."""
import json
import os
import sys

stub, dead = sys.argv[1], sys.argv[2]
os.environ["OPENFERMENT_LOCAL_BASE_URL"] = f"http://127.0.0.1:{stub}/v1"
os.environ["OPENFERMENT_ROUTES"] = json.dumps({"explain": {"models": ["openai-compatible:local-stub"]}})
os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{stub}"
for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
    os.environ[k] = f"http://127.0.0.1:{dead}"
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
if sys.argv[3:] == ["placeholder"]:
    os.environ["ANTHROPIC_API_KEY"] = "placeholder-not-a-key"
else:
    os.environ["ANTHROPIC_API_KEY"] = ""

from openferment_core import llm  # noqa: E402

print("route explain:", [m for m in llm.routes()["explain"].models], "| served:", llm.served_providers(),
      "| ANTHROPIC_API_KEY set:", bool(os.environ.get("ANTHROPIC_API_KEY")))
try:
    r = llm.call(system="s", user="q", schema=None, max_tokens=50, family="explain")
    print(f"ANSWERED {r.model} cost={r.usage.costUsd} tried={r.tried} text={(r.text or '')[:60]}")
except Exception as e:  # the defect's arm: ModelUnavailable
    print(f"RAISED {type(e).__name__}: {str(e)[:200]}")
