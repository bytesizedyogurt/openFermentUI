"""H13: `pnpm ready`'s model rows against a routing table that moves explain, extract and judge.

No network and no key: the Anthropic client is a stand-in whose Models API lists every model but
the two named in OPENFERMENT_ROUTES below, as a key that may not use them would. The rows are
ready.check_model and ready.check_roles, called as ready.run calls them with a key held.

Expected (docs/runbooks/live-host-install.md:170 "`model` and `roles`, the routes' models through the
Models API"; CLAUDE.md "pnpm ready ... says in rows whether the service can run: ... the model routes"):
a row that names the moved routes and warns that their models are not listed for the key.

Usage (from core/, its venv's python, OPENFERMENT_DATABASE_URL naming a migrated bh_ database):
    python ready_routes.py
"""
import json
import os

import anthropic
import httpx

UNLISTED = {"claude-judge-unlisted", "claude-extract-unlisted"}
os.environ["OPENFERMENT_ROUTES"] = json.dumps({
    "judge": {"models": ["claude-judge-unlisted"], "effort": "max"},
    "extract": {"models": ["claude-extract-unlisted"], "effort": "high"},
    "explain": {"models": ["claude-extract-unlisted"], "effort": "high"},
})

from openferment_core import llm, ready  # noqa: E402

asked: list[str] = []


class _Models:
    def retrieve(self, model, timeout=None):
        asked.append(model)
        if model in UNLISTED:
            raise anthropic.NotFoundError(
                "not found", response=httpx.Response(404, request=httpx.Request("GET", "https://stand-in")), body=None)
        return {"id": model}


class _Client:
    models = _Models()


print("routes:", {k: (list(v.models), v.effort) for k, v in llm.routes().items()})
for check in (ready.check_model(True, client_factory=_Client), ready.check_roles(True, client_factory=_Client)):
    print(f"{ready.MARKS[check.mark]} {check.name}: {check.detail}")
print("models the rows asked the Models API about:", sorted(set(asked)))
print("unlisted models the rows never asked about:", sorted(UNLISTED - set(asked)))
