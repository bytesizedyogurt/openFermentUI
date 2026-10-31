// The component architecture (OF-BLD-006 §2, with §2.2 reversed): the named
// components in their layers, as Settings → Architecture shows them. The
// package map of the code is COMPONENTS.md, written from the boundary rules.
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

/** The destinations on the rail. Home is not one of them. */
export type Destination =
  | 'Intake'
  | 'BioRepo'
  | 'Postdoc'
  | 'geneOS'
  | 'fermOS'
  | 'pureOS'
  | 'Proforma'
  | 'Runbooks'
  | 'Primer'
  | 'Guild';

export type ComponentLayer =
  | 'The agent'
  | 'Evidence in'
  | 'Computing'
  | 'Keeping it honest'
  | 'People and permissions'
  | 'Assay';

export interface ComponentDef {
  name: ComponentName;
  layer: ComponentLayer;
  /**
   * Which destination owns this (OF-BLD-008 §8). A destination owns itself.
   * Internal machinery — Audit, Witness, Common Seal, Deposition — is not a
   * destination and names the one it lives inside, so that "where does this
   * live" has an answer for every component.
   */
  owner: Destination;
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
 * result may be used, people decide who may say so — and Assay is where it
 * leaves software entirely.
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
    blurb: 'The models that turn a question into numbers: the organism, the reactor, downstream and the economics, each run in the service on its own engine.',
  },
  {
    id: 'Keeping it honest',
    blurb: 'The components whose job is to refuse. Nothing in this layer produces an answer; everything in it decides whether an answer may be used.',
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
    owner: 'Postdoc',
    layer: 'The agent',
    // OF-BLD-014 §3.4 — the tools its loop calls, and what it may cite.
    // §5.2 — the bounded loop itself, and the validator its plan answers to.
    livesIn: [
      'src/lib/postdoc.ts',
      'src/screens/Postdoc.tsx',
      'core/openferment_core/postdoc_agent.py',
      'core/openferment_core/postdoc/',
      'core/openferment_core/llm.py',
      'core/openferment_core/validate.py',
      // OF-BLD-015 §7.1–§7.4 — the module stores it sweeps and reads, the
      // audit log its writes land in, and the proposals its gates make.
      'core/openferment_core/module_stores.py',
      'core/openferment_core/tools/',
      'core/openferment_core/audit.py',
      'core/openferment_core/proposals.py',
      'core/openferment_core/evidence_pool.py',
    ],
    surfacedAs: 'the rail, /postdoc',
    role: 'Plans, retrieves, and answers with its working shown',
  },
  {
    name: 'Intake',
    owner: 'Intake',
    layer: 'Evidence in',
    // OF-BLD-012, ADR-002 — collection into Sci RAG Kit and extraction are the
    // service's; the board drives them.
    livesIn: [
      'src/screens/IntakeIngest.tsx',
      'src/screens/Intake.tsx',
      'core/openferment_core/intake.py',
      'core/openferment_core/literature/',
      'core/openferment_core/extract.py',
    ],
    surfacedAs: 'the rail, /intake',
    role: 'Documents collected into the project, and parameters extracted from them, each anchored to a sentence',
  },
  {
    name: 'BioRepo',
    owner: 'BioRepo',
    layer: 'Evidence in',
    // OF-BLD-012 §2.3 — one write function for a project's review decisions.
    // OF-BLD-014 §3.2 — and what the service computed, kept and replayable.
    livesIn: [
      'src/screens/BioRepo.tsx',
      'core/openferment_core/biorepo.py',
      'src/screens/BioRepoArtifacts.tsx',
      'core/openferment_core/artifacts.py',
      // Search over the project's documents (Sci RAG Kit, alpha 2.0 stage 3).
      'src/screens/BioRepoSearch.tsx',
      // OF-BLD-014 §6.1 — one figure grammar for drawing evidence.
      'src/components/figures/',
    ],
    surfacedAs: 'the rail, /biorepo',
    role: 'The project\u2019s records and the decisions on them, what was computed from them, and search over its documents',
  },
  {
    // OF-BLD-011 §2 — the first of the three stages. The strain catalogue and
    // its pages moved here from fermOS, because choosing a chassis is a
    // genetic design decision; genus enumeration came with them, being a
    // sequence-space search.
    name: 'geneOS',
    owner: 'geneOS',
    layer: 'Computing',
    livesIn: [
      'src/screens/GeneOS.tsx',
      'src/screens/Organisms.tsx',
      'src/screens/StrainPage.tsx',
      'src/engine/geneos/enumeration.ts',
      // OF-BLD-014 §6.2–§6.4 — flux balance analysis on a shelf of published models.
      'src/screens/GeneOSModel.tsx',
      'core/openferment_core/geneos.py',
      'core/openferment_core/workers/geneos_worker.py',
    ],
    surfacedAs: 'the rail, /geneos',
    role: 'The organism as an engineered system — host, parts, pathway, model, strain design',
  },
  {
    // OF-BLD-011 §3 — the reactor. The catalogue it used to hold went to
    // geneOS. OF-BLD-014 Phase 7 built its kinetics from depositions;
    // OF-BLD-020 Phase 3 its model families (operating mode) and §4.2 its
    // transport and scale (the vessel on BioSTEAM); control is not built.
    name: 'fermOS',
    owner: 'fermOS',
    layer: 'Computing',
    // OF-BLD-014 Phase 7 — fits and forecasts from depositions; OF-BLD-020
    // §3.3 — simulations of a model family, every parameter with its source;
    // §4.2 — the vessel BioSTEAM designs for a kept simulation.
    livesIn: [
      'src/screens/FermOS.tsx',
      'src/screens/FermOSForecast.tsx',
      'src/screens/FermOSSimulate.tsx',
      'src/engine/series.ts',
      'core/openferment_core/fermos.py',
      'core/openferment_core/kinetics.py',
      'src/screens/FermOSVessel.tsx',
      'core/openferment_core/vessel.py',
    ],
    surfacedAs: 'the rail, /fermos',
    role: 'The reactor — kinetics, transport, operating mode, scale, control. Kinetics, operating mode, transport and scale built; control not built',
  },
  {
    name: 'Proforma',
    owner: 'Proforma',
    layer: 'Computing',
    livesIn: [
      'src/screens/Proforma.tsx',
      'src/screens/ProformaScenario.tsx',
      'src/screens/ProformaBiosteam.tsx',
      'src/screens/ProformaReference.tsx',
      'src/engine/interp.ts',
      'src/screens/ProformaStudies.tsx',
      'src/screens/ProformaRun.tsx',
      'src/screens/ProformaComparison.tsx',
      'core/openferment_core/proforma.py',
      'core/openferment_core/engine/',
      'core/openferment_core/studies/',
      'core/openferment_core/flowsheets/',
    ],
    surfacedAs: 'the rail, /proforma',
    role: 'Scenario economics on BioSTEAM: the library\u2019s plants and openFerment\u2019s flowsheets through one adapter, each run kept with its SFF file, and studies of scenarios, comparisons and runbooks',
  },
  {
    // OF-BLD-020 §5 — trains of BioSTEAM's units (and the in-house ones it
    // lacks), each parameter bound with its source, run in the Proforma worker.
    name: 'pureOS',
    owner: 'pureOS',
    layer: 'Computing',
    livesIn: [
      'src/screens/PureOS.tsx',
      'src/screens/PureOSBuilder.tsx',
      'src/screens/PureOSTrain.tsx',
      'src/screens/PureOSPropose.tsx',
      'core/openferment_core/pureos/',
    ],
    surfacedAs: 'the rail, /pureos',
    role: 'Downstream — harvest, capture, polish, recovery: a train of units, each parameter with its source',
  },
  {
    // §3 — Primer moved. It named the unit engine; it now names the Learn
    // section: an introductory text, and a bio pun that earns its place.
    // The unit engine is unnamed until it gets a name of its own, which is
    // better than leaving it wearing one that belongs to something else.
    name: 'Primer',
    owner: 'Primer',
    layer: 'Keeping it honest',
    livesIn: [
      'src/screens/Primer.tsx',
      'src/screens/PrimerLesson.tsx',
      'src/screens/PrimerPath.tsx',
      'src/screens/PrimerPractice.tsx',
      'core/openferment_core/practice.py',
    ],
    surfacedAs: 'the rail, /primer',
    role: 'The introductory text: the platform taught through itself, and each person\u2019s path from lesson to bench',
  },
  {
    name: 'Audit',
    owner: 'BioRepo',
    layer: 'Keeping it honest',
    // OF-BLD-014 §3.1 — a computed value's provenance follows from its basis.
    livesIn: ['src/components/Provenance.tsx', 'aggregateExclusion() in src/store.ts', 'core/openferment_core/basis.py'],
    surfacedAs: 'provenance ticks and their labels',
    role: 'Provenance, and what is held out of aggregates',
  },
  {
    name: 'Witness',
    owner: 'BioRepo',
    layer: 'Keeping it honest',
    // OF-BLD-012 §6.2 — match_run scores the run that ran; the screen renders it.
    livesIn: [
      'src/screens/Witness.tsx',
      'src/engine/metrics.ts',
      'core/openferment_core/witness.py',
    ],
    surfacedAs: 'a BioRepo tab, /biorepo/witness',
    role: 'Extractor validation against the values reviewers typed',
  },
  {
    name: 'Common Seal',
    owner: 'BioRepo',
    layer: 'Keeping it honest',
    livesIn: [],
    surfacedAs: null,
    role: 'Timestamping and attestation',
  },
  {
    name: 'Guild',
    owner: 'Guild',
    layer: 'People and permissions',
    livesIn: [
      'src/screens/Guild.tsx',
      'src/screens/GuildMatrix.tsx',
      'src/screens/GuildPeople.tsx',
      'src/screens/GuildSkills.tsx',
      'src/screens/GuildChecks.tsx',
      'src/screens/BenchCheck.tsx',
      'src/engine/competence.ts',
      'src/engine/checks.ts',
      'core/openferment_core/guild.py',
      'core/openferment_core/checks.py',
    ],
    surfacedAs: '/guild',
    role: 'Review, the competence ledger, and who decided what',
  },
  {
    name: 'Runbook',
    owner: 'Runbooks',
    layer: 'Assay',
    livesIn: ['src/screens/Runbooks.tsx', 'src/screens/RunbookLedger.tsx', 'src/engine/ledger.ts'],
    surfacedAs: 'the rail, /runbooks',
    role: 'The outbound falsifiable claim',
  },
  {
    name: 'Deposition',
    owner: 'Runbooks',
    layer: 'Assay',
    livesIn: ['src/screens/Deposition.tsx', 'src/screens/Depositions.tsx', 'src/components/DepositionPanel.tsx'],
    surfacedAs: 'a Runbooks tab, /runbooks/depositions',
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
    livesIn: ['core/openferment_core/units.py', 'src/engine/units.ts', 'src/engine/scale.ts'],
    role: 'Units, conversion, scaling, and refusals that carry their reason',
  },
  {
    // ADR-001 — PostgreSQL is the one store.
    what: 'the store',
    layer: 'Evidence in',
    livesIn: ['core/openferment_core/db/', 'core/openferment_core/projects/', 'core/openferment_core/migrations.py'],
    role: 'PostgreSQL: every project\u2019s documents, records, decisions, runs, studies and conversations',
  },
  {
    // OF-BLD-014 §3.4 — heavy simulators run in their own processes.
    what: 'the worker runner',
    layer: 'Computing',
    livesIn: ['core/openferment_core/workers/'],
    role: 'Runs a simulator in a process of its own, kept warm, restarted on a timeout or a crash',
  },
];

/** "Guild" is the attribution short form; this is the full name. */
export const FULL_NAME: Partial<Record<ComponentName, string>> = {
  Guild: 'Guild of Applied Life',
};

export const isBuilt = (c: ComponentDef): boolean => c.livesIn.length > 0;

export function componentsInLayer(layer: ComponentLayer): ComponentDef[] {
  return COMPONENTS.filter((c) => c.layer === layer);
}
