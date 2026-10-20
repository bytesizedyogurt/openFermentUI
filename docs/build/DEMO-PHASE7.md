# Postdoc across the modules — the run sheet

For showing OF-BLD-015 Phase 7 (§7.1 and §7.2) live: Postdoc reaching every
module from one question. Committed for the length of the build, like the
rest of `docs/build/`; the closing truth pass deletes it. Every question below
was run on 2026-10-20 on `claude-haiku-5-5` at effort medium, through the
built app, and the numbers are from those runs.

## Start

```
pnpm prototype:up        # the service on :8000, the app on http://127.0.0.1:4173
```

Needs `core/.env` with a key the Models API accepts; `pnpm ready` ends with
`lane: full`. Open **Postdoc**, press **Live (Postdoc service)** at the bottom
right of the chat, and type. One answer costs under a cent and takes 10 to
30 seconds.

If the service is down on the day, `pnpm demo:offline` replays a recorded run
and says it is a replay; it shows the trace and the coverage line, with a
scripted stand-in in place of the model.

## What to point at, on any answer

1. **The first trace line** — *Swept the modules for what the question names ·
   searched eleven, found in two*. Click it: one line a module, with the ids
   it found and which modules were read in part. This is code, run before the
   model's first turn; the model can no longer say "not in the corpus" about
   something a screen shows.
2. **The read lines** — *Read Dominion for molecule · open · 55 rows*. Each
   opens to the exact input the tool was given. The eleven read tools are the
   same ones the MCP server offers Claude Desktop.
3. **The grey tags under each claim** — `dominion Brazzein · fenced`,
   `runbooks Brazzein — pilot process · locked`. Each is a row a tool returned
   in this run, with the state the service computed. A claim citing a row no
   tool returned is dropped before it reaches the screen. Click one: it opens
   the module's page.
4. **The footer** — *Searched eleven, found in two: Dominion (1), Runbooks
   (1) · read in part: Runbooks, fermOS, BioRepo*. The last part names
   what still lives only in the browser (depositions, unposted decisions).
5. **Claims carry no numbers.** When one is dropped, *Answered: 4 claims
   kept, 1 dropped* says so, and the reason is in the Inspector. That is Rule 1
   working, and worth saying out loud if it happens.

## The questions, in a good order

| # | Type this | Modules it reaches | What it showed on 2026-10-20 |
|---|---|---|---|
| 1 | **What is open in Dominion and which runbooks touch it?** | Dominion, Runbooks | The question that failed on 2026-10-16. Now: 55 open molecules read, the ten runbooks read, 5 claims pairing open molecules with the runbooks that name them (thermostable ligase, malaria antigens) and noting the fenced ones (Taq, LNFP-I). $0.005, 19 s. |
| 2 | **Is brazzein open to make, what did its runbook lock, and which host does it run on?** | Dominion, Runbooks, geneOS | Three reads by id, 4 claims, 0 dropped: fenced (core free, variants fenced); the pilot runbook locked with four predictions; GS115 in geneOS. $0.0035, 14 s. The screenshot `docs/shots/of-bld-015-postdoc-brazzein.png` is this one. |
| 3 | **Which hosts in geneOS could make PHB, and what yield ceiling has been computed for Cupriavidus necator H16 on glucose?** | geneOS, `yield_ceiling`, Dominion | Reads the hosts (H16 carries the PHB badge; KT2440 is mcl-PHA), runs the ceiling, and reports the finding in words: the stored ceiling on that model is on fructose, and the model has no glucose uptake. $0.0045, 20 s. |
| 4 | **What PHB titres have been reported on xylose hydrolysate, and which of those papers has Intake fetched with full text?** | BioRepo records and passages, Intake, Dominion | Records cited by id with their values rendered from the record; Intake rows for P6, P19, P20, P27 with full text. $0.005, 20 s. One claim dropped for a typed number on one run. |
| 5 | **What does the Proforma scenario for PHA from cellulosic sugar still wait for, and what does the benchmark run give?** | Proforma, `selling_price` | `selling_price` refuses in words (no run of sc-pha-1; names the inputs waiting for a source) and Postdoc reports that as a gap; the benchmark artifact row carries its headline values. $0.003, 8 s. |
| 6 | **Which downstream unit operations does Taq DNA polymerase need, and what does pureOS say about the centrifugation step?** | Dominion, pureOS, Runbooks | The molecule row hands pureOS its unit-operation ids; 7 claims, 0 dropped, including that centrifugation is not in Taq's train and why thermal clarification is. $0.004, 14 s. |
| 7 | **What is waiting for a person on Home right now, and which Primer lesson teaches measuring dry cell weight?** | Home, Primer | The review queue (candidates awaiting a person; nothing on this machine for a check) and the lesson found by its words, *OD750 and dry cell weight*. $0.003, 9 s. |
| 8 | **Draft a runbook for PHB in Cupriavidus necator H16 on fructose: use the PHB content records on that strain and the fructose ceiling on its model as a bound.** | BioRepo, geneOS, `yield_ceiling`, Dominion, Runbooks, `draft_runbook` | The one that does work: a draft runbook appears under the answer with its predictions written by the service, the ceiling as a bound; **Turn into a runbook** opens it, **Lock predictions** locks it, Runbooks → Ledger counts it. 7 claims, 0 dropped. $0.006, 23 s. The first `draft_runbook` call was refused (a measure's unit did not match) and the model corrected it; both lines show in the trace. |

Question 8 asks for fructose because that is the feed the stored H16 ceiling
is on, and the strain's content records are on waste oils: asked for xylose,
Haiku searches everything and then says, correctly, that no xylose record for
H16 exists, and drafts nothing. That is also a fair thing to show.

## Things to know before he asks

- **Guild is empty on a machine with no `guild.json`**; `guild_read` returns
  nothing. On the Mini it reads the ledger (name, role, active) and the open
  checks, and nothing else.
- **fermOS reads only the fits and forecasts the service computed**;
  depositions stay in the browser, and the footer says so.
- **The sidebar sessions are seed stand-ins** (OF-BLD-017 §5.1 replaces
  them). Live answers vanish on reload until then.
- **Haiku still types a count now and then** ("the first", "2 rows") and the
  validator drops that claim whole; the prompt tells it not to, and across
  the eight questions it happened once in the second run.
- **The read tools go out non-strict** to the model: the API refuses a
  request with eighteen strict tools as too large. Their inputs are validated
  by the registry the same way, before anything runs.
- **Writes** (§7.3) and **gates with Home cards** (§7.4) are the next steps;
  Postdoc reads every module today and writes nothing but a runbook draft.
