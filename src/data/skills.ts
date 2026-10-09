// Skills (OF-BLD-013 §1.1): the trunk competencies Guild records and the
// run-mode gate checks.
//
// PLACEHOLDER CONTENT. These fourteen are drawn from the steps of three seeded
// protocols, PR-CIP-01, PR-OD-01 and PR-SEED-01, and each mastery criterion
// restates something one of those steps asks an operator to do, written as a
// behaviour an assessor can see. The real taxonomy comes with the skills
// content pass; until then the families are working names and the ids are the
// only part meant to last. `check:seed` holds the file to its invariants: ids
// unique, families known, prerequisites resolving and acyclic, every step tag
// naming a skill that exists here.
//
// Reference data, like a protocol. Nothing mutates it at runtime; a change is a
// commit, so the ledger's entries always point at a definition someone can
// read in the history.
import type { Skill, SkillFamily } from './types';

export const FAMILIES: SkillFamily[] = [
  { id: 'contamination', name: 'Contamination control', short: 'Contamination' },
  { id: 'vessel', name: 'Vessel operation', short: 'Vessel' },
  { id: 'monitoring', name: 'Process monitoring', short: 'Monitoring' },
  { id: 'qc', name: 'Sampling and QC', short: 'Sampling and QC' },
  { id: 'records', name: 'Batch records', short: 'Records' },
  { id: 'safety', name: 'Safety and troubleshooting', short: 'Safety' },
];

export const SKILLS: Skill[] = [
  {
    id: 'SK-ASEP',
    name: 'Aseptic transfer',
    family: 'contamination',
    summary: 'Moving culture or medium between vessels without letting anything else in.',
    mastery: [
      'Works within 150 mm of the burner for every open transfer',
      'Opens and reseats plugs and caps without touching inner surfaces',
      'Clears the loop or pipette fully into the medium before withdrawing',
      'Leaves stage 2 unopened for its first day',
    ],
    criticality: 'critical',
    recencyDays: 90,
    supervisedRuns: 3,
    prerequisites: [],
  },
  {
    id: 'SK-STER',
    name: 'Vessel sterilisation',
    family: 'contamination',
    summary: 'Autoclaving an assembled vessel so the cycle can be trusted and traced.',
    mastery: [
      'Fits fresh inlet and exhaust filters before loading',
      'Places the spore strip in the vessel and marks the headplate with indicator tape',
      'Runs the cycle at 121 °C for 45 min with the vent open',
      'Breaks no connection until the chamber reads below 80 °C at zero gauge pressure',
    ],
    criticality: 'critical',
    recencyDays: 120,
    supervisedRuns: 2,
    prerequisites: ['SK-PRESS'],
  },
  {
    id: 'SK-HOLD',
    name: 'Sterility release',
    family: 'contamination',
    summary: 'Deciding whether a sterilised vessel may be released for the next run.',
    mastery: [
      'Holds the vessel at 30 °C for 24 h and reads the hold water',
      'Incubates the spore strip at 55 °C for 48 h and reads it',
      'Releases only when both results are clear and written on the vessel log',
    ],
    criticality: 'critical',
    recencyDays: 120,
    supervisedRuns: 2,
    prerequisites: ['SK-STER'],
  },
  {
    id: 'SK-ISOL',
    name: 'Isolation and drain',
    family: 'vessel',
    summary: 'Making a vessel safe to open before any fitting is touched.',
    mastery: [
      'Works the isolation checklist in order before touching a fitting',
      'Bleeds the gas line and isolates the jacket circuit',
      'Confirms atmospheric pressure through the vent filter',
      'Confirms the drain valve is closed after draining',
    ],
    criticality: 'critical',
    recencyDays: 90,
    supervisedRuns: 2,
    prerequisites: ['SK-PRESS'],
  },
  {
    id: 'SK-CIP',
    name: 'Clean-in-place cycle',
    family: 'vessel',
    summary: 'Running the caustic, rinse and acid sequence through every dead leg.',
    mastery: [
      'Pre-rinses until the effluent runs clear',
      'Recirculates detergent at 60 °C through the spray ball and every dead leg for 20 min',
      'Verifies the rinse is neutral on the conductivity and pH meters before acid',
      'Rinses to neutral again after the acid step',
    ],
    criticality: 'critical',
    recencyDays: 90,
    supervisedRuns: 3,
    prerequisites: ['SK-CAUSTIC'],
  },
  {
    id: 'SK-ASSY',
    name: 'Strip, inspect, reassemble',
    family: 'vessel',
    summary: 'Taking a vessel apart and putting it back the same way, with fresh seals.',
    mastery: [
      'Lays wetted parts out in the order they came off',
      'Replaces elastomers on the fixed cycle',
      'Torques headplate bolts in a diagonal sequence to the manufacturer figure',
      'Records the impeller and sparger configuration fitted',
    ],
    criticality: 'routine',
    recencyDays: 180,
    supervisedRuns: 2,
    prerequisites: [],
  },
  {
    id: 'SK-PROBE',
    name: 'Probe service',
    family: 'monitoring',
    summary: 'Calibrating pH and charging the dissolved-oxygen electrode.',
    mastery: [
      'Calibrates pH against both buffers and records the slope on the vessel log',
      'Charges the DO electrode with fresh electrolyte and fits a new membrane',
      'Checks the probe data sheet before discarding spent electrolyte',
    ],
    criticality: 'routine',
    recencyDays: 90,
    supervisedRuns: 2,
    prerequisites: [],
  },
  {
    id: 'SK-ENV',
    name: 'Culture environment set-up',
    family: 'monitoring',
    summary: 'Setting and recording temperature, light and shaking before a seed train.',
    mastery: [
      'Verifies enclosure temperature before dispensing medium',
      'Measures light at the working liquid depth',
      'Records the shaking speed as a process parameter',
    ],
    criticality: 'routine',
    recencyDays: 180,
    supervisedRuns: 1,
    prerequisites: [],
  },
  {
    id: 'SK-OD',
    name: 'OD750 reading',
    family: 'qc',
    summary: 'Reading optical density so the number means what it says.',
    mastery: [
      'Inverts each sample three times immediately before reading',
      'Blanks against spent cell-free medium',
      'Dilutes into the linear range with the same spent medium',
    ],
    criticality: 'routine',
    recencyDays: 60,
    supervisedRuns: 3,
    prerequisites: [],
  },
  {
    id: 'SK-DCW',
    name: 'Dry cell weight',
    family: 'qc',
    summary: 'Gravimetric biomass on tared filters with blank correction.',
    mastery: [
      'Tares dried filters and records each against its rack position',
      'Runs four blank filters through the identical wash and dry cycle',
      'Keeps the bed wet between sample and wash',
      'Re-weighs until the mass has stopped falling',
    ],
    criticality: 'routine',
    recencyDays: 120,
    supervisedRuns: 2,
    prerequisites: [],
  },
  {
    id: 'SK-FACTOR',
    name: 'OD-to-DCW factor',
    family: 'qc',
    summary: 'Determining the conversion factor for one strain and one set of conditions.',
    mastery: [
      'Regresses dry cell weight on OD750 through the origin over the linear range',
      'Reports the slope with its interval, strain, wavelength, growth phase and point count',
      'Enters the factor as a user measurement with the run identifier',
    ],
    criticality: 'routine',
    recencyDays: 365,
    supervisedRuns: 1,
    prerequisites: ['SK-OD', 'SK-DCW'],
  },
  {
    id: 'SK-LOG',
    name: 'Vessel log and batch sheet',
    family: 'records',
    summary: 'Writing down what the step names, when it happens, with lots and identifiers.',
    mastery: [
      'Records every field the step names, at the time of the step',
      'Writes lot numbers and identifiers in full',
      'Signs the cycle off with the operator name',
    ],
    criticality: 'critical',
    recencyDays: 90,
    supervisedRuns: 2,
    prerequisites: [],
  },
  {
    id: 'SK-CAUSTIC',
    name: 'Caustic and acid handling',
    family: 'safety',
    summary: 'Working safely with CIP detergent and the acid rinse.',
    mastery: [
      'Wears face shield, apron and long-cuff gloves for the whole recirculation',
      'Never lets acid follow caustic without a rinse to neutral',
      'Knows the eye-splash response',
    ],
    criticality: 'critical',
    recencyDays: 180,
    supervisedRuns: 1,
    prerequisites: [],
  },
  {
    id: 'SK-PRESS',
    name: 'Pressure and heat safety',
    family: 'safety',
    summary: 'Never opening or moving anything that is still under pressure or hot.',
    mastery: [
      'Confirms atmospheric pressure and below 40 °C before loosening any triclamp',
      'Never autoclaves with a closed vent filter or clamped exhaust',
      'Lets the vessel stand before moving it and handles hot lines with gloves',
    ],
    criticality: 'critical',
    recencyDays: 180,
    supervisedRuns: 1,
    prerequisites: [],
  },
];

export const SKILL_BY_ID: Record<string, Skill> = Object.fromEntries(SKILLS.map((s) => [s.id, s]));

export const FAMILY_BY_ID: Record<string, SkillFamily> = Object.fromEntries(FAMILIES.map((f) => [f.id, f]));
