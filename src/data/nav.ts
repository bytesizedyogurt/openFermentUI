// The navigation vocabulary (OF-BLD-006 §2.2 as reversed, OF-BLD-008 §1).
//
// ═══════════════════════════════════════════════════════════════════════
// THE RAIL. Home plus ten destinations:
//
//     Home
//     Intake · BioRepo · Postdoc · geneOS · fermOS · pureOS · Proforma
//     Runbooks · Primer · Guild
//
// alpha 2.0 retired the closed-map rule and Dominion with its seeded
// catalogue (ADR-000, ADR-010). Projects become the organizing object at
// stage 7 (ADR-005), and these destinations become views inside a project.
// ═══════════════════════════════════════════════════════════════════════
//
// THE NAMES ARE THE VOCABULARY. OF-BLD-006 §2.2 originally held that these
// were build-time names and that the rail should say "Ask" rather than
// "Postdoc". That was reversed: researchers acquire domain vocabulary
// constantly and use this daily, and a precise name learned once beats a
// generic one re-read forever.
//
// Three things make an invented word learnable rather than hostile, and all
// three live here rather than being left to each screen:
//   - a descriptor, so a first-time viewer is never facing a bare coinage;
//   - an alias, so typing the old word in the palette still finds the thing;
//   - a redirect, so an old link lands on the new screen instead of a 404.
import {
  Boxes,
  Dna,
  FlaskConical,
  Filter,
  GitBranch,
  GraduationCap,
  Home as HomeIcon,
  LineChart,
  Library as LibraryIcon,
  MessagesSquare,
  Table2,
  Users,
  type LucideIcon,
} from 'lucide-react';
import type { ComponentName } from '@/components/ComponentTag';

export interface NavSurface {
  /** The word a user reads. Also the component name, where it is one. */
  label: string;
  to: string;
  /**
   * One line of gloss. Eleven invented words with no explanation is friction
   * the names do not earn on first contact, and this is the cheapest possible
   * fix: the descriptor sits under the label in the rail and in the title
   * attribute when the rail is collapsed.
   */
  descriptor: string;
  /**
   * Old words that must still resolve in search. People will type "organisms"
   * and "molecules" for a while — probably months — and search must not punish
   * them for it.
   */
  aliases: string[];
  icon: LucideIcon;
  /** The component this surface is, when it is one. */
  component?: ComponentName;
}

/**
 * THE TWELVE. Home, then the eleven destinations, in order.
 *
 * Five things that used to be here are now views inside their owner, and none
 * of their screens were deleted: the strain catalogue is geneOS's default view
 * (as Hosts), Molecules is Dominion's, Protocols and Depositions are Runbooks
 * tabs, and Witness is a BioRepo tab. A catalogue of strains is not a
 * destination — it is what one of the eleven happens to hold.
 *
 * OF-BLD-011 §1 corrected which one. The catalogue sat under fermOS until the
 * three OS components were re-cut along the three stages of making something —
 * geneOS the organism, fermOS the reactor, pureOS downstream. Choosing a
 * chassis is a genetic design decision, so Hosts moved to geneOS and
 * `/fermos/organisms` redirects.
 */
export const RAIL: (NavSurface & { key: string })[] = [
  {
    label: 'Home',
    to: '/',
    descriptor: 'where things stand',
    aliases: ['dashboard', 'start'],
    icon: HomeIcon,
    key: 'h',
  },
  {
    label: 'Intake',
    to: '/intake',
    descriptor: 'documents in, anchored to source',
    aliases: ['extract', 'extraction', 'records', 'ingest', 'import'],
    icon: Table2,
    component: 'Intake',
    key: 'i',
  },
  {
    label: 'BioRepo',
    to: '/biorepo',
    descriptor: 'records, artifacts, provenance',
    aliases: ['library', 'corpus', 'papers', 'witness', 'validation', 'gold set', 'compare'],
    icon: LibraryIcon,
    component: 'BioRepo',
    key: 'b',
  },
  {
    label: 'Postdoc',
    to: '/postdoc',
    descriptor: 'ask, plan, answer from records',
    aliases: ['ask', 'chat', 'agent'],
    icon: MessagesSquare,
    component: 'Postdoc',
    key: 'o',
  },
  {
    label: 'geneOS',
    to: '/geneos',
    descriptor: 'host, construct, pathway, design',
    aliases: [
      'organisms',
      'strains',
      'hosts',
      'chassis',
      'sequence',
      'homology',
      'structure',
      'enzyme',
      'genes',
      'parts',
      'construct',
      'pathway',
      'pathways',
      'metabolic',
      'genome-scale',
      'gem',
      'fba',
      'strain design',
      'knockout',
    ],
    icon: Dna,
    component: 'geneOS',
    key: 'e',
  },
  {
    label: 'fermOS',
    to: '/fermos',
    descriptor: 'reactor, kinetics, scale',
    aliases: [
      'fermenter',
      'fermentation',
      'bioreactor',
      'reactor',
      'kinetics',
      'monod',
      'kla',
      'oxygen transfer',
      'transport',
      'fed-batch',
      'feeding',
      'scale-up',
      'control',
    ],
    icon: FlaskConical,
    component: 'fermOS',
    key: 'f',
  },
  {
    label: 'pureOS',
    to: '/pureos',
    descriptor: 'harvest, capture, recovery',
    aliases: [
      'downstream',
      'purification',
      'harvest',
      'lysis',
      'capture',
      'chromatography',
      'polish',
      'unit operations',
      'process train',
      'recovery',
      'storage',
    ],
    icon: Filter,
    component: 'pureOS',
    key: 'u',
  },
  {
    label: 'Proforma',
    to: '/proforma',
    descriptor: 'cost, scale, uncertainty',
    aliases: ['simulate', 'simulation', 'economics', 'cost', 'scenarios'],
    icon: LineChart,
    component: 'Proforma',
    key: 'c',
  },
  {
    label: 'Runbooks',
    to: '/runbooks',
    descriptor: 'claims to be tested',
    aliases: ['claims', 'predictions', 'protocols', 'run mode', 'deposition', 'depositions'],
    icon: GitBranch,
    component: 'Runbook',
    key: 'r',
  },
  {
    label: 'Primer',
    to: '/primer',
    descriptor: 'how the system works',
    aliases: ['learn', 'lessons', 'tutorial'],
    icon: GraduationCap,
    component: 'Primer',
    key: 'n',
  },
  {
    label: 'Guild',
    to: '/guild',
    descriptor: 'who may verify',
    aliases: [
      'review',
      'review queue',
      'triage',
      'guild of applied life',
      // OF-BLD-013 — the competence ledger.
      'training',
      'training matrix',
      'competence',
      'qualification',
      'sign-off',
      'assessor',
    ],
    icon: Users,
    component: 'Guild',
    key: 'g',
  },
];

/** Home is the twelfth entry, not one of the eleven. */
export const ELEVEN = RAIL.filter((r) => r.to !== '/');

/**
 * Sub-views worth naming in search but which are not destinations.
 *
 * Each belongs to one of the eleven and is reached from inside it. They are
 * here so the palette can take somebody who types "organisms" straight to the
 * catalogue rather than to fermOS's front door.
 */
export const SUB_VIEWS: (NavSurface & { owner: string })[] = [
  {
    label: 'Hosts',
    to: '/geneos/hosts',
    descriptor: 'the strain catalogue — chassis and lineage',
    aliases: ['organisms', 'strains', 'hosts', 'chassis', 'cw15'],
    icon: Dna,
    owner: 'geneOS',
  },
  {
    label: 'Pathway',
    to: '/geneos/pathway',
    descriptor: 'biosynthetic routes and their branch points',
    aliases: ['pathway', 'pathways', 'route', 'precursor', 'mva', 'shikimate'],
    icon: Dna,
    owner: 'geneOS',
  },
  {
    label: 'Model',
    to: '/geneos/model',
    descriptor: 'the most product a published reaction network allows, beside what was reported',
    aliases: ['ceiling', 'yield ceiling', 'flux balance', 'fba', 'genome-scale model', 'cobra', 'frontier', 'sugar mix'],
    icon: Dna,
    owner: 'geneOS',
  },
  {
    label: 'Forecast',
    to: '/fermos/forecast',
    descriptor: 'a band for the next run, drawn from a fitted one',
    aliases: ['forecast', 'kinetic fit', 'growth rate', 'mu max', 'luedeking piret', 'logistic', 'time series'],
    icon: FlaskConical,
    owner: 'fermOS',
  },
  {
    // OF-BLD-020 §3.3 — 'simulate' and 'vessel' are reserved under /fermos
    // (check-seed's RESERVED): a model family integrated from its sources,
    // and (§4.2) the fermenter a simulation needs.
    label: 'Simulate',
    to: '/fermos/simulate',
    descriptor: 'a run integrated from a model family, every parameter with its source',
    aliases: ['simulation', 'simulate a run', 'model family', 'monod', 'batch culture', 'fed-batch', 'fed batch', 'chemostat', 'time course'],
    icon: FlaskConical,
    owner: 'fermOS',
  },
  {
    label: 'Vessel',
    to: '/fermos/vessel',
    descriptor: 'the fermenter a simulation needs, sized on BioSTEAM',
    aliases: ['vessel', 'vessel design', 'bioreactor', 'kla', 'aeration', 'oxygen balance'],
    icon: FlaskConical,
    owner: 'fermOS',
  },
  {
    // OF-BLD-020 §5.3 — 'build' is reserved under /pureos: /pureos/build/:trainId, `new` for a fresh train.
    label: 'Builder',
    to: '/pureos/build',
    descriptor: 'a train built unit by unit from the catalogue, every parameter in hand, run on BioSTEAM',
    aliases: ['builder', 'build a train', 'new train', 'train builder', 'unit catalogue', 'palette', 'purity', 'downstream train'],
    icon: Filter,
    owner: 'pureOS',
  },
  {
    // OF-BLD-019 §4.1 — 'train' is reserved under /pureos: /pureos/train/:scenarioId.
    label: 'Train',
    to: '/pureos/train',
    descriptor: 'the units of the run Proforma priced, and what each passes on',
    aliases: ['train', 'step recovery', 'recovery by unit', 'stream table', 'mass balance by unit'],
    icon: Filter,
    owner: 'pureOS',
  },
  {
    // OF-BLD-019 §3.3 — 'reference' is reserved under /proforma: a reference
    // biorefinery's page, /proforma/reference/:id, one a shelf entry.
    label: 'Corn ethanol reference',
    to: '/proforma/reference/corn_drygrind',
    descriptor: 'the dry-grind corn plant run whole, beside its package\u2019s own test',
    aliases: ['reference', 'reference biorefinery', 'dry grind', 'corn ethanol', 'package test', 'regression values'],
    icon: LineChart,
    owner: 'Proforma',
  },
  {
    label: 'Corn stover benchmark',
    to: '/proforma/reference/cornstover_benchmark',
    descriptor: 'the NREL 2011 corn stover design run whole, beside its package\u2019s own test',
    aliases: ['benchmark', 'corn stover', 'nrel 2011', 'reference run'],
    icon: LineChart,
    owner: 'Proforma',
  },
  {
    label: 'Protocols',
    to: '/runbooks/protocols',
    descriptor: 'methods to run',
    aliases: ['protocols', 'methods', 'sops'],
    icon: GitBranch,
    owner: 'Runbooks',
  },
  {
    label: 'Depositions',
    to: '/runbooks/depositions',
    descriptor: 'bench capture, what actually happened',
    aliases: ['depositions', 'deposition', 'run mode', 'bench'],
    icon: GitBranch,
    owner: 'Runbooks',
    component: 'Deposition',
  },
  {
    label: 'Prediction ledger',
    to: '/runbooks/ledger',
    descriptor: 'what was predicted, against what was measured',
    aliases: ['ledger', 'predictions', 'hit rate', 'scorecard'],
    icon: GitBranch,
    owner: 'Runbooks',
  },
  {
    label: 'Witness',
    to: '/biorepo/witness',
    descriptor: 'does it reproduce',
    aliases: ['witness', 'validation', 'gold set', 'metrics'],
    icon: LibraryIcon,
    owner: 'BioRepo',
    component: 'Witness',
  },
  {
    label: 'Search',
    to: '/biorepo/search',
    descriptor: "the papers' own words, searched",
    aliases: ['search', 'passages', 'full text search', 'find in papers'],
    icon: LibraryIcon,
    owner: 'BioRepo',
  },
  {
    label: 'Artifacts',
    to: '/biorepo/artifacts',
    descriptor: 'what was computed, and from what',
    aliases: ['artifacts', 'computed', 'basis', 'replay'],
    icon: LibraryIcon,
    owner: 'BioRepo',
  },
  {
    label: 'Compare',
    to: '/biorepo/compare',
    descriptor: 'scenarios side by side',
    aliases: ['compare', 'diff'],
    icon: LibraryIcon,
    owner: 'BioRepo',
  },
  // ── OF-BLD-013: Primer's path and Guild's competence ledger ─────────
  {
    label: 'My path',
    to: '/primer/path',
    descriptor: 'the next step on each skill, and what is ready for the bench',
    aliases: ['my path', 'training path', 'next up', 'what to learn'],
    icon: GraduationCap,
    owner: 'Primer',
  },
  {
    label: 'Practice',
    to: '/primer/practice',
    descriptor: 'scenarios from the bench, and a tutor who asks why',
    aliases: ['practice', 'scenarios', 'tutor', 'drill'],
    icon: GraduationCap,
    owner: 'Primer',
  },
  {
    label: 'Matrix',
    to: '/guild/matrix',
    descriptor: 'who holds which skill, and who can run a protocol',
    aliases: ['matrix', 'training matrix', 'who can run'],
    icon: Users,
    owner: 'Guild',
  },
  {
    label: 'People',
    to: '/guild/people',
    descriptor: 'everyone on the ledger, and each person\u2019s entries',
    aliases: ['people', 'team', 'ledger', 'roster'],
    icon: Users,
    owner: 'Guild',
  },
  {
    label: 'Skills',
    to: '/guild/skills',
    descriptor: 'what each skill is and which steps need it',
    aliases: ['skills', 'mastery', 'criteria'],
    icon: Users,
    owner: 'Guild',
  },
  {
    label: 'Checks',
    to: '/guild/checks',
    descriptor: 'the assessor queue, and witnessed checks at the bench',
    aliases: ['checks', 'assessor queue', 'surprise checks', 'bench check', 'witnessed check'],
    icon: Users,
    owner: 'Guild',
  },
  {
    label: 'Ingest',
    to: '/intake/ingest',
    descriptor: 'what is queued, fetched, failed',
    aliases: ['ingest', 'fetch', 'queue'],
    icon: Table2,
    owner: 'Intake',
  },
];

export const ALL_SURFACES: NavSurface[] = [...RAIL, ...SUB_VIEWS];

/** Descriptor by label, for screens that want to print their own gloss. */
export const DESCRIPTOR: Record<string, string> = Object.fromEntries(
  ALL_SURFACES.map((s) => [s.label, s.descriptor]),
);

/**
 * Old path → new path.
 *
 * Deep-linked demo scripts, bookmarks, corpus prose, `learn.ts` content and
 * the guided tour all point at paths that have moved — some of them twice, as
 * `/library/papers/H4` became `/biorepo/papers/H4` and is now
 * `/biorepo/paper/H4`. A reorganisation that 404s them punishes the people who
 * used the thing most.
 *
 * ENTRIES POINT AT THE FINAL DESTINATION, NEVER AT ANOTHER REDIRECT. Chaining
 * would work in the browser and would be invisible when one link in the chain
 * later changed; `check:seed` fails the build on a redirect whose target is
 * itself redirected.
 */
export const REDIRECTS: Record<string, string> = {
  // ── OF-BLD-011: the strain catalogue moved from fermOS to geneOS ────
  // Re-aimed rather than chained: '/organisms' used to land on
  // '/fermos/organisms', which is itself retired now, and a redirect whose
  // target redirects bounces the reader through two interstitials.
  '/fermos/organisms': '/geneos/hosts',

  // ── OF-BLD-008: five destinations became views ──────────────────────
  '/organisms': '/geneos/hosts',
  // alpha 2.0 (ADR-010): Dominion left with its seeded catalogue; its paths
  // land on Home, which says what the platform holds.
  '/molecules': '/',
  '/dominion': '/',
  '/protocols': '/runbooks/protocols',
  '/depositions': '/runbooks/depositions',
  '/witness': '/biorepo/witness',
  '/clearance': '/',

  // ── OF-BLD-008: paths that moved between owners ─────────────────────
  '/biorepo/papers': '/biorepo/paper',
  '/biorepo/ingest': '/intake/ingest',
  '/proforma/compare': '/biorepo/compare',
  // OF-BLD-019 §3.3 — the benchmark's card and the old BioSTEAM page became
  // the reference page of the corn stover benchmark.
  '/proforma/benchmark': '/proforma/reference/cornstover_benchmark',
  '/proforma/biosteam': '/proforma/reference/cornstover_benchmark',

  // ── OF-BLD-006 legacy, re-pointed at the CURRENT destination ────────
  // These were already redirects; their targets moved underneath them, so
  // they are re-aimed rather than chained.
  '/extract/review': '/guild',
  '/extract/validation': '/biorepo/witness',
  '/library/papers': '/biorepo/paper',
  '/library/ingest': '/intake/ingest',
  '/simulate/compare': '/biorepo/compare',
  '/ask': '/postdoc',
  '/library': '/biorepo',
  '/extract': '/intake',
  '/simulate': '/proforma',
  '/learn': '/primer',
  '/review': '/guild',
  '/validation': '/biorepo/witness',
};

/**
 * Redirects that need a capture rather than a prefix swap.
 *
 * Three old shapes cannot be expressed as "replace this prefix, keep the
 * tail", because the tail itself changes: a scenario id moves down a level,
 * and a lesson loses the module segment that used to address it. Regex rather
 * than a special case per id, so a scenario added later is covered without
 * anybody remembering to add it.
 */
const PATTERN_REDIRECTS: [RegExp, string][] = [
  // /proforma/sc-s1 → /proforma/scenario/sc-s1 (but not /proforma/scenario/…,
  // nor the reserved /proforma/reference, OF-BLD-019 §3.3)
  [/^\/proforma\/(?!(?:scenario|reference)(?:\/|$))([^/]+)$/, '/proforma/scenario/$1'],
  // /simulate/sc-s1 → /proforma/scenario/sc-s1. The `compare` exclusion is
  // redundant now that exact entries run first, and is kept so the pattern is
  // still correct on its own if that entry is ever removed.
  [/^\/simulate\/(?!compare$)([^/]+)$/, '/proforma/scenario/$1'],
  // /learn/m0/l0-1 → /primer/l0-1. Lesson ids are globally unique, so the
  // module segment was always redundant for addressing.
  [/^\/learn\/[^/]+\/([^/]+)$/, '/primer/$1'],
];

/**
 * Where an old path should land, or null if it is already current.
 *
 * LONGEST PREFIX WINS. `/library/papers/H4` has to match `/library/papers`
 * rather than `/library`, or it lands on `/biorepo/papers/H4` — a path that is
 * itself retired. Trying progressively shorter prefixes makes the specific
 * rule beat the general one without anybody having to order the map by hand.
 *
 * The tail is preserved, so a deep link keeps its target: `/organisms/cw15`
 * reaches `/geneos/hosts/cw15` rather than dumping the reader at the top
 * of the catalogue to find their strain again.
 */
export function redirectFor(path: string): string | null {
  // MOST SPECIFIC FIRST, and an exact entry outranks a pattern. Running the
  // patterns first sent `/proforma/compare` to `/proforma/scenario/compare`,
  // because "compare" looks exactly like a scenario id to a regex. An exact
  // entry is somebody having decided about that one path; a pattern is a
  // guess that happens to be right most of the time.
  const exact = REDIRECTS[path];
  if (exact) return exact;

  for (const [pattern, replacement] of PATTERN_REDIRECTS) {
    if (pattern.test(path)) return path.replace(pattern, replacement);
  }

  // Then the longest matching prefix, so `/library/papers/H4` matches
  // `/library/papers` rather than `/library` — the latter would land it on
  // `/biorepo/papers/H4`, a path that is itself retired.
  const segments = path.split('/').filter(Boolean);
  for (let n = segments.length - 1; n > 0; n--) {
    const prefix = `/${segments.slice(0, n).join('/')}`;
    const to = REDIRECTS[prefix];
    if (to) return to + path.slice(prefix.length);
  }
  return null;
}
