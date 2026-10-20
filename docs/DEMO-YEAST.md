# Demo readiness: yeast ethanol, 2026-10-20

The benchmark case is ethanol production by wild-type *Saccharomyces cerevisiae*
on glucose in batch. A bioprocess professor uses Postdoc hands-on. Every model
call ran on `claude-haiku-5-5` at effort `medium`. Every number below was
measured in this session on branch `claude/hopeful-shannon-j4kl1w`.

## 1. What was seeded

**Thread Q** (program three, `src/data/corpus/threadQ.ts`): 22 sources, written by
`pnpm thread:apply:q --approved-by "Sean Creighton"` after Sean approved the list
on 2026-10-20. All 22 were fetched with full text, and each licence was recorded
from its source.

| Ids | Source | Fetched from | Licence recorded |
|---|---|---|---|
| Q1 | Humbird et al. 2011, NREL/TP-5100-47764 (DOI 10.2172/1013269) | OSTI PDF, 147 pages, one section per page | osti.gov/biblio/1013269, the report's own availability line |
| Q2 | Tao et al. 2014, NREL/TP-5100-61563 (DOI 10.2172/1129271) | OSTI PDF, 43 pages | osti.gov/biblio/1129271, "available at no cost from NREL" |
| Q3, Q4 | SGD strain entries S288C (S000203483) and CEN.PK (S000203459) | yeastgenome.org JSON | CC BY 4.0, the page's own `rel="license"` link |
| Q5–Q22 | 18 open-access papers on *S. cerevisiae* kinetics and wild-type batch physiology | Europe PMC JATS | 15 CC BY (2.0 or 4.0), 1 CC BY-NC-ND (Q13), 2 stated in words (Q14, Q17) |

**Values in BioRepo.** `pnpm intake:extract` (Haiku) anchored **163** values on
thread Q and dropped **15**; each failed rule is counted in the candidate files.
Every value sits inside a verbatim sentence or table row of its source, carries
provenance `unverified`, and shows as "Extracted · unverified" until a named
reviewer decides it in Guild. By field: growth rate 53, ethanol titre 25, ethanol
yield on substrate 22, biomass yield on substrate 17, ethanol productivity 14,
medium component 10, Ks 8, final biomass 6, minimum ethanol selling price 5,
substrate-inhibition constant 2, Pmax 1. 25 of them resolve to the strain
CEN.PK113-7D. Cost: $0.19 for the current files, $0.25 including the first pass.

**New fields** (family "Growth and product kinetics"): `monod_ks`,
`biomass_yield_substrate`, `ethanol_yield_substrate`, `ethanol_titre`,
`ethanol_productivity`, `ethanol_inhibition_ki`, `ethanol_max_conc`,
`substrate_inhibition_ki`, `ethanol_lp_alpha`, `ethanol_lp_beta`, `ethanol_mesp`
(USD gal⁻¹). μmax uses the existing `growth_rate_mu`. Sean accepted the ranges
on 2026-10-20. Unit engine: grams per gram written with labelled grams
(`g EtOH/g glucose`, `gx/g`) and three spellings from these papers now normalise,
in both languages.

**Strains** (`src/data/strains.ts`): `s-cerevisiae-s288c` and
`s-cerevisiae-cenpk113-7d`, identity from the SGD strain pages, with aliases
that carry the designation (bare "CEN.PK" resolves to no strain).

**Genome-scale models on geneOS's shelf** (`pnpm geneos:fetch`, hash-pinned,
host S288C):

| Model | Source | Licence | Ethanol ceiling on glucose |
|---|---|---|---|
| Yeast9 | yeast-GEM v9.1.1, commit 2d594ae, sha256 30842b15… | CC BY 4.0 | 2.000 mol mol⁻¹, 0.5114 g g⁻¹ |
| iMM904 | BiGG static file (ETag 017c8684…), sha256 a4bcff4f… | BiGG terms: educational, research and non-profit use; accepted by Sean | 2.000 mol mol⁻¹, 0.5114 g g⁻¹ |

On xylose, Yeast9 gives 1.500 mol mol⁻¹ (its xylose reductase and xylitol
dehydrogenase use different cofactors), and iMM904 gives 1.667. iMM904's file
publishes oxygen uptake at 2 mmol gDW⁻¹ h⁻¹, so its growth frontier tops out at
0.288 h⁻¹; Yeast9's tops out at 0.839 h⁻¹.

**Proforma.** Postdoc's `selling_price` now cites the stored BioSTEAM benchmark
of the Humbird design (`biorefineries.cornstover` 2.35.1): 1.968 USD gal⁻¹,
provenance `computed`.

## 2. Postdoc, walked and fixed

A browser drove the real service on 127.0.0.1:8000. Found and fixed:

- **Conversation history.** Live answers lived in component state and vanished
  after following a citation, using the rail or reloading. Live conversations
  are now kept in the store and in the Durable tier (IndexedDB), listed in the
  sidebar, and resumed from Home's "Last conversation" card. A follow-up sends
  the earlier turns' questions and claims as words, and the model searches again
  before citing. Checked: two turns survive a citation round trip, the rail
  entry and a reload. "Which of those…" resolved against the earlier turn.
- **Scripted content.** The page opened in Scripted mode, with authored casein
  transcripts. It now opens in Live when the service answers with a key, and
  offers no Scripted mode while it does. With the service down after a reload,
  it stays in Live, keeps the history, and says "Postdoc service not running".
- **Dead or misleading controls.** "New conversation" now starts an empty
  conversation; a Stop button aborts a question; a question in the address
  (`?q=`) is asked once and leaves the address; the palette's "Ask the agent"
  works while on Postdoc; the Inspector and slash hints are hidden in Live,
  where they had nothing to show.
- **Crash containment.** A screen that throws while rendering now shows a
  message in place and leaves the rest of the app working.
- **False statements on screen.** Copy naming Opus as Postdoc's model, or
  saying no extractor had run, now matches what is true. The guided tour's
  BioRepo stop opened a paper that does not exist; it opens B5. The favicon 404
  is gone.
- **Claims dropped for numbers.** Haiku wrote conditions into claims ("at
  30 °C", "the NREL 2011 report"), and the validator dropped them whole, as
  designed. Postdoc's rules now say conditions, settings and dates are numbers,
  and the number rule reads "half-saturation", "first-order" and three other
  model names as names.
- **geneOS figure.** iMM904's flat sugar-mix line was stretched across
  floating-point noise into a zigzag; a spread under a millionth of the value
  now draws flat.
- **Mac Mini.** `deploy.sh` synced the `dev` extra alone, which removed cobra,
  BioSTEAM, scipy and fastembed; geneOS, fermOS fits, Proforma and hybrid
  search would have failed there. It now syncs every extra.

`pnpm verify`: 23 of 23 stages green on the final tree. No console errors on
Home, Postdoc, geneOS (ethanol view), the S288C and CEN.PK113-7D strain pages,
Intake, the reader (Q1, Q4, Q7), Proforma, BioRepo or Guild.

## 3. Five questions that answer well

Asked of the live service three times each over the seeded corpus. A question
takes 13–28 s and costs under half a cent.

1. **What is the theoretical maximum ethanol yield on glucose according to the
   Yeast9 and iMM904 genome-scale models, and how close do measured ethanol
   yields come to it?**
   3 of 3 runs: 5–6 claims kept, none dropped. Two computed ceilings (0.5114 g g⁻¹
   from each model), set beside measured yields from records: 0.47 (Q7,
   CEN.PK113-7D, anaerobic fed-batch), 0.451 (Q10), 0.44 (Q9), 0.22 (Q5, aerobic).
   Inline ceiling figures draw the ethanol yields beside the rule.
   Good follow-up: "Which of those measured yields were made on CEN.PK113-7D,
   and under what aeration?"
2. **How does CEN.PK113-7D differ from S288C, according to the Saccharomyces
   Genome Database?**
   3 of 3: 5–6 claims, nine quoted SGD sentences each: duplicated regions and
   maltose genes, >20,000 SNPs, biotin prototrophy against S288C's `bio1 bio6`
   genotype, origins and uses.
3. **What maximum specific growth rate does wild-type Saccharomyces cerevisiae
   CEN.PK113-7D reach on glucose, and what biomass and ethanol yields go with
   it?**
   2 of 3 runs strong (6–7 claims, none dropped), 1 weak (1 claim kept, 4
   dropped). μmax 0.29 h⁻¹, Yx/s 0.076, Yp/s 0.47 g g⁻¹ (Q7); Yx/s 0.093,
   Yp/s 0.43 (Q9); gaps name the missing aerobic batch value.
4. **What minimum ethanol selling price does the NREL corn stover design report
   by Humbird et al. state, and how does the BioSTEAM benchmark of that design
   compare?**
   3 of 3 after the last fix: 2–3 claims. The report's 2.15 USD gal⁻¹ (record
   from Q1) beside the computed benchmark, 1.968 USD gal⁻¹, and a gap asking for
   the cost-by-cost comparison. Name the report by its authors; with "2011" in
   the question, most claims drop.
5. **Which Monod saturation constants (Ks) and ethanol or substrate inhibition
   constants have been reported for Saccharomyces cerevisiae ethanol
   fermentation, and in which kinetic models?**
   3 of 3: 4–7 claims kept, 1–5 dropped and listed in the validator's box. Ks
   11.37 g L⁻¹ (Q12, Monod on molasses), 10.8 and 1.34 g L⁻¹ (Q5, AFY on glucose
   and on ethanol). Postdoc says no record gives an ethanol inhibition constant
   for a named strain.

The five are offered as buttons on Postdoc's empty Live page.

## 4. Avoid during the demo

- **A year in a question** ("the 2011 report"). Haiku echoes it and the claims
  drop. Name the authors.
- **"At what ethanol concentration does growth stop?"** 0–2 claims kept in three
  runs; long quotes and numbers dropped most of them.
- **Luedeking–Piret coefficients.** No α or β was extracted (Q5's β is
  negative and outside the accepted range), so Postdoc declines.
- **fermOS for Monod or inhibition kinetics.** fermOS fits only a deposition's
  own readings; it has no Monod or ethanol-inhibition model, and its "Load a
  sample run" is an invented, labelled sample.
- **The `s-cerevisiae` host page** (the S288C-derived catalogue host). It
  carries an invented nootkatone runbook. Use the S288C and CEN.PK113-7D pages.
- **Witness → Retrieval.** Its scorecard predates thread Q.
- **BioRepo → Search's paid lanes** (`bm25+expand`, `+rerank`). Haiku's helper
  calls were declined there before. The default lane works.
- **Intake's "Upload PDFs" and "Import by DOI list".** Disabled placeholders.
- **Proforma's PHA scenario, Guild's sample team, `docs/DEMO.md`.** All PHA or
  invented samples, labelled as such.
- **Framing the NREL reports.** The Humbird design co-ferments glucose and
  xylose with recombinant *Zymomonas mobilis*; Postdoc says so when asked.
- **Verification state.** All 163 thread Q values are unverified extractions. A
  reviewer can verify a few CEN.PK113-7D records in Guild beforehand. The two
  SGD entries carry no DOI or PMID, so Guild cannot keep decisions on them.
- **One model, no fallback.** With every role on Haiku, a classifier refusal
  declines the question; asking it again, reworded, is the remedy.

## 5. Run order on the Mac Mini

1. Merge the pull request into `main`.
2. Add to `core/.env` on the Mini (mode 600), then keep it there:
   ```
   OPENFERMENT_MODEL=claude-haiku-5-5
   OPENFERMENT_FALLBACK_MODEL=claude-haiku-5-5
   OPENFERMENT_INDEX_MODEL=claude-haiku-5-5
   OPENFERMENT_EFFORT=medium
   ```
3. `scripts/host/deploy.sh` (pulls main, installs every extra, builds, restarts).
4. `pnpm data:pull` (thread Q's values, the 7,179 passage vectors, the proposal
   files, from `openferment-data`).
5. `pnpm data:prepare` (fetches full text for thread Q here, since full text
   never travels; builds the passage index; checks the vectors; fetches Yeast9
   and iMM904). B1 and D1 still fail to fetch, as before.
6. `sudo launchctl kickstart -k system/com.umutuzo.openferment` (the service
   caches the corpus).
7. `pnpm ready`: expect lane `full`, roles `answer: claude-haiku-5-5; index:
   claude-haiku-5-5`, and Yeast9 and iMM904 present with matching hashes.
8. Rehearse the five questions once, then Settings → Reset demo data (or "New
   conversation") so the professor starts clean.
