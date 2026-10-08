"""The one place openFerment calls a Claude model (Postdoc, Extract).

    PRIMARY   claude-opus-5-5     every call starts here
    FALLBACK  claude-sonnet-5-5   when the primary declines or is unavailable

Override with OPENFERMENT_MODEL and OPENFERMENT_FALLBACK_MODEL in core/.env;
thinking depth with OPENFERMENT_EFFORT (low, medium, high; default medium).

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

What does not fall back: a rejected key, an unreachable network, or a request
the API calls malformed. Another model would fail the same way.

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

from .models import Usage

log = logging.getLogger("openferment.llm")

DEFAULT_PRIMARY = "claude-opus-5-5"
DEFAULT_FALLBACK = "claude-sonnet-5-5"
DEFAULT_EFFORT = "medium"


# Read when a call is made, so core/.env (which api.py and the batch commands
# load after this module is imported) is what decides.
def primary() -> str:
    return os.environ.get("OPENFERMENT_MODEL", "").strip() or DEFAULT_PRIMARY


def fallback() -> str:
    return os.environ.get("OPENFERMENT_FALLBACK_MODEL", "").strip() or DEFAULT_FALLBACK


def effort() -> str:
    return os.environ.get("OPENFERMENT_EFFORT", "").strip() or DEFAULT_EFFORT

# USD per million tokens, input and output, from the pricing page
# (platform.claude.com/docs/en/about-claude/pricing, read 2026-10-08). Kept
# here so the number a cost is computed from can be checked against its source.
# Output tokens include the model's thinking.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}

# JSON Schema keywords structured outputs does not accept. strict_schema moves
# them into the field's description, where the model still reads them, and
# the anchoring and range rules downstream enforce what matters anyway.
_UNSUPPORTED = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "multipleOf", "minLength", "maxLength", "maxItems", "pattern")


class ModelUnavailable(RuntimeError):
    """No answer could be had: the key, the network, or every model in the
    chain unavailable. Distinct from a refusal and from a bad answer."""


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


def chain() -> list[str]:
    """The models a call tries, in order, without repeats."""
    return list(dict.fromkeys(m for m in (primary(), fallback()) if m))


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost from token counts and the price on file. 0 for a model with no
    price on file, which `pnpm ready` reports."""
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    return round(input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out, 6)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def usage_of(response: Any) -> Usage:
    """Tokens and cost of one response, read from the response itself."""
    usage = _get(response, "usage")
    model = str(_get(response, "model") or primary())
    tin = int(_get(usage, "input_tokens", 0) or 0)
    tout = int(_get(usage, "output_tokens", 0) or 0)
    return Usage(inputTokens=tin, outputTokens=tout, costUsd=cost_usd(model, tin, tout), models=[model])


def add(a: Usage, b: Usage) -> Usage:
    return Usage(
        inputTokens=a.inputTokens + b.inputTokens,
        outputTokens=a.outputTokens + b.outputTokens,
        costUsd=round(a.costUsd + b.costUsd, 6),
        models=list(dict.fromkeys([*a.models, *b.models])),
    )


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
) -> Result:
    """One question, answered as JSON matching `schema`, by the first model in
    the chain that will. Raises ModelRefused or ModelUnavailable otherwise."""
    client = (client_factory or _default_client)()
    request = {
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort(), "format": {"type": "json_schema", "schema": strict_schema(schema)}},
    }
    models = chain()
    spent = Usage()
    tried: list[str] = []
    refusal: str | None = None
    refused_by: list[str] = []
    for i, model in enumerate(models):
        last = i == len(models) - 1
        tried.append(model)
        try:
            with client.messages.stream(model=model, **request) as stream:
                response = stream.get_final_message()
        except anthropic.AuthenticationError as e:
            raise ModelUnavailable("The Anthropic API rejected the key in core/.env.") from e
        except anthropic.APIConnectionError as e:
            raise ModelUnavailable(f"Could not reach the Anthropic API: {e}") from e
        except anthropic.BadRequestError as e:
            raise ModelUnavailable(f"The Anthropic API refused the request as malformed: {e.message}") from e
        except (anthropic.NotFoundError, anthropic.PermissionDeniedError) as e:
            why = f"{model} is not available to this key ({e.status_code})"
            if last:
                raise ModelUnavailable(why) from e
            log.warning("%s%s; trying %s", label, why, models[i + 1])
            continue
        except anthropic.APIStatusError as e:  # 429 after retries, 529, 5xx
            why = f"{model} answered {e.status_code}"
            if last:
                raise ModelUnavailable(f"{why}: {e.message}") from e
            log.warning("%s%s; trying %s", label, why, models[i + 1])
            continue

        used = usage_of(response)
        spent = add(spent, used)
        stop = _get(response, "stop_reason")
        if stop == "refusal":
            details = _get(response, "stop_details")
            refusal = _get(details, "category") or refusal
            refused_by.append(str(_get(response, "model") or model))
            if last:
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
