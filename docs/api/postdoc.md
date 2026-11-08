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
| `turns` | One question, in its place (`seq`) in its conversation | `LiveTurn` (`models.py`; the browser reads its generated twin in `src/lib/postdoc.ts`): the question, when it was asked, who asked, the loop's steps as they completed, the validated plan or the failure in words (`error`: message and remedy), the status, and `artifactIds`, the artifacts its tool calls produced and its plan cites |
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
cited by its claim. The browser reads it as the generated `ClaimValue` (`src/lib/postdoc.ts`).

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
| `estimates` | 1 when a labelled estimate stands where the question asks for one and none where it forbids one (a question may also leave it open), every claim stating one `assumed` |
| `bareNumbers` | 1 when no claim was dropped for a number in its text; `droppedForNumbers` keeps the count |

Two suites (alpha 2.1): `default`, the proof's two questions, and `ethanol`, the owner's twelve
real questions of `docs/reports/live-questions-2026-11.md` and the two the alpha 2.2 prompt's §5
adds for the base's seams, each with what a good answer does in words (`expects`):

| Question | What a good answer does |
|---|---|
| `eq-eth-13` Which engines are registered here, what does each take and give, and which of this project's runs came from each? | The engine reads (`engine_plants`, whose `engines` names every engine registered here with the ids of the project's runs it made; `engine_parameters`; then `engine_report`, which names a run's engine and tool, or a module read) set out as one table with a row for each engine registered here when the suite is seeded (the registry's names, `evaluate.engines_here`: the core's three, `biosteam`, `kinetics` and `train`, which `ENGINES_EXPECTED` holds, and any engine installed beside them), each run cited by its evidence id or module row; no estimate |
| `eq-eth-14` Take the ethanol yield measured in this project's most recent deposition, set it as the glucose-only scenario's yield, run it, and say what changed and what the value rests on. | Asked in question 5's conversation: the reading read with `runbooks_read` (kind `reading`), set as the scenario's value with the origin `{"kind": "measurement", "ref": "<the reading's id>"}`, run with `engine_run`, set beside the glucose-only run with `study_compare` and the comparison cited; the run's provenance `measured`, or `assumed` with the reason; where no deposition holds such a reading, said in words |

A question that follows another is asked in that one's conversation: question 4 ("that plant")
follows question 3, question 7 question 6, and questions 8 and 14 question 5, so a seed keeps each
follow as the code holds it.

`pnpm eval seed --suite ethanol` keeps the fourteen; `pnpm eval run --live --suite
ethanol --tag <name> [--judge]` asks them on the routing table the environment sets and keeps each
run under the tag. Beside the code's scores, a run keeps how its answer went (alpha 2.2 F.2a):

| Field | What it is |
|---|---|
| `seconds` | From the question asked to the answer kept, to the millisecond |
| `firstStepSeconds` | To the loop's first step, the code's module sweep (kind `coverage`), timed through the answer path's `on_step` |
| `firstModelSeconds` | To the loop's first step of another kind: the model's first, a tool it called, a restart or the answer; a tool's step lands when the tool returns, so the first tool's own time is in it (an engine run or a worker's cold start among it) |
| `stopped` | Why the loop stopped (`AnswerPlan.stopped`): `done`, `rounds`, `calls`, `cost` or `time` |
| `restarts` | Each restart step's words: a model declined or was unavailable, and the question was asked again on the next model of the route |
| `dropReasons` | The validator's reason for each thing it dropped (`AnswerPlan.rejectionReasons`), a gap or a decline dropped for a number among them |

A run kept before F.2a reads with the five fields after `seconds` empty (`null`, or an empty list),
and its judgements with `tried`, `route` and `refused` empty.

`--only <id,id>` asks the questions it names alone, under the run's tag, the rest left as they
stand: a follow-up among them whose question it leaves out is asked in the conversation of that
question's newest run under the tag, so a table stopped part way is finished where it stopped.
That conversation holds what a full asking of the suite has the follow-up read before it: the
question it follows, and each other follow-up of that question ahead of it (question 14 reads questions
5 and 8), less those the same command asks there first. A follow-up asked again alone would find
its own earlier asking there, and one asked ahead of a question a full asking puts before it would
miss that question; each is refused in words that name the questions to ask with it, so they are
asked again together in a new conversation, as is a follow-up whose question no model of the plan
route answered in its newest run there. A name the suite lacks, or a follow-up whose question has
no run under the tag, is refused in words too. Each refusal exits 2 before anything is asked.

`--judge` has the first model on the `judge` route read each answer as it is kept: the question,
what a good answer does, every claim with what it cites (the evidence's values, each record's
quote, each passage's words), the gaps and the tools called, and score it from 0 to 1:

| Judge's score | What it is |
|---|---|
| `answers` | How far the answer does what the question asks |
| `grounded` | The share of claims that what they cite bears out |
| `labelled` | Every value's origin said, every estimate labelled as the model's |
| `coverage` | How much of what a good answer covers this one covers |

A judgement may write 32,000 tokens, its thinking included (`evaluate.JUDGE_TOKENS`, the plan's own
turn ceiling, set by the measurement in ADR-008, Implementation 15); one that runs out of room is kept
with no score, its `declined` reading "The judge's answer did not arrive whole (it ran out of room)".

A judgement keeps the judge model's id, its faults in words and its cost, beside the code's scores,
with `tried`, the models the route asked in order (the last of them gave the judgement, named in
`model` by the id the API served; a refusal names each model that declined), `refused`, those of
them the safety classifier declined (`llm.Result.refused`), and `route`, the judge route's chain
when the answer was judged. A judgement Sonnet gave after Opus declined on the Opus-then-Sonnet
route reads `model` Sonnet, `tried` Opus then Sonnet and `refused` Opus; one Sonnet gave after Opus
gave no answer (a status such as 529 after the SDK's retries, a model the key cannot reach) reads
the same `tried` with `refused` empty, and the command's log line says why (`… answered 529;
trying …`). `pnpm eval judge --suite ethanol --tag <name> [--only <id,id>]` has the judge route as it
now stands read the newest kept answers again (those of the questions named, with `--only`) and
adds its judgement, so a second judge reads the same answers. It reads `core/.env` as `run` does,
through the service module's own loader (`api.py`; a setting the environment holds stands over the file's), so
the key, the routes and the budgets a judge's call reads are there.

A judge none of whose route's models answers (no key, the account's usage limit, the day's cap)
stops `run --judge` and `judge` in words with exit 1: the JSON names what was kept or judged before
the stop, `stopped` says where and why, with the commands that go on (`--only` with the questions
left), and `spentAtStopUsd` is what the judge route spent on the call it stopped at (a refusal
billed on the first model before the next met the stop; the words name it too, and the day's spend
table holds it; 0 on a command that ran to its end). The answer the run was to judge is kept
unjudged, and the run the pass was judging gains no judgement, so each judgement a pass keeps is
one a judge model gave. A run's stop words say to judge that answer and ask the rest. Where no
model of the plan route answered the question either (the limit most often lands on one of an
answer's plan calls first: the plan holds no claim, its final step reads `No answer: …` and its
decline is no refusal), the words say to ask that question again with the rest, beside the
questions a full asking asks in its conversation before it when it is a follow-up, so its
follow-ups read a conversation of the new asking. A judge that declines is kept as a judgement
with no score.

`pnpm eval summary --suite ethanol [--rows]` sets each tag's newest runs side by side, `{suite,
tags, judgesDisagree}`, each run counted once for each judge model, by that model's newest
judgement of it. Under `tags`, each tag:

| Key | What it holds |
|---|---|
| `questions`, `models` | The questions with a run under the tag, and every model that answered them |
| `code` | The mean of each of the code's four scores |
| `judges` | For each judge model: its mean of each judge score over the answers it scored, `answersJudged`, `declined` (the questions whose newest judgement it took part in holds no score of its own, for any reason: it declined, its route passed the answer on to a later model, or its answer did not arrive whole), `refused` (those of them the safety classifier declined on it, from each judgement's `refused`; a pass-over for a status or a model the key cannot reach stands in `declined` alone) and `costUsd`, what the judgements charged to it cost, every one kept (a judgement is charged to the model that gave it, or to the first its route tried when each model declined) |
| `judgeRoutes` | For each judge route, named by its models in order (`<a> then <b>`): its newest judgement of each run counted, `judgements`, `fellBack` (given by a later model of the route after the first passed the answer on, for any reason; `judges.<model>.refused` names the refusals) and `declined` (with no score). A judgement kept before F.2a names no route and is left out |
| `judgesDisagree` | For each two judge models, `judges`, the mean absolute difference between their newest judgements of each answer both scored, score by score, over `pairs` answers; `unpaired` counts the answers either took part in that lack a score from one of them, which the means leave out |
| `declined`, `restarts`, `restartCount` | The questions whose plan declined; each question's restart steps, by question; and the restarts counted by kind, as the loop writes them: `declined` ("<model> declined; asked again on <next>", a refusal) and `unavailable` ("<model> was unavailable; asked again on <next>", any other failure), with `other` beside them for a restart in other words |
| `claims` | `kept`, `dropped`, `droppedForNumbers`, and `dropReasons`, the validator's reasons counted by kind (a number in a claim's words, a number in a gap or the decline, a typed value, a quote, a row cited as evidence, a citation no tool returned, a claim citing nothing, an empty claim, other) |
| `toolCalls` | The mean and the median of the tool calls an answer made |
| `seconds` | The medians of `firstStep`, `firstModelStep` and `answer` |
| `stops` | The runs by why their loop stopped, each of the five reasons named |
| `cost` | `perQuestion`, the mean and the median of an answer's cost; `answersUsd`; `judgesUsd`, every judgement the runs hold; `totalUsd`, the two together. Each covers the tag's newest runs and the judgements they hold: a run an `--only` re-ask replaced stays in `eval_runs` beside the newer one, and a stop's `spentAtStopUsd` names what the call it stopped at spent; the day's spend table holds every call, both of those among them |

The top level's `judgesDisagree` pools every tag's answers. `--rows` adds `rows`: one row for each
tag's newest run of each question, with its models, the code's scores, tool calls, claims kept and
dropped, stop, restarts, decline, seconds to the first step, to the model's first step and to the
answer, cost, and for each judge model its four scores by its newest judgement of the run (each
`null` where it gave none, `declined` saying why: the judgement Sonnet gave reads "<sonnet> gave the
judgement after <opus> declined", or "… gave no answer" for a pass-over of another kind), its
verdict cut to 200 characters (`note`) and the cost of its judgements of the run.

## A key the request names

A request may name its own Anthropic key in the `X-OpenFerment-Key` header (owner question 10;
ADR-008, Implementation 10): every model call it makes, Postdoc's, extraction's and the kit's, runs
on that key in place of `core/.env`'s, and a request that names none runs on `core/.env`'s. The key
is never stored, logged or echoed; the project's audit table keeps a `key_override` row that says
an override was used. A request through Tailscale Funnel, or under a name the service does not
answer to, is refused with a 403 in words; an empty header with a 422.

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
| `job.queued`, `job.running` | An engine run begins (`engine/runs.py`) | `{id, kind: "engine.run", engine, plant, configuration, scenarioId, by}`, `id` the run's and `engine` the registered name of the engine that runs it (`biosteam` for a library run) |
| `job.done` | The run is kept | the job, `status: "done"`, `provenance`, `artifactId`, `sffRecordId` |
| `job.failed` | The engine refused the values, or the run failed | the job, `status` `refused` or `failed`, `words` (the engine's own, for a refusal) |
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
