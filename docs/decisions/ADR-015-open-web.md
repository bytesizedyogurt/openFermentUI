# ADR-015 — Postdoc reads the open web through a tool of its own, and a page is unverified

- **Status**: accepted (the owner's request of 12 November 2026: "let it be connected to the
  internet and do things"; the owner may reverse it)
- **Date**: 2026-11-12

## Context

Until now Postdoc reached the internet in one way: `intake_write` fetch brings a document into the
project by its identifier (Europe PMC, OSTI, SGD). It could not find a document it did not already
know the identifier of, and it could not read anything else: a current price, a statistic, a
report. The owner asked for Postdoc to be connected to the internet.

Three constraints shaped the answer.

1. Anthropic's web search tool is a server tool: the API runs the searches inside a request and the
   model's words come back with citations. The API refuses citations beside an answer schema
   (`output_config.format`) with a 400, and Postdoc's planning turn carries one, so the tool
   cannot safely ride in the planning request.
2. A page's text is untrusted. In the planning conversation it would sit beside forty-eight tools
   that write to the project.
3. ADR-006: a record's value stands inside a verbatim quote of a document the project holds. A web
   page is held by nobody here.

## Decision

`web_search` is the forty-ninth tool of the registry (`tools/web.py`), a read, offered loose. One
call is one request of its own (`llm.web_search`): the query goes to the first Anthropic model of
the `index` route with the tool `web_search_20250305` and no answer schema, a paused turn is asked
to go on, and what returns to the tool is that model's report in its own words and the pages the
searches listed (address, title, age). The planning conversation reads the report and the pages'
ids, never a page's text.

A page is a `WebSource`, cited by its id (`web:<hash of its address>`) in a claim's `webIds`. The
validator holds it as it holds every citation (an id no search returned in this run drops the
claim), and a claim that cites a page is no stronger than `unverified`, whatever else it cites. A
number read off a report is the answering model's estimate: typed in the claim's values, labelled
with the model's id, and the claim `assumed` (ADR-006, unchanged). No store takes a value from a
page.

The way from a page to evidence is Intake, unchanged: when a search finds a paper or a report with
an identifier, Postdoc brings it in with `intake_write` fetch and quotes its sentences from there.

`OPENFERMENT_WEB_SEARCH` sets how many searches one call may make (3 unset, 8 at most, 0 off). A
call is reserved against the day's cap with its searches (0.01 USD each, as priced in November
2026) and what their results may weigh as input, and settled at what it cost, on the question that
asked. With `OPENFERMENT_FIXTURES` set (the offline suites and the proof) the tool refuses before
any call.

## Consequences

- Postdoc answers questions the project's corpus cannot, with the weakness shown: the answer says
  the claim is from the open web and unverified, and links each page.
- A search costs a model call on the index route (Haiku by default) and its searches.
- An Anthropic organisation can switch web search off in its Console; the call then answers 400,
  the tool refuses in words and Postdoc answers from the project.
- The tool was built with no key in the session (the account's usage limit, `docs/PROGRESS.md`
  Blockers): its request and response shapes follow Anthropic's documentation and are held by
  stand-ins in `core/tests/test_web_search.py`. The first live search is the test that counts.

## Revisit condition

- A live search shows a shape the stand-ins did not: fix `llm._web_pages` and the stand-ins.
- The owner wants pages themselves held (a web collector in Intake, a page's licence recorded),
  which would let a page's sentence be quoted as a document's is.
- A provider other than Anthropic serves the index route: the search needs a tool of that provider.
