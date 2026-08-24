// The component architecture (OF-BLD-006 §2, with §2.2 reversed).
//
// Eighteen named components in seven layers. This module is the source of
// truth; COMPONENTS.md at the repo root carries the same content and
// `check-seed` fails if the two disagree, so the map a reader opens and the map
// the code uses cannot drift apart.
//
// §2.2 SAID THE OPPOSITE AND WAS WRONG. It held that these names were for
// building the system and that a user should see "Ask" rather than "Postdoc".
// The users here are researchers who acquire domain vocabulary constantly and
// will use this daily: a precise name learned once beats a generic one re-read
// forever. So the component names ARE the user-facing vocabulary, `surfacedAs`
// now records where each one is read rather than what it hides behind, and
// `src/data/nav.ts` carries the descriptors, aliases and redirects that make a
// coined word learnable instead of hostile.
//
// Attribution tags survive the reversal unchanged. Naming the surface you are
// standing on and naming the component that did a particular piece of work are
// different jobs, and `ComponentTag` still does the second one.
import type { ComponentName } from '@/components/ComponentTag';

export type ComponentLayer =
  | 'The agent'
  | 'Evidence in'
  | 'Computing'
  | 'Keeping it honest'
  | 'Patents'
  | 'People and permissions'
  | 'Assay';

export interface ComponentDef {
  name: ComponentName;
  layer: ComponentLayer;
  /** Where the code is, or `[]` when the component is not built. */
  livesIn: string[];
  /** Where a user reads this name, or null when there is nothing to read. */
  surfacedAs: string | null;
  /** One line on what it is for. */
  role: string;
}

/**
 * Layer order is the direction evidence travels: something is asked, evidence
 * comes in, models compute over it, the honest layer decides whether the
 * result may be used, patents decide whether you may build it, people decide
 * who may say so — and Assay is where it leaves software entirely.
 */
export const LAYERS: { id: ComponentLayer; blurb: string }[] = [
  {
    id: 'The agent',
    blurb: 'The thing you talk to. It plans, retrieves, and shows its working rather than handing back a paragraph you have to trust.',
  },
  {
    id: 'Evidence in',
    blurb: 'How claims get into the system, and what each one is worth once it is there.',
  },
  {
    id: 'Computing',
    blurb: 'The models that turn a question into numbers. Two of the three are not built, and the map says so rather than quietly omitting them.',
  },
  {
    id: 'Keeping it honest',
    blurb: 'The components whose job is to refuse. Nothing in this layer produces an answer; everything in it decides whether an answer may be used.',
  },
  {
    id: 'Patents',
    blurb: 'Whether you are allowed to build it, and whether somebody else already owns the idea. Research leads, never legal opinions.',
  },
  {
    id: 'People and permissions',
    blurb: 'Who decided what, and who is allowed to decide it.',
  },
  {
    id: 'Assay',
    blurb: 'The boundary, and the only place the arrow reverses. Everything above is software reasoning about the world; this is the world reporting back.',
  },
];

export const COMPONENTS: ComponentDef[] = [
  {
    name: 'Postdoc',
    layer: 'The agent',
    livesIn: ['src/sim/chat.ts', 'src/screens/Postdoc.tsx'],
    surfacedAs: 'the rail, /postdoc',
    role: 'Plans, retrieves, and answers with its working shown',
  },
  {
    name: 'Intake',
    layer: 'Evidence in',
    livesIn: ['src/screens/IntakeIngest.tsx', 'src/screens/Intake.tsx'],
    surfacedAs: 'the rail, /intake',
    role: 'Ingest and extraction of parameters from sources',
  },
  {
    name: 'BioRepo',
    layer: 'Evidence in',
    livesIn: ['src/data/', 'src/engine/retrieval.ts', 'src/screens/BioRepo.tsx'],
    surfacedAs: 'the rail, /biorepo',
    role: 'The corpus, and everything retrieved from it',
  },
  {
    name: 'geneOS',
    layer: 'Computing',
    livesIn: [],
    surfacedAs: null,
    role: 'Construct and strain design',
  },
  {
    name: 'fermOS',
    layer: 'Computing',
    livesIn: [],
    surfacedAs: null,
    role: 'Fermentation and process modelling',
  },
  {
    name: 'Proforma',
    layer: 'Computing',
    livesIn: ['src/screens/Proforma.tsx', 'src/engine/grids.ts', 'src/engine/interp.ts'],
    surfacedAs: 'the rail, /proforma',
    role: 'Cost models, sweeps and scenario economics',
  },
  {
    // §3 — Primer moved. It named the unit engine; it now names the Learn
    // section: an introductory text, and a bio pun that earns its place.
    // The unit engine is unnamed until it gets a name of its own, which is
    // better than leaving it wearing one that belongs to something else.
    name: 'Primer',
    layer: 'Keeping it honest',
    livesIn: ['src/screens/Primer.tsx', 'src/screens/PrimerLesson.tsx'],
    surfacedAs: 'the rail, /primer',
    role: 'The introductory text: the platform taught through itself',
  },
  {
    name: 'Audit',
    layer: 'Keeping it honest',
    livesIn: ['src/components/Provenance.tsx', 'aggregateExclusion() in src/store.ts'],
    surfacedAs: 'provenance ticks and their labels',
    role: 'Provenance, and what is held out of aggregates',
  },
  {
    name: 'Witness',
    layer: 'Keeping it honest',
    livesIn: ['src/screens/Witness.tsx', 'src/engine/metrics.ts'],
    surfacedAs: '/witness',
    role: 'Extractor validation against the gold set',
  },
  {
    name: 'Common Seal',
    layer: 'Keeping it honest',
    livesIn: [],
    surfacedAs: null,
    role: 'Timestamping and attestation',
  },
  {
    name: 'Claim Workbench',
    layer: 'Patents',
    livesIn: [],
    surfacedAs: null,
    role: 'Claim drafting and analysis',
  },
  {
    name: 'Priority Engine',
    layer: 'Patents',
    livesIn: [],
    surfacedAs: null,
    role: 'Priority and filing strategy',
  },
  {
    name: 'Clearance',
    layer: 'Patents',
    livesIn: ['src/engine/clearance.ts', 'src/data/clearanceFindings.ts'],
    surfacedAs: 'ambient on Molecules',
    role: 'Freedom to operate, per jurisdiction',
  },
  {
    name: 'Enablement',
    layer: 'Patents',
    livesIn: [],
    surfacedAs: null,
    role: 'Enablement and written description',
  },
  {
    name: 'Notary',
    layer: 'Patents',
    livesIn: [],
    surfacedAs: null,
    role: 'Inventorship and conception records',
  },
  {
    name: 'Guild',
    layer: 'People and permissions',
    livesIn: ['src/screens/Guild.tsx'],
    surfacedAs: '/guild',
    role: 'Review, roles, and who decided what',
  },
  {
    name: 'Runbook',
    layer: 'Assay',
    livesIn: ['src/screens/Runbooks.tsx', 'src/data/runbooks.ts'],
    surfacedAs: 'the rail, /runbooks',
    role: 'The outbound falsifiable claim',
  },
  {
    name: 'Deposition',
    layer: 'Assay',
    livesIn: ['src/screens/Deposition.tsx', 'src/components/DepositionPanel.tsx'],
    surfacedAs: 'launched from a Runbook',
    role: 'The inbound account of what actually happened',
  },
];

/**
 * Code that sits in a layer without a name of its own.
 *
 * §3 moved Primer off the unit engine and onto the Learn screens. The engine
 * is not renamed on the spot: it is listed here as what it is until somebody
 * chooses a name for it deliberately. An unnamed thing on the map is honest —
 * a hastily renamed one is a name nobody picked, which is how a vocabulary
 * ends up with words its own authors do not use.
 */
export const UNNAMED: {
  what: string;
  layer: ComponentLayer;
  livesIn: string[];
  role: string;
}[] = [
  {
    what: 'the unit engine',
    layer: 'Keeping it honest',
    livesIn: ['src/engine/units.ts', 'src/engine/scale.ts'],
    role: 'Units, conversion, scaling, and refusals that carry their reason',
  },
];

/** "Guild" is the attribution short form; this is the full name. */
export const FULL_NAME: Partial<Record<ComponentName, string>> = {
  Guild: 'Guild of Applied Life',
};

export const COMPONENTS_BY_NAME: Record<string, ComponentDef> = Object.fromEntries(
  COMPONENTS.map((c) => [c.name, c]),
);

export const isBuilt = (c: ComponentDef): boolean => c.livesIn.length > 0;

export function componentsInLayer(layer: ComponentLayer): ComponentDef[] {
  return COMPONENTS.filter((c) => c.layer === layer);
}
