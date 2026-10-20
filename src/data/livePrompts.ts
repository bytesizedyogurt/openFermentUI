// Questions offered on Postdoc's Live empty state, and the first three on
// Home's first-visit band. Questions only: every answer comes from the
// service, over whatever the corpus holds when it is asked.
//
// Each was asked of the live service three times over the seeded corpus on
// 2026-10-20 (claude-haiku-5-5, effort medium) and answered from thread Q's
// records, passages and computed values each time; docs/DEMO-YEAST.md gives
// what came back. Most reliable first.
//
// Each question names what it is about (OF-BLD-016 §2.2, E.1′): the strains
// and papers its answer stands on. A screen offers a question only when every
// one of them shows through the program selector (`useProgramFilter` in
// src/store.ts), so a question about an archived program leaves with the
// program and comes back with the switch. The subjects are ids, never a
// program name: which program an id belongs to is `programOf`'s to answer.

/** What an offered question is about: an entity `programOf` can place. */
export interface PromptSubject {
  kind: 'paper' | 'record' | 'strain' | 'product' | 'scenario' | 'protocol' | 'runbook';
  id: string;
}

/** The program selector's predicate, as `useProgramFilter()` returns it. */
export type SubjectShows = (kind: PromptSubject['kind'], id: string) => boolean;

/** Whether a question shows: every subject it names shows. A question naming none is general. */
export function subjectsShow(about: readonly PromptSubject[], shows: SubjectShows): boolean {
  return about.every((a) => shows(a.kind, a.id));
}

export interface OfferedPrompt {
  text: string;
  about: PromptSubject[];
}

export const LIVE_PROMPT_LIST: OfferedPrompt[] = [
  {
    text: 'What is the theoretical maximum ethanol yield on glucose according to the Yeast9 and iMM904 genome-scale models, and how close do measured ethanol yields come to it?',
    // Both reconstructions are of S288C (geneos_models.py).
    about: [{ kind: 'strain', id: 's-cerevisiae-s288c' }],
  },
  {
    text: 'How does CEN.PK113-7D differ from S288C, according to the Saccharomyces Genome Database?',
    about: [
      { kind: 'strain', id: 's-cerevisiae-cenpk113-7d' },
      { kind: 'strain', id: 's-cerevisiae-s288c' },
    ],
  },
  {
    text: 'What maximum specific growth rate does wild-type Saccharomyces cerevisiae CEN.PK113-7D reach on glucose, and what biomass and ethanol yields go with it?',
    about: [{ kind: 'strain', id: 's-cerevisiae-cenpk113-7d' }],
  },
  {
    text: 'What minimum ethanol selling price does the NREL corn stover design report by Humbird et al. state, and how does the BioSTEAM benchmark of that design compare?',
    // Q1 is the Humbird et al. design report (threadQ.ts).
    about: [{ kind: 'paper', id: 'Q1' }],
  },
  {
    text: 'Which Monod saturation constants (Ks) and ethanol or substrate inhibition constants have been reported for Saccharomyces cerevisiae ethanol fermentation, and in which kinetic models?',
    // Q6 and Q12 are the two thread Q papers whose titles name a kinetic model.
    about: [
      { kind: 'paper', id: 'Q6' },
      { kind: 'paper', id: 'Q12' },
    ],
  },
];

/** Every live question, in order, whatever its program. */
export const LIVE_PROMPTS: string[] = LIVE_PROMPT_LIST.map((p) => p.text);

/** The live questions a screen offers: those whose subjects all show, in order. */
export function livePrompts(shows: SubjectShows): string[] {
  return LIVE_PROMPT_LIST.filter((p) => subjectsShow(p.about, shows)).map((p) => p.text);
}
