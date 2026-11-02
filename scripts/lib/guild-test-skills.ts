// TEST FIXTURE: the skills, skill families and step tags Guild's ladder and
// its checks run on (check:guild, export-competence-fixtures), in the shape of
// the alpha 1.0 seed (src/data/skills.ts and the three generic-method
// protocols that tagged them). The ids, families, criticality and the
// ladder's policy are kept; every summary and criterion is a placeholder, the
// authored text having left with the seed (alpha 2.0, ADR-010). The app ships
// with no skill: a lab adds its own (stage 2). Never imported under src/.
import type { Protocol, Skill } from '../../src/data/types';
import guildProjection from '../../core/tests/fixtures/guild-projection.json';

export const TEST_SKILLS: Skill[] = [
  {
    "id": "SK-ASEP",
    "name": "Aseptic transfer",
    "family": "contamination",
    "summary": "Test skill SK-ASEP (placeholder summary).",
    "mastery": [
      "Criterion A of SK-ASEP (placeholder).",
      "Criterion B of SK-ASEP (placeholder).",
      "Criterion C of SK-ASEP (placeholder).",
      "Criterion D of SK-ASEP (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 90,
    "supervisedRuns": 3,
    "prerequisites": []
  },
  {
    "id": "SK-STER",
    "name": "Vessel sterilisation",
    "family": "contamination",
    "summary": "Test skill SK-STER (placeholder summary).",
    "mastery": [
      "Criterion A of SK-STER (placeholder).",
      "Criterion B of SK-STER (placeholder).",
      "Criterion C of SK-STER (placeholder).",
      "Criterion D of SK-STER (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 120,
    "supervisedRuns": 2,
    "prerequisites": [
      "SK-PRESS"
    ]
  },
  {
    "id": "SK-HOLD",
    "name": "Sterility release",
    "family": "contamination",
    "summary": "Test skill SK-HOLD (placeholder summary).",
    "mastery": [
      "Criterion A of SK-HOLD (placeholder).",
      "Criterion B of SK-HOLD (placeholder).",
      "Criterion C of SK-HOLD (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 120,
    "supervisedRuns": 2,
    "prerequisites": [
      "SK-STER"
    ]
  },
  {
    "id": "SK-ISOL",
    "name": "Isolation and drain",
    "family": "vessel",
    "summary": "Test skill SK-ISOL (placeholder summary).",
    "mastery": [
      "Criterion A of SK-ISOL (placeholder).",
      "Criterion B of SK-ISOL (placeholder).",
      "Criterion C of SK-ISOL (placeholder).",
      "Criterion D of SK-ISOL (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 90,
    "supervisedRuns": 2,
    "prerequisites": [
      "SK-PRESS"
    ]
  },
  {
    "id": "SK-CIP",
    "name": "Clean-in-place cycle",
    "family": "vessel",
    "summary": "Test skill SK-CIP (placeholder summary).",
    "mastery": [
      "Criterion A of SK-CIP (placeholder).",
      "Criterion B of SK-CIP (placeholder).",
      "Criterion C of SK-CIP (placeholder).",
      "Criterion D of SK-CIP (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 90,
    "supervisedRuns": 3,
    "prerequisites": [
      "SK-CAUSTIC"
    ]
  },
  {
    "id": "SK-ASSY",
    "name": "Strip, inspect, reassemble",
    "family": "vessel",
    "summary": "Test skill SK-ASSY (placeholder summary).",
    "mastery": [
      "Criterion A of SK-ASSY (placeholder).",
      "Criterion B of SK-ASSY (placeholder).",
      "Criterion C of SK-ASSY (placeholder).",
      "Criterion D of SK-ASSY (placeholder)."
    ],
    "criticality": "routine",
    "recencyDays": 180,
    "supervisedRuns": 2,
    "prerequisites": []
  },
  {
    "id": "SK-PROBE",
    "name": "Probe service",
    "family": "monitoring",
    "summary": "Test skill SK-PROBE (placeholder summary).",
    "mastery": [
      "Criterion A of SK-PROBE (placeholder).",
      "Criterion B of SK-PROBE (placeholder).",
      "Criterion C of SK-PROBE (placeholder)."
    ],
    "criticality": "routine",
    "recencyDays": 90,
    "supervisedRuns": 2,
    "prerequisites": []
  },
  {
    "id": "SK-ENV",
    "name": "Culture environment set-up",
    "family": "monitoring",
    "summary": "Test skill SK-ENV (placeholder summary).",
    "mastery": [
      "Criterion A of SK-ENV (placeholder).",
      "Criterion B of SK-ENV (placeholder).",
      "Criterion C of SK-ENV (placeholder)."
    ],
    "criticality": "routine",
    "recencyDays": 180,
    "supervisedRuns": 1,
    "prerequisites": []
  },
  {
    "id": "SK-OD",
    "name": "OD750 reading",
    "family": "qc",
    "summary": "Test skill SK-OD (placeholder summary).",
    "mastery": [
      "Criterion A of SK-OD (placeholder).",
      "Criterion B of SK-OD (placeholder).",
      "Criterion C of SK-OD (placeholder)."
    ],
    "criticality": "routine",
    "recencyDays": 60,
    "supervisedRuns": 3,
    "prerequisites": []
  },
  {
    "id": "SK-DCW",
    "name": "Dry cell weight",
    "family": "qc",
    "summary": "Test skill SK-DCW (placeholder summary).",
    "mastery": [
      "Criterion A of SK-DCW (placeholder).",
      "Criterion B of SK-DCW (placeholder).",
      "Criterion C of SK-DCW (placeholder).",
      "Criterion D of SK-DCW (placeholder)."
    ],
    "criticality": "routine",
    "recencyDays": 120,
    "supervisedRuns": 2,
    "prerequisites": []
  },
  {
    "id": "SK-FACTOR",
    "name": "OD-to-DCW factor",
    "family": "qc",
    "summary": "Test skill SK-FACTOR (placeholder summary).",
    "mastery": [
      "Criterion A of SK-FACTOR (placeholder).",
      "Criterion B of SK-FACTOR (placeholder).",
      "Criterion C of SK-FACTOR (placeholder)."
    ],
    "criticality": "routine",
    "recencyDays": 365,
    "supervisedRuns": 1,
    "prerequisites": [
      "SK-OD",
      "SK-DCW"
    ]
  },
  {
    "id": "SK-LOG",
    "name": "Vessel log and batch sheet",
    "family": "records",
    "summary": "Test skill SK-LOG (placeholder summary).",
    "mastery": [
      "Criterion A of SK-LOG (placeholder).",
      "Criterion B of SK-LOG (placeholder).",
      "Criterion C of SK-LOG (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 90,
    "supervisedRuns": 2,
    "prerequisites": []
  },
  {
    "id": "SK-CAUSTIC",
    "name": "Caustic and acid handling",
    "family": "safety",
    "summary": "Test skill SK-CAUSTIC (placeholder summary).",
    "mastery": [
      "Criterion A of SK-CAUSTIC (placeholder).",
      "Criterion B of SK-CAUSTIC (placeholder).",
      "Criterion C of SK-CAUSTIC (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 180,
    "supervisedRuns": 1,
    "prerequisites": []
  },
  {
    "id": "SK-PRESS",
    "name": "Pressure and heat safety",
    "family": "safety",
    "summary": "Test skill SK-PRESS (placeholder summary).",
    "mastery": [
      "Criterion A of SK-PRESS (placeholder).",
      "Criterion B of SK-PRESS (placeholder).",
      "Criterion C of SK-PRESS (placeholder)."
    ],
    "criticality": "critical",
    "recencyDays": 180,
    "supervisedRuns": 1,
    "prerequisites": []
  }
];

export const TEST_SKILL_BY_ID: Record<string, Skill> = Object.fromEntries(TEST_SKILLS.map((s) => [s.id, s]));

/** The first protocol step each skill is tagged on, as the seed's protocols tagged them. */
export const TEST_STEP_FOR: Record<string, { ref: string; stepId: string }> = {
  "SK-ASEP": {
    "ref": "PR-SEED-01",
    "stepId": "s3"
  },
  "SK-STER": {
    "ref": "PR-CIP-01",
    "stepId": "c11"
  },
  "SK-HOLD": {
    "ref": "PR-CIP-01",
    "stepId": "c12"
  },
  "SK-ISOL": {
    "ref": "PR-CIP-01",
    "stepId": "c1"
  },
  "SK-CIP": {
    "ref": "PR-CIP-01",
    "stepId": "c3"
  },
  "SK-ASSY": {
    "ref": "PR-CIP-01",
    "stepId": "c2"
  },
  "SK-PROBE": {
    "ref": "PR-CIP-01",
    "stepId": "c10"
  },
  "SK-ENV": {
    "ref": "PR-SEED-01",
    "stepId": "s1"
  },
  "SK-OD": {
    "ref": "PR-SEED-01",
    "stepId": "s7"
  },
  "SK-DCW": {
    "ref": "PR-OD-01",
    "stepId": "o1"
  },
  "SK-FACTOR": {
    "ref": "PR-SEED-01",
    "stepId": "s13"
  },
  "SK-LOG": {
    "ref": "PR-SEED-01",
    "stepId": "s14"
  },
  "SK-CAUSTIC": {
    "ref": "PR-CIP-01",
    "stepId": "c4"
  },
  "SK-PRESS": {
    "ref": "PR-CIP-01",
    "stepId": "c1"
  }
};

/**
 * The three protocols the step tags name, as the store holds a protocol: the
 * placeholder steps of core/tests/fixtures/guild-projection.json, each with
 * the skills it is tagged with, and nothing else.
 */
export const TEST_PROTOCOLS: Protocol[] = guildProjection.protocols.map((p) => ({
  id: p.protocolId,
  title: p.title,
  category: 'sop',
  organisms: [],
  bsl: 1,
  purpose: '',
  currentVersion: p.version,
  provenanceNote: 'TEST FIXTURE',
  versions: [
    {
      version: p.version,
      baseBatch: { value: 1, unit: 'batch', label: 'a test batch' },
      materials: [],
      equipment: [],
      safety: [],
      steps: p.steps.map((st) => ({ id: st.stepId, text: st.text, skills: st.skills })),
      estMinutes: { active: 0, total: 0 },
      references: [],
    },
  ],
}));
