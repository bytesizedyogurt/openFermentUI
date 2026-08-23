// Runbooks (OF-BLD-005 §7) — a synthesised, followable answer to a question
// about making something.
//
// A runbook is NOT a Job. `Job` (types.ts) models a progress bar: stages, an
// index, a fraction, and a terminal status, owned by the jobs tray and thrown
// away when it finishes. A `Runbook` is a record with content that outlives
// the run which produced it — the stages carry findings, not just percentages.
// The tray still supplies the running affordance for a live runbook; the two
// types cooperate rather than merge.
//
// Two kinds share one toolchain. An **industrial** runbook answers "how would
// we make this" and outputs a process you could build and defend. A
// **research** runbook answers an open question and outputs a prediction plus
// the experiments that would test it. A research runbook that finds something
// is promotable to an industrial one in a single action.
//
// The ten seeded runbooks sit across all seven states at once, so the board
// shows what each state looks like without anyone having to wait for a run.
import type { Runbook, RunbookStatus } from './types';

export const RUNBOOKS: Runbook[] = [
  {
    id: 'rb-taq-kigali',
    kind: 'industrial',
    title: 'Taq polymerase — 2,000 L Kigali facility',
    status: 'running',
    stages: [
      {
        name: 'Clearance sweep',
        status: 'done',
        detail: 'Foundational composition IP expired; 3 variant families flagged',
        value: 'clear-variant',
      },
      {
        name: 'Host & construct selection',
        status: 'done',
        detail: 'E. coli BL21(DE3), T7, His6-tagless via intein',
        value: null,
      },
      {
        name: 'Process train',
        status: 'done',
        detail: 'Homogenise → thermal clarification → IEX → HIC → nuclease clearance → lyophilise',
        value: null,
      },
      {
        name: 'Titre & yield model',
        status: 'running',
        detail: 'fed-batch, 8 g/L target',
        value: null,
      },
      {
        name: 'Equipment & CAPEX',
        status: 'pending',
        detail: null,
        value: null,
      },
      {
        name: 'Quality spec',
        status: 'pending',
        detail: 'endotoxin, nuclease, specific activity',
        value: null,
      },
      {
        name: 'Storage & export',
        status: 'pending',
        detail: '50% glycerol -20 °C vs lyophilised ambient — the cold-chain decision',
        value: null,
      },
    ],
    note:
      'The flagship industrial case. Thermal clarification collapses most chromatography cost because the product survives 75 °C and the host proteome does not.',
    eta: '~40 min',
    outputs: [],
    productId: 'taq-dna-polymerase',
    progressPct: 62,
    estCostUsd: 48,
    strainId: 'ecoli',
  },
  {
    id: 'rb-lnfp1',
    kind: 'industrial',
    title: 'LNFP-I — process definition',
    status: 'awaiting_budget',
    stages: [
      {
        name: 'Clearance sweep',
        status: 'done',
        detail: 'Live blocking claims on transporter and purification',
        value: 'blocked',
      },
      {
        name: 'Pathway configuration',
        status: 'queued',
        detail: 'CMP-Neu5Ac + fucosyltransferase branch',
        value: null,
      },
      {
        name: 'Route enumeration',
        status: 'queued',
        detail: 'est. 1,400 candidate configurations',
        value: null,
      },
      {
        name: 'Downstream train',
        status: 'pending',
        detail: null,
        value: null,
      },
    ],
    note:
      'Blocked clearance means the industrial runbook cannot proceed as-is. Offers to hand off to a research runbook that enumerates around the fence.',
    eta: '~6 h',
    outputs: [],
    productId: 'lnfpi',
    progressPct: 0,
    estCostUsd: 310,
    strainId: 'ecoli',
  },
  {
    id: 'rb-brazzein',
    kind: 'industrial',
    title: 'Brazzein — pilot process',
    status: 'complete',
    stages: [
      {
        name: 'Clearance sweep',
        status: 'done',
        detail: 'Application claims live; composition space open',
        value: 'watch-variant',
      },
      {
        name: 'Host & construct',
        status: 'done',
        detail: 'K. phaffii, AOX1, alpha-MF secretion',
        value: null,
      },
      {
        name: 'Process train',
        status: 'done',
        detail: 'Centrifuge → MF → UF/DF → IEX → spray dry',
        value: null,
      },
      {
        name: 'Titre model',
        status: 'done',
        detail: null,
        value: '2.4 g/L',
      },
      {
        name: 'CAPEX',
        status: 'done',
        detail: null,
        value: '$1.8M at 2,000 L',
      },
      {
        name: 'Quality spec',
        status: 'done',
        detail: null,
        value: null,
      },
      {
        name: 'Storage & export',
        status: 'done',
        detail: 'Spray-dried ambient — no cold chain',
        value: null,
      },
    ],
    note: 'Worked example. Open this first — it shows what a finished industrial runbook contains.',
    eta: null,
    outputs: ['Process flow diagram', 'Equipment list', 'Quality spec', 'Clearance summary'],
    productId: 'brazzein',
    progressPct: 100,
    estCostUsd: 71,
    strainId: 'gs115',
  },
  {
    id: 'rb-diag-panel',
    kind: 'industrial',
    title: 'Malaria antigen panel — regional supply',
    status: 'cache_hit',
    stages: [
      {
        name: 'Clearance sweep',
        status: 'done',
        detail: 'No blocking claims found',
        value: 'clear-none',
      },
      {
        name: 'Host & construct',
        status: 'done',
        detail: 'E. coli BL21(DE3), MBP fusion',
        value: null,
      },
      {
        name: 'Process train',
        status: 'done',
        detail: 'Homogenise → IMAC → SEC → endotoxin clearance → lyophilise',
        value: null,
      },
      {
        name: 'Storage & export',
        status: 'done',
        detail: 'Lyophilised ambient',
        value: null,
      },
    ],
    note:
      'Resolved from BioRepo — a prior run covered the same host/train. Near-zero cost. This is why artifact caching matters.',
    eta: null,
    outputs: [],
    productId: 'malaria-recombinant-antigens',
    progressPct: 100,
    estCostUsd: 0.8,
    strainId: 'ecoli',
  },
  {
    id: 'rb-chymosin',
    kind: 'industrial',
    title: 'Camel chymosin — variant landscape',
    status: 'needs_review',
    stages: [
      {
        name: 'Clearance sweep',
        status: 'done',
        detail: 'Modern variant claims recite sequence — enumerable',
        value: 'watch-variant',
      },
      {
        name: 'Ortholog survey',
        status: 'done',
        detail: null,
        value: '41 chymosin orthologs',
      },
      {
        name: 'Clotting-ratio prediction',
        status: 'done',
        detail: null,
        value: null,
      },
      {
        name: 'Boundary map',
        status: 'review',
        detail: '3 candidates sit close to a claimed identity band',
        value: null,
      },
    ],
    note:
      'Held for human review. Candidates near a claim boundary are exactly what a person, not a model, should rule on.',
    eta: null,
    outputs: [],
    productId: 'chymosin',
    progressPct: 84,
    estCostUsd: 26,
    strainId: 'a-niger',
  },
  {
    id: 'rb-nootkatone',
    kind: 'industrial',
    title: 'Nootkatone — fragrance-grade train',
    status: 'running',
    stages: [
      {
        name: 'Clearance sweep',
        status: 'done',
        detail: 'Process claims live on one route',
        value: 'watch-process',
      },
      {
        name: 'Pathway flux',
        status: 'running',
        detail: 'MVA → FPP → valencene synthase → P450',
        value: null,
      },
      {
        name: 'Recovery train',
        status: 'pending',
        detail: 'LLE → distillation',
        value: null,
      },
      {
        name: 'Grade specification',
        status: 'pending',
        detail: '70 / 80 / 95 / 98%',
        value: null,
      },
    ],
    note:
      'Different downstream equipment entirely from the protein platform — separate facility line.',
    eta: '~50 min',
    outputs: [],
    productId: 'nootkatone',
    progressPct: 31,
    estCostUsd: 39,
    strainId: 's-cerevisiae',
  },
  {
    id: 'rb-thermo-ligase',
    kind: 'research',
    title: 'Thermostable ligase — homolog discovery',
    status: 'running',
    stages: [
      {
        name: 'Novelty scan',
        status: 'done',
        detail: '112 of 3,400 candidates unpublished',
        value: null,
      },
      {
        name: 'Homolog retrieval',
        status: 'done',
        detail: null,
        value: '3,400 sequences',
      },
      {
        name: 'Thermostability prediction',
        status: 'running',
        detail: null,
        value: null,
      },
      {
        name: 'Activity prediction',
        status: 'pending',
        detail: null,
        value: null,
      },
      {
        name: 'Enablement package',
        status: 'pending',
        detail: null,
        value: null,
      },
    ],
    note: 'Hypothesis-driven. Same toolchain as the industrial runbooks, different question.',
    eta: '~2 h',
    outputs: [],
    productId: 'thermostable-dna-ligase',
    progressPct: 47,
    estCostUsd: 63,
    strainId: 'ecoli',
  },
  {
    id: 'rb-sialyl-genus',
    kind: 'research',
    title: 'Sialyltransferase genus enumeration',
    status: 'blocked_unverified',
    stages: [
      {
        name: 'Claim classification',
        status: 'done',
        detail: 'Structure-reciting — enumerable',
        value: null,
      },
      {
        name: 'Homolog retrieval',
        status: 'done',
        detail: null,
        value: '8,900 sequences',
      },
      {
        name: 'Titre estimate',
        status: 'blocked',
        detail: 'Input titre figure has no source',
        value: null,
      },
      {
        name: 'Cascade',
        status: 'pending',
        detail: null,
        value: null,
      },
    ],
    note:
      'Halted: a downstream stage tried to consume an unsourced number. Shows the provenance check working. Resolve by attaching a source or marking the value as an assumption.',
    eta: null,
    outputs: [],
    productId: '6sl',
    progressPct: 22,
    estCostUsd: 180,
    strainId: 'ecoli',
  },
  {
    id: 'rb-heme-calib',
    kind: 'research',
    title: 'Heme protein — claim calibration',
    status: 'complete',
    stages: [
      {
        name: 'Claim classification',
        status: 'done',
        detail: 'Application-reciting — enumeration would not help',
        value: null,
      },
      {
        name: 'Recommendation',
        status: 'done',
        detail: 'Do not schedule enumeration compute',
        value: null,
      },
    ],
    note:
      'Calibration case. A documented instance where a full cross-kingdom protein substitution still infringed, because the claim recited a functional class rather than a sequence. Kept as a reminder that claim architecture, not molecular diversity, decides whether enumeration is worth paying for.',
    eta: null,
    outputs: [],
    productId: 'human-lactoferrin',
    progressPct: 100,
    estCostUsd: 2,
    strainId: null,
  },
  {
    id: 'rb-lyo-ambient',
    kind: 'research',
    title: 'Ambient-stable formulation for export enzymes',
    status: 'draft',
    stages: [
      {
        name: 'Scope',
        status: 'draft',
        detail: 'Which molecular-biology enzymes tolerate lyophilisation without activity loss',
        value: null,
      },
    ],
    note:
      'Cross-cutting. Removing the cold chain changes the economics of every export product from a landlocked facility — arguably the highest-leverage question on the board.',
    eta: null,
    outputs: [],
    productId: null,
    progressPct: 0,
    estCostUsd: null,
    strainId: null,
  },
];

export const RUNBOOKS_BY_ID: Record<string, Runbook> = Object.fromEntries(
  RUNBOOKS.map((r) => [r.id, r]),
);

/**
 * Board column order and copy. Live work first, then the states that need a
 * decision from a person, then the finished and unstarted ones — a board is
 * read top-left first, so what is waiting on you should be there.
 */
export const RUNBOOK_STATUS_ORDER: RunbookStatus[] = [
  'running',
  'blocked_unverified',
  'needs_review',
  'awaiting_budget',
  'complete',
  'cache_hit',
  'draft',
];

export const RUNBOOK_STATUS_LABEL: Record<RunbookStatus, string> = {
  running: 'Running',
  blocked_unverified: 'Blocked · unverified input',
  needs_review: 'Held for review',
  awaiting_budget: 'Awaiting budget',
  complete: 'Complete',
  cache_hit: 'Resolved from cache',
  draft: 'Draft',
};

/** One line saying what the state means, shown under each board column. */
export const RUNBOOK_STATUS_NOTE: Record<RunbookStatus, string> = {
  running: 'Compute is in flight. Stages fill in as they resolve.',
  blocked_unverified:
    'A stage tried to consume a value with no source. Attach one, or mark the value an explicit assumption, and the cascade continues.',
  needs_review: 'A person, not a model, should rule on what this found.',
  awaiting_budget: 'Priced but not authorised. Nothing runs until someone says yes.',
  complete: 'Every stage resolved. The outputs are the deliverable.',
  cache_hit: 'Resolved from prior artifacts in BioRepo at near-zero cost.',
  draft: 'Scoped but not started.',
};

/** Runbooks attached to a product — the Molecules cross-link. */
export function runbooksForProduct(productId: string): Runbook[] {
  return RUNBOOKS.filter((r) => r.productId === productId);
}

/** Runbooks whose chosen host is a given strain — the Organisms cross-link. */
export function runbooksForStrain(strainId: string): Runbook[] {
  return RUNBOOKS.filter((r) => r.strainId === strainId);
}
