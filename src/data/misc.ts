// Collections, activity feed, and resumable chat sessions for the real corpus.
import type { ActivityEvent, ChatSession, Collection } from './types';

export const COLLECTIONS: Collection[] = [
  {
    id: 'col-gold',
    name: 'Gold-set papers (planned)',
    paperIds: ['H1', 'H4', 'I1', 'C2', 'K1', 'F1', 'J10', 'O4', 'O2', 'M5', 'M6', 'M7', 'A1', 'B5'],
  },
  {
    id: 'col-chassis',
    name: 'Why cw15 — the chassis argument',
    paperIds: ['A1', 'A2', 'A7', 'B1', 'B5', 'C2', 'C6', 'J10', 'N2', 'N3', 'N4'],
  },
  {
    id: 'col-phospho',
    name: 'The phosphorylation problem',
    paperIds: ['G1', 'G3', 'G4', 'G7', 'G9', 'H1', 'H2', 'H3', 'H4', 'H8', 'D5'],
  },
  {
    id: 'col-function',
    name: 'Does phosphorylation matter?',
    paperIds: ['I1', 'I2', 'I3', 'I4', 'I6', 'I9', 'E2', 'E6'],
  },
  {
    id: 'col-tea',
    name: 'Techno-economics',
    paperIds: ['O1', 'O2', 'O3', 'O4', 'O5', 'O6', 'O7', 'O8'],
  },
  {
    id: 'col-openaccess',
    name: 'Tranche 1 — open access, ingest first',
    paperIds: ['A1', 'A2', 'A3', 'B1', 'C2', 'C3', 'C4', 'D1', 'D2', 'G3', 'H1', 'I6', 'K1', 'N3'],
  },
];

export const ACTIVITY: ActivityEvent[] = [
  {
    at: '2026-08-10 14:20',
    icon: 'file',
    text: 'Corpus OF-COR-001 v1.0 catalogued — 125 real entries across 15 threads',
    href: '#/biorepo',
    provenance: 'curated',
  },
  {
    at: '2026-08-10 14:05',
    icon: 'chart',
    text: 'Parameter ontology v1 replaced the synthetic 16 fields — now 24 fields in five families',
    href: '#/settings/units',
    provenance: 'gold',
  },
  {
    at: '2026-08-10 13:40',
    icon: 'flask',
    text: 'Open question recorded on cw15: does C. reinhardtii have a Fam20-family kinase?',
    href: '#/organisms/cw15',
    provenance: 'curated',
  },
  {
    at: '2026-08-10 11:12',
    icon: 'check',
    text: 'Strain alias table built — cw15, cw15-302, CC-4350 and Elow47 now normalise on ingest',
    href: '#/organisms/cw15',
    provenance: 'gold',
  },
  {
    at: '2026-08-09 17:30',
    icon: 'chart',
    text: 'Scenario S3 added — conventional β-casein from milk, as the incumbent baseline',
    href: '#/proforma/sc-s3',
    provenance: 'demo',
  },
  {
    at: '2026-08-09 16:02',
    icon: 'file',
    text: 'O8 market figures flagged industry-estimate — excluded from gold and from aggregates',
    href: '#/intake',
    provenance: 'industry-estimate',
  },
  {
    at: '2026-08-08 15:48',
    icon: 'download',
    text: 'Citation-of-a-citation trap logged: C6 recites C2’s 15 mg/L rather than measuring it',
    href: '#/biorepo/papers/C6',
    provenance: 'curated',
  },
  {
    at: '2026-08-08 10:15',
    icon: 'check',
    text: 'Gold-set plan drafted — 60 records across 14 papers, pending tranche-1 ingest',
    href: '#/witness',
    provenance: 'gold',
  },
  {
    at: '2026-08-07 14:33',
    icon: 'flask',
    text: 'D1/D4 sialylation conflict retained deliberately as a corpus disagreement case',
    href: '#/biorepo/papers/D4',
    provenance: 'curated',
  },
  {
    at: '2026-08-06 09:20',
    icon: 'file',
    text: 'Numbering convention enforced on residue positions — β-casein mature 209 vs precursor 224',
    href: '#/organisms/bovine',
    provenance: 'gold',
  },
];

export const SEED_SESSIONS: ChatSession[] = [
  {
    id: 'sess-seed-1',
    title: 'Has anyone expressed a casein in an alga?',
    startedAt: '2026-08-10 13:55',
    messages: [],
    pinned: [],
  },
  {
    id: 'sess-seed-2',
    title: 'Reading H4 on P. pastoris β-casein',
    startedAt: '2026-08-09 16:40',
    scope: { kind: 'paper', id: 'H4', label: 'H4' },
    messages: [],
    pinned: [],
  },
];
