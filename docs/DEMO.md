# The demo: yeast ethanol, for Dr. Ramarao

One run sheet for showing openFerment on the yeast-ethanol program: wild-type *Saccharomyces
cerevisiae* making ethanol from glucose (thread Q, 22 sources, 163 extracted values). Casein and
PHA are archived and out of sight by default. The per-question figures below were measured on 2026-10-20 between
08:46 and 08:54 UTC on `claude-haiku-5-5` at effort medium, through the service's stream route over the merged tree,
with archived programs hidden and search on the hybrid lane. They predate §3.3 (examples hidden) and the §2.R and §3.R
fixes, which changed questions 6, 8 and 10 as their notes say.

**Use a device on your tailnet, with the Tailscale app connected.** The service refuses every question, search and
review that arrives through the public Funnel address (`guard.py`: nothing from the public internet may change
anything, because the app has no login). Pages load for anyone with the link; only a tailnet device can ask. Run the
meeting from your own laptop or phone with Tailscale on, and hand Ram that keyboard, never the link.

Pages are named as the app names them. The route in brackets goes after `#` in the address, for
example `https://seans-mac-mini-1.tail918752.ts.net/#/settings/programs`.

## 1. Start

### On the Mac Mini (about fifteen minutes)

1. If `MORNING` in `STATE.md` says green: GitHub → the pull request → **squash and merge** into `main`.
2. In Terminal, in the openferment folder:
   ```
   git status        # only core/data/biorepo.json may show (your Guild decisions; --keep-decisions commits them).
                     # Anything else: stop and tell Claude. Do not git stash: it would stash the decisions too.
   bash scripts/host/deploy.sh --keep-decisions
   pnpm data:pull
   pnpm data:prepare
   sudo launchctl kickstart -k system/com.umutuzo.openferment
   pnpm ready
   ```
   - `deploy.sh` pulls `main`, installs every Python extra, builds the app and restarts the service. It keeps your review decisions.
   - `data:pull` brings tonight's data from the `openferment-data` branch: thread Q's values, the written questions, the batch's plans.
     It keeps a local file that differs from the branch's and names it. If it names `core/data/rageval/report.json`, the
     Mini still has its old scorecard: run `rm core/data/rageval/report.json && pnpm data:pull` to take tonight's. Keep the
     Mini's own `core/data/index/` files (its vectors belong to its own index).
   - `data:prepare` fetches thread Q's full text on this machine (full text never travels), fetches Yeast9 and iMM904, and builds the passage index. It takes a while.
   - `launchctl kickstart` is macOS restarting the service, so it reads the new corpus. `pnpm ready` checks everything without spending.
3. **Ready looks like this:** the last line reads `lane: full`; the roles read `answer: claude-haiku-5-5; index: claude-haiku-5-5`;
   Yeast9 and iMM904 are present with matching hashes. A `huggingface` warning is fine. If a role is not
   Haiku, `core/.env` lacks these four lines. Add them (the file stays mode 600), then run `kickstart` and `pnpm ready` again:
   ```
   OPENFERMENT_MODEL=claude-haiku-5-5
   OPENFERMENT_FALLBACK_MODEL=claude-haiku-5-5
   OPENFERMENT_INDEX_MODEL=claude-haiku-5-5
   OPENFERMENT_EFFORT=medium
   ```
4. On the device you will use in the meeting, with Tailscale connected, open `https://seans-mac-mini-1.tail918752.ts.net/`.
   The reviewer name, the switch and the conversations are kept per browser, so check them in that browser.
   - Settings → Corpus & ontology (`/settings/corpus`): your reviewer name is set. The top bar shows it.
   - Settings → Programs (`/settings/programs`): Yeast ethanol active, Casein and PHA archived, the switch off.
   - BioRepo → Witness (`/biorepo/witness`), Retrieval: dated 2026-10-20 07:46 UTC, questions drawn from thread Q. If older, see Steer around.
   - Postdoc (`/postdoc`): ask question 1 below. If it answers, you are ready. Press **New conversation** so Ram starts on an empty page.

### Fallback: a laptop

In a checkout of `main` whose `core/.env` holds the key and the four lines above:
```
pnpm data:pull
pnpm data:prepare
pnpm prototype:up    # the service on 127.0.0.1:8000, the app on http://127.0.0.1:4173
pnpm ready           # in a second terminal: lane: full
```
Only the laptop can open it; share your screen.

Leave `pnpm demo:offline` closed. Ram sees the live app alone.

## 2. What to point at, on any answer

1. **The first trace line:** *Swept the modules for what the question names · searched eleven, found in one*. Click it:
   one line per module, with the ids it found and the modules read only in part. Code runs this sweep before the model's first turn.
2. **The read lines**, such as *Read Runbooks for "ethanol" · 0 rows* (question 8 tonight). Each opens to the exact input
   the tool was given. They are the same tools the MCP server offers Claude Desktop.
3. **The grey tags under each claim.** Each is a row a tool returned in this run, with the state the service computed.
   A claim citing a row no tool returned is dropped before it reaches the screen (tonight, in questions 6 and 7). Click a tag: it opens the module's page.
4. **The footer:** *Searched eleven, found in …*, then *read in part: Runbooks, fermOS, BioRepo*. That last part names
   what still lives only in the browser (depositions, decisions not yet posted).
5. **Claims carry no numbers.** The value beside a claim is read from the record, the computed card or the quoted sentence,
   never from the model's words. When a claim is dropped, the line says *Answered: 4 claims kept, 1 dropped*, and a yellow
   box under the answer lists each reason. Tonight's: a number word (*second*, *two*, *zero*, *thirteen*), a quote over 300
   characters, a quote that is not a whole sentence, a source no tool returned. That is Rule 1 working. Say so when it happens.

**The one point to make, once:** every number on every screen was written by a paper, a model file, a run or a named
person, and the model wrote the words.

## 3. The questions, in order

The eleven are buttons on Postdoc's empty page: the yeast five, then *Across the modules*. Each was asked twice (runs
**a** and **b**) and once by `pnpm ask:batch` (**batch**). Figures are claims kept/dropped, seconds, cost. All eleven
cost $0.0499 (a), $0.0574 (b) and $0.0316 (batch).

**1. What is the theoretical maximum ethanol yield on glucose according to the Yeast9 and iMM904 genome-scale models, and how close do measured ethanol yields come to it?**
- Reaches: geneOS (`yield_ceiling` twice, `geneos_read`), BioRepo records. Found in one.
- Tonight: a 5/0, 25.9 s, $0.0046 · b 2/0, 23.4 s, $0.0042 · batch 4/2, 31.8 s, $0.0034.
- Gist: both models give the same ceiling (the computed cards show 0.5114 g g⁻¹ each, as measured for PR #10); measured
  yields sit below it, the anaerobic CEN.PK113-7D ones close. Gaps: yields unverified, conditions unrecorded, no ratio computed.
- Reliable; two to five claims. geneOS → Model (`/geneos/model`) opens on ethanol and draws each model's ceiling. cobra,
  an open-source package, finds the most ethanol each published metabolic network can make from the sugar.

**2. How does CEN.PK113-7D differ from S288C, according to the Saccharomyces Genome Database?**
- Reaches: geneOS hosts, the two SGD entries' passages, BioRepo records. Found in one.
- Tonight: a 5/1, 18.8 s, $0.0031 · b 6/0, 20.2 s, $0.0051 · batch 6/2, 16.1 s, $0.0030.
- Gist: quoted SGD sentences. CEN.PK113-7D comes from ENY.WA-1A and MC996A, has duplicated regions rich in maltose genes
  and many SNPs and indels, and is a biotin prototroph where S288C is an auxotroph; S288C is non-flocculent, galactose-negative, with a mutated HAP1.
- Reliable.

**3. What maximum specific growth rate does wild-type Saccharomyces cerevisiae CEN.PK113-7D reach on glucose, and what biomass and ethanol yields go with it?**
**Hand Ram the keyboard here.** He can check this one against his own knowledge.
- Reaches: BioRepo records and passages, geneOS. Found in one.
- Tonight: a 4/1, 13.2 s, $0.0053 · b 4/1, 13.8 s, $0.0053 · batch 5/0, 15.8 s, $0.0033.
- Gist: μmax, biomass yield and ethanol yield of wild-type CEN.PK113-7D in anaerobic, very-high-gravity fed-batch culture (not batch), from the glycerol-formation
  study (Q7), each value read from its record (PR #10 recorded μmax 0.29 h⁻¹, Yx/s 0.076, Yp/s 0.47 g g⁻¹). Gaps: medium,
  temperature and glucose concentration not recorded; no aerobic value.
- Reliable. One claim usually drops for the word *second*.

**4. What minimum ethanol selling price does the NREL corn stover design report by Humbird et al. state, and how does the BioSTEAM benchmark of that design compare?**
- Reaches: Proforma's stored benchmark (`selling_price`), the report's record, its passages. Found in none.
- Tonight: a **0/3, declined**, 10.9 s, $0.0043 · b 3/0, 10.3 s, $0.0038 · batch 3/1, 16.7 s, $0.0027.
- Gist: the report's stated price (2.15 USD gal⁻¹ in PR #10's run) beside the benchmark, which is lower (1.968 USD gal⁻¹).
  BioSTEAM is an open-source Python package that simulates a whole plant and prices its product. Gap: no side-by-side of the two sets of assumptions.
- Sometimes drops every claim: run a lost all three for *2* and *zero* and said *Postdoc produced 3 claims, none of which
  passed validation*. If it declines, say that is Rule 1, and ask question 10.

**5. Which Monod saturation constants (Ks) and ethanol or substrate inhibition constants have been reported for Saccharomyces cerevisiae ethanol fermentation, and in which kinetic models?**
- Reaches: BioRepo records and passages. Found in none.
- Tonight: a 6/4, 29.2 s, $0.0069 · b 6/4, 24.3 s, $0.0068 · batch 4/4, 17.8 s, $0.0032.
- Gist: Ks on molasses (Monod against Andrews), on sugarcane-leaf hydrolysates, a Ks and a substrate inhibition constant
  from a sorghum extractive fermentation, AFY's Ks on ethanol; then: no record gives an ethanol inhibition constant for *S. cerevisiae*.
- Always answers, always drops several (long quotes, number words, a record that does not exist). The best one for the yellow box.

**6. What does openFerment hold on ethanol fermentation by Saccharomyces cerevisiae, and in which modules?**
- Reaches: BioRepo (`search_records`, `search_passages`, `biorepo_read`), geneOS (`geneos_read`; run b also `yield_ceiling`). Tonight's runs read **found in none**: the sweep did not recognise the species name. It does now (§2.R): on this data it finds geneOS, BioRepo and Intake. The question was not asked live again after that fix.
- Tonight: a 5/4, 16.1 s, $0.0035 · b 3/5, 19.7 s, $0.0064 · batch 7/1, 15.3 s, $0.0030.
- Gist: thread Q's extracted titres and yields in BioRepo (all unverified) and the two computed ceilings in geneOS;
  Runbooks, fermOS, Proforma and the rest hold nothing on it. Run a's own gap says the map found nothing while the reads returned rows.
- Answers every time; drops several (*1*, *zero*, sources no tool returned).

**7. Which hosts in geneOS could make ethanol, which models sit on their pages, and what ceiling does each give on glucose?**
- Reaches: geneOS (`geneos_read`, seven reads). Found in one.
- Tonight: a 3/3, 17.7 s, $0.0056 · b 7/0, 22.1 s, $0.0058 · batch 3/4, 16.1 s, $0.0028.
- Gist: only the S288C host page carries models, iMM904 and Yeast9, with the same ethanol ceiling on glucose; no host page
  claims ethanol; CEN.PK113-7D has no model of its own.
- Varies: drops for sources no tool returned and for *thirteen*.

**8. Draft a runbook for a batch ethanol fermentation in CEN.PK113-7D on glucose, using the extracted yield records and the Yeast9 glucose ceiling as a bound.**
- Reaches: BioRepo, geneOS (`yield_ceiling`), Runbooks, Dominion, `draft_runbook`. Found in two.
- Tonight: a 7/1, 52.8 s, $0.0103 (stopped at the twelve-call limit) · b 5/0, 44.1 s, $0.0090 · batch 4/0, 44.3 s, $0.0066.
- Gist: cites the Yeast9 ceiling and CEN.PK113-7D's yield records, and notes they are fed-batch, not batch.
  **In all three runs `draft_runbook` was refused: there is no product `ethanol` in Dominion's catalogue.** Nothing was drafted or proposed.
- The slowest question. Show the refusal line in the trace: the tool will not invent a product.
- Appendix 2's browser steps, **not walked tonight in a browser**, and out of reach while the draft is refused: **Turn into
  a runbook** under the answer → on its page **Lock predictions** (in the browser this locks at once; a lock proposal
  under the `lock` gate comes only when Postdoc proposes one) → Runbooks → Ledger (`/runbooks/ledger`) counts one.

**9. What is waiting for a person on Home right now?**
- Reaches: Home (`home_read`, three reads). Found in none.
- Tonight: a 2/1, 10.1 s, $0.0018 · b 3/0, 9.9 s, $0.0039 · batch 2/0, 8.0 s, $0.0017.
- Gist: the review queue, extraction candidates on Q1, Q10, Q11, Q12 and others, each awaiting a reviewer. Run b: no open
  checks, no proposals. With no draft from question 8, there is no lock card.
- Reliable and fast.

**10. What does Proforma need before it can price ethanol from glucose on this evidence, and what does the corn stover benchmark give?**
- Reaches: Proforma (`proforma_read`, `selling_price` twice). Found in one.
- Tonight: a 4/1, 11.7 s, $0.0017 · b 4/1, 17.2 s, $0.0042 · batch 2/2, 11.5 s, $0.0015.
- Gist: the corn stover benchmark is Proforma's only artifact, and it prices a cellulosic plant, not glucose; no ethanol
  scenario exists; one would need the sugar fed, a sugar price, and a titre, yield and productivity from a run.
- Reliable; drops a claim that cites nothing. Tonight's runs named the archived PHA draft scenario `sc-pha-1` through the price tool; with the switch off `selling_price` now refuses an archived scenario (§2.R, fixed after the runs and not asked live again).
- Since OF-BLD-019 (not asked again): Proforma now holds the yeast scenario `sc-yeast-1` on the glucose-to-ethanol
  flowsheet and the dry-grind corn reference plant, and `selling_price` reads any seed scenario's newest run; §6 says what
  binds and what still waits.

**11. What is archived in this corpus, and how would I see the PHA work?**
- Reaches: nothing but the sweep, which reads *found in none · found in archived program PHA (hidden)*.
- Tonight: a 0/0, 8.1 s, $0.0028 · b 0/0, 10.4 s, $0.0028 · batch 0/0, 4.8 s, $0.0005. Declined every time.
- Gist: a decline that names the switch, and a gap the code writes: *Settings → Programs has the switch that shows archived programs; turn it on to include them.*
- That decline is the right answer. Point at the first trace line; the footer does not carry the archived line.

## 4. Things to know before he asks

- **The archive switch.** Settings → Programs (`/settings/programs`), *Show archived programs and examples*, off. With it
  off, BioRepo lists 22 papers (thread Q) and says 167 in Casein and PHA are hidden; Hosts shows 13 strains; Molecules 116
  of 119; Protocols `PR-OD-01` and `PR-CIP-01`; Primer module m6; Proforma the yeast scenario `sc-yeast-1`, the two reference plants and the glucose-to-ethanol flowsheet (§6); Runbooks none (the ten seed
  runbooks describe runs nobody made, so they are examples, hidden with the archive), and the Ledger and Home's
  Predictions card count zero. A link to an archived page opens it under a
  banner naming the program. Postdoc sends the switch with every question. With it on, everything shows as before. Nothing was deleted.
- **Every extracted value is unverified until a person decides it in Guild** (`/guild`). Computed values (the ceilings,
  the benchmark) carry their basis instead. Haiku extracted the 163 thread Q
  values, each inside a verbatim sentence or table row of its source; they read *Extracted · unverified*. The two SGD
  entries carry no DOI or PMID, so Guild cannot keep decisions on them.
- **Name the Humbird report by its authors, never its year.** A year in a question makes claims drop. The Humbird design
  co-ferments glucose and xylose with recombinant *Zymomonas mobilis*, not yeast.
- **The retrieval scorecard** (BioRepo → Witness → Retrieval), rerun on thread Q at 07:46 UTC: 85 questions built from the
  163 anchored values (K) and 83 written questions kept of 100 (S); no flow touches thread Q, so F is empty. nDCG@10 (how
  high the right passage ranks in the top ten), mean of K and S: bm25 (word matching) 0.4226, bm25+expand 0.4294, hybrid
  (words plus meaning vectors) 0.4587, bm25+rerank (Haiku reorders the hits) 0.5942; hybrid+rerank was not scored, because
  the night's spend cap stopped it. The rule picks bm25+rerank, but a rerank search is a Haiku call of about 20 seconds,
  so for the meeting the app searches on **hybrid** (`core/data/index/config.json`). The card says so: *in use: hybrid
  (the rule chose bm25+rerank; search stays on hybrid until a person adopts it)*. To adopt it after the meeting, set
  `"lane": "bm25+rerank"` in `core/data/index/config.json` on the Mini and restart the service.
- **The coverage line matches names** (a strain id, a model, a paper, and since §2.R a species named in full or as
  *S. cerevisiae*). Questions 4, 5 and 9 read *found in none*; the reads that follow still find the rows.
- **Guild has no team** until a person is added. The empty ledger says *Add yourself below as the lead*.
- **fermOS has no deposited run.** It says *No run deposited yet* and names what to deposit through Runbooks → Depositions:
  sample times in hours, biomass at four or more times, product and substrate at the same times. It fits only a run's own readings.
- **Writes are marked as the model's.** Postdoc can keep a computed ceiling or add an unverified candidate. Anything at a
  gate (lock, sign, publish, a note, a check) becomes a card on Home that only a named person can carry out. `GET /api/audit` lists every write.
- **One model, no fallback.** Every role runs on Haiku. A classifier refusal declines the question; reword it and ask again.
- **No login.** Anyone with the Funnel address can load the pages; only a tailnet device can ask, search or decide. Accounts are OF-BLD-017's.

## 5. Steer around

Proforma has its own list at the end of §6.

Questions:
- Ram's own phone or laptop: it can load pages but not ask (see the top of this sheet). Use your tailnet device.
- Question 4, when it declines → ask question 10 instead.
- Question 8's browser steps (Turn into a runbook, Lock predictions, the Home card, the ledger): the draft was refused in all three runs. Do not promise a runbook.
- Question 11 → let the decline stand. To show PHA, flip the switch (`/settings/programs`) yourself, then flip it back.
- A year in any question ("the 2011 report") → claims drop. Name the authors.
- *At what ethanol concentration does growth stop?* → 0–2 claims kept in three runs (PR #10).
- Luedeking–Piret coefficients → none were extracted; Postdoc declines.
- PHB, *C. necator* or casein questions with the switch off → Postdoc says they are archived and hidden, and names the switch. Let that stand.

Screens:
- Settings → *Clear this browser's data*: do not press it. After one confirm it discards the conversations, decisions and locks kept in this browser.
- BioRepo → Search (`/biorepo/search`): leave the lane on its default; a rerank lane takes about 20 s a search.
- BioRepo → Witness → Retrieval (`/biorepo/witness`): skip it if it is dated before 2026-10-20.
- Hosts `gs115`, `ecoli`, `treesei` (`/geneos/hosts/gs115` and so on): their descriptions are written as casein comparators (gs115 names bovine β-casein).
- Use the strain pages `/geneos/hosts/s-cerevisiae-s288c` and `/geneos/hosts/s-cerevisiae-cenpk113-7d` rather than the species entry `/geneos/hosts/s-cerevisiae`, whose only runbook is an example.
- Runbooks → Protocols → `PR-OD-01` and `PR-CIP-01`, and Primer lesson l6-1: general methods, but their steps cite casein (thread M) records and values.
- Guild's team flows (`/guild/matrix`, `/guild/people`, `/guild/checks`, `/primer/path`, `/primer/practice`): since the sample team left, no browser test walks adding a person, a sign-off, a cosigned run, a check or practice. Do not add people or draft a Practice scenario live.
- Postdoc with the service down: do not ask from *New conversation* then; it can drop the oldest kept conversation.
- fermOS (`/fermos`, `/fermos/forecast`) for Monod or inhibition kinetics: it has no such model.
- The switch left on: Postdoc then reads casein and PHA too. Turn it off before the next question.

Seed content that describes runs nobody made is marked as examples (§3.3) and hidden with the archive: the ten seed
runbooks, the seven casein protocols, lessons m0–m5 and scenarios `sc-s1`…`sc-s3`. Postdoc's reads leave them out too
with the switch off (§4.R; tonight's runs predate this, and question 8's trace then named three of them). One trace remains:
- With the switch on, run mode opens from any example runbook. Do not start a run from one.

## 6. Proforma on BioSTEAM

Proforma (`/proforma`) prices a process that BioSTEAM, an open-source process simulator, runs: it builds the plant
unit by unit, balances every stream, sizes and costs the equipment, and solves the selling price with a
techno-economic analysis (TEA). Every number on these pages is read from a run the service kept, from thread Q
records, or from an assumption a named person typed. Measured 2026-10-20 at 18:08 UTC on the service of this
branch, over this checkout's data.

### The five things a person does

1. **New scenario.** Proforma → *New scenario* (or *New scenario from this* on the Glucose to ethanol card in the
   Flowsheets row) → pick the flowsheet, name it, keep the program (Yeast ethanol) → it opens on its page. It is kept
   in this browser and survives a reload. The seed's own yeast scenario is `sc-yeast-1` (`/proforma/scenario/sc-yeast-1`).
2. **Inputs.** The parameter panel says where each value comes from: *record ×N low–high* (thread Q, through the
   aggregate gate), *assumption by* a named person, *fitted* (a fermOS fit), *convention*, or *waiting*. On thread Q
   today three bind and three wait: feed glucose 4 records (20–100 g/L), titre 9 records (57–139 g/L), yield 18
   records (0.22–0.518 g/g); productivity waits (its 14 records name no carbon source), and so do plant scale and
   glucose price. Type each waiting value into its row under your reviewer name, with its low, its high and what it
   rests on below it; *Why* says what the input means and where its bounds come from, and *Reset to source* takes a
   value away. A value you type wins over the records too. A run with an assumption is marked *Modeled · not
   measured*. (OF-BLD-020 §2.2 replaced the old *Keep assumption* form with this panel; the counts above are
   2026-10-20's.)
3. **Run.** *Run the scenario* sends it to the warm BioSTEAM worker; the status line says cold, starting or ready.
   The first run after a restart takes about half a minute; a repeat of the same inputs returns the kept run at once.
4. **Read.** The price with its basis and its 5th to 95th percentile over the samples; the base case (or why it could
   not run); the cost breakdown from the TEA; the sensitivity (which input moves the price most); the stream table,
   the equipment with installed costs, the utilities, and the diagram (drawn where Graphviz is installed; otherwise the
   units in order). *Ceiling check* sets the yield beside the geneOS ceilings of the yeast models: today the high end of
   the yield records (0.518) sits above both stored *S. cerevisiae* ceilings (0.5114 g/g), so it is flagged, never
   clamped, and the record above is named. pureOS → Train (`/pureos/train/sc-yeast-1`) reads the same run unit by unit,
   with the product recovered at each, and a Properties card asks thermosteam for the beer's density and boiling point.
5. **Compare.** Pin two or more scenarios (the pin on each page) and open Compare (`/biorepo/compare`): price, cost
   lines and inputs side by side, each read from its own newest run; scenarios on different flowsheets are said to
   differ in basis.

### What the reference runs showed

- **Dry-grind corn to ethanol** (`/proforma/reference/corn_drygrind`), the yeast program's reference plant, built by the
  `biorefineries` package on its own defaults: run in 21 s cold. Ethanol 0.4855 USD/kg, the package's own set price
  (its TEA solves the internal rate of return at it: 5.38 %). All eleven values of the package's own test hold within
  its 5 % (*Held to its package's own test*). One compatibility line lets the package's fermenter take its two inlets on
  this BioSTEAM; it changes no number, and the page says so.
- **Corn stover to ethanol** (`/proforma/reference/cornstover_benchmark`), the NREL 2011 design: 1.9677 USD per gallon
  against the package's 1.968, unchanged. Nine of its eleven package-test values hold; installed equipment cost (−7.9 %)
  and electricity consumption (−5.2 %) miss, as the package's own test misses on these versions.

### The two questions (Postdoc)

- *What does the dry-grind corn ethanol reference plant give for its ethanol price, and what does the glucose-to-ethanol
  scenario still wait for?* — 2 and 4 claims kept in two runs; both name the three inputs that wait. Both say they could
  not tell whether the corn price is solved or set: it is set (see above).
- *What is the density and boiling point of the beer at the titre thread Q reports for CEN.PK113-7D?* — declined both
  times: thermosteam answered, and Haiku wrote the numbers into its claims, which Rule 1 drops. Show the Properties card
  on pureOS → Train or fermOS instead.

### Steer around (Proforma)

- The beer question above: show the Properties card, do not ask it.
- `sc-yeast-1` before anyone types the three waiting assumptions: *Run the scenario* stays disabled and says what waits.
- The corn stover page's two red rows: they are the package's own misses on these versions, not ours.
- The diagram on the cloud copy: it lists the units in order; it draws on the Mini once `brew install graphviz` is done.
- The archived PHA scenario (`sc-pha-1`) and the casein cost surfaces (S1–S3): hidden with the switch off; leave it off.


## 7. fermOS: simulate a batch and size its vessel

fermOS now simulates a culture and sizes the vessel it needs. The simulation runs on scipy, an open-source numerical
library: here it steps the growth equations forward in time, hour by hour. The vessel is BioSTEAM's: the same
open-source process simulator Proforma uses designs the fermenter, its agitation, its air and its cooling. Every
parameter shows in one panel with the source of its value. A value a person types is an assumption under their name,
and anything built on an assumption is marked *Modeled · not measured*. Measured 2026-10-21 at 05:16 UTC on this
branch's service, over this checkout's data (thread Q: 163 unverified candidates, no seed record).

### The four things a person does

1. **Simulate.** fermOS → Simulate (`/fermos/simulate`). Choose the family (*Batch*: Monod growth, product
   inhibition, Luedeking–Piret production), the strain (CEN.PK113-7D, or *Every strain of the program*), the product
   (ethanol), the sugar (glucose), and *Start from* records. The panel lists every parameter with its chip: *record ×N*,
   a *convention* the code states (kd, β and maintenance zero; Ki off; anaerobic), or *waiting*. **Simulate** stays
   off while anything waits, and says what.
2. **Type what waits.** Under your reviewer name, give each waiting value with what it rests on (the panel's value,
   low, high and note). Then **Simulate**. Read the time course (cells, sugar, ethanol, and oxygen uptake when the run
   is aerobic), the end-state card (final titre, yield achieved, productivity, the hour the sugar runs out), the ceiling
   card (the run's Yp/s beside the Yeast9 and iMM904 ceilings: flagged when above, never clamped), and every parameter
   with its source.
3. **Design the vessel.** The button opens fermOS → Vessel (`/fermos/vessel`) on that simulation. An anaerobic yeast
   batch gets NREL's batch fermenter; an aerobic run gets a stirred tank or a bubble column. Type a plant scale (tonnes
   of ethanol a year) under your name, then **Design**. Read the design table (vessels, volume, working volume, batch
   and cycle time, power, cooling duty, installed cost with BioSTEAM's cost index named), the oxygen balance (aerobic
   only: the transfer the vessel reaches against the culture's uptake, the short hours shaded) and the heat line.
4. **Send to Proforma.** A simulation's titre, yield and productivity can feed `sc-yeast-1`, as a fermOS fit does.

### What tonight's live run showed

- **What thread Q binds for a batch of CEN.PK113-7D on glucose:** μmax from 1 record, Yx/s from 3, Yp/s from 3, S₀
  from 4 (20–100 g L⁻¹). Ks, α, Pmax, X₀ and P₀ wait.
- **Over every strain:** Ks (1 record), Pmax (1) and Ki (2) also bind; α, X₀ and P₀ still wait. Thread Q holds no
  Luedeking–Piret α, and a run's starting cells and ethanol are a person's or a fit's.
- **So no simulation was kept tonight, and no vessel designed.** The session typed nothing: those values are Sean's
  (STATE §3.5 and §4.3).
- **Postdoc**, asked *Simulate a glucose batch for CEN.PK113-7D from the extracted kinetics and compare the predicted
  yield with the Yeast9 ceiling*, four times: each run called `fermos_simulate`, quoted its refusal (the five that
  wait), kept the Yeast9 ceiling as a claim and said in gaps that there is no simulated yield to compare. One to five
  claims kept; $0.0036–$0.0073 a run.
- **Asked to design a fermenter for that batch**, three times: `fermos_vessel` refused in words, since no simulation is
  kept. Zero or one claim; $0.0015–$0.0046.

### Steer around (fermOS)

- **Simulate before the waiting values are typed.** The button stays off and says what waits. Show the panel's chips,
  or type the values first.
- **The Postdoc simulate question.** It cannot simulate until a person types the values, and one run called α an
  "ethanol-lipid" parameter. α is Luedeking–Piret's growth-associated coefficient: say so if it comes up.
- **The Postdoc vessel question before a simulation is kept.** It refuses in words.
- **Price this in Proforma on the Vessel tab.** It says what night two adds (a vessel and a train priced together) and
  does nothing yet.
- **The storage family (PHA's shape).** It is hidden with the archive switch off. Leave the switch off.

---

This file folds `docs/DEMO-YEAST.md` and `docs/build/DEMO-PHASE7.md`, which are removed.
