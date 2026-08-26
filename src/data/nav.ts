// The navigation vocabulary (OF-BLD-006 §2.2 as reversed, OF-BLD-008 §1).
//
// ═══════════════════════════════════════════════════════════════════════
// THE LIST IS CLOSED. Home plus eleven destinations. Twelve rail entries,
// exactly. It does not grow.
//
//     Home
//     Intake · BioRepo · Postdoc · geneOS · fermOS · pureOS · Proforma
//     Runbooks · Dominion · Primer · Guild
//
// Everything that exists now, and everything built later, lives INSIDE one of
// the eleven. When something new appears and does not obviously belong, the
// question is which of the eleven owns it — never whether to add a twelfth.
// That constraint is the point: a rail that grows with the codebase stops
// being a map and becomes an index, and an index of a system nobody can hold
// in their head is not navigation.
//
// If a thirteenth entry ever seems necessary, the honest options are to find
// its owner among the eleven, or to argue that the eleven are wrong. Adding
// one is not an option. `check:seed` fails the build if RAIL is not twelve.
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
    label: 'Dominion',
    to: '/dominion',
    descriptor: 'what is fenced, what is open',
    aliases: ['molecules', 'products', 'clearance', 'patents', 'freedom to operate', 'fto'],
    icon: Boxes,
    component: 'Dominion',
    key: 'd',
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
    aliases: ['review', 'review queue', 'triage', 'guild of applied life'],
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
    label: 'Molecules',
    to: '/dominion/molecules',
    descriptor: 'targets and markets',
    aliases: ['molecules', 'products', 'targets'],
    icon: Boxes,
    owner: 'Dominion',
  },
  {
    label: 'Clearance',
    to: '/dominion/clearance',
    descriptor: 'freedom to operate, per jurisdiction',
    aliases: ['clearance', 'fto', 'patents', 'blocked'],
    icon: Boxes,
    owner: 'Dominion',
    component: 'Clearance',
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
    label: 'Witness',
    to: '/biorepo/witness',
    descriptor: 'does it reproduce',
    aliases: ['witness', 'validation', 'gold set', 'metrics'],
    icon: LibraryIcon,
    owner: 'BioRepo',
    component: 'Witness',
  },
  {
    label: 'Compare',
    to: '/biorepo/compare',
    descriptor: 'scenarios side by side',
    aliases: ['compare', 'diff'],
    icon: LibraryIcon,
    owner: 'BioRepo',
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
  '/molecules': '/dominion/molecules',
  '/protocols': '/runbooks/protocols',
  '/depositions': '/runbooks/depositions',
  '/witness': '/biorepo/witness',
  '/clearance': '/dominion/clearance',

  // ── OF-BLD-008: paths that moved between owners ─────────────────────
  '/biorepo/papers': '/biorepo/paper',
  '/biorepo/ingest': '/intake/ingest',
  '/proforma/compare': '/biorepo/compare',

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
  // /proforma/sc-s1 → /proforma/scenario/sc-s1 (but not /proforma/scenario/…)
  [/^\/proforma\/(?!scenario(?:\/|$))([^/]+)$/, '/proforma/scenario/$1'],
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
