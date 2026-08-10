// Collections, the activity feed, and resumable chat sessions.
// SYNTHETIC — see BUILD-SPEC.md content rules.
import type { ActivityEvent, ChatSession, Collection } from './types';

export const COLLECTIONS: Collection[] = [
  {
    id: 'col-gold',
    name: 'Gold set papers',
    // The ten papers carrying the densest hand-curated annotation.
    paperIds: [
      'SP-001',
      'SP-002',
      'SP-003',
      'SP-004',
      'SP-006',
      'SP-007',
      'SP-009',
      'SP-010',
      'SP-012',
      'SP-014',
    ],
  },
  {
    id: 'col-kinetics',
    name: 'cw15 kinetics',
    paperIds: ['SP-001', 'SP-002', 'SP-003', 'SP-005', 'SP-009'],
  },
  {
    id: 'col-downstream',
    name: 'Downstream',
    paperIds: ['SP-006', 'SP-010', 'SP-011'],
  },
];

export const ACTIVITY: ActivityEvent[] = [
  {
    at: '2026-08-09 16:42',
    icon: 'chart',
    text: 'Extractor run v0.4+rules scored against the gold set — precision 0.86',
    href: '#/extract/validation',
    provenance: 'gold',
  },
  {
    at: '2026-08-09 15:10',
    icon: 'check',
    text: 'ex-0080 verified — OD₇₅₀→DCW factor for cw15, 0.42 g L⁻¹ OD⁻¹',
    href: '#/library/papers/SP-010?span=ex-0080',
    provenance: 'verified',
  },
  {
    at: '2026-08-08 11:27',
    icon: 'file',
    text: 'PR-TAP-01 v1.1 published — acetate raised to 1.20 g L⁻¹',
    href: '#/protocols/PR-TAP-01',
    provenance: 'user',
  },
  {
    at: '2026-08-07 09:55',
    icon: 'flask',
    text: 'Curator note added to Chlamydomonas reinhardtii cw15 on shear sensitivity',
    href: '#/organisms/cw15',
    provenance: 'gold',
  },
  {
    at: '2026-08-06 17:03',
    icon: 'chart',
    text: 'Scenario S2 pinned for comparison — K. phaffii fed-batch at 13 g L⁻¹ titer',
    href: '#/simulate/sc-s2',
    provenance: 'demo',
  },
  {
    at: '2026-08-06 14:18',
    icon: 'check',
    text: '12 records verified in a 9-minute review session on SP-012',
    href: '#/extract?paper=SP-012',
    provenance: 'verified',
  },
  {
    at: '2026-08-05 13:40',
    icon: 'download',
    text: 'SP-016 ingested — 4 sections parsed, 9 parameters extracted',
    href: '#/library/papers/SP-016',
    provenance: 'unverified',
  },
  {
    at: '2026-08-04 10:22',
    icon: 'chart',
    text: 'ex-0033 promoted to the gold set — corrected d⁻¹ to h⁻¹',
    href: '#/library/papers/SP-004?span=ex-0033',
    provenance: 'gold',
  },
  {
    at: '2026-08-03 16:09',
    icon: 'file',
    text: 'PR-HARV-01 drafted from the SP-006 bead-milling method',
    href: '#/protocols/PR-HARV-01',
    provenance: 'user',
  },
  {
    at: '2026-08-01 12:31',
    icon: 'download',
    text: 'Extraction queued for the Downstream collection — 3 papers',
    href: '#/library',
    provenance: 'unverified',
  },
  {
    at: '2026-07-30 15:47',
    icon: 'check',
    text: 'ex-0027 rejected — extracted 0.079 h⁻¹ against a published 0.097 h⁻¹',
    href: '#/library/papers/SP-003?span=ex-0027',
    provenance: 'verified',
  },
  {
    at: '2026-07-28 11:12',
    icon: 'chart',
    text: 'Extractor run v0.4 completed against 41 gold annotations',
    href: '#/extract/validation',
    provenance: 'demo',
  },
  {
    at: '2026-07-26 09:38',
    icon: 'flask',
    text: 'Arthrospira platensis added as a strain — coverage wanted',
    href: '#/organisms/aplat',
    provenance: 'unverified',
  },
  {
    at: '2026-07-24 14:55',
    icon: 'file',
    text: 'Parameter ontology v0 frozen at 16 fields',
    href: '#/settings/corpus',
    provenance: 'gold',
  },
];

export const SEED_SESSIONS: ChatSession[] = [
  {
    id: 'sess-seed-1',
    title: 'Growth rates for cw15 in TAP',
    startedAt: '2026-08-09 14:02',
    messages: [],
    pinned: [],
  },
  {
    id: 'sess-seed-2',
    title: 'Reading SP-012 on methanol induction',
    startedAt: '2026-08-06 10:31',
    scope: { kind: 'paper', id: 'SP-012', label: 'SP-012' },
    messages: [],
    pinned: [],
  },
];
