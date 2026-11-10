"""H13-03: `pnpm ready`'s `model` and `roles` rows against a routing table that moves explain,
extract and judge to models the key's Models API does not list.

Keyless, no network: the Anthropic client is a stand-in. Its Models API (`models.retrieve`) and its
Messages API (`messages.stream`) answer 404 for the two moved models, as a key that may not use them
would, and accept every other model. The rows are ready.check_model and ready.check_roles, called
as ready.run calls them with a key held (have_key True), their client the stand-in.

Run from core/ with its venv's python, OPENFERMENT_DATABASE_URL naming a migrated bh_ database.
Prints CASE lines; the last line is VERDICT: DEFECT or VERDICT: NO-DEFECT.
"""
import ipaddress
import json
import os
import socket

# Belt and braces: no socket leaves loopback, and a real client (none is made) would aim at a dead port.
os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:9"
_connect = socket.socket.connect
refused: list[str] = []


def _loopback_only(self, address):
    host = address[0] if isinstance(address, tuple) else None
    if host is not None:
        try:
            if not ipaddress.ip_address(host).is_loopback:
                refused.append(str(host))
                raise ConnectionRefusedError(f"repro guard: {host} is not loopback")
        except ValueError:
            refused.append(str(host))
            raise ConnectionRefusedError(f"repro guard: {host} is a name") from None
    return _connect(self, address)


socket.socket.connect = _loopback_only

import anthropic  # noqa: E402
import httpx  # noqa: E402

# Priced models (llm.PRICES), so the live call below reaches the client and is refused there.
UNLISTED_EXTRACT = "claude-haiku-4-5-20251001"
UNLISTED_JUDGE = "claude-opus-4-8"
UNLISTED = {UNLISTED_EXTRACT, UNLISTED_JUDGE}
MOVED = {
    "judge": {"models": [UNLISTED_JUDGE], "effort": "max"},
    "extract": {"models": [UNLISTED_EXTRACT], "effort": "high"},
    "explain": {"models": [UNLISTED_EXTRACT], "effort": "high"},
}

from openferment_core import llm, ready  # noqa: E402

asked: list[str] = []


def _404(model: str) -> anthropic.NotFoundError:
    req = httpx.Request("GET", f"https://stand-in/v1/models/{model}")
    return anthropic.NotFoundError(f"model: {model}", response=httpx.Response(404, request=req), body=None)


class _Models:
    def retrieve(self, model, timeout=None):
        asked.append(model)
        if model in UNLISTED:
            raise _404(model)
        return {"id": model}


class _Messages:
    def stream(self, model, **request):
        if model in UNLISTED:
            raise _404(model)
        raise AssertionError(f"the repro makes no call on {model}")


class _Client:
    models = _Models()
    messages = _Messages()


def rows() -> list[ready.Check]:
    return [ready.check_model(True, client_factory=_Client), ready.check_roles(True, client_factory=_Client)]


def show(label: str, checks: list[ready.Check]) -> None:
    for c in checks:
        print(f"CASE {label}: {ready.MARKS[c.mark]} {c.name}: {c.detail}")


# Control: the plan route moved to an unlisted model. The rows ask about plan, so they should say so.
os.environ["OPENFERMENT_ROUTES"] = json.dumps({"plan": {"models": [UNLISTED_JUDGE], "effort": "high"}})
asked.clear()
control = rows()
show("control (plan moved)", control)
control_caught = any(UNLISTED_JUDGE in c.detail and c.mark in ("warn", "fail") for c in control)
print(f"CASE control (plan moved): a row names {UNLISTED_JUDGE} with ! or ✗: {control_caught}")

# The case: explain, extract and judge moved; plan and index at their defaults.
os.environ["OPENFERMENT_ROUTES"] = json.dumps(MOVED)
table = llm.routes()
print("CASE moved: routing table read back:", json.dumps({k: [list(v.models), v.effort] for k, v in table.items()}))
asked.clear()
moved = rows()
show("moved", moved)
print("CASE moved: models the rows asked the Models API about:", sorted(set(asked)))
print("CASE moved: moved routes' models the rows never asked about:", sorted(UNLISTED - set(asked)))
named_anywhere = sorted(m for m in UNLISTED if any(m in c.detail for c in moved))
print("CASE moved: moved routes' models either row names:", named_anywhere)

# What the live loop meets: one extraction and one judgement on the same key, through llm.call.
failures = {}
for family in ("extract", "judge"):
    try:
        llm.call(system="", user="ping", schema=None, max_tokens=16, client_factory=_Client, family=family,
                 label=f"[{family}] ")
        failures[family] = "answered"
    except llm.ModelUnavailable as e:
        failures[family] = f"ModelUnavailable: {e}"
    print(f"CASE live call on {family}: {failures[family]}")

print("CASE guard: non-loopback connections refused:", refused or "none")

rows_pass = all(c.mark == "ok" for c in moved)
missed = UNLISTED - set(asked)
live_fails = all(v.startswith("ModelUnavailable") for v in failures.values())
defect = control_caught and rows_pass and missed == UNLISTED and not named_anywhere and live_fails
print("VERDICT:", "DEFECT" if defect else "NO-DEFECT",
      f"(control caught {control_caught}; both rows ✓ {rows_pass}; unasked {sorted(missed)}; "
      f"live extract and judge fail {live_fails})")
