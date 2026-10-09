"""Practice — scenarios drafted from the bench, and a tutor that questions the
trainee's reasoning (OF-BLD-013 §4.1, §4.2).

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
    EvidenceSource,
    GuildEvidence,
    Practice,
    PracticeDeposition,
    PracticeDraftRequest,
    PracticeObservation,
    PracticeScenario,
    PracticeSession,
    PracticeSource,
    PracticeStepRef,
    PracticeTurn,
    PracticeTurnRequest,
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
                    # The operator's own words; the measure's name is for the
                    # model to read, and stays out of the evidence pane.
                    "text": e.raw,
                    "measure": e.label,
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


# ── the tutor (§4.2) ───────────────────────────────────────────────────
#
# A session is held here, turn by turn: the trainee's answer and the tutor's
# reply are kept together or not at all. A reply is refused, and the answer
# with it, when:
#
#   scenario    the scenario does not exist
#   session     the session does not exist, is another scenario's or another
#               person's, the person cannot hold skills, or another answer
#               reached it first
#   closed      the session has closed
#   answer      the trainee's answer is empty or too long to read
#   move        the tutor did not close when the last answer was in, or closed
#               without saying what it observed
#   quantity    the tutor wrote a number, as for drafts
#   unresolved  the tutor marked a [vN] past the evidence pane
#   steps       the tutor named a step that does not exist
#
# When a session closes for a person on Guild's ledger, guild.write_evidence
# records it as practice on their skill: no observer, and the session's id as
# its source, so an assessor can read every word of it.

MAX_ANSWERS = 3
MAX_ANSWER_CHARS = 2000
TURN_TOKENS = 4000

TUTOR_SYSTEM = """You are the tutor in openFerment's Primer. A trainee \
operator in a bioprocess lab is working through a practice scenario on one \
skill. You see the scenario, the evidence pane with the values the trainee \
sees, the points a sound answer would reach, the protocol steps involved, and \
the conversation so far, ending with the trainee's latest answer.

Your job is to make the trainee's reasoning visible, in short turns. Choose \
one move:
  why     ask them to explain the reason behind what they said
  change  change one condition in the situation and ask what follows
  next    ask what they would check or do next
  close   end the session
Write one or two sentences and ask one question. While the session is open, \
keep the answer to yourself: when the trainee is wrong, a question that \
exposes the gap teaches more than a correction.

When you close, write what you observed in `observed`: plain sentences an \
assessor can read, each naming the protocol steps it bears on, saying what \
the trainee reasoned soundly and what they missed or were unsure of. In the \
closing `text`, tell the trainee briefly what to look at again. There is no \
score and no pass or fail: describe what you saw.

NEVER WRITE A NUMBER. No digits, no number words (one, two, first, second, \
once, twice, half, double, dozen), no "twofold", no "an order of magnitude". \
Refer to an item of the evidence pane as [v1], [v2] and so on. The trainee may \
write numbers; you never repeat them. Identifiers with digits are fine: OD750, \
PR-OD-01, step c12. A reply with a number in it is discarded whole.

`steps` names the protocol steps your turn bears on, as "PROTOCOL:step"."""

TURN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "move": {"type": "string", "enum": ["why", "change", "next", "close"]},
        "text": {"type": "string", "description": "One or two sentences to the trainee. No number."},
        "steps": {"type": "array", "items": {"type": "string"}, "description": 'Steps as "PROTOCOL:step".'},
        "observed": {
            "type": "array",
            "description": "Only when closing: what you observed, for an assessor. Empty otherwise.",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "One plain sentence. No number."},
                    "steps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "steps"],
            },
        },
    },
    "required": ["move", "text", "steps", "observed"],
}


def scenario(scenario_id: str) -> PracticeScenario | None:
    return next((s for s in read().scenarios if s.id == scenario_id), None)


def session(session_id: str) -> PracticeSession | None:
    return next((s for s in read().sessions if s.id == session_id), None)


def _learner(person_id: str | None) -> None:
    if person_id is None:
        return
    p = next((x for x in guild.read().people if x.id == person_id), None)
    if p is None or not p.active or p.role == "auditor":
        raise PracticeRefused("session", f"{person_id!r} is not an active person on Guild's ledger who can hold skills")


def _tutor_payload(sc: PracticeScenario, held: PracticeSession, answer: str, last: bool) -> str:
    steps = []
    for ref in sc.steps:
        text = next(
            (st["text"] for p in _protocols() if p["protocolId"] == ref.protocolId for st in p["steps"] if st["stepId"] == ref.stepId),
            "",
        )
        steps.append({"ref": f"{ref.protocolId}:{ref.stepId}", "text": text})
    skill = guild.skills()[sc.skillId]
    payload = {
        "skill": {"id": sc.skillId, "name": skill["name"], "assessorWatchesFor": skill["mastery"]},
        "scenario": {
            "title": sc.title,
            "situation": sc.situation,
            "prompt": sc.prompt,
            "evidence": [
                {"marker": f"[{v.id}]", "label": v.label, "text": v.text, "value": v.value, "unit": v.unit} for v in sc.evidence
            ],
            "soundAnswerReaches": sc.watchFor,
            "steps": steps,
        },
        "conversation": [{"role": t.role, "text": t.text, **({"move": t.move} if t.move else {})} for t in held.turns],
        "latestAnswer": answer,
    }
    told = (
        "That was the trainee's last answer: close the session now."
        if last
        else "Choose your move. Close early only if the trainee has already shown their reasoning in full."
    )
    return told + "\n\n" + json.dumps(payload, ensure_ascii=False)


def validate_turn(
    raw: dict[str, Any] | None, sc: PracticeScenario, *, last: bool, usage: Usage
) -> tuple[PracticeTurn, list[PracticeObservation]]:
    if not isinstance(raw, dict):
        raise PracticeRefused("move", "the tutor returned no reply in the expected form", usage)
    move = raw.get("move")
    if move not in ("why", "change", "next", "close"):
        raise PracticeRefused("move", f"{move!r} is not a move the tutor makes", usage)
    if last and move != "close":
        raise PracticeRefused("move", "the trainee's last answer was in, and the tutor did not close", usage)
    text = str(raw.get("text") or "").strip()
    if not text:
        raise PracticeRefused("move", "the tutor's reply is empty", usage)
    n = len(sc.evidence)
    check_text("tutor's reply", text, n, usage)
    steps = check_steps([str(s) for s in raw.get("steps") or []], sc.skillId, usage, need_one=False)
    observed: list[PracticeObservation] = []
    if move == "close":
        for o in raw.get("observed") or []:
            said = str(o.get("text") or "").strip()
            if not said:
                continue
            check_text("tutor's observation", said, n, usage)
            observed.append(PracticeObservation(text=said, steps=check_steps([str(s) for s in o.get("steps") or []], sc.skillId, usage, need_one=False)))
        if not observed:
            raise PracticeRefused("move", "the tutor closed without saying what it observed", usage)
    return PracticeTurn(role="tutor", text=text, move=move, steps=steps, at=_now()), observed


def _record(held: PracticeSession, sc: PracticeScenario) -> str | None:
    """Practice on the learner's ledger, when there is a learner. The id of the
    entry, or None when there is none or the ledger refused it."""
    if held.personId is None:
        return None
    raw = f"Practice, “{sc.title}”. The tutor observed: " + " ".join(o.text for o in held.observed)
    entry = GuildEvidence(
        id=f"e-{_id('pt')[3:]}",
        personId=held.personId,
        skillId=held.skillId,
        kind="scenario",
        outcome="pass",
        at=held.closedAt[:10] if held.closedAt else _now()[:10],
        observerId=None,
        source=EvidenceSource(kind="scenario", ref=held.id),
        raw=raw,
    )
    try:
        return guild.write_evidence(entry).id
    except guild.GuildRefused as e:
        log.warning("practice: %s closed, and the ledger kept nothing (%s)", held.id, e)
        return None


def turn(request: PracticeTurnRequest, *, ask: Ask | None = None) -> PracticeSession:
    """The trainee's answer and the tutor's reply, kept together, or refused."""
    sc = scenario(request.scenarioId)
    if sc is None:
        raise PracticeRefused("scenario", f"{request.scenarioId!r} is not a practice scenario")
    answer = request.answer.strip()
    if len(answer) < 2:
        raise PracticeRefused("answer", "write an answer before the tutor can question it")
    if len(answer) > MAX_ANSWER_CHARS:
        raise PracticeRefused("answer", "the answer is too long to read in one turn; say it in fewer words")
    _learner(request.personId)
    if request.sessionId:
        held = session(request.sessionId)
        if held is None or held.scenarioId != sc.id:
            raise PracticeRefused("session", f"{request.sessionId!r} is not a session on this scenario")
        if held.personId != request.personId:
            raise PracticeRefused("session", "this session is someone else's")
        if held.closedAt:
            raise PracticeRefused("closed", f"{held.id} closed at {held.closedAt}")
    else:
        held = PracticeSession(id=_id("pt"), scenarioId=sc.id, skillId=sc.skillId, personId=request.personId, startedAt=_now())
    answered = sum(1 for t in held.turns if t.role == "trainee")
    last = answered + 1 >= MAX_ANSWERS
    result = _call(
        ask,
        system=TUTOR_SYSTEM,
        user=_tutor_payload(sc, held, answer, last),
        schema=TURN_SCHEMA,
        max_tokens=TURN_TOKENS,
        label="practice tutor: ",
    )
    reply, observed = validate_turn(result.data, sc, last=last, usage=result.usage)

    with _WRITE_LOCK:
        practice = read()
        stored = next((s for s in practice.sessions if s.id == held.id), None)
        if stored is not None and len(stored.turns) != len(held.turns):
            raise PracticeRefused("session", "another answer reached this session first; reload it", result.usage)
        held = held.model_copy(
            update={
                "turns": [*held.turns, PracticeTurn(role="trainee", text=answer, at=_now()), reply],
                "usage": llm.add(held.usage, result.usage),
            }
        )
        if reply.move == "close":
            held = held.model_copy(update={"observed": observed, "closedAt": _now()})
        practice.sessions = [s for s in practice.sessions if s.id != held.id] + [held]
        _persist(practice)

    if held.closedAt:
        evidence_id = _record(held, sc)
        if evidence_id:
            with _WRITE_LOCK:
                practice = read()
                held = held.model_copy(update={"evidenceId": evidence_id})
                practice.sessions = [held if s.id == held.id else s for s in practice.sessions]
                _persist(practice)
    log.info("practice: %s %s on %s, $%.4f", held.id, reply.move, sc.id, result.usage.costUsd)
    return held
