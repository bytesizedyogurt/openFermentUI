// Patents (OF-FE-003 §9, Parchment).
//
// Six real entries, catalogued in OF-COR-001 §9 as H17a–f from the patent
// landscape of H1 Table 4. Numbers, assignees and subject matter are as
// recorded there.
//
// NO CLAIM TEXT HAS BEEN RETRIEVED. The corpus holds a curator's one-line
// description of each patent's subject matter and nothing more, so every claim
// below carries `bounds: []` and `parseUncertain: true`, and `rawText` is the
// curation note verbatim rather than invented claim language.
//
// That makes Parchment honestly empty in the same way Validation is: the
// structure is real and the arithmetic is built, but the scope map cannot be
// drawn until claims are fetched and parsed. §12.6 forbids inventing a patent;
// inventing a *bound* on a real patent would be worse, because it would read as
// analysis rather than as a placeholder.
//
// priorityDate is recorded as the publication year where the corpus states one
// and left empty otherwise. `anticipates` refuses to run without a real date on
// both sides, so an empty string disables the check rather than skewing it.
import type { Patent } from './types';

const UNPARSED = (note: string) => [
  {
    number: 1,
    independent: true,
    bounds: [],
    rawText: note,
    parseUncertain: true,
  },
];

export const PATENTS: Patent[] = [
  {
    id: 'PT-H17a',
    paperId: 'H17a',
    jurisdiction: 'US',
    number: 'US12139737B2',
    title: 'Host cells comprising a recombinant casein protein and a recombinant kinase protein',
    assignee: 'Nobell Foods',
    priorityDate: '',
    status: 'granted',
    verifyNeeded: true,
    claims: UNPARSED(
      'From the patent landscape of H1 Table 4: US12139737B2 (Nobell Foods) — host cells comprising a recombinant casein protein and a recombinant kinase protein; explicitly incorporates Fam20C. The closest prior art to the cw15 strategy.',
    ),
  },
  {
    id: 'PT-H17b',
    paperId: 'H17b',
    jurisdiction: 'WO',
    number: 'WO2023092005A1 / WO2023197002A2',
    title: 'Phosphorylation of proteins in plants',
    assignee: 'Mozza Foods',
    priorityDate: '',
    status: 'pending',
    verifyNeeded: true,
    claims: UNPARSED(
      'From the patent landscape of H1 Table 4: WO2023092005A1 and WO2023197002A2 (Mozza Foods) — phosphorylation of proteins in plant systems.',
    ),
  },
  {
    id: 'PT-H17c',
    paperId: 'H17c',
    jurisdiction: 'WO',
    number: 'WO2024013749A1',
    title: 'Functional milk proteins in plant cells co-expressed with a kinase',
    assignee: 'Imagene Foods',
    priorityDate: '',
    status: 'pending',
    verifyNeeded: true,
    claims: UNPARSED(
      'From the patent landscape of H1 Table 4: WO2024013749A1 (Imagene Foods) — functional milk proteins in plant cells co-expressed with a kinase.',
    ),
  },
  {
    id: 'PT-H17d',
    paperId: 'H17d',
    jurisdiction: 'US',
    number: 'US12077798B2',
    title: 'Transgenic plants stably expressing recombinant fusion proteins',
    assignee: 'Nobell Foods',
    priorityDate: '',
    status: 'granted',
    verifyNeeded: true,
    claims: UNPARSED(
      'From the patent landscape of H1 Table 4: US12077798B2 (Nobell Foods) — transgenic plants stably expressing recombinant fusion proteins.',
    ),
  },
  {
    id: 'PT-H17e',
    paperId: 'H17e',
    jurisdiction: 'WO',
    number: 'WO2024015365A1',
    title: 'Recombinant food proteins in chemoautotrophic microorganisms',
    assignee: 'Kiverdi',
    priorityDate: '',
    status: 'pending',
    verifyNeeded: true,
    claims: UNPARSED(
      'From the patent landscape of H1 Table 4: WO2024015365A1 (Kiverdi) — recombinant food proteins in chemoautotrophic microorganisms, host list includes algae; the only algal claim found.',
    ),
  },
  {
    id: 'PT-H17f',
    paperId: 'H17f',
    jurisdiction: 'US',
    number: 'US12359212',
    title: 'Recombinant micelle and in vivo assembly',
    assignee: 'Not recorded in OF-COR-001',
    priorityDate: '',
    status: 'granted',
    verifyNeeded: true,
    claims: UNPARSED(
      'From the patent landscape of H1 Table 4: US12359212 — recombinant micelle and in vivo assembly.',
    ),
  },
];
