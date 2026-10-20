// Questions offered on Postdoc's empty state (SUGGESTED_PROMPTS in flows.ts
// reads this list), and the first three on Home's first-visit band. Questions
// only: every answer comes from the service, over whatever the corpus holds
// when it is asked.
//
// The yeast five come first, in this order. Each was asked of the live service
// three times over the seeded corpus on 2026-10-20 (claude-haiku-5-5, effort
// medium) and answered from thread Q's records, passages and computed values
// each time; docs/DEMO-YEAST.md gives what came back. Most reliable first.
//
// Then the cross-module questions, numbered six to eleven in OF-BLD-016
// Appendix 2 and written exactly as it words them. They show Postdoc reading
// and writing across the modules (OF-BLD-015 Phase 7); OF-BLD-016 §4.1 asks
// each of them live and records what came back.
export const LIVE_PROMPTS: string[] = [
  'What is the theoretical maximum ethanol yield on glucose according to the Yeast9 and iMM904 genome-scale models, and how close do measured ethanol yields come to it?',
  'How does CEN.PK113-7D differ from S288C, according to the Saccharomyces Genome Database?',
  'What maximum specific growth rate does wild-type Saccharomyces cerevisiae CEN.PK113-7D reach on glucose, and what biomass and ethanol yields go with it?',
  'What minimum ethanol selling price does the NREL corn stover design report by Humbird et al. state, and how does the BioSTEAM benchmark of that design compare?',
  'Which Monod saturation constants (Ks) and ethanol or substrate inhibition constants have been reported for Saccharomyces cerevisiae ethanol fermentation, and in which kinetic models?',
  // ── cross-module (OF-BLD-016 Appendix 2, questions 6 to 11) ──────────
  'What does openFerment hold on ethanol fermentation by Saccharomyces cerevisiae, and in which modules?',
  'Which hosts in geneOS could make ethanol, which models sit on their pages, and what ceiling does each give on glucose?',
  'Draft a runbook for a batch ethanol fermentation in CEN.PK113-7D on glucose, using the extracted yield records and the Yeast9 glucose ceiling as a bound.',
  'What is waiting for a person on Home right now?',
  'What does Proforma need before it can price ethanol from glucose on this evidence, and what does the corn stover benchmark give?',
  'What is archived in this corpus, and how would I see the PHA work?',
];

/** How many of LIVE_PROMPTS are the yeast five; the rest are cross-module. */
export const YEAST_PROMPT_COUNT = 5;
