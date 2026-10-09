"""Practice — scenarios drafted from the bench, and a tutor that questions the
trainee's reasoning (OF-BLD-013 §4).

The model drafts a short situation from the steps that need a skill, the
protocol's materials, and what was recorded at those steps in real runs. The
trainee reads it, looks at the evidence pane, and answers in their own words.

RULE 1, APPLIED TO TEACHING. No quantity a trainee reads comes from the
model. The model writes words and cites sources by the refs it was given;
every item of the evidence pane is copied here from the source it cites, so
its words, its number and its unit are the protocol's or the operator's. A
draft is refused whole, never repaired, when:

  shape       a field is empty, the evidence pane is empty or too long, a
              source is cited twice, or no protocol step is named
  quantity    any text the model wrote carries a number (validate.find_number:
              digits outside identifiers, number words, "twofold")
  unresolved  a cited ref is one it was not given, or a [vN] marker points
              past the evidence pane
  steps       a named step does not exist, or none of them needs the skill
  skill       the skill is not in src/data/skills.ts

core/data/practice.json keeps every scenario and every session, and never
enters git: a session holds a person's own words.
"""
from __future__ import annotations

import json
import logging
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from . import atomic, guild, intake, llm
from .models import (
    Practice,
    PracticeDeposition,
    PracticeDraftRequest,
    PracticeScenario,
    PracticeSource,
    PracticeStepRef,
    PracticeValue,
    Usage,
)
from .validate import find_number

log = logging.getLogger("openferment.practice")

PATH = intake.DATA_DIR / "practice.json"
_WRITE_LOCK = threading.Lock()

RULES = ("shape", "quantity", "unresolved", "steps", "skill", "scenario", "session", "closed", "answer", "move")

MAX_EVIDENCE = 6
MAX_DEPOSITIONS = 3
DRAFT_TOKENS = 8000

MARKER = re.compile(r"\[v(\d+)\]")


class PracticeRefused(ValueError):
    """What the model wrote was discarded, and `rule` says why."""

    def __init__(self, rule: str, why: str, usage: Usage | None = None):
        assert rule in RULES, rule
        super().__init__(f"{rule}: {why}")
        self.rule = rule
        self.why = why
        self.usage = usage or Usage()


class PracticeUnavailable(RuntimeError):
    """No answer could be had: no key, no network, every model unavailable, or
    every model declined. Distinct from an answer that was refused here."""

    def __init__(self, message: str, usage: Usage | None = None):
        super().__init__(message)
        self.usage = usage or Usage()


Ask = Callable[..., llm.Result]


# ── the file ───────────────────────────────────────────────────────────


def read() -> Practice:
    if not PATH.exists():
        return Practice()
    return Practice.model_validate_json(PATH.read_text(encoding="utf-8"))


def _persist(practice: Practice) -> None:
    atomic.write_text(PATH, practice.model_dump_json(indent=2, exclude_none=True) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _id(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000):x}-{secrets.token_hex(3)}"


# ── what a scenario may quote ──────────────────────────────────────────


def _protocols() -> list[dict[str, Any]]:
    return list(guild.projection().get("protocols", []))


def step_needs(protocol_id: str, step_id: str) -> list[str] | None:
    """The skills a projected step needs, or None when there is no such step."""
    for p in _protocols():
        if p["protocolId"] == protocol_id:
            for st in p["steps"]:
                if st["stepId"] == step_id:
                    return list(st["skills"])
    return None


def sources_for(skill_id: str, depositions: list[PracticeDeposition]) -> dict[str, dict[str, Any]]:
    """Everything the model may cite for this skill, keyed by the ref it cites
    it by: the steps that need the skill and their protocols' materials, then
    what was recorded at those steps in the newest runs shown."""
    out: dict[str, dict[str, Any]] = {}
    needing: dict[str, set[str]] = {}
    for p in _protocols():
        steps = [st for st in p["steps"] if skill_id in st["skills"]]
        if not steps:
            continue
        needing[p["protocolId"]] = {st["stepId"] for st in steps}
        for st in steps:
            out[f"step:{p['protocolId']}:{st['stepId']}"] = {
                "kind": "step",
                "protocolId": p["protocolId"],
                "stepId": st["stepId"],
                "text": st["text"],
                "note": st.get("note"),
            }
        for m in p["materials"]:
            out[f"material:{p['protocolId']}:{m['name']}"] = {
                "kind": "material",
                "protocolId": p["protocolId"],
                "material": m["name"],
                "text": m["name"],
                "value": m["amount"],
                "unit": m["unit"],
            }
    newest = sorted(depositions, key=lambda d: d.startedAt, reverse=True)
    shown = [d for d in newest if d.protocolId in needing][:MAX_DEPOSITIONS]
    for d in shown:
        steps = needing[d.protocolId]
        for e in d.entries:
            if e.stepId in steps:
                out[f"entry:{d.id}:{e.id}"] = {
                    "kind": "entry",
                    "protocolId": d.protocolId,
                    "depositionId": d.id,
                    "itemId": e.id,
                    "stepId": e.stepId,
                    "text": e.label or e.raw,
                    "operatorSaid": e.raw,
                    "value": e.value,
                    "unit": e.unit,
                    "at": e.at,
                }
        for o in d.observations:
            if o.stepId in steps:
                out[f"observation:{d.id}:{o.id}"] = {
                    "kind": "observation",
                    "protocolId": d.protocolId,
                    "depositionId": d.id,
                    "itemId": o.id,
                    "stepId": o.stepId,
                    "text": o.raw,
                    "at": o.at,
                }
    return out


def _value(index: int, label: str, src: dict[str, Any]) -> PracticeValue:
    """An evidence item, with everything but its label copied from the source."""
    return PracticeValue(
        id=f"v{index}",
        label=label.strip(),
        source=PracticeSource(
            kind=src["kind"],
            protocolId=src.get("protocolId"),
            stepId=src.get("stepId"),
            material=src.get("material"),
            depositionId=src.get("depositionId"),
            itemId=src.get("itemId"),
        ),
        text=src["text"],
        value=src.get("value"),
        unit=src.get("unit"),
        at=src.get("at"),
    )


def _step_ref(ref: str) -> PracticeStepRef | None:
    protocol_id, _, step_id = ref.partition(":")
    if not protocol_id or not step_id:
        return None
    return PracticeStepRef(protocolId=protocol_id, stepId=step_id)


def check_text(field: str, text: str, evidence: int, usage: Usage | None = None) -> None:
    """Rule 1 and the markers, for one piece of text the model wrote."""
    if hit := find_number(text):
        raise PracticeRefused("quantity", f"the {field} says {hit!r}; a value reaches the trainee through the evidence pane", usage)
    for m in MARKER.finditer(text):
        n = int(m.group(1))
        if n < 1 or n > evidence:
            raise PracticeRefused(
                "unresolved",
                f"the {field} marks [v{n}], and the evidence pane holds {evidence} item{'s' if evidence != 1 else ''}",
                usage,
            )


def check_steps(refs: list[str], skill_id: str, usage: Usage | None = None, *, need_one: bool = True) -> list[PracticeStepRef]:
    steps: list[PracticeStepRef] = []
    for ref in refs:
        step = _step_ref(ref)
        if step is None or step_needs(step.protocolId, step.stepId) is None:
            raise PracticeRefused("steps", f"{ref!r} is not a protocol step (PR-ID:stepId)", usage)
        if step not in steps:
            steps.append(step)
    if need_one and not any(skill_id in (step_needs(s.protocolId, s.stepId) or []) for s in steps):
        raise PracticeRefused("steps", f"none of the steps named needs {skill_id}", usage)
    return steps


def validate_draft(
    raw: dict[str, Any] | None,
    skill_id: str,
    sources: dict[str, dict[str, Any]],
    *,
    model: str,
    usage: Usage,
) -> PracticeScenario:
    """The model's draft as a scenario, or PracticeRefused. Nothing is repaired."""
    if not isinstance(raw, dict):
        raise PracticeRefused("shape", "the model returned no draft in the expected form", usage)
    title = str(raw.get("title") or "").strip()
    situation = str(raw.get("situation") or "").strip()
    prompt = str(raw.get("prompt") or "").strip()
    if not title or not situation or not prompt:
        raise PracticeRefused("shape", "a draft needs a title, a situation and a prompt", usage)
    cited = raw.get("evidence") or []
    if not cited:
        raise PracticeRefused("shape", "the evidence pane is empty; a scenario shows what it rests on", usage)
    if len(cited) > MAX_EVIDENCE:
        raise PracticeRefused("shape", f"the evidence pane holds more than {MAX_EVIDENCE} items", usage)
    refs = [str(c.get("ref") or "") for c in cited]
    if len(set(refs)) != len(refs):
        raise PracticeRefused("shape", "a source is cited twice in the evidence pane", usage)
    for ref in refs:
        if ref not in sources:
            raise PracticeRefused("unresolved", f"{ref!r} is not a source the model was given", usage)

    n = len(cited)
    watch = [str(w).strip() for w in raw.get("watchFor") or [] if str(w).strip()]
    check_text("title", title, n, usage)
    check_text("situation", situation, n, usage)
    check_text("prompt", prompt, n, usage)
    for c in cited:
        check_text("label of an evidence item", str(c.get("label") or ""), n, usage)
        if not str(c.get("label") or "").strip():
            raise PracticeRefused("shape", "every evidence item needs a label", usage)
    for w in watch:
        check_text("note for the tutor", w, n, usage)
    steps = check_steps([str(s) for s in raw.get("steps") or []], skill_id, usage)

    evidence = [_value(i + 1, str(c["label"]), sources[str(c["ref"])]) for i, c in enumerate(cited)]
    used = sorted({v.source.depositionId for v in evidence if v.source.depositionId})
    return PracticeScenario(
        id=_id("ps"),
        skillId=skill_id,
        title=title,
        situation=situation,
        prompt=prompt,
        watchFor=watch,
        evidence=evidence,
        steps=steps,
        depositionIds=used,
        model=model,
        usage=usage,
        createdAt=_now(),
    )


# ── drafting ───────────────────────────────────────────────────────────

DRAFT_SYSTEM = """You draft one practice scenario for a trainee operator in a \
bioprocess lab, in openFerment's Primer. The trainee is learning one skill. \
You are given the skill, what an assessor watches for, and sources: the \
protocol steps that need the skill (with the reason the protocol gives), the \
protocols' materials, and what operators recorded at those steps in real runs.

Build a short situation at the bench from those sources, at a moment where \
the reason behind a step decides what the operator should do next: a reading \
that looks wrong, a step about to be skipped, a choice between two actions. \
The trainee reads the situation, looks at the evidence pane, and answers your \
prompt in their own words. A tutor then questions their reasoning, so ask for \
a decision and its reason, in one question.

NEVER WRITE A NUMBER in the title, the situation, the prompt, a label or a \
note for the tutor. No digits, no number words (one, two, first, second, \
once, twice, half, double, dozen), no "twofold", no "an order of magnitude". \
Every value the trainee needs goes in the evidence pane: cite its source by \
its ref, exactly as given, and write [v1], [v2] and so on in the situation or \
the prompt where it belongs, numbered in the order of your evidence list. The \
interface shows the value from the source beside its label. Identifiers with \
digits are fine: OD750, PR-OD-01, step c12, cw15. A draft that contains a \
number, cites a ref you were not given, or marks a [vN] past the end of the \
evidence list is discarded whole.

When a real run's records are among the sources, prefer them: a situation \
built on what happened at this bench teaches more than one built on the \
protocol alone. Use only what the sources say; invent no reading and no event.

`steps` names the protocol steps the scenario is about, as "PROTOCOL:step" \
(for example "PR-OD-01:o4"), and at least one of them must need the skill. \
`watchFor` holds the points a sound answer would reach, for the tutor's eyes \
only. Keep the situation short enough to read standing at a bench."""

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "A few words naming the situation. No number."},
        "situation": {
            "type": "string",
            "description": "What is happening at the bench, with [vN] where an evidence item belongs. No number.",
        },
        "prompt": {"type": "string", "description": "The one question the trainee answers. No number."},
        "evidence": {
            "type": "array",
            "description": "The evidence pane, in order: [v1] is the first item.",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "A source ref, exactly as given."},
                    "label": {"type": "string", "description": "What this item is, in a few words. No number."},
                },
                "required": ["ref", "label"],
            },
        },
        "steps": {"type": "array", "items": {"type": "string"}, "description": 'Steps as "PROTOCOL:step".'},
        "watchFor": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Points a sound answer reaches, for the tutor. No number.",
        },
    },
    "required": ["title", "situation", "prompt", "evidence", "steps", "watchFor"],
}


def _skill(skill_id: str) -> dict[str, Any]:
    known = guild.skills()
    if skill_id not in known:
        raise PracticeRefused("skill", f"{skill_id!r} is not a skill in src/data/skills.ts")
    return known[skill_id]


def _call(ask: Ask | None, *, system: str, user: str, schema: dict[str, Any], max_tokens: int, label: str) -> llm.Result:
    # Resolved at call time, so a test that replaces llm.call reaches here.
    try:
        return (ask or llm.call)(system=system, user=user, schema=schema, max_tokens=max_tokens, label=label)
    except llm.ModelRefused as e:
        raise PracticeUnavailable(f"The request was {e}", e.usage) from e
    except llm.ModelUnavailable as e:
        raise PracticeUnavailable(str(e), e.usage) from e


def draft(request: PracticeDraftRequest, *, ask: Ask | None = None) -> PracticeScenario:
    """One call: a scenario for one skill, validated and kept, or refused."""
    skill = _skill(request.skillId)
    sources = sources_for(request.skillId, request.depositions)
    if not any(s["kind"] == "step" for s in sources.values()):
        raise PracticeRefused("steps", f"no protocol step needs {request.skillId} yet, so there is nothing to build on")
    payload = {
        "skill": {
            "id": request.skillId,
            "name": skill["name"],
            "summary": skill["summary"],
            "assessorWatchesFor": skill["mastery"],
        },
        "sources": [{"ref": ref, **{k: v for k, v in s.items() if v is not None}} for ref, s in sources.items()],
    }
    result = _call(
        ask,
        system=DRAFT_SYSTEM,
        user="Draft one practice scenario from these.\n\n" + json.dumps(payload, ensure_ascii=False),
        schema=DRAFT_SCHEMA,
        max_tokens=DRAFT_TOKENS,
        label="practice draft: ",
    )
    scenario = validate_draft(
        result.data,
        request.skillId,
        sources,
        model=result.model,
        usage=result.usage,
    )
    with _WRITE_LOCK:
        practice = read()
        practice.scenarios.append(scenario)
        _persist(practice)
    log.info(
        "practice: drafted %s for %s from %d source(s), $%.4f",
        scenario.id, scenario.skillId, len(scenario.evidence), scenario.usage.costUsd,
    )
    return scenario
