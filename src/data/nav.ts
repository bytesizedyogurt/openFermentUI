// The navigation vocabulary (OF-BLD-006 §2.2, as reversed).
//
// THE REVERSAL. OF-BLD-006 originally held that component names were for
// building the system and nav labels were for using it — "Ask" in the rail,
// "Postdoc" only in attribution. That was wrong for these users. Researchers
// acquire domain vocabulary constantly and will use this daily; a precise name
// learned once beats a generic one re-read forever. "Ask" tells you the verb
// and nothing about what you are talking to. "Postdoc" tells you what it is:
// something that plans, retrieves, and shows its working, and that you can
// hand a half-formed question to.
//
// So the component names ARE the user-facing vocabulary, and this module is
// the single place they are written down. The rail, the command palette, the
// Architecture map and the smoke tests all read from here, so the product and
// the codebase cannot drift into two vocabularies.
//
// Three things make an invented word learnable rather than hostile, and all
// three are in this file rather than left to each screen:
//   - a descriptor, so a first-time viewer is never facing a bare coinage;
//   - an alias, so typing the old word in the palette still finds the thing;
//   - a redirect, so an old link lands on the new screen instead of a 404.
import {
  Boxes,
  ClipboardList,
  FlaskConical,
  GitBranch,
  GraduationCap,
  Home as HomeIcon,
  LineChart,
  Library as LibraryIcon,
  MessagesSquare,
  Ruler,
  ScrollText,
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
   * One line of gloss (§7). Eight invented words with no explanation is
   * friction the names do not earn on first contact, and this is the cheapest
   * possible fix: the descriptor sits under the label in the rail and in the
   * title attribute when the rail is collapsed.
   */
  descriptor: string;
  /**
   * Old words that must still resolve in search (§6). People will type "ask"
   * and "library" for a while — probably months — and search must not punish
   * them for it.
   */
  aliases: string[];
  icon: LucideIcon;
  /** The component this surface is, when it is one. */
  component?: ComponentName;
}

/**
 * The left rail, in order. Ten items, which is the cap.
 *
 * Organisms, Molecules and Protocols keep their plain names: they are
 * catalogue views of domain objects a biologist already has words for, not
 * components. Renaming a list of strains would be coining for its own sake.
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
    label: 'Postdoc',
    to: '/postdoc',
    descriptor: 'ask and orchestrate',
    aliases: ['ask', 'chat', 'agent'],
    icon: MessagesSquare,
    component: 'Postdoc',
    key: 'o',
  },
  {
    label: 'BioRepo',
    to: '/biorepo',
    descriptor: 'papers and records',
    aliases: ['library', 'corpus', 'papers'],
    icon: LibraryIcon,
    component: 'BioRepo',
    key: 'b',
  },
  {
    label: 'Intake',
    to: '/intake',
    descriptor: 'extract and review',
    aliases: ['extract', 'extraction', 'records'],
    icon: Table2,
    component: 'Intake',
    key: 'i',
  },
  {
    label: 'Organisms',
    to: '/organisms',
    descriptor: 'strains and hosts',
    aliases: ['strains', 'hosts'],
    icon: FlaskConical,
    key: 'g',
  },
  {
    label: 'Molecules',
    to: '/molecules',
    descriptor: 'targets and markets',
    aliases: ['products', 'targets'],
    icon: Boxes,
    key: 'm',
  },
  {
    label: 'Protocols',
    to: '/protocols',
    descriptor: 'methods to run',
    aliases: ['methods', 'sops'],
    icon: ClipboardList,
    key: 'p',
  },
  {
    label: 'Runbooks',
    to: '/runbooks',
    descriptor: 'claims to be tested',
    aliases: ['claims', 'predictions'],
    icon: GitBranch,
    component: 'Runbook',
    key: 'r',
  },
  {
    label: 'Proforma',
    to: '/proforma',
    descriptor: 'cost and scale',
    aliases: ['simulate', 'simulation', 'economics', 'cost'],
    icon: LineChart,
    component: 'Proforma',
    key: 'f',
  },
  {
    label: 'Primer',
    to: '/primer',
    descriptor: 'learn the system',
    aliases: ['learn', 'lessons', 'tutorial'],
    icon: GraduationCap,
    component: 'Primer',
    key: 'n',
  },
];

/**
 * Named surfaces that do not earn a rail slot but are still destinations with
 * a name of their own. Deposition is here rather than in the rail because it
 * is launched from a Runbook and takes the whole screen when it is.
 */
export const OFF_RAIL: NavSurface[] = [
  {
    label: 'Guild',
    to: '/guild',
    descriptor: 'who may verify',
    aliases: ['review', 'review queue', 'triage', 'guild of applied life'],
    icon: Users,
    component: 'Guild',
  },
  {
    label: 'Witness',
    to: '/witness',
    descriptor: 'does it reproduce',
    aliases: ['validation', 'gold set', 'metrics'],
    icon: ScrollText,
    component: 'Witness',
  },
  {
    label: 'Deposition',
    to: '/depositions',
    descriptor: 'bench capture',
    aliases: ['run mode', 'run', 'bench'],
    icon: Ruler,
    component: 'Deposition',
  },
];

export const ALL_SURFACES: NavSurface[] = [...RAIL, ...OFF_RAIL];

/** Descriptor by label, for screens that want to print their own gloss. */
export const DESCRIPTOR: Record<string, string> = Object.fromEntries(
  ALL_SURFACES.map((s) => [s.label, s.descriptor]),
);

/**
 * Old path → new path (§8).
 *
 * Deep-linked demo scripts, bookmarks, and the odd screenshot caption all
 * point at the old words. A rename that 404s them is a rename that punishes
 * the people who used the thing most.
 *
 * Exact entries are matched first, because `/extract/review` moved to a
 * different screen than `/extract` did — the review queue became Guild, which
 * is not under Intake at all.
 */
export const REDIRECTS: Record<string, string> = {
  '/extract/review': '/guild',
  '/extract/validation': '/witness',
  '/ask': '/postdoc',
  '/library': '/biorepo',
  '/extract': '/intake',
  '/simulate': '/proforma',
  '/learn': '/primer',
  '/review': '/guild',
  '/validation': '/witness',
};

/**
 * Where an old path should land, or null if it is already current.
 *
 * The tail is preserved, so `/library/papers/H4` becomes `/biorepo/papers/H4`
 * rather than dumping the reader at the top of the corpus and making them find
 * their paper again.
 */
export function redirectFor(path: string): string | null {
  const exact = REDIRECTS[path];
  if (exact) return exact;
  const first = path.split('/').filter(Boolean)[0];
  if (!first) return null;
  const prefix = `/${first}`;
  const to = REDIRECTS[prefix];
  if (!to) return null;
  return to + path.slice(prefix.length);
}
