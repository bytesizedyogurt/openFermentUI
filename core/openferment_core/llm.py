"""The one place openFerment calls a Claude model (Postdoc, Extract).

    PRIMARY   claude-opus-5-5     every call starts here
    FALLBACK  claude-sonnet-5-5   when the primary declines or is unavailable

Override with OPENFERMENT_MODEL and OPENFERMENT_FALLBACK_MODEL in core/.env
(the fallback may be a comma-separated list, tried in order);
thinking depth with OPENFERMENT_EFFORT (low, medium, high, xhigh, max;
default medium).

THE ROUTING TABLE (execution prompt §4.8; ADR-008). A call names its task
family, and `routes()` gives the family's models, tried in order, and the
effort they run at: `plan` (Postdoc's loop of tools), `explain` (an answer in
one call, the literature layer's cited answers), `extract` (a document read
into candidates), `index` (bulk helper work, OPENFERMENT_INDEX_MODEL first,
default claude-haiku-5-5) and `judge` (an evaluation's grading). `ROUTES` is
the table core/.env leaves alone; OPENFERMENT_ROUTES lays a JSON object of
family to `{"models": [...], "effort": ...}` over it. A model is a spec in
Sci RAG Kit's syntax, `provider:model` (a bare id is Anthropic's), so every
provider routes the same way; the service serves Anthropic's models itself,
and a route naming another provider waits, said in words, for the owner's
decision on how its key is read (execution prompt §11.1). The day's spend is
charged under two roles, `answer` and `index` (`SPEND_ROLES`); `role=` names
a family as it did before (`answer` reads `plan`'s route).

ONE DAILY CAP. Every response is charged to `spend.py` under its role, and a
call whose worst case could take the UTC day past `OPENFERMENT_DAILY_BUDGET_USD`
is refused before it is sent (`BudgetExhausted`).

TOOL TURNS. `converse` runs one turn of a conversation the caller owns, each
tool strict unless the registry marks it loose (the module tools, OF-BLD-015
§7.2), `tool_choice` `auto` or `none` and nothing else, the answer schema in
`output_config.format`, and top-level `cache_control`. It falls back
nowhere; the loop that owns the conversation decides (§5.2).

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
# The day's-spend roles (spend.py).
ROLES = ("answer", "index")


def index_model() -> str:
    return os.environ.get("OPENFERMENT_INDEX_MODEL", "").strip() or DEFAULT_INDEX


# ── the routing table (execution prompt §4.8; ADR-008) ─────────────────────

FAMILIES = ("plan", "explain", "extract", "index", "judge")
# The day's-spend role each family is charged under.
SPEND_ROLES = {"plan": "answer", "explain": "answer", "extract": "answer", "index": "index", "judge": "answer"}
# The roles of before, as the families whose routes they read.
ROLE_FAMILIES = {"answer": "plan", "index": "index"}
ROUTES_SETTING = "OPENFERMENT_ROUTES"
# The providers a spec may name, as Sci RAG Kit writes them (sci_rag.llm.spec).
PROVIDERS = ("anthropic", "openai-compatible", "google")
# The providers this service calls itself. Another provider's model is called
# through the kit's client, which reads that provider's key from the kit's
# settings: a change to how keys are read, which waits for the owner (§11.1).
SERVED = ("anthropic",)


class RoutesInvalid(ValueError):
    """OPENFERMENT_ROUTES, or a model spec it holds, in words."""


@dataclass(frozen=True)
class Route:
    """A family's models, tried in order, and the effort they run at."""

    models: tuple[str, ...]
    effort: str


_DEFAULT_CHAIN = (DEFAULT_PRIMARY, DEFAULT_FALLBACK)
ROUTES: dict[str, Route] = {
    "plan": Route(_DEFAULT_CHAIN, DEFAULT_EFFORT),
    "explain": Route(_DEFAULT_CHAIN, DEFAULT_EFFORT),
    "extract": Route(_DEFAULT_CHAIN, DEFAULT_EFFORT),
    "index": Route((DEFAULT_INDEX, *_DEFAULT_CHAIN), DEFAULT_EFFORT),
    "judge": Route(_DEFAULT_CHAIN, DEFAULT_EFFORT),
}


def spec(text: str) -> tuple[str, str]:
    """A model spec as Sci RAG Kit writes it, `provider:model`, as its two
    halves; a bare model id is Anthropic's."""
    raw = text.strip()
    provider, sep, model = raw.partition(":")
    if not sep:
        return "anthropic", raw
    if provider not in PROVIDERS:
        raise RoutesInvalid(f"{raw!r} names the provider {provider!r}; the providers are {', '.join(PROVIDERS)}")
    if not model.strip():
        raise RoutesInvalid(f"{raw!r} names a provider and no model")
    return provider, model.strip()


def routes() -> dict[str, Route]:
    """The routing table a call reads, when it is made: `ROUTES` with the
    models and the effort core/.env names (OPENFERMENT_MODEL, its fallback,
    OPENFERMENT_INDEX_MODEL, OPENFERMENT_EFFORT), then OPENFERMENT_ROUTES laid
    over it family by family. Raises RoutesInvalid in words."""
    answer = tuple(dict.fromkeys(m for m in (primary(), *(x.strip() for x in fallback().split(","))) if m))
    table = {family: Route(answer, effort()) for family in FAMILIES}
    table["index"] = Route(tuple(dict.fromkeys((index_model(), *answer))), effort())
    raw = os.environ.get(ROUTES_SETTING, "").strip()
    if not raw:
        return table
    try:
        given = json.loads(raw)
    except ValueError as e:
        raise RoutesInvalid(f"{ROUTES_SETTING} is not JSON: {e}") from None
    if not isinstance(given, dict):
        raise RoutesInvalid(f"{ROUTES_SETTING} is an object of family to route")
    for family, route in given.items():
        if family not in FAMILIES:
            raise RoutesInvalid(f"{ROUTES_SETTING} names {family!r}; the families are {', '.join(FAMILIES)}")
        if not isinstance(route, dict) or set(route) - {"models", "effort"}:
            raise RoutesInvalid(f"{ROUTES_SETTING}.{family} is an object of models and effort")
        models = route.get("models", list(table[family].models))
        if not isinstance(models, list) or not models or not all(isinstance(m, str) and m.strip() for m in models):
            raise RoutesInvalid(f"{ROUTES_SETTING}.{family}.models is a list of model specs")
        for m in models:
            spec(m)
        level = route.get("effort", table[family].effort)
        if level not in EFFORTS:
            raise RoutesInvalid(f"{ROUTES_SETTING}.{family}.effort is one of {', '.join(EFFORTS)}")
        table[family] = Route(tuple(dict.fromkeys(m.strip() for m in models)), level)
    return table


def family_of(name: str) -> str:
    """A family by its name, or by a role of before (`answer` reads `plan`'s route)."""
    family = ROLE_FAMILIES.get(name, name)
    if family not in FAMILIES:
        raise ValueError(f"unknown family {name!r}; the families are {', '.join(FAMILIES)}, and the roles "
                         f"{', '.join(ROLES)} name {ROLE_FAMILIES['answer']} and {ROLE_FAMILIES['index']}")
    return family


def waits(named: str) -> str:
    """Why a route's model the service does not serve is passed over, in words."""
    return (f"{named} is a {spec(named)[0]} model: calling it reads that provider's key through Sci RAG Kit's "
            "settings, a change to how keys are read that waits for the owner (execution prompt §11.1)")

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
    response stopped at max_tokens or held no parseable JSON; `text` is the
    response's words as written, for a call that asked for prose."""

    data: dict[str, Any] | None
    model: str
    usage: Usage
    stop_reason: str | None = None
    fell_back: bool = False
    tried: list[str] = field(default_factory=list)
    text: str = ""

    @property
    def truncated(self) -> bool:
        return self.stop_reason == "max_tokens"


def chain(name: str = "plan") -> list[str]:
    """The model specs a call in a family tries, in order, without repeats
    (`routes()`). The fallback may name several, comma-separated, each tried
    in turn; `index` tries its own model first, then the answer chain (E.7)."""
    return list(routes()[family_of(name)].models)


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


def _reserve(model: str, request: dict[str, Any], max_tokens: int, spent: Usage, role: str) -> str:
    """Hold the call's worst case against the daily cap before it is sent,
    or refuse it. The hold and the check are one step (`spend.reserve`), so
    the service and the nightly job cannot each take the last of the day;
    the caller settles what the call cost (§3.R)."""
    if model not in PRICES:
        raise BudgetExhausted(
            f"There is no price on file for {model}, so the daily cap cannot hold for a call on it. "
            "Add it to PRICES in core/openferment_core/llm.py, or choose a priced model in core/.env.",
            spent,
        )
    try:
        return spend.reserve(role, worst_case_usd(model, request, max_tokens))
    except spend.SpendUnknown as e:
        raise BudgetExhausted(str(e), spent) from None
    except spend.CapReached as e:
        held = f" with ${e.reserved:.2f} held for calls in flight" if e.reserved else ""
        raise BudgetExhausted(
            f"Today's model spend is ${e.spent:.2f} of the ${e.cap:.2f} daily cap{held}, and this call could pass it. "
            f"Raise {spend.DAILY_SETTING} in core/.env, or wait for the next UTC day.",
            spent,
        ) from None


def strict_schema(schema: dict[str, Any], *, keep_maps: bool = False) -> dict[str, Any]:
    """A tool-style JSON schema made acceptable to structured outputs: every
    object closed (`additionalProperties: false`) and the keywords it rejects
    moved into the description. The input is left untouched. With
    `keep_maps` (a loose tool's input, OF-BLD-020 §3.4) an object whose
    `additionalProperties` is a schema stays a map, that schema kept and
    walked, so a model reads `recordsByParam` as keys to record ids and a
    write's `fields` as names to words, not as objects that take nothing."""
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
            extra = node.get("additionalProperties")
            if keep_maps and isinstance(extra, dict):
                walk(extra)
            else:
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


def _text_of(response: Any) -> str:
    return "".join(_get(b, "text") or "" for b in (_get(response, "content") or []) if _get(b, "type") == "text")


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


# A key not scoped to a workspace is accepted only with the workspace named
# on each request; the API's own 400 says so. The id is not a secret, and
# with it unset nothing extra is sent.
WORKSPACE_SETTING = "OPENFERMENT_WORKSPACE_ID"


def client_headers() -> dict[str, str]:
    workspace = os.environ.get(WORKSPACE_SETTING, "").strip()
    return {"anthropic-workspace-id": workspace} if workspace else {}


def make_client(**kwargs: Any) -> Any:
    """Every Anthropic client the service builds, so the workspace header
    reaches the model calls and `pnpm ready`'s checks alike."""
    headers = {**client_headers(), **kwargs.pop("default_headers", {})}
    return anthropic.Anthropic(default_headers=headers or None, **kwargs)


def _default_client() -> Any:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ModelUnavailable(
            "ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service."
        )
    return make_client(api_key=key)


def call(
    *,
    system: str,
    user: str,
    schema: dict[str, Any] | None,
    max_tokens: int,
    client_factory: Callable[[], Any] | None = None,
    label: str = "",
    role: str = "answer",
    family: str | None = None,
) -> Result:
    """One question, answered as JSON matching `schema` (or in words when
    `schema` is None), by the first model in the family's route that will
    (`role` names one as before: `answer` is `explain` here, an answer in one
    call). Raises ModelRefused or ModelUnavailable (BudgetExhausted among
    them) otherwise."""
    family = family_of(family or ("explain" if role == "answer" else role))
    route = routes()[family]
    role = SPEND_ROLES[family]
    client = (client_factory or _default_client)()
    output: dict[str, Any] = {"effort": route.effort}
    if schema is not None:
        output["format"] = {"type": "json_schema", "schema": strict_schema(schema)}
    request: dict[str, Any] = {
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
        "output_config": output,
    }
    if system:
        request["system"] = system
    models = list(route.models)
    spent = Usage()
    tried: list[str] = []
    refusal: str | None = None
    refused_by: list[str] = []
    for i, named in enumerate(models):
        last = i == len(models) - 1
        provider, model = spec(named)
        if provider not in SERVED:
            if last:
                raise ModelUnavailable(waits(named), spent)
            log.warning("%s%s; trying %s", label, waits(named), models[i + 1])
            continue
        tried.append(model)
        held = _reserve(model, request, max_tokens, spent, role)
        cost = 0.0
        try:
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
            cost = used.costUsd
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
                data=None if stop == "max_tokens" or schema is None else _text_json(response),
                model=served,
                usage=spent,
                stop_reason=stop,
                fell_back=i > 0,
                tried=tried,
                text=_text_of(response),
            )
        finally:
            spend.settle(held, role, cost)
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


def tool_param(name: str, description: str, input_schema: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    """A tool as the API takes it: strict unless the registry says otherwise,
    its schema made acceptable either way; a loose tool keeps its maps."""
    return {"name": name, "description": description,
            "input_schema": strict_schema(input_schema, keep_maps=not strict), "strict": strict}


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
    family: str | None = None,
) -> Turn:
    """One model turn on one named model. Tools go out strict; the answer
    schema, when given, goes in `output_config.format`; `cache_control` is set
    at the top level. Raises ModelRefused (with what was spent) and
    ModelUnavailable as `call` does, and falls back nowhere.

    `tools` are `{"name", "description", "input_schema"}`, and `strict`
    when a tool is not; `tool_param` is applied here. A tool goes out strict
    unless its registry entry says otherwise: the API compiles one grammar
    for every strict tool in a request and refused eighteen as too large
    (OF-BLD-015 §7.2, 2026-10-19), so the module read tools go out loose and
    `tools.run` validates their input as it validates every tool's. `ask` stands in for
    the API in offline tests: it receives the request and returns a message.
    """
    if tool_choice not in TOOL_CHOICES:
        raise ValueError(f"tool_choice {tool_choice!r} is not sent: these models answer a forced tool with a 400")
    family = family_of(family or role)
    role = SPEND_ROLES[family]
    provider, model = spec(model)
    if provider not in SERVED:
        raise ModelUnavailable(waits(f"{provider}:{model}"), Usage())
    output_config: dict[str, Any] = {"effort": routes()[family].effort}
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
        request["tools"] = [tool_param(t["name"], t["description"], t["input_schema"], t.get("strict", True)) for t in tools]
        request["tool_choice"] = {"type": tool_choice}
    held = _reserve(model, request, max_tokens, Usage(), role)
    try:
        response = _converse_once(request, ask, model)
    except BaseException:
        spend.settle(held, role, 0.0)
        raise
    used = usage_of(response)
    spend.settle(held, role, used.costUsd)
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


def _converse_once(request: dict[str, Any], ask: Callable[[dict[str, Any]], Any] | None, model: str) -> Any:
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
    return response


# ── the literature layer's model client (ADR-002) ──────────────────────────


#: The kit's roles, as our families: its answers with citations explain, its
#: high-volume extraction (a document's graph, HyDE's passage) is an index
#: chore, and its judge judges.
KIT_ROLES = {"answer": "explain", "extraction": "index", "judge": "judge"}


def kit_client(kit_role: str = "answer") -> Any:
    """The model client Sci RAG Kit generates with, for one of its roles:
    answers with citations, HyDE's hypothetical passage, a document's graph.
    Every call goes through `call` here, so the kit's calls are capped by the
    day's spend, read the key in this one place, and fall back along the
    role's chain like any other. Built on demand: the kit is the `lit` extra."""
    import asyncio

    from sci_rag.llm.client import LLMClient

    family = KIT_ROLES[kit_role]

    class KitLLM(LLMClient):
        model = chain(family)[0]

        async def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
                           max_tokens: int = 2048, json_mode: bool = False) -> str:
            result = await asyncio.to_thread(
                call, system=system or "", user=prompt, schema=None, max_tokens=max_tokens,
                family=family, label="sci-rag-kit: ",
            )
            return result.text

        async def stream(self, prompt: str, *, system: str | None = None, temperature: float = 0.2,
                         max_tokens: int = 2048):  # type: ignore[override]
            yield await self.generate(prompt, system=system, temperature=temperature, max_tokens=max_tokens)

    return KitLLM()

