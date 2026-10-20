// Questions offered on Postdoc's Live empty state, and the first three on
// Home's first-visit band. Questions only: every answer comes from the
// service, over whatever the corpus holds when it is asked.
//
// Each was asked of the live service three times over the seeded corpus on
// 2026-10-20 (claude-haiku-5-5, effort medium) and answered from thread Q's
// records, passages and computed values each time; docs/DEMO-YEAST.md gives
// what came back. Most reliable first.
export const LIVE_PROMPTS: string[] = [
  'What is the theoretical maximum ethanol yield on glucose according to the Yeast9 and iMM904 genome-scale models, and how close do measured ethanol yields come to it?',
  'How does CEN.PK113-7D differ from S288C, according to the Saccharomyces Genome Database?',
  'What maximum specific growth rate does wild-type Saccharomyces cerevisiae CEN.PK113-7D reach on glucose, and what biomass and ethanol yields go with it?',
  'What minimum ethanol selling price does the NREL corn stover design report by Humbird et al. state, and how does the BioSTEAM benchmark of that design compare?',
  'Which Monod saturation constants (Ks) and ethanol or substrate inhibition constants have been reported for Saccharomyces cerevisiae ethanol fermentation, and in which kinetic models?',
];
