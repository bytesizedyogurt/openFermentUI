// The families Guild groups a lab's skills into. Vocabulary only: the skills
// themselves are the project's skill catalogue (lib/catalogues.ts, `Skill`),
// and none ship with the app (ADR-010). A skill's entry names its family by
// one of these ids; an entry may name another, which the screens show as it
// is written.

/** The six trunk families. Working names until the skills content pass. */
type SkillFamilyId = 'contamination' | 'vessel' | 'monitoring' | 'qc' | 'records' | 'safety';

interface SkillFamily {
  id: SkillFamilyId;
  name: string;
  /** Column-header form for the Matrix. */
  short: string;
}

export const FAMILIES: SkillFamily[] = [
  { id: 'contamination', name: 'Contamination control', short: 'Contamination' },
  { id: 'vessel', name: 'Vessel operation', short: 'Vessel' },
  { id: 'monitoring', name: 'Process monitoring', short: 'Monitoring' },
  { id: 'qc', name: 'Sampling and QC', short: 'Sampling and QC' },
  { id: 'records', name: 'Batch records', short: 'Records' },
  { id: 'safety', name: 'Safety and troubleshooting', short: 'Safety' },
];

const FAMILY_BY_ID: Record<string, SkillFamily> = Object.fromEntries(FAMILIES.map((f) => [f.id, f]));

/** A group the screens list skills under: one of the six families, or the skills naming another or none. */
interface FamilyGroup {
  id: string;
  name: string;
  short: string;
}

/** The group of skills whose entry names a family outside the six, or none. */
const OTHER_FAMILY: FamilyGroup = { id: '', name: 'Other skills', short: 'Other' };

/** The group a skill is listed under: its family where it is one of the six, else the other skills. */
export const familyOf = (s: { family?: string | null }): FamilyGroup => (s.family ? FAMILY_BY_ID[s.family] : undefined) ?? OTHER_FAMILY;

/** The six families, and the other skills after them when any skill names another family or none. */
export function familyGroups(skills: readonly { family?: string | null }[]): FamilyGroup[] {
  return skills.some((s) => familyOf(s) === OTHER_FAMILY) ? [...FAMILIES, OTHER_FAMILY] : [...FAMILIES];
}
