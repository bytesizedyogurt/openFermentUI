# H8-08 (with H14-03): the answer stream with no key says "generation failed (see server logs)" and names no key

**Statement.** With no key, `POST /api/literature/answer` ends in the event
`error {"code": "generation_failed", "message": "ModelUnavailable: generation failed (see server logs)"}`;
the words naming the missing key ("ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart
the service.") stay in the service log, and BioRepo Search shows the generic words with "The service log says
why."

**Contract.** `core/openferment_core/api.py:2146-2149`, the route's docstring, published as its description in
`docs/api/openapi.json:23239` and `src/api/types.gen.ts:1542`: "One model call through llm.py, under the day's
cap; with no key the stream says so in an `error`." The client's reader promises the same at
`src/lib/literature.ts:115-116`: "An `error` event throws IntakeDown with the service's words, a missing key
among them."

**Command.** From the repository root: `bash bughunt/repro/H8-08/run.sh`. It makes the database
`bh_r_h8_08_svc` fresh, starts the head's service keyless on 127.0.0.1:9510 (it stops before any model call if
`/api/health` says `hasKey` true), makes project `h808`, pastes one sentence, waits until search (no model)
finds it, reads the answer stream with `curl -N`, reads the service log's `answer_generation_failed` line,
asks `POST /api/intake/{id}/extract` for the same service's words on the same missing key, then opens BioRepo
Search in headless Chromium (`screen.mjs`), presses "Answer with citations" and reads the alert (screenshot in
`answer-nokey.png`). It stops the service and drops the database on exit. No request leaves the machine:
`llm._default_client` (`core/openferment_core/llm.py:715-720`) raises before a client is made.

**Expected.** The stream's `error` says there is no key, in the service's words as the extract route gives
them ("ANTHROPIC_API_KEY is not set ..."), and BioRepo Search shows those words.

**Observed (both runs, `run1.log`, `run2.log`).**

```
OBSERVED: GET /api/health hasKey False
OBSERVED: the stream's events, in order: retrieval_started retrieval_done compression_done generation_started error
OBSERVED: the stream's error: {"code": "generation_failed", "message": "ModelUnavailable: generation failed (see server logs)"}
OBSERVED: the service log: ... answer_generation_failed detail='ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service.' error=ModelUnavailable
OBSERVED: POST /api/intake/{id}/extract answers HTTP 503: {"detail":"ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and restart the service."}
OBSERVED: BioRepo Search shows: ModelUnavailable: generation failed (see server logs) The service log says why.
RESULT: DEFECT
```

The same generic words stand for every `ModelUnavailable` the kit's generator catches: the day's cap reached,
a rejected key, an unreachable API. The stream also carries four event kinds the route's 200 description
("Server-sent events: `delta`, `citations`, `done`, or `error`.", `api.py:2143-2144`) leaves out:
`retrieval_started`, `retrieval_done`, `compression_done`, `generation_started` (H14-03's second clause); the
client passes over them.

**Likely cause.** The kit's generator,
`core/.venv/lib/python3.13/site-packages/sci_rag/answer/generator.py:298-311`, catches any exception from
`llm.stream`, writes its words to the log (line 304) and sends the client
`f"{type(exc).__name__}: generation failed (see server logs)"` (line 309). openFerment's adapter
`core/openferment_core/literature/kit.py:833-838` passes the kit's `error` event on as it came (it drops the
`_` keys alone), and the route `api.py:2151-2155` sends it. llm.py's own words (`llm.py:717-719`) reach the
log alone. Confidence high. A small fix in openFerment: `kit.answer` (or `llm.kit_client`'s `stream`) keeps the
`ModelUnavailable` words of the call that failed and puts them in the `error` event's message, or refuses with
those words before the kit's stream starts when no key is held.

Severity S3: the no-key state is an edge case, the service log and Settings' key status are the workaround,
and the screen gives a person no way to tell a missing key from the day's cap or an unreachable API. Kind:
contract break.
