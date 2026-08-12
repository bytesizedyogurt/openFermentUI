"""Agent chat sessions, the activity feed, and background jobs.

Ported from `src/data/types.ts`. Three things in here are documented nowhere
else and so port with care: the `[[...]]` chip syntax inside a flow's answer
markdown, the `"flow:F2|label"` encoding of a followup, and the fact that a
job's progress is split between a stage index and a fraction within that stage.

Everything a `ChatFlow` produces is scripted rather than measured, which is why
`Provenance.DEMO` exists; the transcript models here describe the shape of that
scripted conversation, not evidence.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import Field

from ._base import OFModel
from .corpus import Provenance

__all__ = [
    "ActivityEvent",
    "AnswerMessage",
    "ChatFlow",
    "ChatMessage",
    "ChatRetrievalHit",
    "ChatSession",
    "ChatToolCall",
    "ClarifyMessage",
    "ClarifyOption",
    "ClarifyPrompt",
    "Job",
    "JobKind",
    "JobStage",
    "JobStatus",
    "PlanMessage",
    "SessionScope",
    "SystemMessage",
    "ToolMessage",
    "UserMessage",
]


class ChatRetrievalHit(OFModel):
    paper_id: str
    section_id: str
    score: float
    snippet: str


class ChatToolCall(OFModel):
    name: str
    args: dict[str, Any]
    duration_ms: float = Field(description="Milliseconds.")
    retrieval: list[ChatRetrievalHit] | None = None


class ClarifyOption(OFModel):
    """One branch a clarifying question can send the conversation down.

    Inline in the TypeScript — shared by `ChatFlow.clarify` and the `clarify`
    arm of `ChatMessage` — and named here because Pydantic has no anonymous
    model.
    """

    label: str
    flow_id: str


class ClarifyPrompt(OFModel):
    """The clarifying question a flow asks before it will answer.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    question: str
    options: list[ClarifyOption]


class ChatFlow(OFModel):
    id: str
    triggers: list[str]
    plan: list[str]
    tool_calls: list[ChatToolCall]
    answer_md: str = Field(description="chips as [[ex-0112]] / [[SP-004]]")
    followups: list[str] = Field(description='may be "flow:F2|label"')
    clarify: ClarifyPrompt | None = None


class UserMessage(OFModel):
    """The user arm of `ChatMessage`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["user"]
    id: str
    text: str


class PlanMessage(OFModel):
    """The plan arm of `ChatMessage`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["plan"]
    id: str
    steps: list[str]
    # A count of completed steps, not a measurement — int rather than float.
    done: int
    collapsed: bool


class ToolMessage(OFModel):
    """The tool arm of `ChatMessage`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["tool"]
    id: str
    call: ChatToolCall
    expanded: bool


class AnswerMessage(OFModel):
    """The answer arm of `ChatMessage`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["answer"]
    id: str
    md: str
    streaming: bool
    flow_id: str | None = None
    followups: list[str]


class ClarifyMessage(OFModel):
    """The clarify arm of `ChatMessage`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["clarify"]
    id: str
    question: str
    options: list[ClarifyOption]


class SystemMessage(OFModel):
    """The system arm of `ChatMessage`.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["system"]
    id: str
    text: str
    retry: bool | None = None


ChatMessage = Annotated[
    UserMessage | PlanMessage | ToolMessage | AnswerMessage | ClarifyMessage | SystemMessage,
    Field(discriminator="kind"),
]
"""One turn in an agent transcript, discriminated on `kind`."""


class SessionScope(OFModel):
    """What a chat session is scoped to — one paper, or a collection of them.

    Inline in the TypeScript; named here because Pydantic has no anonymous
    model.
    """

    kind: Literal["paper", "collection"]
    id: str
    label: str


class ChatSession(OFModel):
    id: str
    title: str
    started_at: str
    scope: SessionScope | None = None
    messages: list[ChatMessage]
    pinned: list[ChatRetrievalHit]


class ActivityEvent(OFModel):
    at: str
    icon: str
    text: str
    href: str | None = None
    provenance: Provenance


class JobStage(OFModel):
    label: str
    ms: float = Field(description="Milliseconds.")


class JobKind(StrEnum):
    INGEST = "ingest"
    EXTRACTION = "extraction"
    SIMULATION = "simulation"
    RUN = "run"


class JobStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Job(OFModel):
    id: str
    title: str
    kind: JobKind
    stages: list[JobStage]
    # An index into `stages` — int rather than float.
    stage_index: int
    stage_progress: float = Field(description="0-1 within current stage")
    status: JobStatus
    fail_reason: str | None = None
    href: str | None = None
    started_at: float = Field(description="Epoch milliseconds.")
