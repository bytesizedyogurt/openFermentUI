// Tab sets per owner (OF-BLD-008 §6).
//
// Derived from the same paths `nav.ts` declares, and defined once rather than
// per screen, because a tab strip that disagrees with itself between two views
// of the same owner is the specific bug this file exists to prevent: you click
// Protocols, land on Protocols, and the strip above you shows a different set.
//
// Owners with ONE view get no strip. A single tab is a label pretending to be a
// choice.
import type { OwnerTab } from '@/components/OwnerTabs';

export const BIOREPO_TABS: OwnerTab[] = [
  // Papers is BioRepo's own screen and its default view. §6 also names a
  // "Records" tab; extraction records live in Intake and are reached there, so
  // a second tab pointing at the same table would be a duplicate rather than a
  // view — and duplicating a screen is the kind of feature §10 forbids.
  { label: 'Papers', to: '/biorepo' },
  { label: 'Compare', to: '/biorepo/compare' },
  { label: 'Witness', to: '/biorepo/witness' },
];

export const INTAKE_TABS: OwnerTab[] = [
  { label: 'Extract', to: '/intake' },
  { label: 'Ingest', to: '/intake/ingest' },
];

export const RUNBOOK_TABS: OwnerTab[] = [
  { label: 'Runbooks', to: '/runbooks' },
  { label: 'Protocols', to: '/runbooks/protocols' },
  { label: 'Depositions', to: '/runbooks/depositions' },
];

// OF-BLD-013 §3.3. The module map keeps /primer, so every link to it that
// exists today still lands on it; a person's path sits beside it.
export const PRIMER_TABS: OwnerTab[] = [
  { label: 'Lessons', to: '/primer' },
  { label: 'My path', to: '/primer/path' },
  { label: 'Practice', to: '/primer/practice' },
];

// OF-BLD-013 §1.4. Review keeps /guild, so every link into the queue that
// exists today still lands on it; the workforce views sit beside it.
export const GUILD_TABS: OwnerTab[] = [
  { label: 'Review', to: '/guild' },
  { label: 'Matrix', to: '/guild/matrix' },
  { label: 'People', to: '/guild/people' },
  { label: 'Skills', to: '/guild/skills' },
];
