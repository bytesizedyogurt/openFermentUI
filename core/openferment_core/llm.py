"""The one place openFerment calls a Claude model (Postdoc, Extract).

    PRIMARY   claude-opus-5-5     every call starts here
    FALLBACK  claude-sonnet-5-5   when the primary declines or is unavailable

Override with OPENFERMENT_MODEL and OPENFERMENT_FALLBACK_MODEL in core/.env
(the fallback may be a comma-separated list, tried in order);
thinking depth with OPENFERMENT_EFFORT (low, medium, high, xhigh, max;
default medium).

TWO ROLES (OF-BLD-014 §3.3, E.7). `answer` is the chain above: Postdoc and
Extract. `index` is bulk helper work, `OPENFERMENT_INDEX_MODEL` (default
claude-haiku-5-5), falling back to the answer chain. `call(role=...)` picks
one; every existing caller is `answer`.

ONE DAILY CAP. Every response is charged to `spend.py` under its role, and a
call whose worst case could take the UTC day past `OPENFERMENT_DAILY_BUDGET_USD`
is refused before it is sent (`BudgetExhausted`).

TOOL TURNS. `converse` runs one turn of a conversation the caller owns, with
strict tools, `tool_choice` `auto` or `none` and nothing else, the answer
schema in `output_config.format`, and top-level `cache_control`. It falls
back nowhere; the loop that owns the conversation decides (§5.2).

STRUCTURED OUTPUT BY CONSTRUCTION. Both callers used to pin `tool_choice` to a
single tool, so the model had exactly one way to answer. Claude Opus 5.5 and
Claude Sonnet 5.5 reject forced tool use (a 400 error), so the schema moves to
structured outputs: `output_config.format` with a JSON schema. The API then
returns JSON that matches the schema in the response's text block, which keeps
the property that mattered: the model has no free-text way to answer, and the
shape is checked before we see it. `strict_schema` turns a tool-style schema
into one the API accepts.

TWO KINDS OF FALLING BACK, both to the same next model:

- A refusal. These models run safety classifiers, a biology one among them,
  and a request about fermentation can trip it. A refusal is a normal response
  with `stop_reason: "refusal"` and `stop_details.category`; the same request
  usually succeeds on another model. A refusal that arrives before any output
  in the `bio` category is billed, so its tokens count toward the cost.
- The model is unavailable: retired or not offered to this key (404, 403),
  rate limited past the SDK's own retries (429), overloaded (529) or failing
  (5xx).

What does not fall back: a rejected key, an unreachable network, a request
the API calls malformed, or a refusal in the `reasoning_extraction` category,
which Anthropic's docs say to answer by changing the prompt. Another model
would fail the same way.

A connection that drops after the stream has opened surfaces from the SDK as
a raw transport error (it wraps only the opening of the request), so it is
caught here and treated as the model being unavailable.

A refusal that produced no output is billed only in the categories Anthropic
bills (`bio`, `frontier_llm`, `reasoning_extraction`, as of September 2026);
its tokens are counted either way and its cost is $0 otherwise.

Calls stream, because a long extraction with thinking can run for minutes and
a non-streaming request is cut off at ten; the final message is the same.
"""
from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

from . import spend
from .models import Usage

try:  # what the anthropic SDK is built on; its stream readers raise these raw
    import httpx2 as _http
except ImportError:  # pragma: no cover - an SDK built on plain httpx
    import httpx as _http

log = logging.getLogger("openferment.llm")

DEFAULT_PRIMARY = "claude-opus-5-5"
DEFAULT_FALLBACK = "claude-sonnet-5-5"
DEFAULT_EFFORT = "medium"
# What `output_config.effort` accepts; anything else is a 400 on every call,
# which `pnpm ready` reports before the first one.
EFFORTS = ("low", "medium", "high", "xhigh", "max")


# Read when a call is made, so core/.env (which api.py and the batch commands
# load after this module is imported) is what decides.
def primary() -> str:
    return os.environ.get("OPENFERMENT_MODEL", "").strip() or DEFAULT_PRIMARY


def fallback() -> str:
    return os.environ.get("OPENFERMENT_FALLBACK_MODEL", "").strip() or DEFAULT_FALLBACK


def effort() -> str:
    return os.environ.get("OPENFERMENT_EFFORT", "").strip() or DEFAULT_EFFORT


DEFAULT_INDEX = "claude-haiku-5-5"
ROLES = ("answer", "index")


def index_model() -> str:
    return os.environ.get("OPENFERMENT_INDEX_MODEL", "").strip() or DEFAULT_INDEX

# USD per million tokens, input and output, from the pricing page
# (platform.claude.com/docs/en/about-claude/pricing, read 2026-10-08; the
# Haiku 5.5 tiers and the cache multipliers below read 2026-10-13 for
# OF-BLD-014 B.4 and confirmed on the page 2026-10-15). Kept here so the
# number a cost is computed from can be checked against its source. Output
# tokens include the model's thinking.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),  # a prompt of up to 100,000 tokens
    "claude-opus-4-8": (5.00, 25.00),  # a possible third rung; see core/.env.example
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}
# A model whose price rises with the prompt: past the threshold (in prompt
# tokens, cache reads and writes included) the whole request pays the second
# pair. Claude Haiku 5.5 alone, as of the date above.
LONG_PROMPT_PRICES: dict[str, tuple[int, tuple[float, float]]] = {
    "claude-haiku-5-5": (100_000, (0.50, 2.50)),
}
# Prompt caching, as multiples of the input price: a five-minute cache write
# costs 1.25 times it; a cache read 0.1 times, and 0.05 times on Opus 5.5 and
# Sonnet 5.5.
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER: dict[str, float] = {"claude-opus-5-5": 0.05, "claude-sonnet-5-5": 0.05}
DEFAULT_CACHE_READ_MULTIPLIER = 0.1

# JSON Schema keywords structured outputs does not accept. strict_schema moves
# them into the field's description, where the model still reads them, and
# the anchoring and range rules downstream enforce what matters anyway.
_UNSUPPORTED = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "multipleOf", "minLength", "maxLength", "maxItems", "pattern")

# Refusal categories billed when they arrive before any output, per
# platform.claude.com/docs/en/build-with-claude/refusals-and-fallback (read
# 2026-10-08). Every other category, and none, is free when nothing came out.
BILLED_REFUSALS = frozenset({"bio", "frontier_llm", "reasoning_extraction"})
# Refusals no other model is recommended for; the docs say to change the prompt.
NO_FALLBACK_REFUSALS = frozenset({"reasoning_extraction"})


class ModelUnavailable(RuntimeError):
    """No answer could be had: the key, the network, or every model in the
    chain unavailable. Distinct from a refusal and from a bad answer. `usage`
    is what was spent getting here: a billed refusal before the outage."""

    def __init__(self, message: str, usage: Usage | None = None):
        super().__init__(message)
        self.usage = usage or Usage()


class BudgetExhausted(ModelUnavailable):
    """The call could take today's spend past the daily cap, so it was not
    sent. A kind of unavailability, so every caller that already reports one
    reports this, in these words."""


class ModelRefused(RuntimeError):
    """Every model in the chain declined the request."""

    def __init__(self, category: str | None, models: list[str], usage: Usage):
        named = f" ({category})" if category else ""
        super().__init__(
            f"declined by the safety classifier{named} on {', then '.join(models)}. "
            "Nothing was kept; the request can be asked again later"
        )
        self.category = category
        self.models = models
        self.usage = usage


@dataclass
class Result:
    """What one call produced. `data` is the parsed JSON, or None when the
    response stopped at max_tokens or held no parseable JSON."""

    data: dict[str, Any] | None
    model: str
    usage: Usage
    stop_reason: str | None = None
    fell_back: bool = False
    tried: list[str] = field(default_factory=list)

    @property
    def truncated(self) -> bool:
        return self.stop_reason == "max_tokens"


def chain(role: str = "answer") -> list[str]:
    """The models a call in `role` tries, in order, without repeats. The
    fallback may name several, comma-separated, each tried in turn. `index`
    tries its own model first, then the answer chain (E.7)."""
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; the roles are {', '.join(ROLES)}")
    rungs = [primary(), *(m.strip() for m in fallback().split(","))]
    if role == "index":
        rungs = [index_model(), *rungs]
    return list(dict.fromkeys(m for m in rungs if m))


def prices_for(model: str, prompt_tokens: int = 0) -> tuple[float, float]:
    """Input and output price per million tokens for a prompt of this length."""
    tier = LONG_PROMPT_PRICES.get(model)
    if tier and prompt_tokens > tier[0]:
        return tier[1]
    return PRICES.get(model, (0.0, 0.0))


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Cost from the four token counts and the prices on file. `input_tokens`
    is what the API reports as such, which excludes cache reads and writes.
    0 for a model with no price on file, which `pnpm ready` reports."""
    price_in, price_out = prices_for(model, input_tokens + cache_read_tokens + cache_write_tokens)
    read = CACHE_READ_MULTIPLIER.get(model, DEFAULT_CACHE_READ_MULTIPLIER)
    usd = (
        input_tokens * price_in
        + cache_write_tokens * price_in * CACHE_WRITE_MULTIPLIER
        + cache_read_tokens * price_in * read
        + output_tokens * price_out
    ) / 1_000_000
    return round(usd, 6)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def usage_of(response: Any) -> Usage:
    """Tokens and cost of one response, read from the response itself. Output
    tokens include the model's thinking, which is billed as output."""
    usage = _get(response, "usage")
    model = str(_get(response, "model") or primary())
    tin = int(_get(usage, "input_tokens", 0) or 0)
    tout = int(_get(usage, "output_tokens", 0) or 0)
    cread = int(_get(usage, "cache_read_input_tokens", 0) or 0)
    cwrite = int(_get(usage, "cache_creation_input_tokens", 0) or 0)
    cost = cost_usd(model, tin, tout, cread, cwrite)
    if _get(response, "stop_reason") == "refusal" and tout == 0:
        category = _get(_get(response, "stop_details"), "category")
        if category not in BILLED_REFUSALS:
            cost = 0.0
    return Usage(
        inputTokens=tin,
        outputTokens=tout,
        cacheReadTokens=cread,
        cacheWriteTokens=cwrite,
        costUsd=cost,
        models=[model],
    )


def add(a: Usage, b: Usage) -> Usage:
    return Usage(
        inputTokens=a.inputTokens + b.inputTokens,
        outputTokens=a.outputTokens + b.outputTokens,
        cacheReadTokens=a.cacheReadTokens + b.cacheReadTokens,
        cacheWriteTokens=a.cacheWriteTokens + b.cacheWriteTokens,
        costUsd=round(a.costUsd + b.costUsd, 6),
        models=list(dict.fromkeys([*a.models, *b.models])),
    )


# ── the daily cap ──────────────────────────────────────────────────────

# How many characters of a request count as one token when a call's worst
# case is estimated before it is sent. Fewer characters per token than any
# text this service sends, so the estimate leans high: a convention for a
# guard, never a number a result depends on.
CHARS_PER_TOKEN_ESTIMATE = 2


def worst_case_usd(model: str, request: dict[str, Any], max_tokens: int) -> float:
    """The most a request could cost: its size read as tokens at the
    estimate above, priced as uncached input, plus every output token it
    allows."""
    chars = len(json.dumps(request, default=str, ensure_ascii=False))
    return cost_usd(model, chars // CHARS_PER_TOKEN_ESTIMATE + 1, max_tokens)


def _guard(model: str, request: dict[str, Any], max_tokens: int, spent: Usage) -> None:
    refuse, today, cap = spend.would_pass(worst_case_usd(model, request, max_tokens))
    if refuse:
        raise BudgetExhausted(
            f"Today's model spend is ${today:.2f} of the ${cap:.2f} daily cap, and this call could pass it. "
            f"Raise {spend.DAILY_SETTING} in core/.env, or wait for the next UTC day.",
            spent,
        )


def _charge(role: str, used: Usage) -> None:
    if used.costUsd > 0:
        spend.charge(role, used.costUsd)


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """A tool-style JSON schema made acceptable to structured outputs: every
    object closed (`additionalProperties: false`) and the keywords it rejects
    moved into the description. The input is left untouched."""
    out = copy.deepcopy(schema)

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        moved = [f"{k} {node.pop(k)}" for k in _UNSUPPORTED if k in node]
        if node.get("minItems", 0) > 1:
            moved.append(f"minItems {node.pop('minItems')}")
        if moved:
            node["description"] = (node.get("description", "") + f" ({'; '.join(moved)})").strip()
        is_object = node.get("type") == "object" or (
            isinstance(node.get("type"), list) and "object" in node["type"]
        ) or "properties" in node
        if is_object:
            node["additionalProperties"] = False
        for key in ("properties", "$defs", "definitions"):
            if isinstance(node.get(key), dict):
                for child in node[key].values():
                    walk(child)
        for key in ("items", "anyOf", "allOf", "oneOf"):
            if key in node:
                walk(node[key])

    walk(out)
    return out


def _text_json(response: Any) -> dict[str, Any] | None:
    for block in _get(response, "content") or []:
        if _get(block, "type") == "text":
            try:
                value = json.loads(_get(block, "text") or "")
            except ValueError:
                return None
            return value if isinstance(value, dict) else None
    return None


def _error_type(e: Exception) -> str:
    """The API's own name for an error sent inside a stream
    (`overloaded_error`), else the exception's class name."""
    body = getattr(e, "body", None)
    inner = _get(body, "error") if isinstance(body, dict) else None
    return str(_get(inner, "type") or type(e).__name__) if inner else type(e).__name__


def _default_client() -> Any:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ModelUnavailable(
            "ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service."
        )
    return anthropic.Anthropic(api_key=key)


def call(
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    max_tokens: int,
    client_factory: Callable[[], Any] | None = None,
    label: str = "",
    role: str = "answer",
) -> Result:
    """One question, answered as JSON matching `schema`, by the first model in
    the role's chain that will. Raises ModelRefused or ModelUnavailable
    (BudgetExhausted among them) otherwise."""
    client = (client_factory or _default_client)()
    request = {
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort(), "format": {"type": "json_schema", "schema": strict_schema(schema)}},
    }
    models = chain(role)
    spent = Usage()
    tried: list[str] = []
    refusal: str | None = None
    refused_by: list[str] = []
    for i, model in enumerate(models):
        last = i == len(models) - 1
        tried.append(model)
        _guard(model, request, max_tokens, spent)
        try:
            with client.messages.stream(model=model, **request) as stream:
                response = stream.get_final_message()
        except anthropic.AuthenticationError as e:
            raise ModelUnavailable("The Anthropic API rejected the key in core/.env.", spent) from e
        except anthropic.APIConnectionError as e:
            raise ModelUnavailable(f"Could not reach the Anthropic API: {e}", spent) from e
        except anthropic.BadRequestError as e:
            raise ModelUnavailable(f"The Anthropic API refused the request as malformed: {e.message}", spent) from e
        except (anthropic.NotFoundError, anthropic.PermissionDeniedError) as e:
            why = f"{model} is not available to this key ({e.status_code})"
            if last:
                raise ModelUnavailable(why, spent) from e
            log.warning("%s%s; trying %s", label, why, models[i + 1])
            continue
        except (anthropic.APIError, _http.TransportError) as e:
            # 429 after the SDK's retries, 529, 5xx, an error event inside the
            # stream (which the SDK reports with the stream's own 200), or the
            # connection dropping after the stream opened.
            status = getattr(e, "status_code", None)
            if status and status != 200:
                why = f"{model} answered {status}"
            else:
                why = f"{model} stream failed ({_error_type(e)})"
            if last:
                raise ModelUnavailable(f"{why}: {getattr(e, 'message', e)}", spent) from e
            log.warning("%s%s; trying %s", label, why, models[i + 1])
            continue

        used = usage_of(response)
        _charge(role, used)
        spent = add(spent, used)
        stop = _get(response, "stop_reason")
        if stop == "refusal":
            details = _get(response, "stop_details")
            refusal = _get(details, "category") or refusal
            refused_by.append(str(_get(response, "model") or model))
            if last or refusal in NO_FALLBACK_REFUSALS:
                raise ModelRefused(refusal, refused_by, spent)
            log.warning("%s%s declined (%s); trying %s", label, model, refusal or "no category", models[i + 1])
            continue
        served = str(_get(response, "model") or model)
        return Result(
            data=None if stop == "max_tokens" else _text_json(response),
            model=served,
            usage=spent,
            stop_reason=stop,
            fell_back=i > 0,
            tried=tried,
        )
    raise ModelUnavailable("no model to call")  # pragma: no cover - chain() is never empty


# ── one turn of a conversation the caller owns (OF-BLD-014 §3.3) ────────

# The only values `converse` sends as `tool_choice`. `any` and `tool` force a
# tool, which these models answer with a 400 (B.4); the loop uses `auto`, and
# `none` on the last turn of a spent budget (Part G, rule 13).
TOOL_CHOICES = ("auto", "none")


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Turn:
    """What one model turn produced.

    `content` is the assistant's blocks exactly as returned, thinking blocks
    included, as plain dicts ready to append to `messages`. `data` is the
    parsed final JSON when the turn called no tool, else None."""

    content: list[dict[str, Any]]
    toolCalls: list[ToolCall]
    data: dict[str, Any] | None
    stopReason: str | None
    usage: Usage
    model: str


def _block_dict(block: Any) -> dict[str, Any]:
    if isinstance(block, dict):
        return dict(block)
    dump = getattr(block, "model_dump", None)
    if callable(dump):
        return dump(mode="json", exclude_none=True)
    return {k: v for k, v in vars(block).items() if v is not None}


def tool_param(name: str, description: str, input_schema: dict[str, Any]) -> dict[str, Any]:
    """A tool as the API takes it: strict, its schema made acceptable."""
    return {"name": name, "description": description, "input_schema": strict_schema(input_schema), "strict": True}


def converse(
    *,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    schema: dict[str, Any] | None,
    max_tokens: int,
    model: str,
    tool_choice: str = "auto",
    ask: Callable[[dict[str, Any]], Any] | None = None,
    role: str = "answer",
) -> Turn:
    """One model turn on one named model. Tools go out strict; the answer
    schema, when given, goes in `output_config.format`; `cache_control` is set
    at the top level. Raises ModelRefused (with what was spent) and
    ModelUnavailable as `call` does, and falls back nowhere.

    `tools` are `{"name", "description", "input_schema"}`; `tool_param` is
    applied here, so a caller cannot send a loose one. `ask` stands in for
    the API in offline tests: it receives the request and returns a message.
    """
    if tool_choice not in TOOL_CHOICES:
        raise ValueError(f"tool_choice {tool_choice!r} is not sent: these models answer a forced tool with a 400")
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; the roles are {', '.join(ROLES)}")
    output_config: dict[str, Any] = {"effort": effort()}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": strict_schema(schema)}
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "output_config": output_config,
        "cache_control": {"type": "ephemeral"},
    }
    if tools:
        request["tools"] = [tool_param(t["name"], t["description"], t["input_schema"]) for t in tools]
        request["tool_choice"] = {"type": tool_choice}
    _guard(model, request, max_tokens, Usage())

    try:
        if ask is not None:
            response = ask(request)
        else:
            client = _default_client()
            with client.messages.stream(**request) as stream:
                response = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise ModelUnavailable("The Anthropic API rejected the key in core/.env.") from e
    except anthropic.APIConnectionError as e:
        raise ModelUnavailable(f"Could not reach the Anthropic API: {e}") from e
    except anthropic.BadRequestError as e:
        raise ModelUnavailable(f"The Anthropic API refused the request as malformed: {e.message}") from e
    except (anthropic.NotFoundError, anthropic.PermissionDeniedError) as e:
        raise ModelUnavailable(f"{model} is not available to this key ({e.status_code})") from e
    except (anthropic.APIError, _http.TransportError) as e:
        status = getattr(e, "status_code", None)
        why = f"{model} answered {status}" if status and status != 200 else f"{model} stream failed ({_error_type(e)})"
        raise ModelUnavailable(f"{why}: {getattr(e, 'message', e)}") from e

    used = usage_of(response)
    _charge(role, used)
    stop = _get(response, "stop_reason")
    served = str(_get(response, "model") or model)
    if stop == "refusal":
        raise ModelRefused(_get(_get(response, "stop_details"), "category"), [served], used)
    content = [_block_dict(b) for b in (_get(response, "content") or [])]
    calls = [
        ToolCall(id=str(b.get("id", "")), name=str(b.get("name", "")), input=dict(b.get("input") or {}))
        for b in content
        if b.get("type") == "tool_use"
    ]
    data = None if calls or stop == "max_tokens" else _text_json(response)
    return Turn(content=content, toolCalls=calls, data=data, stopReason=stop, usage=used, model=served)
