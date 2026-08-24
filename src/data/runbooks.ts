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
import { runbookLockHash } from '@/engine/lock';

const SEED: Runbook[] = [
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
        value: 'watch-variant',
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
    predictions: [
      {
        id: 'pr-taq-titre',
        label: 'Final titre',
        value: 8,
        unit: 'g/L',
        confidence: 'medium',
        basis:
          'Fed-batch model at 2,000 L, E. coli BL21(DE3) under T7 induction',
      },
      {
        id: 'pr-taq-recovery',
        label: 'Overall recovery',
        value: 62,
        unit: '%',
        confidence: 'medium',
        basis:
          'Seven-step train; thermal clarification recovery taken from Taq-class precedent',
      },
      {
        id: 'pr-taq-endo',
        label: 'Endotoxin at release',
        value: 5,
        unit: 'EU/mg',
        confidence: 'medium',
        basis:
          'IEX plus HIC plus dedicated endotoxin clearance, RUO grade',
      },
      {
        id: 'pr-taq-dna',
        label: 'Residual host DNA',
        value: 10,
        unit: 'pg/U',
        confidence: 'low',
        basis:
          'Nuclease clearance is the defining step for this grade and is not calibrated here',
      },
      {
        id: 'pr-taq-capex',
        label: 'Installed capital',
        value: 4200000,
        unit: 'USD',
        confidence: 'low',
        basis:
          'Equipment and CAPEX stage has not run; figure is a placeholder to be tested',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-taq-od',
        label: 'Cell density at harvest',
        unit: 'OD600',
        timepoint: 'harvest',
        predictionId: null,
      },
      {
        id: 'ms-taq-titre',
        label: 'Titre at harvest',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-taq-titre',
      },
      {
        id: 'ms-taq-mass',
        label: 'Purified mass',
        unit: 'g',
        timepoint: 'post-purification',
        predictionId: null,
      },
      {
        id: 'ms-taq-recovery',
        label: 'Overall recovery',
        unit: '%',
        timepoint: 'post-purification',
        predictionId: 'pr-taq-recovery',
      },
      {
        id: 'ms-taq-act',
        label: 'Specific activity',
        unit: 'U/mg',
        timepoint: 'release',
        predictionId: null,
      },
      {
        id: 'ms-taq-endo',
        label: 'Endotoxin',
        unit: 'EU/mg',
        timepoint: 'release',
        predictionId: 'pr-taq-endo',
      },
      {
        id: 'ms-taq-dna',
        label: 'Residual host DNA',
        unit: 'pg/U',
        timepoint: 'release',
        predictionId: 'pr-taq-dna',
      },
    ],
    lockedAt: '2026-08-18T09:12:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-lnfp-titre',
        label: 'Final titre',
        value: 12,
        unit: 'g/L',
        confidence: 'low',
        basis:
          'HMO fed-batch precedent; this route has not been modelled',
      },
      {
        id: 'pr-lnfp-purity',
        label: 'Purity after desalting',
        value: 94,
        unit: '%',
        confidence: 'low',
        basis:
          'Electrodialysis plus nanofiltration, literature typical',
      },
      {
        id: 'pr-lnfp-routes',
        label: 'Viable route configurations',
        value: 1400,
        unit: 'configurations',
        confidence: 'low',
        basis:
          'Route enumeration estimate; the enumeration has not been run',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-lnfp-titre',
        label: 'Titre at harvest',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-lnfp-titre',
      },
      {
        id: 'ms-lnfp-purity',
        label: 'Purity after desalting',
        unit: '%',
        timepoint: 'post-purification',
        predictionId: 'pr-lnfp-purity',
      },
      {
        id: 'ms-lnfp-lactose',
        label: 'Residual lactose',
        unit: 'g/L',
        timepoint: 'post-purification',
        predictionId: null,
      },
    ],
    lockedAt: null,
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-braz-titre',
        label: 'Final titre',
        value: 2.4,
        unit: 'g/L',
        confidence: 'high',
        basis:
          'AOX1 methanol-induced fed-batch with alpha-MF secretion, pilot-scale precedent',
      },
      {
        id: 'pr-braz-capex',
        label: 'Installed capital',
        value: 1800000,
        unit: 'USD',
        confidence: 'medium',
        basis:
          'Equipment list costed at 2,000 L with a spray-dry finish',
      },
      {
        id: 'pr-braz-recovery',
        label: 'Overall recovery',
        value: 71,
        unit: '%',
        confidence: 'high',
        basis:
          'Centrifuge, MF, UF/DF, IEX, spray dry',
      },
      {
        id: 'pr-braz-sweet',
        label: 'Sweetness potency',
        value: 800,
        unit: 'x sucrose',
        confidence: 'medium',
        basis:
          'Reported range for brazzein; assayed at release',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-braz-titre',
        label: 'Titre at harvest',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-braz-titre',
      },
      {
        id: 'ms-braz-recovery',
        label: 'Overall recovery',
        unit: '%',
        timepoint: 'post-purification',
        predictionId: 'pr-braz-recovery',
      },
      {
        id: 'ms-braz-sweet',
        label: 'Sweetness potency',
        unit: 'x sucrose',
        timepoint: 'release',
        predictionId: 'pr-braz-sweet',
      },
      {
        id: 'ms-braz-moisture',
        label: 'Residual moisture',
        unit: '%',
        timepoint: 'release',
        predictionId: null,
      },
    ],
    lockedAt: '2026-07-02T11:40:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-diag-titre',
        label: 'Soluble titre',
        value: 1.1,
        unit: 'g/L',
        confidence: 'medium',
        basis:
          'MBP fusion in BL21(DE3); resolved from a prior run on the same host and train',
      },
      {
        id: 'pr-diag-purity',
        label: 'Purity at release',
        value: 95,
        unit: '%',
        confidence: 'medium',
        basis:
          'IMAC then SEC, IVD component specification',
      },
      {
        id: 'pr-diag-endo',
        label: 'Endotoxin at release',
        value: 1,
        unit: 'EU/mg',
        confidence: 'medium',
        basis:
          'Dedicated endotoxin clearance step, cached from the prior run',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-diag-titre',
        label: 'Soluble titre',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-diag-titre',
      },
      {
        id: 'ms-diag-purity',
        label: 'Purity',
        unit: '%',
        timepoint: 'post-purification',
        predictionId: 'pr-diag-purity',
      },
      {
        id: 'ms-diag-endo',
        label: 'Endotoxin',
        unit: 'EU/mg',
        timepoint: 'release',
        predictionId: 'pr-diag-endo',
      },
    ],
    lockedAt: '2026-08-05T14:05:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-chym-imcu',
        label: 'Milk-clotting activity',
        value: 1200,
        unit: 'IMCU/mg',
        confidence: 'medium',
        basis:
          'Predicted across 41 chymosin orthologs against a camel-type parent',
      },
      {
        id: 'pr-chym-ratio',
        label: 'Clotting-to-proteolysis ratio',
        value: 3.2,
        unit: 'ratio',
        confidence: 'medium',
        basis:
          'The property that decides whether the enzyme is usable, not the titre',
      },
      {
        id: 'pr-chym-titre',
        label: 'Secreted titre',
        value: 1.6,
        unit: 'g/L',
        confidence: 'medium',
        basis:
          'A. oryzae secretion with a strong native promoter',
      },
      {
        id: 'pr-chym-free',
        label: 'Candidates outside the claimed identity band',
        value: 38,
        unit: 'candidates',
        confidence: 'low',
        basis:
          'Boundary map: 3 of 41 sit close to the band and are held for human review',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-chym-titre',
        label: 'Secreted titre',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-chym-titre',
      },
      {
        id: 'ms-chym-imcu',
        label: 'Milk-clotting activity',
        unit: 'IMCU/mg',
        timepoint: 'post-purification',
        predictionId: 'pr-chym-imcu',
      },
      {
        id: 'ms-chym-ratio',
        label: 'Clotting-to-proteolysis ratio',
        unit: 'ratio',
        timepoint: 'post-purification',
        predictionId: 'pr-chym-ratio',
      },
    ],
    lockedAt: '2026-08-11T08:30:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-noot-titre',
        label: 'Nootkatone titre',
        value: 1.2,
        unit: 'g/L',
        confidence: 'low',
        basis:
          'MVA flux model; the P450 conversion is the bottleneck and is not calibrated',
      },
      {
        id: 'pr-noot-val',
        label: 'Valencene intermediate',
        value: 3.5,
        unit: 'g/L',
        confidence: 'low',
        basis:
          'Upstream of the P450 step, so it accumulates when conversion lags',
      },
      {
        id: 'pr-noot-purity',
        label: 'Fragrance-grade purity',
        value: 98,
        unit: '%',
        confidence: 'medium',
        basis:
          'LLE then distillation; grade is set by the rectification cut',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-noot-val',
        label: 'Valencene at harvest',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-noot-val',
      },
      {
        id: 'ms-noot-titre',
        label: 'Nootkatone at harvest',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: 'pr-noot-titre',
      },
      {
        id: 'ms-noot-purity',
        label: 'Purity after distillation',
        unit: '%',
        timepoint: 'post-purification',
        predictionId: 'pr-noot-purity',
      },
    ],
    lockedAt: '2026-08-19T16:20:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-lig-cands',
        label: 'Candidates above the thermostability threshold',
        value: 45,
        unit: 'candidates',
        confidence: 'medium',
        basis:
          'Predicted Tm at or above 85 C across the 112 unpublished homologs',
      },
      {
        id: 'pr-lig-tm',
        label: 'Best-candidate melting temperature',
        value: 92,
        unit: 'C',
        confidence: 'low',
        basis:
          'Structure-free Tm prediction with no experimental anchor in this set',
      },
      {
        id: 'pr-lig-act',
        label: 'Activity retained after 30 min at 95 C',
        value: 70,
        unit: '%',
        confidence: 'low',
        basis:
          'Predicted, not measured. This is the claim the assay exists to test',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-lig-sol',
        label: 'Candidates expressing solubly',
        unit: 'candidates',
        timepoint: 'harvest',
        predictionId: null,
      },
      {
        id: 'ms-lig-tm',
        label: 'Measured Tm',
        unit: 'C',
        timepoint: 'post-purification',
        predictionId: 'pr-lig-tm',
      },
      {
        id: 'ms-lig-act',
        label: 'Residual activity after 95 C',
        unit: '%',
        timepoint: 'post-purification',
        predictionId: 'pr-lig-act',
      },
      {
        id: 'ms-lig-pass',
        label: 'Candidates above threshold on assay',
        unit: 'candidates',
        timepoint: 'post-purification',
        predictionId: 'pr-lig-cands',
      },
    ],
    lockedAt: '2026-08-14T10:00:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-sial-cands',
        label: 'Candidates outside the claimed structure',
        value: 240,
        unit: 'candidates',
        confidence: 'medium',
        basis:
          'Structure-reciting claim, enumerated across the 8,900 retrieved sequences',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-sial-cands',
        label: 'Candidates confirmed active',
        unit: 'candidates',
        timepoint: 'post-purification',
        predictionId: 'pr-sial-cands',
      },
      {
        id: 'ms-sial-titre',
        label: 'Product titre',
        unit: 'g/L',
        timepoint: 'harvest',
        predictionId: null,
      },
    ],
    lockedAt: '2026-08-20T13:15:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-heme-escapes',
        label: 'Candidates falling outside the claim',
        value: 0,
        unit: 'candidates',
        confidence: 'high',
        basis:
          'The claim recites a functional class rather than a sequence, so molecular diversity does not escape it',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-heme-escapes',
        label: 'Candidates outside the claim on counsel review',
        unit: 'candidates',
        timepoint: 'analysis',
        predictionId: 'pr-heme-escapes',
      },
    ],
    lockedAt: '2026-06-28T09:00:00Z',
    lockHash: null,
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
    predictions: [
      {
        id: 'pr-lyo-share',
        label: 'Share of the enzyme panel tolerating lyophilisation',
        value: 60,
        unit: '%',
        confidence: 'low',
        basis:
          'Prior art on lyophilised molecular-biology enzymes; no panel has been run',
      },
      {
        id: 'pr-lyo-shelf',
        label: 'Shelf life at 25 C',
        value: 18,
        unit: 'months',
        confidence: 'low',
        basis:
          'Accelerated-stability extrapolation, not measured',
      },
    ],
    measurementSchema: [
      {
        id: 'ms-lyo-act',
        label: 'Activity retained after lyophilisation',
        unit: '%',
        timepoint: 'post-lyophilisation',
        predictionId: 'pr-lyo-share',
      },
      {
        id: 'ms-lyo-shelf',
        label: 'Activity at 12 months ambient',
        unit: '%',
        timepoint: 't=12 months',
        predictionId: 'pr-lyo-shelf',
      },
    ],
    lockedAt: null,
    lockHash: null,
  },
];

/**
 * Lock hashes are computed here rather than authored into the literals above.
 *
 * A hand-written hash is a hash nobody can check and everybody will eventually
 * get wrong: edit a prediction, forget the digest, and the fixture ships
 * claiming an integrity it does not have. Computing it at module load means
 * the seed cannot lie about itself, and check-seed still recomputes
 * independently so a broken hash function would not hide behind its own
 * output.
 */
export const RUNBOOKS: Runbook[] = SEED.map((r) =>
  r.lockedAt ? { ...r, lockHash: runbookLockHash(r.predictions, r.measurementSchema) } : r,
);

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
