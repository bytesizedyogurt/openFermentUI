# Postdoc's conversations and the event stream

Postdoc keeps each question as a turn of a conversation under the project, and says what every
worker job, tool call, artifact and turn does as it happens (execution prompt §4.8, §7.3 item 2;
ADR-008). The code is `core/openferment_core/postdoc/conversations.py` (the store),
`core/openferment_core/events.py` (the stream) and `api.py` (`_answer`, the routes).

## The record

Three tables of the project (migration 0005 split the conversations the page kept whole):

| Table | A row is | Its body |
|---|---|---|
| `conversations` | One conversation | `{id, title, startedAt, by}`: its first question as its title (at most 120 characters), when it began, who began it |
| `turns` | One question, in its place (`seq`) in its conversation | `LiveTurn` (`models.py`, paired with `types.ts` by `check:plan`): the question, when it was asked, who asked, the loop's steps as they completed, the validated plan or the failure in words (`error`: message and remedy), the status, and `artifactIds`, the artifacts its tool calls produced and its plan cites |
| `tool_calls` | One tool call of a turn, in order | `ToolCallRecord`: the tool, its input, what it answered the model (`summary`, `error`) and what it offered to cite (`evidenceIds`, `recordIds`, `passageIds`, `artifactIds`), who asked and when |

A turn's status is one of:

| Status | Meaning |
|---|---|
| `running` | Being answered: the service began it and has not finished |
| `answered` | The loop ended with a plan. A declined plan is an answer |
| `failed` | The service failed while answering; `error` says how and what to do |
| `stopped` | The page stopped waiting; the turn keeps the steps it took until then |
| `interrupted` | Kept `running` with nobody answering it: the service that was answering it stopped, or a page wrote the turn and its ask never arrived. A read says `interrupted`; the row keeps what was written |

A conversation is never taken back (`project_state.remove` refuses it).

## How a question becomes a turn

`POST /api/ask` and `POST /api/ask/stream` take three more fields (`AskRequest`):

| Field | What it does |
|---|---|
| `conversationId` | The conversation the question belongs to. A follow-up's history is read from what the service keeps of it: each answered turn's question and its plan's words, oldest first. The request's own `history` is read only when no conversation is named |
| `turnId` | The turn the service keeps the question as. A turn is asked once: a second ask of a turn the project holds is declined in words. A turn the page wrote `running` before its ask arrived is taken over, in its place |
| `by` | Who asked; `this browser` when nobody said |

The service makes `lc-…` and `turn-…` ids when none are named. The plan carries both ids back
(`AnswerPlan.conversationId`, `turnId`), and the stream's first event, `turn`, names them before
the first step. An id the page makes holds letters, digits and `. _ : | -`, at most 200.

## A claim's values

A plan's claim states no number in its words; the numbers it states are its `values`
(`ClaimValue`, ADR-006): a label in words and a `Quantity` whose origin the validator wrote. A
value read from a computed value names its evidence id in `source` and carries origin `artifact`
(the evidence's artifact); one read from a record names the record and carries origin `record`;
the answering model's estimate carries origin `model-estimate` with the model's id, the moment
and what it rests on, and the claim stating it is `assumed`. A value's evidence or record is
cited by its claim. The browser's `ClaimValue` mirrors it (`check:plan`).

## The page's writes

The page keeps writing its Live conversations through `PUT /api/state/conversations/{id}`
(`lib/projectState.ts`), and those writes land on the same tables (`conversations.merge`). The
conversation is begun when the service lacks it. A turn the service lacks is kept as the page
wrote it: a question asked while the service was away, or one kept by a browser before alpha 2.0.
A turn the service holds stays as the service kept it, unless it is `running` and nobody is
answering it, when the page's record of how it ended stands. A turn moved to another
conversation is refused in words.

## The evaluation set

A project's questions for Postdoc are rows of `eval_questions`, each scored run a row of
`eval_runs` (migration 0006; `core/openferment_core/postdoc/evaluate.py`). `pnpm eval seed` keeps
the default questions in the project named by `OPENFERMENT_PROJECT`; `pnpm eval run` asks each
through the service's answer path, as turns of a conversation, offline with the evaluation's
stand-in model or with `--live` on the routing table's, and prints the runs and the mean of each
score as JSON:

| Score | What it is |
|---|---|
| `tools` | The share of the question's tool groups the trace reached (any one tool of a group) |
| `citations` | The share of the claims kept that cite what the question expects (evidence, records, passages, module rows) |
| `estimates` | 1 when a labelled estimate stands exactly where the question asks for one, every claim stating one `assumed` |
| `bareNumbers` | 1 when no claim was dropped for a number in its text; `droppedForNumbers` keeps the count |

## Routes

| Route | Answers |
|---|---|
| `GET /api/conversations` | The project's conversations, oldest first, each with its turns |
| `GET /api/conversations/{id}` | One conversation with its turns in order; 404 in words when the project holds none |
| `GET /api/conversations/{id}/turns/{turn}/calls` | The tool calls the turn made, in order; 404 in words when the conversation holds no such turn |
| `GET /api/events` | The project's event stream, below |

## The event stream

`GET /api/events` is a server-sent event stream of the request's project (the project header, or
`?project=` as every route takes it). An event is `{id, type, at, project, data}`:

| Type | Said when | `data` |
|---|---|---|
| `job.queued`, `job.running` | An engine run begins (`engine/runs.py`) | `{id, kind: "engine.run", plant, configuration, scenarioId, by}`, `id` the run's |
| `job.done` | The run is kept | the job, `status: "done"`, `provenance`, `artifactId`, `sffRecordId` |
| `job.failed` | The plant refused the values, or the run failed | the job, `status` `refused` or `failed`, `words` (the plant's own, for a refusal) |
| `artifact.kept` | A computed artifact is kept (`artifacts.compute`) | `{id, tool, toolVersion, provenance, durationMs}` |
| `turn.started` | A question is kept as a turn | `{conversationId, turnId, seq, question, by}` |
| `tool.call` | The loop calls a tool | `{conversationId, turnId, tool, input}` |
| `tool.result` | The tool answered, and the call is kept | `{conversationId, turnId, tool, ok, error, hits, evidenceIds, artifactIds}`, `hits` the records, passages, evidence and rows it returned |
| `turn.delta` | A step of the loop completes | `{conversationId, turnId, step}` (a `TraceStep`) |
| `turn.plan`, `turn.decline` | The validated plan, or the plan that declines | `{conversationId, turnId, plan}` |

A run answered from its row is no job and says nothing. Each event's `id` counts up in the
service's process. A page that names no event is sent what happens from when it opens the stream,
so a page opens the stream and then reads the record. `Last-Event-ID` (an EventSource sends it
when it reconnects) or `?after=` resumes after the event a page read last, from the newest 2000
events the process holds; an event said while the stream opens is sent once. A comment
(`: keepalive`) goes out after 15 s with nothing to say. A page that falls 1000 unread events
behind is closed, and reads the rest when it reconnects. The stream waits on the event loop and
holds no thread, so every page may keep one open. Events live in the process's memory: the tables
are the record, and nothing reads an event back after a restart.
