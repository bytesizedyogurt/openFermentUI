// The families Guild groups a lab's skills into. Vocabulary only: the skills
// themselves are a lab's own records (alpha 2.0 stage 2), and none ship with
// the app (ADR-010).
import type { SkillFamily } from './types';

export const FAMILIES: SkillFamily[] = [
  { id: 'contamination', name: 'Contamination control', short: 'Contamination' },
  { id: 'vessel', name: 'Vessel operation', short: 'Vessel' },
  { id: 'monitoring', name: 'Process monitoring', short: 'Monitoring' },
  { id: 'qc', name: 'Sampling and QC', short: 'Sampling and QC' },
  { id: 'records', name: 'Batch records', short: 'Records' },
  { id: 'safety', name: 'Safety and troubleshooting', short: 'Safety' },
];

export const FAMILY_BY_ID: Record<string, SkillFamily> = Object.fromEntries(FAMILIES.map((f) => [f.id, f]));
