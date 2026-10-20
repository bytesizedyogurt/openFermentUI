// Programs (OF-BLD-016 §2.1, E.1′, D7).
//
// A program is data: the corpus threads that are its papers, a name, and
// whether it is active or archived. Three are declared. Casein (threads A to
// O) and PHA (thread P) are archived: their papers, records, strains,
// products, scenarios, protocols, runbooks and lessons stay in the repository
// and leave every default view, and Settings → Programs shows them again
// (D1: archive, never delete). Yeast ethanol (thread Q) is active.
//
// Which program an entity belongs to is answered by `programOf` in
// src/store.ts: a paper by its thread letter, a record by the paper it cites,
// a strain, product, scenario, protocol, module or lesson by its own
// `program` field, a runbook by its own field or else by the product or strain
// it names. An entity with no program is general and always shows.
//
// `check:seed` holds the letters: every thread a paper carries has exactly
// one program, every program has a letter, and the `[A-Q]` thread-letter
// patterns written in papers.ts, src/sim/chat.ts and scripts/golden-path.mjs
// span exactly the letters declared here. A new thread changes this file
// first, and check:seed names every pattern that has not followed.
//
// `pnpm export:corpus` writes PROGRAMS into corpus.json and modules.json, so
// the service reads the same three (core/openferment_core/programs.py).
import type { CorpusThread, Program, ProgramId } from './types';

export const PROGRAMS: Program[] = [
  {
    id: 'yeast',
    name: 'Yeast ethanol',
    letters: ['Q'],
    status: 'active',
    summary:
      'Ethanol from glucose by wild-type Saccharomyces cerevisiae: the S288C and CEN.PK113-7D strains, their genome-scale models, and the kinetics papers of thread Q.',
  },
  {
    id: 'casein',
    name: 'Casein',
    letters: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O'],
    status: 'archived',
    summary:
      'Bovine β-casein in the cell-wall-deficient alga Chlamydomonas reinhardtii cw15, with the precision-fermentation dairy comparators of threads A to O.',
  },
  {
    id: 'pha',
    name: 'PHA',
    letters: ['P'],
    status: 'archived',
    summary:
      'Polyhydroxyalkanoates from waste cellulosic sugars in Cupriavidus necator H16 and Pseudomonas putida KT2440.',
  },
];

export const PROGRAM_BY_ID: Record<ProgramId, Program> = Object.fromEntries(
  PROGRAMS.map((p) => [p.id, p]),
) as Record<ProgramId, Program>;

/** Where the switch lives: Settings → Programs (OF-BLD-016 §2.2 builds the section). */
export const PROGRAMS_SETTINGS_PATH = '/settings/programs';

/** Thread letter → program id, built once from PROGRAMS. */
const BY_LETTER: Map<string, ProgramId> = new Map(
  PROGRAMS.flatMap((p) => p.letters.map((l) => [l, p.id] as [string, ProgramId])),
);

/** Every thread letter a program declares, in alphabetical order. */
export const THREAD_LETTERS: CorpusThread[] = [...BY_LETTER.keys()].sort() as CorpusThread[];

/**
 * The character class the thread-letter patterns write, `[A-Q]` today: the
 * first letter to the last. `check:seed` fails when the declared letters do
 * not run without a gap, because then no single class names them.
 */
export const THREAD_LETTER_CLASS = `[${THREAD_LETTERS[0]}-${THREAD_LETTERS[THREAD_LETTERS.length - 1]}]`;

/** The program a thread letter belongs to, or null for a letter no program declares. */
export function programOfLetter(letter: string): ProgramId | null {
  return BY_LETTER.get(letter) ?? null;
}

/**
 * The program of a paper, by its id's thread letter ('P12' → 'pha'). A paper
 * id is its thread letter and an index (OF-COR-001 §1); an id that is not
 * one resolves to null.
 */
export function programOfPaperId(paperId: string): ProgramId | null {
  const m = /^([A-Z])\d/.exec(paperId);
  return m ? programOfLetter(m[1]) : null;
}

/** Whether a program is archived. A general entity (null) never is. */
export function isArchived(program: ProgramId | null | undefined): boolean {
  return program ? PROGRAM_BY_ID[program]?.status === 'archived' : false;
}
